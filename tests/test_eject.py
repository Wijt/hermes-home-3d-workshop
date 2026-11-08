"""eject.py: the pure plate-clear state machine (time is passed in, no I/O)."""

from __future__ import annotations

import json

from home3d_ws.home3d.backends.base import PlateCheck, PrinterStatus
from home3d_ws.home3d.eject import (EJECT_RECHECK_S, EVENTS, GIVE_UP_S, PHASES, RECHECK_S, PlateState,
                                    needs_plate_check, step)

T0 = 1_000_000.0
MIN = 60.0
EMPTY = PlateCheck(is_empty=True, difference_pct=2.0)
OCCUPIED = PlateCheck(is_empty=False, difference_pct=40.0)
UNSURE = PlateCheck(is_empty=None, difference_pct=22.0)


def st(state, bed=None, job="Gift box", **kw) -> PrinterStatus:
    return PrinterStatus(state=state, bed_temp=bed, job_name=job, **kw)


class Machine:
    """Drives step() like the watcher does: ask needs_plate_check, then step with or without a check."""

    def __init__(self, eject_planned=True, plate_fn=None, **kw):
        self.state = PlateState("idle")
        self.eject_planned = eject_planned
        self.plate_fn = plate_fn or (lambda now: OCCUPIED)
        self.kw = kw
        self.phases: list[str] = []
        self.events: list[str] = []
        self.checks_done = 0

    def tick(self, status, now):
        plate = None
        if needs_plate_check(self.state, status, now, self.kw.get("cool_temp_c", 30.0)):
            plate = self.plate_fn(now)
            self.checks_done += 1
        prev = self.state
        self.state, ev = step(prev, status, now, eject_planned=self.eject_planned, plate=plate, **self.kw)
        assert prev is not self.state
        if not self.phases or self.phases[-1] != self.state.phase:
            self.phases.append(self.state.phase)
        self.events += ev
        return ev


def bed_at(minutes_after_finish: float) -> float:
    """Simulator-like cooling: 65 C -> about 30 C after ~10 min."""
    return round(25 + 40 * (0.8 ** minutes_after_finish), 1)


def test_planned_eject_cooling_ejecting_verifying_clear():
    finish_at = T0 + 30 * MIN
    eject_at = finish_at + 21 * MIN  # the pushed part leaves the plate just after the eject window
    m = Machine(eject_planned=True, plate_fn=lambda now: EMPTY if now >= eject_at else OCCUPIED)
    m.tick(st("PREPARE"), T0)
    m.tick(st("RUNNING"), T0 + 5 * MIN)
    assert m.state.phase == "printing" and m.state.eject_planned
    for k in range(0, 40, 2):
        now = finish_at + k * MIN
        m.tick(st("FINISH", bed=bed_at(k)), now)
        if m.state.phase == "clear":
            break
    assert m.phases == ["printing", "cooling", "ejecting", "verifying", "clear"]
    assert m.events == ["finished", "plate_clear"]
    # one early (uncounted) check once cool, one counted at the end of the window, one that sees it empty
    assert m.checks_done == 3
    assert m.state.checks == 0 and m.state.last_check["is_empty"] is True
    # clear is stable while the printer stays FINISH or goes IDLE
    assert step(m.state, st("FINISH", bed=24), now + MIN, eject_planned=True, plate=None) == (m.state, [])
    s, ev = step(m.state, st("IDLE", bed=24), now + 2 * MIN, eject_planned=False, plate=None)
    assert s.phase == "clear" and ev == []
    assert not needs_plate_check(m.state, st("FINISH", bed=24), now + 10 * MIN)


