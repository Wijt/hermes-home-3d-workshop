"""Zero-token print watcher: one pass per cron tick (``hermes cron ... --no-agent --script home3d_watch.py``).

No model calls. Each pass reads the printer status, detects transitions (pause, new HMS, offline), takes the
"done" photo at the last layers (before an auto-eject push), feeds the plate-clear state machine
(``eject.step``, with a camera plate check only when it asks for one), turns the resulting events into an
owner text (technical, with photo) and a family line (by name), logs human-needed moments, evaluates
upgrade proposals and tells the owner when the plate is clear and a manual job is waiting (it never starts
anything itself). State lives in ``store.kv('watcher')``.
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
                            PlateCheck, PrinterStatus)
from .config import Person, Settings, data_dir, load_settings
from .store import Store

KV_KEY = "watcher"
LOG_FILE = "watcher.log"
LOCK_FILE = "watcher.lock"
OFFLINE_NOTIFY_S = 10 * 60  # tell the owner once the printer has been unreachable this long
IDLE_CHECK_S = 15 * 60  # idle printer, plate state unknown, manual job waiting: look this often
LAST_LAYER_PCT = 98.0  # "done" photo from this progress (or the last two layers) on
MEDIA_KEEP_S = 14 * 86400
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

    # -- backend calls (never raise) --
    def _status(self) -> tuple[Optional[PrinterStatus], str]:
        try:
            return self.backend.status(), ""
        except Exception as exc:  # BackendError or anything unexpected
            return None, str(exc) or type(exc).__name__

    def _check_plate(self) -> Optional[PlateCheck]:
        try:
            return self.backend.check_plate()
        except Exception as exc:
            _log(f"check_plate failed: {exc}")
            return None

    def _snapshot(self) -> Optional[Path]:
        if not self._fresh_tried:
            self._fresh_tried = True
            try:
                self.out_dir.mkdir(parents=True, exist_ok=True)
                snap = self.backend.snapshot(self.out_dir, lit=True)
                self._fresh = Path(snap.path) if snap and snap.path else None
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
    def _job(self, name: str) -> Optional[dict]:
        try:
            return self.store.job_by_name(name) if name else None
        except Exception:
            return None

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
        requester = (jobrow or {}).get("requester") or ""
        if not requester and jobrow and jobrow.get("request_id"):
            req = self.store.get_request(int(jobrow["request_id"])) or {}
            requester = req.get("requester") or ""
        person = self._person(requester)
        ctx: dict[str, Any] = {
            "persona": self.s.persona_name, "owner": self.s.owner_name, "job": pretty_job(job),
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
        if st.is_active and (prev not in ACTIVE_STATES or (job and job != self.w.get("job_name"))):
            jobrow = self._job(job)
            self._job_state(jobrow, "printing")
            self.w.update(started_ts=self.now, started_job=job)
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
                self._note("plate_clear", job, ctx, **payload)
        if "plate_not_clear" in ev:
            self._note("plate_not_clear", job, ctx, family=family, owner_media=self._snapshot(),
                       human="remove_part", detail=new.reason, **payload)
        if "eject_unverified" in ev:
            self._note("eject_unverified", job, ctx, family=family, owner_media=self._snapshot(),
                       human="camera_check", detail=new.reason, **payload)

    def ready_next(self, st: PrinterStatus) -> None:
        if st.is_active or st.state not in (IDLE, FINISH, FAILED) or st.blocking_hms:
            return
        try:
            pending = [q for q in self.backend.queue() if q.is_pending]
        except Exception as exc:
            _log(f"queue failed: {exc}")
            return
        self.w["pending"] = len(pending)
        if not pending or not pending[0].manual_start:
            return  # nothing waiting, or the printer manager starts it by itself
        nxt = pending[0]
        notified = [int(i) for i in (self.w.get("ready_notified_for") or []) if str(i).lstrip("-").isdigit()]
        if nxt.id in notified:
            return
        ps = eject.PlateState.from_dict(self.w.get("plate_state"))
        if ps.phase != "clear":
            if ps.phase != "idle" or st.state != IDLE:
                return
            if self.now - float(self.w.get("idle_check_ts") or 0) < IDLE_CHECK_S:
                return
            self.w["idle_check_ts"] = self.now
            check = self._check_plate()
            if check is None or check.is_empty is not True:
                return
            ps.phase = "clear"
            ps.last_check = {"ts": self.now, "is_empty": True, "difference_pct": check.difference_pct,
                             "confidence": check.confidence, "message": check.message,
                             "needs_calibration": check.needs_calibration}
            self.w["plate_state"] = ps.to_dict()
        jobrow = None
        try:
            jobrow = self.store.get_job(nxt.id)
        except Exception:
            pass
        name = nxt.name or (jobrow or {}).get("name") or ""
        ctx, _ = self._ctx(name, jobrow, None)
        ctx.update(next_job=pretty_job(name), next_id=nxt.id)
        self._note("ready_next", name, ctx, queue_item_id=nxt.id)
        self.w["ready_notified_for"] = (notified + [nxt.id])[-50:]

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
            self.transitions(st)
            self.plate(st)
            self.ready_next(st)
            self.remember(st)
        self.proposals()
        results = self.deliver_notes()
        self.w.update(now=self.now, updated=time.time())
        self.store.kv_set(KV_KEY, _jsonable(self.w))
        self.prune_media()
        return results


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
