"""gates.py: start / clear-plate safety decisions and their tr/en descriptions."""

from __future__ import annotations

from home3d_ws.home3d.backends.base import HMSError, PlateCheck, PrinterStatus, QueueItem
from home3d_ws.home3d.gates import Gate, clear_plate_gate, describe, start_gate

EMPTY = PlateCheck(is_empty=True, difference_pct=2.0, confidence=0.9)
OCCUPIED = PlateCheck(is_empty=False, difference_pct=45.0, confidence=0.9, message="Objects detected")
UNSURE = PlateCheck(is_empty=None, difference_pct=21.0, message="uncertain")


def idle(**kw) -> PrinterStatus:
    kw.setdefault("bed_temp", 24.0)
    return PrinterStatus(state=kw.pop("state", "IDLE"), **kw)


def q(id_, status="pending", position=None, name="", manual=True) -> QueueItem:
    return QueueItem(id=id_, status=status, position=position, name=name or f"job{id_}", manual_start=manual)


def gate(status=None, queue=None, item=10, *, plate=EMPTY, in_cron=False, own=frozenset({10}), **kw) -> Gate:
    return start_gate(status or idle(), queue if queue is not None else [q(10, position=1)], item,
                      plate=plate, in_cron=in_cron, own_item_ids=set(own), **kw)


# ---- start_gate -------------------------------------------------------------------------------------
def test_start_ok_when_idle_empty_and_first():
    g = gate()
    assert g.ok and g.reasons == [] and g.needs_owner is True and g.action == "start"


def test_start_blocked_in_cron():
    g = gate(in_cron=True)
    assert not g.ok and "in_cron" in g.codes


def test_start_blocked_offline():
    assert "offline" in gate(idle(state="OFFLINE")).codes
    assert "offline" in gate(idle(connected=False)).codes


def test_start_blocked_when_active():
    for state in ("PREPARE", "RUNNING", "PAUSE"):
        g = gate(idle(state=state, job_name="Phone stand"))
        assert not g.ok and "busy" in g.codes
        assert "Phone stand" in g.reasons[0]


def test_start_blocked_on_unknown_state():
    assert "state_unknown" in gate(idle(state="SLICING")).codes


def test_start_blocked_on_hms_but_x_belt_notice_passes():
    bad = gate(idle(hms=[HMSError(code="0700-2000-0002-0001", message="runout")]))
    assert not bad.ok and "hms" in bad.codes and "0700-2000-0002-0001" in bad.reasons[0]
    harmless = gate(idle(hms=[HMSError(code="0300_1000_0002_0001")]))
    assert harmless.ok
    assert any("0300_1000_0002_0001" in w for w in harmless.warnings)


def test_start_blocked_item_missing_or_not_pending():
    assert "item_missing" in gate(item=99).codes
    g = gate(queue=[q(10, status="printing")])
    assert "item_not_pending" in g.codes
    assert "item_missing" not in gate(item="10").codes  # ids from tool args may be strings


def test_start_requires_explicitly_empty_plate():
    assert "plate_unknown" in gate(plate=None).codes
    assert "plate_occupied" in gate(plate=OCCUPIED).codes
    unsure = gate(plate=UNSURE)
    assert "plate_uncertain" in unsure.codes and not unsure.ok


def test_start_after_finish_or_failure_needs_cleared_plate():
    g = gate(idle(state="FAILED"), plate=OCCUPIED)
    assert {"plate_occupied", "after_job"} <= set(g.codes)
    assert "after_job" in gate(idle(state="FINISH"), plate=None).codes
    assert gate(idle(state="FINISH"), plate=EMPTY).ok  # verified empty after a finish: fine


def test_start_never_jumps_someone_elses_job():
    queue = [q(5, position=1, name="Phone stand"), q(10, position=2)]
    g = gate(queue=queue)
    assert not g.ok and "jump" in g.codes and "Phone stand" in g.reasons[0]
    allowed = gate(queue=queue, allow_jump=True)
    assert allowed.ok and any("Phone stand" in w for w in allowed.warnings)


def test_start_may_pass_own_items_and_items_behind():
    assert gate(queue=[q(5, position=1), q(10, position=2)], own={5, 10}).ok  # ours ahead
    assert gate(queue=[q(10, position=1), q(5, position=2)]).ok  # theirs behind
    assert gate(queue=[q(5, status="printing", position=1), q(10, position=2)]).ok  # not pending
    # no positions: list order decides
    assert "jump" in gate(queue=[q(5), q(10)]).codes
    assert gate(queue=[q(10), q(5)]).ok