def test_empty_at_end_of_window_clears_without_delay():
    finish_at = T0 + 30 * MIN
    m = Machine(eject_planned=True, plate_fn=lambda now: EMPTY if now >= finish_at + 15 * MIN else OCCUPIED)
    m.tick(st("RUNNING"), T0)
    for k in range(0, 40, 2):
        m.tick(st("FINISH", bed=bed_at(k)), finish_at + k * MIN)
        if m.state.phase == "clear":
            break
    assert m.phases == ["printing", "cooling", "ejecting", "clear"]
    assert k == 20 and m.events == ["finished", "plate_clear"]


def test_real_printer_pushes_before_finish_fast_path():
    # the A1 end G-code cools and pushes before reporting FINISH: bed is already cool at FINISH
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    status = st("FINISH", bed=29.0)
    assert needs_plate_check(s, status, T0)
    s, ev = step(s, status, T0, eject_planned=True, plate=EMPTY)
    assert s.phase == "clear" and ev == ["finished", "plate_clear"]


def test_planned_eject_plate_stays_occupied_needs_human_after_max_checks():
    m = Machine(eject_planned=True, plate_fn=lambda now: OCCUPIED, max_checks=3)
    m.tick(st("RUNNING"), T0)
    finish = T0 + MIN
    for k in range(0, 60, 2):
        m.tick(st("FINISH", bed=bed_at(k)), finish + k * MIN)
        if m.state.phase == "needs_human":
            break
    assert m.phases[-2:] == ["verifying", "needs_human"]
    assert m.events == ["finished", "plate_not_clear"]
    assert m.state.checks == 3 and "3 checks" in m.state.reason
    # reached exactly when the 3rd counted check came in (window 20 min, checks every 2 min)
    assert k == 24
    # no repeated events while the part is still there
    s, ev = step(m.state, st("FINISH", bed=24), finish + 30 * MIN, eject_planned=True, plate=OCCUPIED)
    assert s.phase == "needs_human" and ev == []


def test_inconclusive_checks_give_eject_unverified():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    now = T0
    s, ev = step(s, st("FINISH", bed=25), now, eject_planned=True, plate=None)
    assert ev == ["finished"] and s.phase == "ejecting"
    events = []
    for k in range(1, 6):
        now = T0 + (20 + k) * MIN
        s, ev = step(s, st("FINISH", bed=25), now, eject_planned=True, plate=UNSURE)
        events += ev
    assert s.phase == "needs_human" and events == ["eject_unverified"]
    assert "inconclusive" in s.reason


def test_no_eject_plan_goes_straight_to_needs_human():
    m = Machine(eject_planned=False)
    m.tick(st("RUNNING"), T0)
    assert not needs_plate_check(m.state, st("FINISH", bed=60), T0 + MIN)
    ev = m.tick(st("FINISH", bed=60), T0 + MIN)
    assert ev == ["finished", "plate_not_clear"]
    assert m.state.phase == "needs_human" and "take the part off" in m.state.reason
    assert m.state.eject_planned is False


def test_no_eject_plan_but_check_says_empty_is_clear():
    s = PlateState("printing", job_name="Gift box")
    s, ev = step(s, st("FINISH", bed=24), T0, eject_planned=False, plate=EMPTY)
    assert s.phase == "clear" and ev == ["finished", "plate_clear"]


def test_needs_human_rechecks_and_clears_when_part_removed():
    s = PlateState("printing", job_name="Gift box")
    s, _ = step(s, st("FINISH", bed=60), T0, eject_planned=False, plate=None)
    assert s.phase == "needs_human"
    assert not needs_plate_check(s, st("FINISH", bed=55), T0 + 5 * MIN)  # still hot
    assert needs_plate_check(s, st("FINISH", bed=25), T0 + 20 * MIN)  # cool, never checked
    s, ev = step(s, st("FINISH", bed=25), T0 + 20 * MIN, eject_planned=False, plate=OCCUPIED)
    assert ev == [] and s.phase == "needs_human"
    assert not needs_plate_check(s, st("FINISH", bed=25), T0 + 25 * MIN)  # checked 5 min ago
    assert needs_plate_check(s, st("FINISH", bed=25), T0 + 20 * MIN + RECHECK_S)
    s, ev = step(s, st("FINISH", bed=25), T0 + 40 * MIN, eject_planned=False, plate=EMPTY)
    assert s.phase == "clear" and ev == ["plate_clear"]


