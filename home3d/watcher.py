"""Zero-token print watcher: one pass per cron tick (``hermes cron ... --no-agent --script home3d_watch.py``).

No model calls. Each pass reads the printer status, detects transitions (pause, new HMS, offline), takes the
"done" photo at the last layers (before an auto-eject push), feeds the plate-clear state machine
(``eject.step``, with a camera plate check only when it asks for one), turns the resulting events into an
owner text (technical, with photo) and a family line (by name), logs human-needed moments, evaluates
upgrade proposals and tells the owner when the plate is clear and a manual job is waiting (it never starts
anything itself). State lives in ``store.kv('watcher')`` and starts over when the printer changes (backend, URL
or printer id: ``backend_key``).

Which workshop job is printing (decided once per print, remembered in ``job_memo``): when the printer manager
has a queue item in status ``printing``, its id decides (names are not compared: an archive reprint is named
by its archive title). No active store row for that id = nobody's job (no family message, no guess by name).
Only when the queue was read and no item is printing, the store's exact name match among workshop jobs still
queued or printing (never one whose own queue item still waits or failed before it started). A job never goes back
to ``printing`` once it left the active states. Jobs the store still calls ``printing``
whose queue item ended while the printer was idle or on another job (a dispatch that failed, a FINISH the
watcher never saw because the next job started at once) are closed from the queue (``reconcile``).

Light discipline: a pass switches the chamber light at most once (``snapshot_and_check`` gives the plate check
and the pass photo in one light cycle); no near-end photo for prints the workshop did not queue; plate
re-checks while a person is needed (or on an idle printer with a job waiting) back off 15 -> 30 -> 60 -> 120
min, at most ``MAX_RECHECKS`` per (printer state, job, queue head).

Family approval requests the hook refused (``Store.pending_approval_requests``) are told to the owner once, with
the exact ``/home3d approve`` command.

"Next job ready" names the first pending manual-start job the WORKSHOP queued; jobs queued elsewhere that
wait ahead of it are named in the same owner text (with ``/home3d approve start N jump``), and jobs queued
elsewhere are announced to the owner at most once per item. Plate notes carry a fresh lit photo and say the
camera *thinks* the plate is empty.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import eject, messages, notify, upgrades
from .backends import make_backend
from .backends.base import (ACTIVE_STATES, FAILED, FINISH, IDLE, OFFLINE, PAUSE, RUNNING, Backend, HMSError,
                            PlateCheck, PrinterStatus, QueueItem)
from .config import Person, Settings, data_dir, load_settings
from .gates import same_person
from .store import ACTIVE_JOB_STATES, Store

KV_KEY = "watcher"
LOG_FILE = "watcher.log"
LOCK_FILE = "watcher.lock"
OFFLINE_NOTIFY_S = 10 * 60  # tell the owner once the printer has been unreachable this long
IDLE_CHECK_S = 15 * 60  # idle printer, plate state unknown, manual job waiting: look this often
RECHECK_BACKOFF_S = (15 * 60, 30 * 60, 60 * 60, 120 * 60)  # waits between plate re-checks (last one repeats)
MAX_RECHECKS = 6  # plate checks per (kind, printer state, job, queue head) before the watcher stops looking
LAST_LAYER_PCT = 98.0  # "done" photo from this progress (or the last two layers) on
MEDIA_KEEP_S = 14 * 86400
LIGHT_ALERT_S = 6 * 3600  # "chamber light left on" owner alert at most this often
LIGHT_FLAG = "light_left_on"  # the backend's flag in Snapshot.note / PlateCheck.message
LIGHT_PENDING_KEY = "light_left_on:pending"  # runtime.LIGHT_PENDING_KEY: a hook/handler check left the light on
_CANCELLED_QUEUE = ("cancelled", "canceled", "skipped")
_ENDED_QUEUE = {"completed": ("finished", "done"), "failed": ("failed", "failed")}
_REQUEST_STATUS = {"printing": "printing", "finished": "done", "failed": "failed", "start_failed": "start_failed",
                   "cancelled": "cancelled"}
_EJECT_FLOW = ("finished", "cooling", "ejecting", "verifying")
_SUFFIXES = (".gcode.3mf", ".3mf", ".gcode", ".stl")
ROUTE_KEY = "_route"  # ctx key of the job's notify.Route (never rendered, never stored in an event)
NOT_TOLD_KEEP = 100  # jobs remembered as "the owner was told nobody else was" (once per job)
_FILAMENT_HMS = re.compile(r"^07[0-9A-F]{2}-[0-9A-F]{4}-0002-000[12]$")


# ---- helpers ----------------------------------------------------------------------------------
def _log(msg: str) -> None:
    try:
        path = data_dir() / LOG_FILE
        if path.exists() and path.stat().st_size > 1_000_000:
            path.write_text(path.read_text(encoding="utf-8", errors="replace")[-500_000:], encoding="utf-8")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg.rstrip()}\n")
    except OSError:
        pass


def _code(h: HMSError) -> str:
    return (h.code or "").replace("_", "-").upper()


def _is_filament(h: Optional[HMSError]) -> bool:
    if h is None:
        return False
    text = (h.message or "").lower()
    return "filament" in text or "run out" in text or "runout" in text or bool(_FILAMENT_HMS.match(_code(h)))


def pretty_job(name: str) -> str:
    """'gul_kutusu_v2.gcode.3mf' -> 'gul kutusu v2' (what the family sees)."""
    n = (name or "").strip()
    for suf in _SUFFIXES:
        if n.lower().endswith(suf):
            n = n[: -len(suf)]
            break
    return re.sub(r"\s+", " ", n.replace("_", " ")).strip()


def _backend_now(backend: Backend) -> float:
    fn = getattr(backend, "now", None)  # the simulator has a virtual clock
    if callable(fn):
        try:
            return float(fn())
        except Exception:
            pass
    return time.time()


def backend_key(backend: Backend) -> list:
    """Which printer the watcher state is about: ``[backend name, printer manager URL, printer id]``."""
    return [str(getattr(backend, "name", "") or ""), str(getattr(backend, "root", "") or "").rstrip("/"),
            str(getattr(backend, "printer_id", "") or "")]


def _try_lock():
    try:
        import fcntl
    except ImportError:
        return None
    try:
        fh = open(data_dir() / LOCK_FILE, "a+")
    except OSError:
        return None
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return False
    return fh


def _unlock(fh) -> None:
    if fh:
        try:
            import fcntl

            fcntl.flock(fh, fcntl.LOCK_UN)
        except Exception:
            pass
        fh.close()


@dataclass
class _Note:
    kind: str
    job: str = ""
    ctx: dict = field(default_factory=dict)
    family: bool = False
    owner_media: Optional[Path] = None
    family_media: Optional[Path] = None
    payload: dict = field(default_factory=dict)
    owner: bool = True  # False: only the person who asked hears about it (the one-line "started" notice)


# ---- one pass -----------------------------------------------------------------------------------
class _Pass:
    def __init__(self, settings: Settings, backend: Backend, store: Store, now: Optional[float],
                 deliver: bool, out_dir: Optional[Path]):
        self.s, self.backend, self.store, self.deliver = settings, backend, store, deliver
        self.default_media = out_dir is None
        self.out_dir = Path(out_dir) if out_dir else data_dir() / "media" / "watcher"
        self.now = float(now) if now is not None else _backend_now(backend)
        w = store.kv_get(KV_KEY) or {}
        self.w: dict = w if isinstance(w, dict) else {}
        key = backend_key(backend)
        old = self.w.get("backend_key")
        if old is not None and old != key:  # another printer (or the simulator): the old state is not about it
            _log(f"printer changed ({old} -> {key}): the watcher starts over")
            self.w = {}
        self.w["backend_key"] = key
        self.first = not self.w.get("initialized")
        self.notes: list[_Note] = []
        self.moments = 0
        self._fresh: Optional[Path] = None
        self._fresh_tried = False
        self._queue_items: Optional[list[QueueItem]] = None
        self._queue_tried = False
        self.gcode_push = bool(getattr(backend, "eject_in_gcode", False))  # push before FINISH (real A1)
        self._announced: list[int] = []  # approval request ids told to the owner this pass
        self._announced_via_outbox = False  # this pass's approval requests ride on its owner outbox record
        self._pass_deliveries: list = []  # final deliveries of this pass's records (no_target / dry run)
        self._pass_records = 0
        self._surfaced = ""  # the "notices could not be delivered" text when there is no owner chat
        self._st: Optional[PrinterStatus] = None  # this pass's printer status (None: not read / offline)
        self._back_online = False  # the printer manager answered again after an outage this pass

    # -- backend calls (never raise) --
    def _status(self) -> tuple[Optional[PrinterStatus], str]:
        try:
            return self.backend.status(), ""
        except Exception as exc:  # BackendError or anything unexpected
            return None, str(exc) or type(exc).__name__

    def _check_plate(self) -> Optional[PlateCheck]:
        """One lit plate check. The first one of a pass also takes this pass's photo in the same light cycle
        (``snapshot_and_check``), so a later ``_snapshot()`` does not switch the chamber light again."""
        check: Optional[PlateCheck] = None
        if not self._fresh_tried:
            self._fresh_tried = True
            try:
                self.out_dir.mkdir(parents=True, exist_ok=True)
                snap, check = self.backend.snapshot_and_check(self.out_dir)
                self._fresh = Path(snap.path) if snap and snap.path else None
                self._light_left_on(getattr(snap, "note", ""))
            except Exception as exc:
                _log(f"snapshot_and_check failed: {exc}")
                check = None
        if check is None:
            try:
                check = self.backend.check_plate()
            except Exception as exc:
                _log(f"check_plate failed: {exc}")
                return None
        self._light_left_on(getattr(check, "message", ""))
        return check

    def _light_left_on(self, text: Any) -> None:
        """The backend could not switch the chamber light off again after a check: tell the owner (owner only, at
        most once every ``LIGHT_ALERT_S``)."""
        if LIGHT_FLAG not in str(text or ""):
            return
        last = self.w.get("light_alert_ts")
        if isinstance(last, (int, float)) and self.now - float(last) < LIGHT_ALERT_S:
            return
        self.w["light_alert_ts"] = self.now
        ctx = {"persona": self.s.persona_name, "owner": self.s.owner_name}
        self._note(LIGHT_FLAG, self.w.get("job_name", ""), ctx, note=str(text)[:200])

    def _queue_all(self) -> Optional[list[QueueItem]]:
        """Every queue item, finished ones included, read at most once per pass (one GET on Bambuddy; the watcher
        never changes the queue); None when unreadable."""
        if not self._queue_tried:
            self._queue_tried = True
            try:
                self._queue_items = list(self.backend.queue(include_done=True))
            except Exception as exc:
                _log(f"queue failed: {exc}")
                self._queue_items = None
        return self._queue_items

    def _queue(self) -> Optional[list[QueueItem]]:
        """The live queue (pending / printing items, in the backend's order); None when unreadable."""
        items = self._queue_all()
        return None if items is None else [q for q in items if not q.is_done]

    def _queue_head(self) -> Any:
        """Id of the first pending item (None: nothing pending; "?" when the queue is unreadable)."""
        items = self._queue()
        if items is None:
            return "?"
        pending = [q for q in items if q.is_pending]
        return int(pending[0].id) if pending else None

    # -- light discipline: plate re-checks back off --
    def _recheck_ok(self, kind: str, st: PrinterStatus, job: str, base_ok: bool) -> bool:
        """May the pass run one more plate check of ``kind`` ("needs_human" / "idle")? ``base_ok`` is the plain
        rule (eject's 15-min re-check, the idle interval). After the first check the waits grow 15 -> 30 -> 60 ->
        120 min, and at most ``MAX_RECHECKS`` checks run while the printer state, the job and the queue head stay
        the same (any change starts over)."""
        if not base_ok:
            return False
        rec = self.w.get("recheck")
        rec = rec if isinstance(rec, dict) else {}
        head = self._queue_head()
        old_key = rec.get("key") if isinstance(rec.get("key"), list) else None
        if head == "?" and old_key and len(old_key) == 4:
            head = old_key[3]  # an unreadable queue is not a new queue head
        key = [kind, st.state, job or "", head]
        if old_key != key:
            rec = {"key": key, "n": 0, "ts": None}
            self.w["recheck"] = rec
        n = int(rec.get("n") or 0)
        if n >= MAX_RECHECKS:
            return False
        if n == 0:
            return True
        wait = RECHECK_BACKOFF_S[min(n - 1, len(RECHECK_BACKOFF_S) - 1)]
        return self.now - float(rec.get("ts") or 0) >= wait

    def _count_recheck(self) -> None:
        rec = self.w.get("recheck")
        if isinstance(rec, dict):
            rec["n"], rec["ts"] = int(rec.get("n") or 0) + 1, self.now

    def _snapshot(self) -> Optional[Path]:
        if not self._fresh_tried:
            self._fresh_tried = True
            try:
                self.out_dir.mkdir(parents=True, exist_ok=True)
                snap = self.backend.snapshot(self.out_dir, lit=True)
                self._fresh = Path(snap.path) if snap and snap.path else None
                self._light_left_on(getattr(snap, "note", ""))
            except Exception as exc:
                _log(f"snapshot failed: {exc}")
        return self._fresh

    def _part_photo(self, job: str, *, take: bool) -> Optional[Path]:
        """Photo of the finished part: the last-layer photo, else (``take``) a fresh one remembered for later."""
        path = self.w.get("photo_path") or ""
        if job and _same_name(self.w.get("photo_for_job") or "", job) and path and Path(path).is_file():
            return Path(path)
        if not take:
            return None
        fresh = self._snapshot()
        if fresh is not None and job:
            self.w["photo_for_job"], self.w["photo_path"] = job, str(fresh)
        return fresh

    # -- household lookups --
    def _lookup(self, name: str) -> tuple[Optional[dict], Optional[int]]:
        """(workshop job row, queue item id) of the print called ``name``. A queue item in status ``printing``
        decides by its id (an archive reprint carries the archive title, so names are not compared; with several,
        one whose name matches): a store row that is not queued / printing any more, or none at all, means not
        ours (None), never a guess by name. Only when the queue was read and nothing in it is printing: the store's
        exact name match among the workshop jobs still queued or printing, unless that job's own queue item is
        visibly still waiting, or failed without ever starting (then this print came from elsewhere: the printer
        screen, a phone app, an archive reprint)."""
        live = self._queue()
        if live is None:
            return None, None  # the queue is unreadable: never guess by name (the next pass looks again)
        printing = [q for q in live if str(q.status or "").strip().lower() == "printing"]
        if printing:
            q = next((x for x in printing if x.name and name and _same_name(x.name, name)), printing[0])
            try:
                row = self.store.get_job(int(q.id))
            except Exception:
                row = None
            return (row if row and row.get("state") in ACTIVE_JOB_STATES else None), int(q.id)
        try:
            row = self.store.job_by_name(name)
        except Exception:
            row = None
        if row and row.get("state") not in ACTIVE_JOB_STATES:
            row = None  # an old job of the same file (a reprint, a family copy) is not this print
        if row and row.get("queue_item_id") is not None:
            item = next((q for q in self._queue_all() or [] if int(q.id) == int(row["queue_item_id"])), None)
            if item is not None and (item.is_pending or (str(item.status or "").strip().lower() == "failed"
                                                         and not item.started_at)):
                row = None  # its own queue item still waits / never started: this print is not that job
        qid = row.get("queue_item_id") if row else None
        return row, (int(qid) if qid is not None else None)

    def _printing_item(self) -> Optional[int]:
        """Id of the queue item the printer manager says is printing (None: none, or the queue is unreadable)."""
        q = next((x for x in self._queue() or [] if str(x.status or "").strip().lower() == "printing"), None)
        return int(q.id) if q is not None else None

    def _remember_job(self, name: str, row: Optional[dict]) -> None:
        if self._queue() is None:
            return  # decided without the queue: not remembered, the next pass decides again
        qid = (row or {}).get("queue_item_id")
        self.w["job_memo"] = {"name": name, "qid": int(qid) if qid is not None else None}
        self.w["job_qid"] = self.w["job_memo"]["qid"]

    def _attribute(self, name: str) -> Optional[dict]:
        """A print just started: decide whose job it is and remember it for the rest of the print."""
        row = self._lookup(name)[0] if name else None
        self._remember_job(name, row)
        return row

    def _job(self, name: str) -> Optional[dict]:
        """The workshop job row of the print called ``name``: the decision remembered for that print (``job_memo``,
        None = not ours), else a lookup that is remembered from then on."""
        if not name:
            return None
        memo = self.w.get("job_memo")
        if isinstance(memo, dict) and memo.get("name") == name:
            if memo.get("qid") is None:
                return None
            try:
                return self.store.get_job(int(memo["qid"]))
            except Exception:
                return None
        qid = self.w.get("job_qid")  # state written before job_memo existed
        if qid is not None and name == self.w.get("started_job"):
            try:
                row = self.store.get_job(int(qid))
            except Exception:
                row = None
            if row:
                return row
        row = self._lookup(name)[0]
        self._remember_job(name, row)
        return row

    def _person(self, name: str) -> Optional[Person]:
        n = (name or "").strip().lower()
        if not n:
            return None
        for p in self.s.people():
            if n in (p.name.strip().lower(), (p.address_as or "").strip().lower()):
                return p
        return None

    def _ctx(self, job: str, jobrow: Optional[dict], status: Optional[PrinterStatus]) -> tuple[dict, bool]:
        """Message context + whether the family should hear about it (a known, non-owner requester)."""
        req: dict = {}
        if jobrow and jobrow.get("request_id"):
            try:
                req = self.store.get_request(int(jobrow["request_id"])) or {}
            except Exception:
                req = {}
        requester = (jobrow or {}).get("requester") or req.get("requester") or ""
        req_text = str(req.get("text") or "")  # family texts name the print by what was asked for
        person = self._person(requester)
        ctx: dict[str, Any] = {
            "persona": self.s.persona_name, "owner": self.s.owner_name, "job": pretty_job(job),
            "family_job": messages.short_text(req_text) or pretty_job(job),
            "queue_item_id": (jobrow or {}).get("queue_item_id"), "requester": requester,
            "address_as": person.address_as if person else "",
            "eject_planned": bool((jobrow or {}).get("eject_planned")),
        }
        if status is not None:
            ctx.update(progress=status.progress, layer=status.layer, total_layers=status.total_layers,
                       bed_temp=status.bed_temp, nozzle_temp=status.nozzle_temp)
            hms = status.blocking_hms
            if hms:
                ctx.update(hms_code=hms[0].code, hms_message=hms[0].message, wiki_url=hms[0].wiki_url)
        started = self.w.get("started_ts")
        if started and self.w.get("started_job") == job and 0 < self.now - float(started) < 7 * 86400:
            ctx["duration_min"] = (self.now - float(started)) / 60.0
        # who hears about it besides the owner: the group of the chat the request came from (notify.route_for)
        origin = req if (req.get("chat_id") or req.get("sender_id")) else (jobrow or {})
        route = notify.route_for(self.s, requester=requester, platform=str(origin.get("platform") or ""),
                                 chat_id=str(origin.get("chat_id") or ""), sender_id=str(origin.get("sender_id") or ""))
        ctx[ROUTE_KEY] = route
        # "family": a person who asked should hear (announced in their group, or the owner is told nobody was)
        return ctx, route.announce or route.why == "outsider"

    def _note(self, kind: str, job: str, ctx: dict, *, family: bool = False, owner_media: Optional[Path] = None,
              family_media: Optional[Path] = None, human: str = "", detail: str = "", owner: bool = True,
              **payload: Any) -> None:
        self.notes.append(_Note(kind, job, ctx, family, owner_media, family_media, payload, owner))
        if human:
            try:
                upgrades.log_moment(self.store, human, detail or kind, job_name=job, source="watcher")
                self.moments += 1
            except Exception as exc:
                _log(f"log_moment failed: {exc}")

    def _job_state(self, jobrow: Optional[dict], state: str, outcome: str = "") -> None:
        if not jobrow or jobrow.get("queue_item_id") is None:
            return
        if state == "printing" and jobrow.get("state") not in (None, *ACTIVE_JOB_STATES):
            return  # a job never goes back to printing once it left the active states
        if state in ("finished", "failed") and jobrow.get("state") == "cancelled":
            return  # stopped on purpose (home3d_stop): the printer's FAILED / IDLE is the stop, keep its outcome
        try:
            fields: dict[str, Any] = {"state": state}
            if state in ("finished", "failed"):
                fields.update(finished_ts=self.now, outcome=outcome or state)
            elif outcome:
                fields["outcome"] = outcome
            if state == "printing" and jobrow.get("started_ts") is None:
                fields["started_ts"] = self.now  # the start tool may already have recorded it
            self.store.upsert_job(int(jobrow["queue_item_id"]), **fields)
            jobrow.update(fields)
            rid = jobrow.get("request_id")
            req_status = _REQUEST_STATUS.get(state)
            if rid and req_status:
                self.store.update_request(int(rid), status=req_status, outcome=outcome or state)
        except Exception as exc:
            _log(f"job update failed: {exc}")

    # -- stages --
    def offline(self, reason: str) -> None:
        since = self.w.get("offline_since")
        self.w["online"] = False
        if since is None:
            self.w["offline_since"] = self.now
            self.store.add_event("offline", self.w.get("job_name", ""), {"reason": reason[:200]})
            return
        if not self.w.get("offline_notified") and self.now - float(since) >= OFFLINE_NOTIFY_S:
            self.w["offline_notified"] = True
            ctx = {"persona": self.s.persona_name, "owner": self.s.owner_name,
                   "offline_min": (self.now - float(since)) / 60.0, "reason": reason[:120]}
            self._note("offline", self.w.get("job_name", ""), ctx, reason=reason[:200])

    def online(self, st: Optional[PrinterStatus] = None) -> None:
        since = self.w.get("offline_since")
        if since is not None:
            self._back_online = True
            if self.w.get("offline_notified"):  # the owner was told it is unreachable: tell them it is back
                job = (st.job_name if st is not None else "") or ""
                ctx = {"persona": self.s.persona_name, "owner": self.s.owner_name,
                       "offline_min": max(0.0, (self.now - float(since)) / 60.0), "job": pretty_job(job)}
                if st is not None:
                    ctx.update(state=st.state, progress=st.progress if st.is_active else None)
                self._note("online", job, ctx, offline_since=since)
            self.w["offline_since"], self.w["offline_notified"] = None, False
        self.w["online"] = True

    def transitions(self, st: PrinterStatus) -> None:
        prev = self.w.get("state") or ""
        job = st.job_name or ""
        first = self.first
        blocking = st.blocking_hms
        if first:
            self.w["initialized"] = True
            self.w["hms_codes"] = [_code(h) for h in blocking]  # old errors are not news
            # A workshop job the start tool already recorded as printing that ended before this very first pass (a
            # watcher set up right after the start, the simulator's fast clock) is reported like any other end:
            # the plate state machine sees its FINISH / FAILED below. Anything else that already ended is old.
            row = self._job(job) if job and st.state in (FINISH, FAILED) else None
            started_here = bool(row and row.get("state") == "printing")
            if st.state in (FINISH, FAILED) and not started_here:  # ended before the watcher existed: wait for a
                self.w["plate_state"] = eject.PlateState(  # clear plate
                    "needs_human", job_name=job, finished_ts=self.now,
                    reason="found finished before the watcher started").to_dict()
            if st.state == FAILED and not started_here and not self._plate_confirmed(job, st):
                self._record_failure(job, "found failed before the watcher started")
        item_now = self._printing_item() if st.is_active else None
        item_before = self.w.get("print_item")
        next_item = item_now is not None and item_before is not None and item_now != item_before
        if st.is_active and (prev not in ACTIVE_STATES or (job and job != self.w.get("job_name")) or next_item):
            # a new print (also the same file again: the printer manager's printing item changed between passes)
            jobrow = self._attribute(job)
            self.w["print_item"] = item_now
            self._job_state(jobrow, "printing")
            self.w.update(started_ts=self._start_time(item_now, prev, first), started_job=job,
                          started_wall=time.time())
            self.w["ready_notified_for"] = []  # the plate was in use: a job still waiting is announced again
            try:  # the plate is in use by a new print: an earlier failure is settled
                self.store.clear_failure(f"a new print started: {job}"[:120])
            except Exception as exc:
                _log(f"clear_failure failed: {exc}")
            if self.w.get("photo_for_job") == job:  # keep it for a finish the watcher may report late (reconcile)
                self.w["prev_photo"] = {"job": job, "path": self.w.get("photo_path") or ""}
                self.w["photo_for_job"] = ""
            ctx, family = self._ctx(job, jobrow, st) if jobrow and not first else ({}, False)
            if family:  # the person who asked hears one short line; the owner started it and is not told again
                ctx.update(one_line=True, duration_min=st.remaining_min)
                self._note("started", job, ctx, family=True, owner=False,
                           queue_item_id=(jobrow or {}).get("queue_item_id"))
            else:
                self.store.add_event("started", job, {"state": st.state,
                                                      "queue_item_id": (jobrow or {}).get("queue_item_id"),
                                                      "silent": True})
        if (st.state == RUNNING and job and self.w.get("photo_for_job") != job and self._near_end(st)
                and self._job(job) is not None):  # the "done" photo is for workshop prints only (light discipline)
            photo = self._snapshot()
            if photo is not None:
                self.w["photo_for_job"], self.w["photo_path"] = job, str(photo)
        paused = False
        if prev == PAUSE and st.state in (RUNNING, FINISH) and not first:
            try:  # it runs again: the filament swap that held it is done
                self.store.resolve_human_needed(("filament_swap",), "the print resumed", job_name=job or None)
            except Exception as exc:
                _log(f"resolve_human_needed failed: {exc}")
        if st.state == PAUSE and prev != PAUSE:
            paused = True
            h = blocking[0] if blocking else None
            filament = _is_filament(h)
            jobrow = self._job(job)
            ctx, family = self._ctx(job, jobrow, st)
            ctx["filament"] = filament
            self._note("paused", job, ctx, family=family, owner_media=self._snapshot(),
                       human="filament_swap" if filament else "",
                       detail=f"{h.code} {h.message}".strip() if h else "paused without HMS",
                       hms=[_code(x) for x in blocking])
        codes = [_code(h) for h in blocking]
        new = [h for h in blocking if _code(h) not in (self.w.get("hms_codes") or [])]
        if new and not paused and not first and st.state != FAILED:  # the failed notice carries the HMS
            ctx, _ = self._ctx(job, self._job(job), st)
            ctx.update(hms_code=new[0].code, hms_message=new[0].message, wiki_url=new[0].wiki_url)
            self._note("hms", job, ctx, hms=[_code(h) for h in new])
        self.w["hms_codes"] = codes

    def _start_time(self, item_id: Optional[int], prev: str, first: bool) -> Optional[float]:
        """When the print that just showed up really started, on the backend's clock: the printer manager's
        ``started_at`` of the printing queue item; else now, when the previous pass saw the printer (idle, finished
        or on another print) so the start fell between two passes; else unknown (None: the first pass ever, an
        unknown state, right after an outage): the finish text then leaves the duration out."""
        if item_id is not None:
            item = next((q for q in self._queue_all() or [] if int(q.id) == int(item_id)), None)
            ts = _iso_ts(item.started_at) if item is not None else None
            if ts is not None and ts <= self.now + 300:
                return ts
        if first or self._back_online or prev not in (IDLE, FINISH, FAILED, *ACTIVE_STATES):
            return None
        return self.now

    @staticmethod
    def _near_end(st: PrinterStatus) -> bool:
        if st.total_layers and st.layer and st.layer >= st.total_layers - 1:
            return True
        return (st.progress or 0) >= LAST_LAYER_PCT

    def plate(self, st: PrinterStatus) -> None:
        ps = eject.PlateState.from_dict(self.w.get("plate_state"))
        job = st.job_name or ps.job_name
        jobrow = self._job(job)
        planned = bool((jobrow or {}).get("eject_planned"))
        cool = float(self.s.eject_cool_temp_c)
        if (ps.phase in ("needs_human", "verifying") and not st.is_active and self._plate_confirmed(job, st)):
            # the owner confirmed the plate (/home3d approve clear), e.g. over a camera doubt: settle it here,
            # without a camera check, so the next job can be announced. Nothing to tell anyone: the owner did it.
            ps.phase, ps.reason, ps.checks = "clear", "confirmed by the owner", 0
            self.w["plate_state"] = ps.to_dict()
            return
        want = eject.needs_plate_check(ps, st, self.now, cool, eject_in_gcode=self.gcode_push)
        if (not want and jobrow is None and ps.phase == "printing" and st.state == FINISH and self.gcode_push
                and st.connected):
            # a print the workshop did not queue: its eject plan is unknown (the household may slice with the
            # auto-eject preset, which pushes the part before FINISH). One look in the light cycle the finish photo
            # needs anyway, so the owner is not told to take off a part that is already gone.
            want = True
        if want and ps.phase == "needs_human":  # waiting for a person: re-checks back off (light discipline)
            want = self._recheck_ok("needs_human", st, ps.job_name, want)
            if want:
                self._count_recheck()
        check = self._check_plate() if want else None
        new, events = eject.step(ps, st, self.now, eject_planned=planned, plate=check, cool_temp_c=cool,
                                 eject_in_gcode=self.gcode_push)
        self.w["plate_state"] = new.to_dict()
        if self.first and set(events) <= {"plate_clear"}:
            return  # first pass: the plate of an old job is already clear, nothing to announce
        if events:
            self._plate_events(ps, new, events, st, jobrow)

    def _plate_events(self, prev: eject.PlateState, new: eject.PlateState, events: list[str],
                      st: PrinterStatus, jobrow: Optional[dict]) -> None:
        job = new.job_name or st.job_name
        ctx, family = self._ctx(job, jobrow, st)
        ctx["eject_planned"] = bool(new.eject_planned)
        ctx["eject_in_gcode"] = self.gcode_push
        last = new.last_check or {}
        ctx.update(reason=new.reason, plate_diff=last.get("difference_pct"))
        payload = {"phase": new.phase, "prev_phase": prev.phase, "events": list(events), "plate": last or None}
        ev = set(events)
        if "failed" in ev:
            stop = self._stop_info(job, jobrow)
            if stop is not None:  # stopped on purpose (home3d_stop): not a failure, but the plate still needs a look
                if jobrow and jobrow.get("state") in ACTIVE_JOB_STATES:  # the stop tool did not find it by name
                    why = f"stopped by {stop.get('who') or 'someone'}" + (f": {stop['reason']}" if stop.get("reason")
                                                                          else "")
                    self._job_state(jobrow, "cancelled", why[:200])
                self._record_failure(job, f"stopped by {stop.get('who') or 'someone'}")
                ctx.update(stopped_by=stop.get("who") or "", stop_reason=stop.get("reason") or "")
                self._note("stopped", job, ctx, owner_media=self._snapshot(), **payload)
            else:
                self._job_state(jobrow, "failed")
                self._record_failure(job, new.reason)
                self._note("failed", job, ctx, family=family, owner_media=self._snapshot(), human="failure_check",
                           detail=new.reason, **payload)
        if "finished" in ev:
            self._job_state(jobrow, "finished")
            pushed = self.gcode_push and new.eject_planned  # the plate is already empty when all went well
            part = self._part_photo(job, take=not pushed)
            if "plate_clear" in ev and new.eject_planned:
                # one owner message: the finish facts, then the camera's opinion (with the fresh plate photo)
                self._note("finished", job, dict(ctx, eject_result_follows=True), **payload)
                self._job_state(jobrow, "cleared", "ejected")
                self._note("finished_ejected", job, ctx, family=family, owner_media=self._snapshot(),
                           family_media=part, **payload)
                self._done_part(jobrow, job, ctx, "pushed_off", part)
            elif new.eject_planned and "plate_not_clear" not in ev:
                # family hears the eject outcome; the owner sees what the camera sees now (or the last layers)
                self._note("finished", job, ctx, owner_media=(self._fresh if pushed else None) or part, **payload)
                self._done_part(jobrow, job, ctx, "unknown", part)  # the camera's look decides
            elif jobrow is None:
                # not a workshop job (or nobody knows whose): its eject plan is unknown, so no "take it off" order
                # and no remove_part moment without evidence; the camera's look at FINISH decides the wording
                ctx.update(eject_unknown="foreign" if self._known_foreign(job) else "unknown",
                           camera_empty="plate_clear" in ev)
                self._note("finished", job, ctx, family=family, owner_media=part, family_media=part,
                           human="remove_part" if last.get("is_empty") is False else "",
                           detail="part left on the plate", **payload)
            else:
                self._note("finished", job, ctx, family=family, owner_media=part, family_media=part,
                           human="remove_part" if "plate_not_clear" in ev else "",
                           detail="no auto-eject planned", **payload)
                self._done_part(jobrow, job, ctx, "on_plate", part)
            return
        if "plate_clear" in ev:
            self._job_state(jobrow, "cleared", "ejected" if prev.phase in _EJECT_FLOW else "removed")
            if prev.phase in _EJECT_FLOW:
                part = self._part_photo(job, take=False)
                self._note("finished_ejected", job, ctx, family=family, owner_media=self._snapshot(),
                           family_media=part, **payload)
                self._done_part(jobrow, job, ctx, "pushed_off", part)
            else:
                self._plate_emptied()
                photo = self._snapshot()
                ctx.update(photo=photo is not None, confirm_first=self._confirm_first(st))
                self._note("plate_clear", job, ctx, owner_media=photo, **payload)
        if "plate_not_clear" in ev:
            self._note("plate_not_clear", job, ctx, family=family, owner_media=self._snapshot(),
                       human="remove_part", detail=new.reason, **payload)
            self._done_part(jobrow, job, ctx, "on_plate")
        if "eject_unverified" in ev:
            self._note("eject_unverified", job, ctx, family=family, owner_media=self._snapshot(),
                       human="camera_check", detail=new.reason, **payload)

    def _done_part(self, jobrow: Optional[dict], job: str, ctx: dict, left_plate: str,
                   photo: Optional[Path] = None) -> None:
        """Record a workshop job's finished part in the done box (who it is for, the group told, the photo, how it
        left the plate). Prints that are not workshop jobs are not recorded. Never raises."""
        if not jobrow or jobrow.get("queue_item_id") is None:
            return
        route = ctx.get(ROUTE_KEY)
        try:
            self.store.record_done_part(int(jobrow["queue_item_id"]), job_name=pretty_job(job),
                                        title=str(ctx.get("family_job") or pretty_job(job)),
                                        requester=str(jobrow.get("requester") or ""),
                                        group=route.group if isinstance(route, notify.Route) else "",
                                        photo=str(photo or ""), left_plate=left_plate,
                                        request_id=jobrow.get("request_id"))
        except Exception as exc:
            _log(f"record_done_part failed: {exc}")

    def _plate_emptied(self) -> None:
        """The camera saw the plate empty after a part waited on it: a person took it off (done box, open
        human-needed moments about the plate)."""
        try:
            self.store.plate_emptied()
            self.store.resolve_human_needed(("remove_part", "camera_check", "failure_check"),
                                            "the camera saw the plate empty")
        except Exception as exc:
            _log(f"plate_emptied failed: {exc}")

    def _known_foreign(self, job: str) -> bool:
        """This print was decided "not ours" when it started (``job_memo`` with no queue id)."""
        memo = self.w.get("job_memo")
        return isinstance(memo, dict) and memo.get("name") == job and memo.get("qid") is None

    def _stop_info(self, job: str, jobrow: Optional[dict]) -> Optional[dict]:
        """``{"who", "reason"}`` when this print ended because someone stopped it (``home3d_stop`` records a
        ``stop_request`` event and closes a workshop job as cancelled), else None."""
        cancelled = bool(jobrow and jobrow.get("state") == "cancelled"
                         and str(jobrow.get("outcome") or "").startswith("stopped by"))
        since = self.w.get("started_wall")
        if not isinstance(since, (int, float)):  # the watcher did not see it start: since its last pass, roughly
            last = self.w.get("updated")
            since = float(last) - OFFLINE_NOTIFY_S if isinstance(last, (int, float)) else None
        try:
            rows = self.store.events(limit=20, kind="stop_request")
        except Exception:
            rows = []
        for r in rows:
            if since is not None and float(r.get("ts") or 0) < float(since) - 60:
                continue
            name = str(r.get("job_name") or "")
            # a stop sent while the status could not be read carries no name: it counts only for a recent window
            if not (cancelled or _same_name(name, job) or (not name and since is not None)):
                continue
            try:
                p = json.loads(r.get("payload") or "{}")
            except ValueError:
                p = {}
            return {"who": str(p.get("who") or ""), "reason": str(p.get("reason") or "")}
        if cancelled:
            out = str(jobrow.get("outcome") or "")[len("stopped by "):]
            who, _, reason = out.partition(": ")
            return {"who": who.strip(), "reason": reason.strip()}
        return None

    def _record_failure(self, job: str, reason: str = "") -> None:
        """Remember a failed print until a person confirms the plate (survives a power cycle / IDLE)."""
        try:
            self.store.record_failure(job, "watcher", reason)
        except Exception as exc:
            _log(f"record_failure failed: {exc}")

    def _plate_confirmed(self, job: str, st: Optional[PrinterStatus] = None) -> bool:
        try:
            if st is not None:
                return bool(self.store.plate_confirmed(job or "", status=st))
            return bool(self.store.plate_confirmed(job or ""))
        except Exception:
            return False

    def _confirm_first(self, st: PrinterStatus) -> bool:
        """The last print failed and nobody confirmed its plate yet (the start gate will want that first): the
        printer still says FAILED, or the store remembers a failure the printer has forgotten (power cycle,
        cancel to IDLE)."""
        try:
            if self.store.unconfirmed_failure() is not None:
                return True
        except Exception:
            return True
        return st.state == FAILED and not self._plate_confirmed(st.job_name or "", st)

    def _plate_ready(self, st: PrinterStatus) -> bool:
        """The camera thinks the plate is empty (plate phase "clear"; an idle printer with an unknown plate is
        checked every ``IDLE_CHECK_S``)."""
        ps = eject.PlateState.from_dict(self.w.get("plate_state"))
        if ps.phase == "clear":
            return True
        if ps.phase != "idle" or st.state != IDLE:
            return False
        base_ok = self.now - float(self.w.get("idle_check_ts") or 0) >= IDLE_CHECK_S
        if not self._recheck_ok("idle", st, "", base_ok):
            return False
        self.w["idle_check_ts"] = self.now
        self._count_recheck()
        check = self._check_plate()
        if not _says_empty(check):
            return False
        ps.phase = "clear"
        ps.last_check = {"ts": self.now, "is_empty": True, "difference_pct": check.difference_pct,
                         "confidence": check.confidence, "message": check.message,
                         "needs_calibration": check.needs_calibration, "light_ok": getattr(check, "light_ok", None)}
        self.w["plate_state"] = ps.to_dict()
        return True

    def ready_next(self, st: PrinterStatus) -> None:
        if st.is_active or st.state not in (IDLE, FINISH, FAILED) or st.blocking_hms:
            return
        items = self._queue()
        if items is None:
            return
        pending = [q for q in items if q.is_pending]
        self.w["pending"] = len(pending)
        if not pending or not pending[0].manual_start:
            return  # nothing waiting, or the printer manager starts it by itself
        try:
            ours = {int(i) for i in self.store.active_job_ids()}
        except Exception as exc:
            _log(f"active_job_ids failed: {exc}")
            return
        notified = _ids(self.w.get("ready_notified_for"))
        foreign_told = _ids(self.w.get("foreign_notified_for"))
        nxt = next((q for q in pending if q.id in ours and q.manual_start), None)
        announce = nxt is not None and nxt.id not in notified
        ahead = [q for q in pending[: pending.index(nxt)] if q.id not in ours] if nxt is not None else []
        foreign = [q for q in pending if q.id not in ours and q.id not in foreign_told
                   and not (announce and q in ahead)]
        if not announce and not foreign:
            return
        if not self._plate_ready(st):
            return
        ps = eject.PlateState.from_dict(self.w.get("plate_state"))
        diff = (ps.last_check or {}).get("difference_pct")
        photo = self._snapshot()
        if announce:
            jobrow = None
            try:
                jobrow = self.store.get_job(nxt.id)
            except Exception:
                pass
            name = nxt.name or (jobrow or {}).get("name") or ""
            ctx, _ = self._ctx(name, jobrow, None)
            said = {n.kind for n in self.notes}  # one owner message: the plate note above already says these
            confirm_said = any(n.kind == "plate_clear" and n.ctx.get("confirm_first") for n in self.notes)
            ctx.update(next_job=pretty_job(name), next_id=nxt.id, plate_diff=diff, photo=photo is not None,
                       ahead=[{"id": q.id, "name": pretty_job(q.name)} for q in ahead],
                       confirm_first=self._confirm_first(st) and not confirm_said, confirm_said=confirm_said,
                       camera_said=bool(said & {"plate_clear", "finished_ejected"}),
                       awaiting_clear=st.awaiting_plate_clear is True)
            self._note("ready_next", name, ctx, owner_media=photo, queue_item_id=nxt.id,
                       ahead_ids=[q.id for q in ahead])
            self.w["ready_notified_for"] = (notified + [nxt.id])[-50:]
            foreign_told += [q.id for q in ahead]
        if foreign:
            ctx = {"persona": self.s.persona_name, "owner": self.s.owner_name, "plate_diff": diff,
                   "foreign": [{"id": q.id, "name": pretty_job(q.name), "since": str(q.created_at or "")[:10]}
                               for q in foreign]}
            self._note("queue_foreign", "", ctx, owner_media=None if announce else photo,
                       queue_item_ids=[q.id for q in foreign])
            foreign_told += [q.id for q in foreign]
        self.w["foreign_notified_for"] = foreign_told[-100:]

    def stale_jobs(self) -> None:
        """Workshop jobs still "queued" whose queue item was removed or cancelled in the printer manager's UI stop
        counting as ours (the jump check, "next job ready"), so a reused queue id is never mistaken for one; an item
        that already completed / failed there is closed the same way. An item must be missing on two passes in a
        row: one odd queue read never cancels anything."""
        try:
            queued = {int(j["queue_item_id"]): j for j in self.store.jobs(state="queued", limit=200)
                      if j.get("queue_item_id") is not None}
        except Exception as exc:
            _log(f"jobs(queued) failed: {exc}")
            return
        live = self._queue()
        if live is None:
            return
        unseen = set(queued) - {int(q.id) for q in live}
        if not unseen:
            self.w["missing_jobs"] = []
            return
        every = {int(q.id): q for q in self._queue_all() or []}
        before = set(_ids(self.w.get("missing_jobs")))
        missing: list[int] = []
        for qid in sorted(unseen):
            item = every.get(qid)
            status = str(item.status or "").strip().lower() if item is not None else ""
            if item is None and qid not in before:
                missing.append(qid)
                continue
            if item is not None and status == "failed" and not item.started_at:
                self._start_failed(queued[qid], item)  # started elsewhere, but the printer never began
                continue
            if item is None or status in _CANCELLED_QUEUE:
                state, req_status = "cancelled", "cancelled"
            elif status in _ENDED_QUEUE:  # it printed while nobody watched (started in the printer manager)
                state, req_status = _ENDED_QUEUE[status]
            else:
                continue  # still pending / printing under another status: leave it
            outcome = "removed from the printer queue" if item is None else f"{status} in the printer queue"
            try:
                self.store.upsert_job(qid, state=state, outcome=outcome)
                rid = queued[qid].get("request_id")
                if rid:
                    self.store.update_request(int(rid), status=req_status, outcome=outcome)
            except Exception as exc:
                _log(f"close stale job {qid} failed: {exc}")
        self.w["missing_jobs"] = missing[-100:]

    def reconcile(self, st: PrinterStatus) -> None:
        """Workshop jobs the store still calls ``printing`` whose queue item already ended while the printer is idle
        or on another job: a FINISH the watcher never saw (the next job started at once) gets its finished / failed
        notice (with the stored last-layer photo) and is closed; an item that failed without ever starting is a
        start that did not happen (owner notice with the printer manager's error). The plate state machine keeps
        every print that is still on the printer."""
        try:
            printing = [j for j in self.store.jobs(state="printing", limit=50) if j.get("queue_item_id") is not None]
        except Exception as exc:
            _log(f"jobs(printing) failed: {exc}")
            return
        if not printing:
            return
        every = self._queue_all()
        if every is None:
            return
        by_id = {int(q.id): q for q in every}
        for job in printing:
            try:
                self._reconcile_one(job, by_id.get(int(job["queue_item_id"])), st)
            except Exception as exc:  # one odd row never stops the pass
                _log(f"reconcile job {job.get('queue_item_id')} failed: {exc}")

    def _reconcile_one(self, job: dict, item: Optional[QueueItem], st: PrinterStatus) -> None:
        qid = int(job["queue_item_id"])
        status = str(item.status or "").strip().lower() if item is not None else ""
        if item is None or not item.is_done or self._on_printer(qid, job, st):
            return  # still waiting / printing, or the plate state machine follows it
        if status == "failed" and not item.started_at:
            self._start_failed(job, item)
        elif status in ("completed", "failed"):
            self._unseen_end(job, item, status, st)
        else:  # cancelled / skipped in the printer manager
            self._job_state(job, "cancelled", f"{status} in the printer queue")

    def _on_printer(self, qid: int, job: dict, st: PrinterStatus) -> bool:
        """Is the printer (still) showing this workshop job? Unknown states count as yes (nothing is closed)."""
        if st.state == IDLE:
            return False
        if st.state not in (*ACTIVE_STATES, FINISH, FAILED):
            return True
        memo = self.w.get("job_memo")
        if isinstance(memo, dict) and st.job_name and memo.get("name") == st.job_name:
            return memo.get("qid") is not None and int(memo["qid"]) == qid
        return bool(st.job_name) and _same_name(job.get("name") or "", st.job_name)

    def _start_failed(self, job: dict, item: QueueItem) -> None:
        """The printer manager gave up on the item before it started: tell the owner why, close job + request."""
        name = job.get("name") or item.name or ""
        err = str(item.error_message or "").strip()
        ctx, _ = self._ctx(name, job, None)
        ctx.update(error=err, queue_item_id=int(item.id))
        self._job_state(job, "start_failed", ("start did not happen: " + (err or "failed in the printer queue"))[:200])
        self._note("start_failed", name, ctx, queue_item_id=int(item.id), error=err[:300])

    def _unseen_end(self, job: dict, item: QueueItem, status: str, st: PrinterStatus) -> None:
        """Our print ended (completed / failed in the queue) without the watcher seeing its end."""
        name = job.get("name") or item.name or ""
        idle = st.state == IDLE
        ctx, family = self._ctx(name, job, None)
        ctx["missed_end"] = "idle" if idle else "busy"
        photo = self._part_photo(name, take=False)
        prev = self.w.get("prev_photo")
        if photo is None and isinstance(prev, dict) and _same_name(str(prev.get("job") or ""), name) \
                and prev.get("path") and Path(str(prev["path"])).is_file():
            photo = Path(str(prev["path"]))  # the same file started again right away: its last-layer photo
        if idle:  # the plate was never looked at: the next start waits for a camera check (or a person)
            planned = bool(job.get("eject_planned"))
            reason = ("print failed while the watcher was not looking: check the printer and the plate"
                      if status == "failed" else "the print ended while the watcher was not looking: check the plate")
            self.w["plate_state"] = eject.PlateState("needs_human", job_name=_stem(name), eject_planned=planned,
                                                     finished_ts=self.now, reason=reason).to_dict()
        if status == "completed":
            self._job_state(job, "finished", "finished (the watcher did not see the end)")
            self._note("finished", name, ctx, family=family, owner_media=photo, family_media=photo,
                       queue_item_id=int(item.id), missed_end=ctx["missed_end"])
            self._done_part(job, name, ctx, "unknown", photo)  # nobody saw how it left the plate
        else:
            self._job_state(job, "failed", "failed in the printer queue (the watcher did not see the end)")
            if idle:
                self._record_failure(_stem(name), "failed in the printer queue")
            self._note("failed", name, ctx, family=family, owner_media=self._snapshot() if idle else photo,
                       human="failure_check", detail="failed in the printer queue", queue_item_id=int(item.id),
                       missed_end=ctx["missed_end"])

    def approvals(self) -> None:
        """Household requests the hook refused (start / resume / clear): tell the owner each one once, with the
        exact command. A start request whose queue item is no longer waiting is dropped without a word."""
        fn = getattr(self.store, "pending_approval_requests", None)
        if not callable(fn):
            return
        try:
            rows = list(fn() or [])
        except Exception as exc:
            _log(f"pending_approval_requests failed: {exc}")
            return
        try:  # a request whose owner message is still waiting in the outbox is not written a second time
            waiting = self.store.outbox_open_refs("approval_request_ids")
        except Exception:
            waiting = set()
        for r in rows:
            try:
                rid = int(r.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            if rid in waiting:
                continue
            try:
                self._approval_note(rid, r)
            except Exception as exc:  # one odd row never stops the pass
                _log(f"approval request {rid} failed: {exc}")

    def _approval_note(self, rid: int, r: dict) -> None:
        action = str(r.get("action") or "start").strip().lower()
        action = {"home3d_start": "start", "clear_plate": "clear", "confirm_clear": "clear"}.get(action, action)
        who = self._display_name(str(r.get("who") or r.get("requester") or ""))
        raw_qid = r.get("queue_item_id", r.get("target"))
        qid = int(raw_qid) if str(raw_qid or "").strip().isdigit() else None
        jobrow: Optional[dict] = None
        item: Optional[QueueItem] = None
        items = self._queue() if action == "start" else None
        if qid is not None:
            try:
                jobrow = self.store.get_job(qid)
            except Exception:
                jobrow = None
            item = next((q for q in items or [] if int(q.id) == qid), None)
        if action == "start" and items is not None and (item is None or not item.is_pending):
            self._announced.append(rid)  # started, removed or finished meanwhile: nothing left to approve
            return
        ready = next((n for n in self.notes if n.kind == "ready_next" and qid is not None
                      and n.payload.get("queue_item_id") == qid), None)
        if ready is not None:  # this pass already says "ready, start it with ..." for the same job: one message
            ready.ctx["asked_by"] = who
            self._announced.append(rid)
            return
        name = (jobrow or {}).get("name") or (item.name if item else "")
        if action != "start" and not name:
            name = str(self.w.get("job_name") or "")
        ctx, _ = self._ctx(name, jobrow, None)
        meta: dict = {}
        if jobrow and jobrow.get("sliced_file_id") is not None:
            try:
                meta = self.store.kv_get(f"slice:{jobrow['sliced_file_id']}") or {}
            except Exception:
                meta = {}
        minutes = (item.print_time_s / 60.0) if item and item.print_time_s else (meta or {}).get("print_time_min")
        ahead: list[dict] = []
        if item is not None and items is not None:
            try:  # whose each workshop job is: another person's workshop job ahead needs jump too (start gate)
                whose = {int(k): str(v or "") for k, v in self.store.active_job_requesters().items()}
            except Exception:
                whose = {}
            mine = whose.get(int(item.id), "")
            pending = [q for q in items if q.is_pending]
            for q in (pending[: pending.index(item)] if item in pending else []):
                if q.id in whose and same_person(whose[q.id], mine, self.s.owner_name):
                    continue
                other = (whose[q.id].strip() or self.s.owner_name) if q.id in whose else ""
                ahead.append({"id": q.id, "name": pretty_job(q.name), "who": other})
        ctx.update(action=action, who=who, queue_item_id=qid, duration_min=minutes,
                   grams=(meta or {}).get("grams"), ahead=ahead)
        st = self._st
        if action == "resume" and st is not None and st.connected and st.state != PAUSE:
            ctx["not_paused"] = st.state  # resumed on the printer meanwhile, or it ended: nothing to approve
        self._note("approval_request", name, ctx, approval_request_id=rid, action=action, who=who)
        self._announced.append(rid)

    def _display_name(self, who: str) -> str:
        """A household member's name for the owner text ("Mum"), from a name or a sender id."""
        w = who.strip()
        for p in self.s.people():
            if w and w.lower() in {str(p.id or "").strip().lower(), p.name.strip().lower(),
                                    (p.address_as or "").strip().lower()}:
                return p.name
        return w

    def mark_announced(self) -> None:
        fn = getattr(self.store, "mark_approval_request_announced", None)
        if not callable(fn):
            return
        for rid in self._announced:
            try:
                fn(rid)
            except Exception as exc:
                _log(f"mark_approval_request_announced({rid}) failed: {exc}")

    def light_pending(self) -> None:
        """A plate check made by the hook or a tool could not switch the chamber light off again: tell the owner."""
        try:
            rec = self.store.kv_get(LIGHT_PENDING_KEY)
            if rec:
                self.store.kv_delete(LIGHT_PENDING_KEY)
        except Exception:
            return
        if isinstance(rec, dict):
            self._light_left_on(str(rec.get("note") or LIGHT_FLAG))

    def proposals(self) -> None:
        if not self.moments:
            return
        try:
            created = upgrades.evaluate(self.store, self.s)
        except Exception as exc:
            _log(f"upgrades.evaluate failed: {exc}")
            return
        for u in created:
            ctx = {"persona": self.s.persona_name, "owner": self.s.owner_name, "upgrade_id": u.get("id"),
                   "upgrade_title": u.get("title"), "upgrade_label": u.get("label"), "evidence": u.get("evidence"),
                   "window_days": u.get("window_days"), "model_ref": u.get("model_ref")}
            self._note("upgrade_proposed", "", ctx, upgrade=u)

    def remember(self, st: PrinterStatus) -> None:
        self.w.update(state=st.state, job_name=st.job_name, progress=st.progress, layer=st.layer,
                      total_layers=st.total_layers, remaining_min=st.remaining_min, bed_temp=st.bed_temp,
                      nozzle_temp=st.nozzle_temp, printer_name=st.printer_name)

    # -- delivery --
    def deliver_notes(self) -> list[dict]:
        """Turn this pass's notes into outbox records (``notify.enqueue``): ONE owner message (its texts merged, the
        first photo) and one message per group chat a requester is told in (that group's language and tone). The
        records are sent by ``deliver`` (``notify.flush``); an event counts as told only once its record went out."""
        if not self.notes:
            return []
        lang = self.s.language
        results: list[dict] = []
        owner_parts: list[str] = []
        owner_events: list[int] = []
        owner_media: Optional[Path] = None
        buckets: dict[tuple, dict] = {}  # (audience, language, target, group) -> parts, media, events, who
        not_told = [str(x) for x in self.w.get("not_told_for") or []]
        for n in self.notes:
            route = n.ctx.get(ROUTE_KEY)
            ctx = {k: v for k, v in n.ctx.items() if k != ROUTE_KEY}
            owner_text = messages.render(n.kind, "owner", lang, **ctx) if n.owner else ""
            family_text, group = "", ""
            if n.family and isinstance(route, notify.Route) and route.announce:
                family_text = messages.render(n.kind, route.audience, route.language, **ctx)
                group = route.group
            elif n.family and isinstance(route, notify.Route) and route.why == "outsider":
                key = str(ctx.get("queue_item_id") or n.job)
                if key not in not_told and messages.render(n.kind, "family", lang, **ctx):
                    not_told.append(key)  # once per job: the owner learns nobody else was told
                    line = messages.render("requester_not_told", "owner", lang, **ctx)
                    owner_text = "\n".join(x for x in (owner_text, line) if x)
            payload = {k: v for k, v in ctx.items() if v not in (None, "")}
            payload.update(n.payload)
            payload.update(owner_text=owner_text, family_text=family_text, group=group)
            try:
                event_id = self.store.add_event(n.kind, n.job, _jsonable(payload))
            except Exception as exc:
                _log(f"add_event failed: {exc}")
                event_id = None
            if owner_text:
                owner_parts.append(owner_text)
                owner_media = owner_media or n.owner_media
                if event_id is not None:
                    owner_events.append(event_id)
            if family_text:
                b = buckets.setdefault((route.audience, route.language, route.target, route.group),
                                       {"parts": [], "media": None, "events": [], "job": n.job,
                                        "requester": str(ctx.get("requester") or ""), "kinds": []})
                b["parts"].append(family_text)
                b["media"] = b["media"] or n.family_media
                b["kinds"].append(n.kind)
                if event_id is not None:
                    b["events"].append(event_id)
            results.append({"event_id": event_id, "kind": n.kind, "job": n.job, "owner_text": owner_text,
                            "family_text": family_text, "group": group, "owner_media": str(n.owner_media or ""),
                            "family_media": str(n.family_media or "") if family_text else "", "deliveries": []})
        self.w["not_told_for"] = not_told[-NOT_TOLD_KEEP:]
        dry = not self.deliver
        records: list[tuple[Optional[notify.Delivery], Any]] = []
        try:
            if owner_parts:
                # the approval requests of this pass count as told once THIS message went out (notify._settle)
                d = notify.enqueue(self.s, self.store, audience="owner", target=self.s.owner_target,
                                   text="\n\n".join(owner_parts), media=owner_media,
                                   kinds=[n.kind for n in self.notes if n.owner], job_name=self.notes[0].job,
                                   event_ids=owner_events, approval_request_ids=self._announced, now=self.now,
                                   dry_run=dry)
                self._announced_via_outbox = True
                records.append((d, "owner"))
            for (audience, language, target, group), b in buckets.items():
                d = notify.enqueue(self.s, self.store, audience=audience, target=target, text="\n\n".join(b["parts"]),
                                   media=b["media"], kinds=b["kinds"], job_name=b["job"], requester=b["requester"],
                                   group=group, event_ids=b["events"], now=self.now, dry_run=dry)
                records.append((d, audience))
        except Exception as exc:
            _log(f"outbox write failed: {exc}")
        self._pass_deliveries = [d for d, _ in records if d is not None]
        self._pass_records = len(records)
        return results

    def send_outbox(self, results: list[dict]) -> None:
        """Send what is due in the outbox (this pass's records and earlier ones waiting for a retry), bounded by
        ``send_budget_s``; what does not fit goes out on the next pass. Attaches this pass's deliveries."""
        report = notify.flush(self.s, self.store, now=self.now, dry_run=not self.deliver)
        for d in report.deliveries:
            if d.status in (notify.PENDING, notify.FAILED):
                _log(f"delivery to {d.audience} {d.target} failed (attempt {d.attempts}): {d.error}")
        if report.gave_up:
            _log(f"{len(report.gave_up)} notice(s) given up after every retry")
        mine = list(self._pass_deliveries) + [d for d in report.deliveries if d.record_id is not None]
        done = [d.to_dict() for d in mine]
        for r in results:
            r["deliveries"] = done
        if report.surfaced_text and not str(self.s.owner_target or "").strip():
            self._surfaced = report.surfaced_text  # no owner chat: the cron output carries it

    def prune_media(self) -> None:
        if not self.default_media or not self.out_dir.is_dir():
            return
        cutoff = time.time() - MEDIA_KEEP_S
        keep = {self.w.get("photo_path") or "", str((self.w.get("prev_photo") or {}).get("path") or "")}
        for p in self.out_dir.iterdir():
            try:
                if p.is_file() and str(p) not in keep and p.stat().st_mtime < cutoff:
                    p.unlink()
            except OSError:
                pass

    def run(self) -> list[dict]:
        st, err = self._status()
        if st is None:
            self._queue_tried = True  # the printer manager did not answer: no second slow call this pass
        if st is None or st.state == OFFLINE or not st.connected:
            self.offline(err or "printer offline")
        else:
            self._st = st
            self.online(st)
            self.light_pending()
            self.transitions(st)
            self.plate(st)
            self.reconcile(st)
            self.stale_jobs()
            self.ready_next(st)
            self.remember(st)
        self.approvals()
        self.proposals()
        results = self.deliver_notes()
        if not self._announced_via_outbox:
            self.mark_announced()  # nothing to tell the owner about them (started / removed meanwhile)
        self.send_outbox(results)
        if self._surfaced:
            results.append({"event_id": None, "kind": notify.FAILURE_KIND, "job": "", "owner_text": self._surfaced,
                            "family_text": "", "group": "", "owner_media": "", "family_media": "",
                            "deliveries": []})
        self.w.update(now=self.now, updated=time.time())
        self.store.kv_set(KV_KEY, _jsonable(self.w))
        self.prune_media()
        return results


def _says_empty(check: Optional[PlateCheck]) -> bool:
    """A plate check that explicitly says empty and was not taken in the dark (``light_ok`` False)."""
    return check is not None and check.is_empty is True and getattr(check, "light_ok", None) is not False


def _same_name(a: str, b: str) -> bool:
    """Queue item / job name vs printer job name ("gul_kutusu.gcode.3mf" == "gul kutusu"); both must be set."""
    x, y = pretty_job(a).casefold(), pretty_job(b).casefold()
    return bool(x) and x == y


def _stem(name: str) -> str:
    """'towel_hook.gcode.3mf' -> 'towel_hook' (how the printer reports the job name)."""
    n = (name or "").strip()
    for suf in _SUFFIXES:
        if n.lower().endswith(suf):
            return n[: -len(suf)]
    return n


def _iso_ts(text: Any) -> Optional[float]:
    """'2026-11-07T23:18:28.123Z' (Bambuddy / simulator ``started_at``) -> epoch seconds; naive text is UTC."""
    raw = str(text or "").strip()
    if not raw:
        return None
    from datetime import datetime, timezone

    try:
        d = datetime.fromisoformat(raw.replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def _ids(raw: Any) -> list[int]:
    return [int(i) for i in (raw or []) if str(i).lstrip("-").isdigit()]


def _jsonable(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    if isinstance(v, Path):
        return str(v)
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    try:
        from .backends.base import to_jsonable

        return to_jsonable(v)
    except Exception:
        return str(v)


def run_once(settings: Settings, backend: Backend, store: Store, *, now: Optional[float] = None,
             deliver: bool = True, out_dir: Optional[Path] = None) -> list[dict]:
    """One watcher pass. Returns one dict per announced event: kind, job, owner_text, family_text,
    owner_media, family_media, deliveries. ``deliver=False`` only writes the outbox (dry run).
    Returns [] when another pass holds the lock."""
    lock = _try_lock()
    if lock is False:
        _log("another watcher pass is running; skipped")
        return []
    try:
        return _Pass(settings, backend, store, now, deliver, out_dir).run()
    finally:
        _unlock(lock)


def stdout_text(results: list[dict], *, verbose: bool = False) -> str:
    """Owner texts of a pass (plus a ``MEDIA:`` line) for cron delivery; ``verbose`` adds family texts."""
    owner = [r["owner_text"] for r in results if r.get("owner_text")]
    media = next((r["owner_media"] for r in results if r.get("owner_text") and r.get("owner_media")), "")
    out = "\n\n".join(owner)
    if out and media and Path(media).is_file():
        out += f"\nMEDIA:{Path(media).resolve()}"
    if verbose:
        fam = [r["family_text"] for r in results if r.get("family_text")]
        if fam:
            out = (out + "\n\n" if out else "") + "[family]\n" + "\n\n".join(fam)
    return out


ERROR_FILE = "watcher-error.json"  # the error dedupe when the store itself is broken
ERROR_REPEAT_S = 6 * 3600  # the same error is told again at most this often when only the file remembers it


def _error_is_new(store: Optional[Store], msg: str) -> bool:
    """Remember ``msg`` as the watcher's current error; True when it is news (to be told). The store's kv first;
    when the store cannot be opened or written (corrupt database, full disk), a small file in the data dir that
    repeats the same error at most every ``ERROR_REPEAT_S``; when neither can be written, False (never a message
    on every cron tick)."""
    if store is not None:
        try:
            if store.kv_get("watcher_error") == msg:
                return False
            store.kv_set("watcher_error", msg)
            return True
        except Exception:
            pass
    try:
        path = data_dir() / ERROR_FILE
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old = {}
        now = time.time()
        if isinstance(old, dict) and old.get("msg") == msg and isinstance(old.get("ts"), (int, float)) \
                and 0 <= now - float(old["ts"]) < ERROR_REPEAT_S:
            return False
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"msg": msg, "ts": now}), encoding="utf-8")
        tmp.replace(path)
        return True
    except Exception as exc:
        _log(f"watcher error not recorded ({exc}): not told")
        return False


def _report_error(settings: Settings, store: Optional[Store], msg: str, *, dry_run: bool = False) -> str:
    """Tell the owner about a broken watcher once per distinct error; returns text for stdout (or ''). A dry run
    never sends and records nothing (the text goes to stdout)."""
    msg = (msg or "unknown error").strip().splitlines()[-1][:300]
    text = f"⚠️ home3d watcher: {msg}"
    if dry_run:
        return text
    if not _error_is_new(store, msg):
        return ""
    if not settings.owner_target:
        return text
    try:
        notify.send(settings, settings.owner_target, text, audience="owner", retry=False,  # bounded: one try
                    timeout_s=notify._limits(settings)[0])
    except Exception:
        pass
    return ""


def main(argv: Optional[list[str]] = None) -> int:
    """Cron ``--no-agent`` entry point: one pass, silent stdout when ``owner_target`` is set. Always exit 0."""
    parser = argparse.ArgumentParser(prog="home3d_watch", description="home-3d-workshop watcher (one pass)")
    parser.add_argument("--dry-run", action="store_true", help="never send, only write the outbox")
    parser.add_argument("--verbose", "-v", action="store_true", help="print owner and family texts")
    args, _ = parser.parse_known_args(argv)
    try:
        settings = load_settings()
    except Exception as exc:
        _log(f"load_settings failed: {exc}")
        settings = Settings()
    store: Optional[Store] = None
    try:
        store = Store()
        backend = make_backend(settings)
        results = run_once(settings, backend, store, deliver=not args.dry_run)
    except Exception as exc:
        _log("watcher pass failed:\n" + traceback.format_exc())
        out = _report_error(settings, store, f"{type(exc).__name__}: {exc}", dry_run=args.dry_run)
        if out or args.verbose:
            print(out or f"watcher pass failed: {exc}")
        return 0
    if store is not None:
        try:
            if store.kv_get("watcher_error"):
                store.kv_set("watcher_error", "")
        except Exception:
            pass
    try:  # the store works again: the file-based error memory is not needed any more
        (data_dir() / ERROR_FILE).unlink(missing_ok=True)
    except OSError:
        pass
    out = stdout_text(results, verbose=args.verbose)
    if out and (args.verbose or not settings.owner_target):
        print(out)
    return 0
