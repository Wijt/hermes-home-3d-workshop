"""Plate-clear state machine: after a print, is the plate empty again so the next job may start?

Pure: ``step()`` takes the previous state, the printer status, the time and (optionally) a plate check,
and returns the new state plus the event kinds to announce. The watcher persists the state
(``to_dict``/``from_dict``) and calls ``check_plate`` only when ``needs_plate_check()`` says so.

Flow (``eject_planned``: the sliced file ends with the auto-eject block that cools, then pushes the part):
  printing -> FINISH -> cooling (bed > cool_temp_c) -> ejecting (eject window still open; one early
  check may already see an empty plate, real printers push before reporting FINISH) -> verifying
  (plate checks; empty -> clear, not empty after ``max_checks`` -> needs_human).
  Without an eject plan FINISH goes straight to needs_human ("take the part off") unless a check says
  empty. FAILED (or a print that ends without FINISH) -> needs_human with a ``failed`` event.
  needs_human re-checks the plate every ``RECHECK_S`` and becomes clear when a check says empty (the
  watcher backs these re-checks off further: 15 -> 30 -> 60 -> 120 min, at most 6 in a row).

  ``eject_in_gcode`` (the REAL A1 order, ``Backend.eject_in_gcode``): the end G-code cools the bed and pushes
  the part while the printer still reports RUNNING at 100 %, and FINISH comes after the push. Then:
  printing -> FINISH (plate check at once, no cool-down gate) -> clear when empty; otherwise verifying with
  one re-check ``EJECT_RECHECK_S`` later -> clear, or needs_human (``plate_not_clear`` / ``eject_unverified``).
  "Says empty" means ``is_empty is True`` from a check that was not run in the dark (``light_ok`` not
  False). The phase "clear" is the camera's opinion only: after a ``failed`` event (FAILED, or a print that
  ended in IDLE) the watcher records the failure (``Store.record_failure``) and ``gates.start_gate`` still
  wants a person's confirmation (``plate_confirmed`` / ``after_failure``), even after a power cycle.
  An UNKNOWN or OFFLINE printer state never changes the phase and never asks for a plate check.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Optional

from .backends.base import ACTIVE_STATES, FAILED, FINISH, IDLE, OFFLINE, PlateCheck, PrinterStatus

PHASES = ("idle", "printing", "finished", "cooling", "ejecting", "verifying", "clear", "needs_human")
EVENTS = ("finished", "failed", "plate_clear", "plate_not_clear", "eject_unverified")
_AFTER = ("finished", "cooling", "ejecting", "verifying", "needs_human")

RELAX_AFTER_S = 40 * 60  # after 40 min accept a bed a little above the limit (it may never reach it)
RELAX_EXTRA_C = 5.0
GIVE_UP_S = 2 * 3600  # bed never cooled / plate never verifiable -> ask a person
RECHECK_S = 15 * 60  # while waiting for a person, look at the plate again this often
EJECT_RECHECK_S = 3 * 60  # eject_in_gcode: a plate that is not empty at FINISH is looked at once more after this
GCODE_EJECT_CHECKS = 2  # eject_in_gcode: checks (FINISH + one re-check) before a person is asked


@dataclass
class PlateState:
    phase: str
    job_name: str = ""
    eject_planned: bool = False
    finished_ts: Optional[float] = None
    checks: int = 0  # counted (post-window) plate checks that did not say "empty"
    last_check: Optional[dict] = None  # {"ts", "is_empty", "difference_pct", "confidence", "message"}
    reason: str = ""
    verify_after_ts: Optional[float] = None  # end of the eject window (finished_ts + eject_window_s)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PlateState":
        data = data if isinstance(data, dict) else {}
        names = {f.name for f in fields(cls)}
        state = cls(**{k: v for k, v in data.items() if k in names and k != "phase"},
                    phase=str(data.get("phase") or "idle"))
        if state.phase not in PHASES:
            state.phase = "idle"
        return state


def _record(plate: PlateCheck, now: float) -> dict:
    return {"ts": now, "is_empty": plate.is_empty, "difference_pct": plate.difference_pct,
            "confidence": plate.confidence, "message": plate.message,
            "needs_calibration": plate.needs_calibration, "light_ok": getattr(plate, "light_ok", None)}


def says_empty(plate: Optional[PlateCheck]) -> bool:
    """A plate check that explicitly says empty and was not taken in the dark."""
    return plate is not None and plate.is_empty is True and getattr(plate, "light_ok", None) is not False


def _bed_cool(status: PrinterStatus, cool_temp_c: float, elapsed: Optional[float]) -> bool:
    bed = status.bed_temp
    if bed is None or bed <= cool_temp_c:
        return True  # unknown bed temperature: the eject window still has to pass
    return elapsed is not None and elapsed >= RELAX_AFTER_S and bed <= cool_temp_c + RELAX_EXTRA_C


def _checked_since_finish(state: PlateState) -> bool:
    ts = (state.last_check or {}).get("ts")
    return ts is not None and state.finished_ts is not None and ts >= state.finished_ts


def step(prev: PlateState, status: PrinterStatus, now: float, *, eject_planned: bool,
         plate: Optional[PlateCheck], cool_temp_c: float = 30.0, eject_window_s: float = 20 * 60,
         max_checks: int = 3, eject_in_gcode: bool = False) -> tuple[PlateState, list[str]]:
    """Advance the plate state; returns (new state, emitted event kinds). Never mutates ``prev``.
    ``eject_in_gcode``: the push already ran before FINISH (see the module docstring)."""
    s = replace(prev, last_check=dict(prev.last_check) if prev.last_check else None)
    if s.phase not in PHASES:
        s.phase = "idle"
    events: list[str] = []
    st = status.state

    if st == OFFLINE or not status.connected:
        return s, events  # nothing is known; the watcher reports offline itself

    if st in ACTIVE_STATES:
        if s.phase != "printing" or (status.job_name and status.job_name != s.job_name):
            s = PlateState("printing", job_name=status.job_name, eject_planned=bool(eject_planned))
        else:
            s.eject_planned = bool(eject_planned)
        return s, events

    if st == IDLE and s.phase == "printing":  # ended without FINISH/FAILED (cancel, power loss)
        s = replace(s, phase="needs_human", finished_ts=now, checks=0,
                    reason="print ended without finishing: check the plate")
        return s, ["failed"]

    if st not in (FINISH, FAILED) and not (st == IDLE and s.phase in _AFTER):
        if st == IDLE and s.phase != "clear":
            s.phase = "idle"
        return s, events  # idle / clear / unknown state: nothing to decide

    job = status.job_name or s.job_name
    if st in (FINISH, FAILED):
        new_job = s.phase in ("idle", "printing") or bool(status.job_name and s.job_name
                                                         and status.job_name != s.job_name)
        if new_job:
            planned = bool(eject_planned) or (s.phase == "printing" and s.eject_planned and s.job_name == job)
            s = PlateState("finished", job_name=job, eject_planned=planned, finished_ts=now)
            if st == FAILED:
                s.phase, s.reason = "needs_human", "print failed: check the printer and the plate"
                if plate is not None:
                    s.last_check = _record(plate, now)
                return s, ["failed"]
            events.append("finished")

    if plate is not None:
        s.last_check = _record(plate, now)
    if s.phase == "clear":
        return s, events
    if says_empty(plate):
        s.phase, s.reason, s.checks = "clear", "", 0
        return s, events + ["plate_clear"]
    if s.phase == "needs_human":
        return s, events
    if not s.eject_planned:
        s.phase, s.reason = "needs_human", "no auto-eject planned: take the part off"
        return s, events + ["plate_not_clear"]

    finished_ts = s.finished_ts if s.finished_ts is not None else now
    s.finished_ts = finished_ts
    if eject_in_gcode:
        return _step_pushed(s, plate, now, finished_ts, events)
    s.verify_after_ts = finished_ts + eject_window_s
    elapsed = now - finished_ts
    cool = _bed_cool(status, cool_temp_c, elapsed)
    if elapsed >= max(GIVE_UP_S, 3 * eject_window_s):
        s.phase = "needs_human"
        s.reason = (f"bed did not cool below {cool_temp_c:g} C" if not cool
                    else "the plate could not be verified after the eject")
        return s, events + ["eject_unverified"]
    if not cool:
        s.phase = "cooling"
        return s, events
    if elapsed < eject_window_s:
        s.phase = "ejecting"  # a not-empty early check does not count: the push may not have run yet
        return s, events
    s.phase = "verifying"
    if plate is not None:
        s.checks += 1
        if s.checks >= max_checks:
            s.phase = "needs_human"
            if plate.is_empty is False:
                s.reason = f"part still on the plate after {s.checks} checks"
                events.append("plate_not_clear")
            else:
                s.reason = f"plate check inconclusive after {s.checks} checks"
                events.append("eject_unverified")
    return s, events


def _step_pushed(s: PlateState, plate: Optional[PlateCheck], now: float, finished_ts: float,
                 events: list[str]) -> tuple[PlateState, list[str]]:
    """eject_in_gcode: the end G-code already cooled the bed and pushed the part before FINISH. A plate that is
    not empty is looked at once more ``EJECT_RECHECK_S`` later (the camera's first frame may be early), then a
    person is asked. No cool-down gate: the camera does not need a cool bed."""
    s.phase = "verifying"
    if plate is None:  # the check could not run (yet): look again on the next pass, give up after GIVE_UP_S
        if now - finished_ts >= GIVE_UP_S:
            s.phase, s.reason = "needs_human", "the plate could not be verified after the eject"
            return s, events + ["eject_unverified"]
        if s.verify_after_ts is None:
            s.verify_after_ts = now
        return s, events
    s.checks += 1
    if s.checks < GCODE_EJECT_CHECKS:
        s.verify_after_ts = now + EJECT_RECHECK_S
        return s, events
    s.phase = "needs_human"
    if plate.is_empty is False:
        s.reason = f"part still on the plate after {s.checks} checks"
        return s, events + ["plate_not_clear"]
    s.reason = f"plate check inconclusive after {s.checks} checks"
    return s, events + ["eject_unverified"]


def needs_plate_check(state: PlateState, status: PrinterStatus, now: float, cool_temp_c: float = 30.0,
                      eject_in_gcode: bool = False) -> bool:
    """Should the watcher run a plate check (camera + check-plate) before the next ``step()``?"""
    if not status.connected or status.state not in (FINISH, FAILED, IDLE):
        return False  # printing, offline or an unknown state: nothing to look at yet
    elapsed = (now - state.finished_ts) if state.finished_ts is not None else None
    cool = _bed_cool(status, cool_temp_c, elapsed)
    phase = state.phase
    if phase == "printing":  # the step that will see FINISH: the push may already be done
        return status.state == FINISH and state.eject_planned and (cool or eject_in_gcode)
    if eject_in_gcode and phase in ("finished", "cooling", "ejecting", "verifying"):
        return state.eject_planned and (state.verify_after_ts is None or now >= state.verify_after_ts)
    if phase in ("finished", "cooling", "ejecting"):
        window_over = state.verify_after_ts is not None and now >= state.verify_after_ts
        return state.eject_planned and cool and (window_over or not _checked_since_finish(state))
    if phase == "verifying":
        return True
    if phase == "needs_human":
        last = (state.last_check or {}).get("ts")
        return cool and (last is None or now - last >= RECHECK_S)
    return False