def test_failed_emits_failed_once():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, ev = step(s, st("FAILED", bed=60), T0, eject_planned=True, plate=None)
    assert ev == ["failed"] and s.phase == "needs_human" and "failed" in s.reason
    s2, ev2 = step(s, st("FAILED", bed=50), T0 + 2 * MIN, eject_planned=True, plate=None)
    assert ev2 == [] and s2.phase == "needs_human"
    # failed from idle (watcher started after the failure) still reports once
    s3, ev3 = step(PlateState("idle"), st("FAILED", bed=20), T0, eject_planned=False, plate=None)
    assert ev3 == ["failed"]
    # after a person cleared it, a later empty check clears the plate state
    s4, ev4 = step(s2, st("FAILED", bed=22), T0 + 30 * MIN, eject_planned=False, plate=EMPTY)
    assert s4.phase == "clear" and ev4 == ["plate_clear"]
    assert step(s4, st("FAILED", bed=22), T0 + 40 * MIN, eject_planned=False, plate=None)[1] == []


def test_print_ending_without_finish_counts_as_failed():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, ev = step(s, st("IDLE", bed=40, job=""), T0, eject_planned=True, plate=None)
    assert ev == ["failed"] and s.phase == "needs_human"


def test_offline_and_unknown_states_change_nothing():
    s = PlateState("ejecting", job_name="Gift box", eject_planned=True, finished_ts=T0)
    for status in (st("OFFLINE"), st("FINISH", connected=False), st("SLICING")):
        s2, ev = step(s, status, T0 + MIN, eject_planned=True, plate=None)
        assert s2 == s and ev == []
        assert not needs_plate_check(s, status, T0 + MIN)


def test_new_print_resets_and_tracks_eject_plan():
    s = PlateState("needs_human", job_name="Old", reason="x", checks=3, finished_ts=T0)
    s, ev = step(s, st("PREPARE", job="New"), T0 + MIN, eject_planned=False, plate=None)
    assert ev == [] and s == PlateState("printing", job_name="New", eject_planned=False)
    s, _ = step(s, st("RUNNING", job="New"), T0 + 2 * MIN, eject_planned=True, plate=None)
    assert s.eject_planned is True
    assert not needs_plate_check(s, st("RUNNING", job="New"), T0 + 2 * MIN)


def test_missed_print_with_new_name_is_a_new_finish():
    s = PlateState("clear", job_name="Old", finished_ts=T0)
    s, ev = step(s, st("FINISH", bed=60, job="New"), T0 + 90 * MIN, eject_planned=True, plate=None)
    assert ev == ["finished"] and s.job_name == "New" and s.phase == "cooling"


def test_bed_that_never_cools_ends_with_eject_unverified():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, _ = step(s, st("FINISH", bed=60), T0, eject_planned=True, plate=None)
    assert s.phase == "cooling"
    # after 40 min a bed within +5 C of the limit is accepted
    s2, _ = step(s, st("FINISH", bed=33), T0 + 41 * MIN, eject_planned=True, plate=None)
    assert s2.phase == "verifying"
    s3, ev = step(s, st("FINISH", bed=45), T0 + GIVE_UP_S, eject_planned=True, plate=None)
    assert s3.phase == "needs_human" and ev == ["eject_unverified"] and "did not cool" in s3.reason


