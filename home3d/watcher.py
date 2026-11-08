"""Zero-token print watcher: one pass per cron tick (``hermes cron ... --no-agent --script home3d_watch.py``).

No model calls. Each pass reads the printer status, detects transitions (pause, new HMS, offline), takes the
"done" photo at the last layers (before an auto-eject push), feeds the plate-clear state machine
(``eject.step``, with a camera plate check only when it asks for one), turns the resulting events into an
owner text (technical, with photo) and a family line (by name), logs human-needed moments, evaluates
upgrade proposals and tells the owner when the plate is clear and a manual job is waiting (it never starts
anything itself). State lives in ``store.kv('watcher')``.

Which workshop job is printing: the backend queue item whose status is ``printing`` (and whose name matches),
remembered for the rest of that print; else the store's exact name match. A printing queue item the workshop
did not queue is nobody's job (no family message).

"Next job ready" names the first pending manual-start job the WORKSHOP queued; jobs queued elsewhere that
wait ahead of it are named in the same owner text (with ``/home3d approve start N jump``), and jobs queued
elsewhere are announced to the owner at most once per item. Plate notes carry a fresh lit photo and say the
camera *thinks* the plate is empty.
"""

from __future__ import annotations

import argparse
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
from .store import Store

KV_KEY = "watcher"
LOG_FILE = "watcher.log"
LOCK_FILE = "watcher.lock"
OFFLINE_NOTIFY_S = 10 * 60  # tell the owner once the printer has been unreachable this long
IDLE_CHECK_S = 15 * 60  # idle printer, plate state unknown, manual job waiting: look this often
LAST_LAYER_PCT = 98.0  # "done" photo from this progress (or the last two layers) on
MEDIA_KEEP_S = 14 * 86400
LIGHT_ALERT_S = 6 * 3600  # "chamber light left on" owner alert at most this often
LIGHT_FLAG = "light_left_on"  # the backend's flag in Snapshot.note / PlateCheck.message
LIGHT_PENDING_KEY = "light_left_on:pending"  # runtime.LIGHT_PENDING_KEY: a hook/handler check left the light on
_CANCELLED_QUEUE = ("cancelled", "canceled", "skipped")
_ENDED_QUEUE = {"completed": ("finished", "done"), "failed": ("failed", "failed")}
_EJECT_FLOW = ("finished", "cooling", "ejecting", "verifying")
_SUFFIXES = (".gcode.3mf", ".3mf", ".gcode", ".stl")
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
        self.first = not self.w.get("initialized")
        self.notes: list[_Note] = []
        self.moments = 0
        self._fresh: Optional[Path] = None
        self._fresh_tried = False
        self._queue_items: Optional[list[QueueItem]] = None
        self._queue_tried = False

    # -- backend calls (never raise) --
    def _status(self) -> tuple[Optional[PrinterStatus], str]:
        try:
            return self.backend.status(), ""
        except Exception as exc:  # BackendError or anything unexpected
            return None, str(exc) or type(exc).__name__

    def _check_plate(self) -> Optional[PlateCheck]:
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

    def _queue(self) -> Optional[list[QueueItem]]:
        """The backend queue, read at most once per pass (the watcher never changes it); None when unreadable."""
        if not self._queue_tried:
            self._queue_tried = True
            try:
                self._queue_items = list(self.backend.queue())
            except Exception as exc:
                _log(f"queue failed: {exc}")
                self._queue_items = None
        return self._queue_items

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
        if job and self.w.get("photo_for_job") == job and path and Path(path).is_file():
            return Path(path)
        if not take:
            return None
        fresh = self._snapshot()
        if fresh is not None and job:
            self.w["photo_for_job"], self.w["photo_path"] = job, str(fresh)
        return fresh

    # -- household lookups --
    def _lookup(self, name: str) -> tuple[Optional[dict], Optional[int]]:
        """(workshop job row, queue item id) of the print called ``name``: the backend queue item that is
        printing under that name wins (not in the store = not ours: None, never a guess by name); else the
        store's exact name match."""
        for q in self._queue() or []:
            if str(q.status or "").strip().lower() == "printing" and _same_job(q.name, name):
                try:
                    return self.store.get_job(int(q.id)), int(q.id)
                except Exception:
                    return None, int(q.id)
        try:
            row = self.store.job_by_name(name)
        except Exception:
            row = None
        qid = row.get("queue_item_id") if row else None
        return row, (int(qid) if qid is not None else None)

    def _attribute(self, name: str) -> Optional[dict]:
        """A print just started: decide whose job it is and remember it for the rest of the print."""
        row, qid = self._lookup(name) if name else (None, None)
        self.w["job_qid"] = qid if row else None
        return row

    def _job(self, name: str) -> Optional[dict]:
        if not name:
            return None
        qid = self.w.get("job_qid")
        if qid is not None and name == self.w.get("started_job"):
            try:
                row = self.store.get_job(int(qid))
            except Exception:
                row = None
            if row:
                return row
        return self._lookup(name)[0]

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
        owner = (self.s.owner_name or "").strip().lower()
        family = bool(requester) and not (person and person.role == "owner") and requester.strip().lower() != owner
        return ctx, family

    def _note(self, kind: str, job: str, ctx: dict, *, family: bool = False, owner_media: Optional[Path] = None,
              family_media: Optional[Path] = None, human: str = "", detail: str = "", **payload: Any) -> None:
        self.notes.append(_Note(kind, job, ctx, family, owner_media, family_media, payload))
        if human:
            try:
                upgrades.log_moment(self.store, human, detail or kind, job_name=job, source="watcher")
                self.moments += 1
            except Exception as exc:
                _log(f"log_moment failed: {exc}")

    def _job_state(self, jobrow: Optional[dict], state: str, outcome: str = "") -> None:
        if not jobrow or jobrow.get("queue_item_id") is None:
            return
        try:
            fields: dict[str, Any] = {"state": state}
            if state in ("finished", "failed"):
                fields.update(finished_ts=self.now, outcome=outcome or state)
            elif outcome:
                fields["outcome"] = outcome
            if state == "printing" and jobrow.get("started_ts") is None:
                fields["started_ts"] = self.now  # the start tool may already have recorded it
            self.store.upsert_job(int(jobrow["queue_item_id"]), **fields)
            rid = jobrow.get("request_id")
            req_status = {"printing": "printing", "finished": "done", "failed": "failed"}.get(state)
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

    def online(self) -> None:
        if self.w.get("offline_since") is not None:
            if self.w.get("offline_notified"):
                self.store.add_event("online", self.w.get("job_name", ""), {"offline_since": self.w["offline_since"]})
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
            if st.state in (FINISH, FAILED):  # a job ended before the watcher existed: wait for a clear plate
                self.w["plate_state"] = eject.PlateState(
                    "needs_human", job_name=job, finished_ts=self.now,
                    reason="found finished before the watcher started").to_dict()
            if st.state == FAILED and not self._plate_confirmed(job):
                self._record_failure(job, "found failed before the watcher started")
        if st.is_active and (prev not in ACTIVE_STATES or (job and job != self.w.get("job_name"))):
            jobrow = self._attribute(job)
            self._job_state(jobrow, "printing")
            self.w.update(started_ts=self.now, started_job=job)
            try:  # the plate is in use by a new print: an earlier failure is settled
                self.store.clear_failure(f"a new print started: {job}"[:120])
            except Exception as exc:
                _log(f"clear_failure failed: {exc}")
            if self.w.get("photo_for_job") == job:
                self.w["photo_for_job"] = ""
            self.store.add_event("started", job, {"state": st.state, "queue_item_id": (jobrow or {}).get("queue_item_id"),
                                                  "silent": True})
        if st.state == RUNNING and job and self.w.get("photo_for_job") != job and self._near_end(st):
            photo = self._snapshot()
            if photo is not None:
                self.w["photo_for_job"], self.w["photo_path"] = job, str(photo)
        paused = False
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
        check = self._check_plate() if eject.needs_plate_check(ps, st, self.now, cool) else None
        new, events = eject.step(ps, st, self.now, eject_planned=planned, plate=check, cool_temp_c=cool)
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
        last = new.last_check or {}
        ctx.update(reason=new.reason, plate_diff=last.get("difference_pct"))
        payload = {"phase": new.phase, "prev_phase": prev.phase, "events": list(events), "plate": last or None}
        ev = set(events)
        if "failed" in ev:
            self._job_state(jobrow, "failed")
            self._record_failure(job, new.reason)
            self._note("failed", job, ctx, family=family, owner_media=self._snapshot(), human="failure_check",
                       detail=new.reason, **payload)
        if "finished" in ev:
            self._job_state(jobrow, "finished")
            part = self._part_photo(job, take=True)
            if "plate_clear" in ev and new.eject_planned:
                self._job_state(jobrow, "cleared", "ejected")
                self._note("finished_ejected", job, ctx, family=family, owner_media=self._snapshot(),
                           family_media=part, **payload)
            elif new.eject_planned and "plate_not_clear" not in ev:
                self._note("finished", job, ctx, owner_media=part, **payload)  # family hears the eject outcome
            else:
                self._note("finished", job, ctx, family=family, owner_media=part, family_media=part,
                           human="remove_part" if "plate_not_clear" in ev else "",
                           detail="no auto-eject planned", **payload)
            return
        if "plate_clear" in ev:
            self._job_state(jobrow, "cleared", "ejected" if prev.phase in _EJECT_FLOW else "removed")
            if prev.phase in _EJECT_FLOW:
                self._note("finished_ejected", job, ctx, family=family, owner_media=self._snapshot(),
                           family_media=self._part_photo(job, take=False), **payload)
            else:
                photo = self._snapshot()
                ctx.update(photo=photo is not None, confirm_first=self._confirm_first(st))
                self._note("plate_clear", job, ctx, owner_media=photo, **payload)
        if "plate_not_clear" in ev:
            self._note("plate_not_clear", job, ctx, family=family, owner_media=self._snapshot(),
                       human="remove_part", detail=new.reason, **payload)
        if "eject_unverified" in ev:
            self._note("eject_unverified", job, ctx, family=family, owner_media=self._snapshot(),
                       human="camera_check", detail=new.reason, **payload)

    def _record_failure(self, job: str, reason: str = "") -> None:
        """Remember a failed print until a person confirms the plate (survives a power cycle / IDLE)."""
        try:
            self.store.record_failure(job, "watcher", reason)
        except Exception as exc:
            _log(f"record_failure failed: {exc}")

    def _plate_confirmed(self, job: str) -> bool:
        try:
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
        return st.state == FAILED and not self._plate_confirmed(st.job_name or "")

    def _plate_ready(self, st: PrinterStatus) -> bool:
        """The camera thinks the plate is empty (plate phase "clear"; an idle printer with an unknown plate is
        checked every ``IDLE_CHECK_S``)."""
        ps = eject.PlateState.from_dict(self.w.get("plate_state"))
        if ps.phase == "clear":
            return True
        if ps.phase != "idle" or st.state != IDLE:
            return False
        if self.now - float(self.w.get("idle_check_ts") or 0) < IDLE_CHECK_S:
            return False
        self.w["idle_check_ts"] = self.now
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
            ctx.update(next_job=pretty_job(name), next_id=nxt.id, plate_diff=diff, photo=photo is not None,
                       ahead=[{"id": q.id, "name": pretty_job(q.name)} for q in ahead],
                       confirm_first=self._confirm_first(st))
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
        try:
            every = {int(q.id): q for q in self.backend.queue(include_done=True)}
        except Exception as exc:
            _log(f"queue(include_done) failed: {exc}")
            return
        before = set(_ids(self.w.get("missing_jobs")))
        missing: list[int] = []
        for qid in sorted(unseen):
            item = every.get(qid)
            status = str(item.status or "").strip().lower() if item is not None else ""
            if item is None and qid not in before:
                missing.append(qid)
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
        if not self.notes:
            return []
        lang = self.s.language
        results: list[dict] = []
        owner_parts: list[str] = []
        family_parts: list[str] = []
        owner_media = family_media = None
        for n in self.notes:
            owner_text = messages.render(n.kind, "owner", lang, **n.ctx)
            family_text = messages.render(n.kind, "family", lang, **n.ctx) if n.family else ""
            payload = {k: v for k, v in n.ctx.items() if v not in (None, "")}
            payload.update(n.payload)
            payload.update(owner_text=owner_text, family_text=family_text)
            try:
                event_id = self.store.add_event(n.kind, n.job, _jsonable(payload))
            except Exception as exc:
                _log(f"add_event failed: {exc}")
                event_id = None
            if owner_text:
                owner_parts.append(owner_text)
                owner_media = owner_media or n.owner_media
            if family_text:
                family_parts.append(family_text)
                family_media = family_media or n.family_media
            results.append({"event_id": event_id, "kind": n.kind, "job": n.job, "owner_text": owner_text,
                            "family_text": family_text, "owner_media": str(n.owner_media or ""),
                            "family_media": str(n.family_media or "") if family_text else "", "deliveries": []})
        deliveries: list[notify.Delivery] = []
        try:
            if owner_parts:
                deliveries += notify.notify(self.s, owner_text="\n\n".join(owner_parts), family_text=None,
                                            media=owner_media, dry_run=not self.deliver)
            if family_parts:
                deliveries += notify.notify(self.s, owner_text=None, family_text="\n\n".join(family_parts),
                                            media=family_media, owner_media_only=False, dry_run=not self.deliver)
        except Exception as exc:
            _log(f"notify failed: {exc}")
        ok = {d.audience: d.ok for d in deliveries}
        for d in deliveries:
            if not d.ok:
                _log(f"delivery to {d.audience} {d.target} failed: {d.error}")
        for r in results:
            r["deliveries"] = [d.to_dict() for d in deliveries]
            if r["event_id"] is not None and self.deliver:
                try:
                    self.store.mark_event_notified(r["event_id"],
                                                   owner=ok.get("owner") if r["owner_text"] else None,
                                                   family=ok.get("family") if r["family_text"] else None)
                except Exception:
                    pass
        return results

    def prune_media(self) -> None:
        if not self.default_media or not self.out_dir.is_dir():
            return
        cutoff = time.time() - MEDIA_KEEP_S
        keep = {self.w.get("photo_path") or ""}
        for p in self.out_dir.iterdir():
            try:
                if p.is_file() and str(p) not in keep and p.stat().st_mtime < cutoff:
                    p.unlink()
            except OSError:
                pass

    def run(self) -> list[dict]:
        st, err = self._status()
        if st is None or st.state == OFFLINE or not st.connected:
            self.offline(err or "printer offline")
        else:
            self.online()
            self.light_pending()
            self.transitions(st)
            self.plate(st)
            self.stale_jobs()
            self.ready_next(st)
            self.remember(st)
        self.proposals()
        results = self.deliver_notes()
        self.w.update(now=self.now, updated=time.time())
        self.store.kv_set(KV_KEY, _jsonable(self.w))
        self.prune_media()
        return results