def test_start_warnings_voice_not_ours_auto_start_calibration():
    g = gate(voice_request=True, own=set(), queue=[q(10, position=1, manual=False)],
             plate=PlateCheck(is_empty=True, needs_calibration=True))
    assert g.ok
    text = " ".join(g.warnings)
    assert "voice" in text and "not queued through" in text and "automatically" in text
    assert "calibration" in text


def test_start_collects_several_reasons():
    g = gate(idle(state="RUNNING", job_name="x"), in_cron=True, plate=None)
    assert {"in_cron", "busy", "plate_unknown"} <= set(g.codes)
    assert len(g.reasons) == len(g.codes)


# ---- clear_plate_gate -------------------------------------------------------------------------------
def cgate(status=None, plate=EMPTY, *, in_cron=False, cool=30.0, auto=()):
    return clear_plate_gate(status or idle(state="FINISH", bed_temp=26.0), plate, in_cron=in_cron,
                            cool_temp_c=cool, auto_start_pending=list(auto))


def test_clear_ok_when_cool_empty_and_no_auto_start():
    g = cgate()
    assert g.ok and g.action == "clear_plate" and g.needs_owner


def test_clear_blocked_hot_bed():
    g = cgate(idle(state="FINISH", bed_temp=48.0))
    assert not g.ok and "bed_hot" in g.codes and "48" in g.reasons[0]
    assert cgate(idle(state="FINISH", bed_temp=48.0), cool=50.0).ok


def test_clear_blocked_auto_start_items():
    g = cgate(auto=[q(7, manual=False, name="Gift box")])
    assert not g.ok and "auto_start_pending" in g.codes and "Gift box" in g.reasons[0]
    assert cgate(auto=[q(7, manual=True)]).ok  # manual items never auto-start
    assert cgate(auto=[q(7, status="completed", manual=False)]).ok


def test_clear_blocked_cron_active_plate():
    assert "in_cron" in cgate(in_cron=True).codes
    assert "busy" in cgate(idle(state="RUNNING", bed_temp=60.0)).codes
    assert "plate_occupied" in cgate(plate=OCCUPIED).codes
    assert "plate_uncertain" in cgate(plate=UNSURE).codes
    assert "plate_unknown" in cgate(plate=None).codes
    assert "offline" in cgate(idle(state="OFFLINE")).codes


def test_clear_unknown_bed_is_a_warning():
    g = cgate(idle(state="FINISH", bed_temp=None))
    assert g.ok and any("bed temperature" in w for w in g.warnings)


# ---- describe ---------------------------------------------------------------------------------------
def test_describe_tr_and_en():
    blocked = gate(idle(state="RUNNING", job_name="Gül kutusu"), plate=None)
    en, tr = describe(blocked, "en"), describe(blocked, "tr")
    assert en.startswith("Cannot start: ") and "busy" in en and en.endswith(".")
    assert tr.startswith("Başlatamam: ") and "meşgul" in tr and "Gül kutusu" in tr
    assert "printer" not in tr  # no English inside Turkish
    ok = gate(voice_request=True)
    assert describe(ok, "tr").startswith("Başlatılabilir") and "yazılı onay" in describe(ok, "tr")
    assert describe(ok, "en").startswith("Start possible") and "Note:" in describe(ok, "en")
    hot = cgate(idle(state="FINISH", bed_temp=41.0))
    assert describe(hot, "tr").startswith("Tablayı boş işaretleyemem") and "41" in describe(hot, "tr")
    assert describe(cgate(), "en") == "The plate can be marked clear."


def test_describe_is_short_and_handles_hand_made_gates():
    g = gate(idle(state="PAUSE", hms=[HMSError(code="0700-2000-0002-0001")]), in_cron=True, plate=OCCUPIED)
    for lang in ("tr", "en"):
        assert len(describe(g, lang)) < 400
    manual = Gate(ok=False, reasons=["custom reason"])
    assert describe(manual, "en") == "Blocked: custom reason."
    assert describe(Gate(ok=True), "tr") == "Tamam."
    d = g.to_dict()
    assert d["ok"] is False and d["items"][0]["code"] == "in_cron"