def test_step_is_pure_and_state_round_trips_json():
    prev = PlateState("verifying", job_name="Gift box", eject_planned=True, finished_ts=T0, checks=1,
                      last_check={"ts": T0, "is_empty": False})
    snapshot = json.dumps(prev.to_dict())
    new, _ = step(prev, st("FINISH", bed=24), T0 + 25 * MIN, eject_planned=True, plate=OCCUPIED)
    assert json.dumps(prev.to_dict()) == snapshot  # prev untouched
    assert new.checks == 2
    restored = PlateState.from_dict(json.loads(json.dumps(new.to_dict())))
    assert restored == new
    assert PlateState.from_dict(None).phase == "idle"
    assert PlateState.from_dict({"phase": "bogus", "extra": 1}).phase == "idle"
    assert set(EVENTS) >= {"finished", "failed", "plate_clear", "plate_not_clear", "eject_unverified"}
    assert PHASES[0] == "idle" and "needs_human" in PHASES


def test_against_the_simulator(tmp_path):
    """The watcher's loop (needs_plate_check -> check_plate -> step) on the simulated printer."""
    import pytest

    simmod = pytest.importorskip("home3d_ws.home3d.backends.simulator")
    from home3d_ws.home3d.backends.base import SliceOptions
    from home3d_ws.home3d.gcode import inspect_gcode

    def run(scenario, preset):
        b = simmod.SimulatorBackend(tmp_path / f"sim-{scenario}-{preset or 'std'}.json")
        gcode_push = b.eject_in_gcode
        b.set_scenario(scenario)
        lib = b.import_model(simmod.DEMO_MODEL_IDS[0])
        sliced = b.slice(lib.id, SliceOptions(printer_preset=preset))
        planned = inspect_gcode(b.library_gcode(sliced.library_file_id)).has_eject_marker
        b.start(b.queue_add(sliced.library_file_id).id)
        s, events, phases = PlateState("idle"), [], []
        for _ in range(400):
            status, now = b.status(), b.now()
            plate = b.check_plate() if needs_plate_check(s, status, now, eject_in_gcode=gcode_push) else None
            s, ev = step(s, status, now, eject_planned=planned, plate=plate, eject_in_gcode=gcode_push)
            events += ev
            if not phases or phases[-1] != s.phase:
                phases.append(s.phase)
            if status.state == "FINISH" and s.phase in ("clear", "needs_human"):
                break
            b.advance(2)
        return planned, phases, events

    # the simulator pushes inside the end G-code (RUNNING at 100 %), so FINISH already shows the empty plate
    assert run("ok", "sim-autoeject") == (True, ["printing", "clear"], ["finished", "plate_clear"])
    planned, phases, events = run("eject_miss", "sim-autoeject")
    assert phases == ["printing", "verifying", "needs_human"] and events == ["finished", "plate_not_clear"]
    assert run("ok", "") == (False, ["printing", "needs_human"], ["finished", "plate_not_clear"])


def test_a_dark_plate_check_never_clears_the_plate():
    """A check taken with the chamber light off (light_ok False) is not "empty", even if a backend says so."""
    from home3d_ws.home3d.eject import says_empty

    dark_empty = PlateCheck(is_empty=True, difference_pct=0.0, light_ok=False)
    assert not says_empty(dark_empty) and not says_empty(None) and not says_empty(UNSURE)
    assert says_empty(EMPTY) and says_empty(PlateCheck(is_empty=True, light_ok=True))
    s = PlateState("needs_human", job_name="Gift box", finished_ts=T0, reason="no auto-eject planned")
    s2, ev = step(s, st("FINISH", bed=24), T0 + 30 * MIN, eject_planned=False, plate=dark_empty)
    assert s2.phase == "needs_human" and ev == [] and s2.last_check["light_ok"] is False
    s3, ev3 = step(s, st("FINISH", bed=24), T0 + 30 * MIN, eject_planned=False,
                   plate=PlateCheck(is_empty=True, light_ok=True))
    assert s3.phase == "clear" and ev3 == ["plate_clear"] and s3.last_check["light_ok"] is True