def _says_empty(check: Optional[PlateCheck]) -> bool:
    """A plate check that explicitly says empty and was not taken in the dark (``light_ok`` False)."""
    return check is not None and check.is_empty is True and getattr(check, "light_ok", None) is not False


def _same_job(a: str, b: str) -> bool:
    """Queue item name vs printer job name ("gul_kutusu.gcode.3mf" == "gul kutusu"); an empty side matches."""
    x, y = pretty_job(a).casefold(), pretty_job(b).casefold()
    return not x or not y or x == y


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


def _report_error(settings: Settings, store: Optional[Store], msg: str) -> str:
    """Tell the owner about a broken watcher once per distinct error; returns text for stdout (or '')."""
    msg = (msg or "unknown error").strip().splitlines()[-1][:300]
    if store is not None:
        try:
            if store.kv_get("watcher_error") == msg:
                return ""
            store.kv_set("watcher_error", msg)
        except Exception:
            pass
    text = f"⚠️ home3d watcher: {msg}"
    if not settings.owner_target:
        return text
    try:
        notify.send(settings, settings.owner_target, text, audience="owner")
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
        out = _report_error(settings, store, f"{type(exc).__name__}: {exc}")
        if out or args.verbose:
            print(out or f"watcher pass failed: {exc}")
        return 0
    if store is not None:
        try:
            if store.kv_get("watcher_error"):
                store.kv_set("watcher_error", "")
        except Exception:
            pass
    out = stdout_text(results, verbose=args.verbose)
    if out and (args.verbose or not settings.owner_target):
        print(out)
    return 0