def test_unknown_state_changes_nothing_and_asks_for_no_check():
    for phase in ("printing", "needs_human", "clear", "verifying"):
        s = PlateState(phase, job_name="Gift box", finished_ts=T0)
        s2, ev = step(s, st("UNKNOWN", bed=24), T0 + 30 * MIN, eject_planned=True, plate=None)
        assert s2.phase == phase and ev == []
        assert not needs_plate_check(s, st("UNKNOWN", bed=24), T0 + 30 * MIN)


# ---- fix round 2: the real A1 order (push inside the end G-code, FINISH after it) --------------------------
def pushed(prev, status, now, plate):
    return step(prev, status, now, eject_planned=True, plate=plate, eject_in_gcode=True)


def test_real_order_checks_at_finish_without_waiting_for_the_bed():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    hot = st("FINISH", bed=45.0)  # no cool-down gate: the camera does not need a cool bed
    assert needs_plate_check(s, hot, T0, eject_in_gcode=True)
    assert not needs_plate_check(s, hot, T0)  # the old model waits for the bed
    s2, ev = pushed(s, hot, T0, EMPTY)
    assert s2.phase == "clear" and ev == ["finished", "plate_clear"]


def test_real_order_eject_miss_is_rechecked_once_then_asks_a_person():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, ev = pushed(s, st("FINISH", bed=28), T0, OCCUPIED)
    assert ev == ["finished"] and s.phase == "verifying" and s.checks == 1
    assert s.verify_after_ts == T0 + EJECT_RECHECK_S
    assert not needs_plate_check(s, st("FINISH", bed=28), T0 + 2 * MIN, eject_in_gcode=True)
    s, ev = pushed(s, st("FINISH", bed=28), T0 + 2 * MIN, None)  # a pass without a check changes nothing
    assert ev == [] and s.phase == "verifying"
    assert needs_plate_check(s, st("FINISH", bed=28), T0 + 4 * MIN, eject_in_gcode=True)
    s, ev = pushed(s, st("FINISH", bed=28), T0 + 4 * MIN, OCCUPIED)
    assert s.phase == "needs_human" and ev == ["plate_not_clear"] and "2 checks" in s.reason
    s, ev = pushed(s, st("FINISH", bed=27), T0 + 20 * MIN, OCCUPIED)
    assert ev == [] and s.phase == "needs_human"


def test_real_order_late_empty_reading_clears():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, _ = pushed(s, st("FINISH", bed=28), T0, OCCUPIED)
    s, ev = pushed(s, st("FINISH", bed=28), T0 + 4 * MIN, EMPTY)
    assert s.phase == "clear" and ev == ["plate_clear"]


def test_real_order_unsure_twice_is_eject_unverified_and_a_failing_check_gives_up_late():
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, _ = pushed(s, st("FINISH", bed=28), T0, UNSURE)
    s, ev = pushed(s, st("FINISH", bed=28), T0 + 4 * MIN, UNSURE)
    assert s.phase == "needs_human" and ev == ["eject_unverified"] and "inconclusive" in s.reason
    s = PlateState("printing", job_name="Gift box", eject_planned=True)
    s, ev = pushed(s, st("FINISH", bed=28), T0, None)  # the camera did not answer
    assert ev == ["finished"] and s.phase == "verifying"
    assert needs_plate_check(s, st("FINISH", bed=28), T0 + 2 * MIN, eject_in_gcode=True)
    s, ev = pushed(s, st("FINISH", bed=28), T0 + GIVE_UP_S, None)
    assert s.phase == "needs_human" and ev == ["eject_unverified"]


def test_real_order_without_an_eject_plan_is_unchanged():
    s = PlateState("printing", job_name="Gift box")
    assert not needs_plate_check(s, st("FINISH", bed=28), T0, eject_in_gcode=True)
    s, ev = step(s, st("FINISH", bed=28), T0, eject_planned=False, plate=None, eject_in_gcode=True)
    assert s.phase == "needs_human" and ev == ["finished", "plate_not_clear"]
