"""gates.py: start / clear-plate safety decisions and their tr/en descriptions."""

from __future__ import annotations

from home3d_ws.home3d.backends.base import UNKNOWN, HMSError, PlateCheck, PrinterStatus, QueueItem
from home3d_ws.home3d.gates import Gate, clear_plate_gate, describe, resume_gate, start_gate

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
    g = gate(idle(state=UNKNOWN))
    assert not g.ok and "state_unknown" in g.codes
    assert "bilinmiyor" in describe(g, "tr") and "unknown" in describe(g, "en")
    assert "state_unknown" in gate(idle(state="")).codes


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
    g = gate(idle(state="FAILED"), plate=OCCUPIED, plate_confirmed=True)
    assert {"plate_occupied", "after_job"} <= set(g.codes)
    assert "after_job" in gate(idle(state="FINISH"), plate=None).codes
    finish = gate(idle(state="FINISH"), plate=EMPTY)
    assert finish.ok  # camera says empty after a finish: allowed, but flagged as camera-only
    assert "camera_only" in [i["code"] for i in finish.items] and "2%" in finish.warnings[0]
    assert "nobody has confirmed" in describe(finish, "en") and "%2" in describe(finish, "tr")
    confirmed = gate(idle(state="FINISH"), plate=EMPTY, plate_confirmed=True)
    assert confirmed.ok and confirmed.warnings == []


def test_start_after_failure_needs_a_person_not_just_the_camera():
    g = gate(idle(state="FAILED"), plate=EMPTY)
    assert not g.ok and g.codes == ["after_failure"]
    assert "/home3d approve clear" in g.reasons[0]
    assert "/home3d approve clear" in describe(g, "tr") and "yarıda kaldı" in describe(g, "tr")
    assert gate(idle(state="FAILED"), plate=EMPTY, plate_confirmed=True).ok
    # confirmed, but the camera disagrees: still blocked
    assert "plate_occupied" in gate(idle(state="FAILED"), plate=OCCUPIED, plate_confirmed=True).codes
    # no duplicate "after_job" when the failure itself already blocks
    both = gate(idle(state="FAILED"), plate=OCCUPIED)
    assert "after_failure" in both.codes and "after_job" not in both.codes


def test_start_blocked_when_plate_check_ran_in_the_dark():
    dark = PlateCheck(is_empty=None, difference_pct=0.0, message="chamber light was off", light_ok=False)
    g = gate(plate=dark)
    assert not g.ok and g.codes == ["plate_dark"]
    assert "kabin ışığı" in describe(g, "tr") and "chamber light" in describe(g, "en")
    # even a (buggy) backend that says empty without light is not trusted
    assert "plate_dark" in gate(plate=PlateCheck(is_empty=True, light_ok=False)).codes
    assert gate(plate=PlateCheck(is_empty=True, light_ok=True)).ok


def test_start_never_jumps_someone_elses_job():
    queue = [q(5, position=1, name="Phone stand"), q(10, position=2)]
    g = gate(queue=queue)
    assert not g.ok and "jump" in g.codes and "Phone stand" in g.reasons[0]
    allowed = gate(queue=queue, allow_jump=True)
    assert allowed.ok and any("Phone stand" in w for w in allowed.warnings)


def test_start_may_pass_own_items_and_items_behind():
    assert gate(queue=[q(5, position=1), q(10, position=2)], own={5, 10}).ok  # ours ahead
    assert gate(queue=[q(10, position=1), q(5, position=2)]).ok  # theirs behind
    for done in ("completed", "Failed", "CANCELLED", "canceled", "skipped"):
        assert gate(queue=[q(5, status=done, position=1), q(10, position=2)]).ok, done  # done items
    # no positions: list order decides
    assert "jump" in gate(queue=[q(5), q(10)]).codes
    assert gate(queue=[q(10), q(5)]).ok


def test_jump_check_is_case_insensitive_and_counts_every_unfinished_status():
    for status in ("Pending", "PENDING", "printing", "paused", "on_hold", ""):
        g = gate(queue=[q(5, status=status, position=1, name="Phone stand"), q(10, position=2)])
        assert not g.ok and g.codes == ["jump"], status
    # our own item may also be written "Pending"
    assert gate(queue=[q(10, status="Pending", position=1)]).ok


def test_jump_check_only_trusts_active_own_ids():
    # own_item_ids is the set of the workshop's ACTIVE jobs: an id not in it is somebody else's
    queue = [q(5, position=1, name="Phone stand"), q(10, position=2)]
    assert "jump" in gate(queue=queue, own={10}).codes
    assert gate(queue=queue, own={5, 10}).ok
    assert gate(queue=queue, own={"5", "10"}).ok  # ids may come back from JSON as strings


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


def test_clear_unknown_bed_blocks():
    g = cgate(idle(state="FINISH", bed_temp=None))
    assert not g.ok and g.codes == ["bed_unknown"] and "bed temperature" in g.reasons[0]
    assert "tabla sıcaklığı bilinmiyor" in describe(g, "tr")


def test_clear_blocked_on_unknown_state_and_dark_plate_check():
    assert "state_unknown" in cgate(idle(state=UNKNOWN, bed_temp=24.0)).codes
    assert "offline" in cgate(idle(state="FINISH", bed_temp=24.0, connected=False)).codes
    assert "plate_dark" in cgate(plate=PlateCheck(is_empty=None, light_ok=False)).codes


# ---- resume_gate ------------------------------------------------------------------------------------
RUNOUT = HMSError(code="0700-2000-0002-0001", message="AMS A Slot 1 filament has run out.")


def rgate(status=None, *, in_cron=False, ack=False):
    return resume_gate(status or idle(state="PAUSE"), in_cron=in_cron, hms_acknowledged=ack)


def test_resume_ok_when_paused_without_errors():
    g = rgate()
    assert g.ok and g.action == "resume" and g.needs_owner
    assert describe(g, "en").startswith("Resume possible") and describe(g, "tr").startswith("Devam ettirilebilir")


def test_resume_blocked_when_not_paused_offline_or_in_cron():
    for state in ("IDLE", "RUNNING", "FINISH", "FAILED", UNKNOWN):
        g = rgate(idle(state=state))
        assert not g.ok and "not_paused" in g.codes, state
    assert "offline" in rgate(idle(state="OFFLINE")).codes
    assert "offline" in rgate(idle(state="PAUSE", connected=False)).codes
    assert "in_cron" in rgate(in_cron=True).codes
    assert describe(rgate(idle(state="RUNNING")), "en").startswith("Cannot resume: ")
    assert describe(rgate(idle(state="RUNNING")), "tr").startswith("Devam ettiremem: ")


def test_resume_with_blocking_hms_needs_acknowledgement():
    paused = idle(state="PAUSE", hms=[RUNOUT])
    g = rgate(paused)
    assert not g.ok and g.codes == ["hms_unacknowledged"]
    assert "0700-2000-0002-0001" in g.reasons[0] and "/home3d approve resume ack" in g.reasons[0]
    assert "/home3d approve resume ack" in describe(g, "tr")
    acked = rgate(paused, ack=True)
    assert acked.ok and "0700-2000-0002-0001" in acked.warnings[0]
    # the harmless X-belt notice never needs an acknowledgement
    harmless = rgate(idle(state="PAUSE", hms=[HMSError(code="0300-1000-0002-0001")]))
    assert harmless.ok and "hms_ignored" in [i["code"] for i in harmless.items]
    # acknowledging does not make an idle printer resumable
    assert "not_paused" in rgate(idle(state="IDLE", hms=[RUNOUT]), ack=True).codes


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


def test_every_code_renders_in_both_languages():
    from home3d_ws.home3d.gates import _TEXT

    params = {"state": "FAILED", "job": "Gift box", "codes": "0700-2000-0002-0001", "item": 7, "status": "printing",
              "pct": 21.0, "msg": "uncertain", "name": "Phone stand", "other": 5, "bed": 41.0, "limit": 30.0,
              "names": "Gift box"}
    for code in _TEXT:
        for lang in ("en", "tr"):
            g = Gate(ok=False, action="resume")
            g.block(code, **params)
            text = describe(g, lang)
            assert "{" not in text and "}" not in text, (code, lang, text)
    for code in ("after_failure", "camera_only", "plate_dark", "not_paused", "hms_unacknowledged",
                 "hms_acknowledged", "bed_unknown"):
        assert code in _TEXT


# ---- fix round 2 ------------------------------------------------------------------------------------
BAND = PlateCheck(is_empty=None, difference_pct=19.9, message="uncertain: inside the false-positive band",
                  light_ok=True, uncertain_band=True)


def test_an_unconfirmed_failure_blocks_even_when_the_printer_forgot_it():
    """Safety 6 / e2e NEW-2: FAILED -> power cycle -> IDLE, or RUNNING -> IDLE (cancel): the camera alone never
    decides; ``after_failure`` comes from the store and blocks even with plate_confirmed for the current name."""
    g = gate(idle(state="IDLE", job_name=""), after_failure=True)
    assert not g.ok and "after_failure" in g.codes and "/home3d approve clear" in describe(g, "en")
    assert "after_failure" in gate(idle(state="IDLE"), after_failure=True, plate_confirmed=True).codes
    assert gate(idle(state="IDLE"), after_failure=False).ok


def test_a_person_can_overrule_only_the_false_positive_band():
    """e2e NEW-1: an empty plate read at 18-25 % used to dead-end both /home3d approve clear and start."""
    c = clear_plate_gate(idle(state="FAILED", bed_temp=26.0), BAND, in_cron=False, cool_temp_c=30.0,
                         auto_start_pending=[], person_confirms=True)
    assert c.ok and "plate_unsure_person" in [i["code"] for i in c.items]
    assert "19.9" in describe(c, "en") and "kamera emin değil" in describe(c, "tr")
    assert not cgate(plate=BAND).ok  # nobody is confirming: still uncertain
    s = gate(idle(state="FAILED", job_name="clip"), plate=BAND, plate_confirmed=True)
    assert s.ok and "plate_unsure_confirmed" in [i["code"] for i in s.items]
    assert "plate_uncertain" in gate(idle(state="FINISH"), plate=BAND).codes  # the camera alone: blocked
    for plate in (OCCUPIED, UNSURE,  # occupied / a doubt that is not the band
                  PlateCheck(is_empty=None, difference_pct=19.9, light_ok=False, uncertain_band=True),
                  PlateCheck(is_empty=None, difference_pct=19.9, needs_calibration=True, uncertain_band=True)):
        assert not gate(idle(state="FINISH"), plate=plate, plate_confirmed=True).ok, plate
        assert not clear_plate_gate(idle(state="FINISH", bed_temp=26.0), plate, in_cron=False, cool_temp_c=30.0,
                                    auto_start_pending=[], person_confirms=True).ok, plate


def test_a_skipped_plate_check_never_opens_a_gate():
    from home3d_ws.home3d.gates import printer_blocks

    busy = idle(state="RUNNING", job_name="x")
    assert printer_blocks(busy) and printer_blocks(idle(connected=False))
    assert printer_blocks(idle(hms=[HMSError(code="0700-2000-0002-0001")]))
    assert not printer_blocks(idle(hms=[HMSError(code="0700-2000-0002-0001")]), "clear_plate")
    assert not printer_blocks(idle()) and not printer_blocks(idle(state="FAILED"))
    g = gate(busy, plate=None, plate_skipped=True)
    assert not g.ok and g.codes == ["busy"]  # no noisy "no plate check yet"
    g = gate(idle(), plate=None, plate_skipped=True)  # a caller that skips on an idle printer: still blocked
    assert not g.ok and "plate_unknown" in g.codes
    c = clear_plate_gate(idle(), None, in_cron=False, cool_temp_c=30.0, auto_start_pending=[], plate_skipped=True)
    assert not c.ok and "plate_unknown" in c.codes


def test_start_waits_for_the_printer_managers_plate_clear_flag():
    g = gate(idle(awaiting_plate_clear=True))
    assert not g.ok and "awaiting_plate_clear" in g.codes and "/home3d approve clear" in describe(g, "en")
    assert gate(idle(awaiting_plate_clear=False)).ok and gate(idle(awaiting_plate_clear=None)).ok


# ---- fix round 2 (R2-6): the hook defers the plate to the handler -------------------------------------------------
def test_a_deferred_plate_check_does_not_block_but_says_so():
    g = gate(plate=None, plate_deferred=True)
    assert g.ok and [i["code"] for i in g.items] == ["plate_deferred"]
    assert "the camera checks the plate right before the start" in describe(g, "en")
    assert "kamera başlatmadan hemen önce tablaya bakacak" in describe(g, "tr")
    assert not gate(plate=None).ok  # without deferral an unknown plate still blocks


def test_a_deferred_check_after_a_finish_leaves_the_plate_to_the_handler():
    g = gate(idle(state="FINISH"), plate=None, plate_deferred=True)
    assert g.ok and "after_job" not in g.codes and "camera_only" not in [i["code"] for i in g.items]
    assert not gate(idle(state="FINISH"), plate=None).ok


def test_a_remembered_check_still_decides_when_deferred():
    """A recent plate check this process made (the handler's) counts in the hook: occupied / unsure block."""
    for plate, code in ((OCCUPIED, "plate_occupied"), (UNSURE, "plate_uncertain"),
                        (PlateCheck(is_empty=None, light_ok=False), "plate_dark")):
        g = gate(plate=plate, plate_deferred=True)
        assert not g.ok and code in g.codes, code
    g = gate(idle(state="FINISH"), plate=OCCUPIED, plate_deferred=True)
    assert {"plate_occupied", "after_job"} <= set(g.codes)
    assert gate(plate=EMPTY, plate_deferred=True).ok and "plate_deferred" not in [i["code"] for i in gate(
        plate=EMPTY, plate_deferred=True).items]


def test_deferral_never_opens_a_gate_the_printer_or_a_failure_closes():
    assert "busy" in gate(idle(state="RUNNING"), plate=None, plate_deferred=True, plate_skipped=True).codes
    g = gate(plate=None, plate_deferred=True, after_failure=True)
    assert not g.ok and "after_failure" in g.codes
    assert not gate(idle(state="FAILED"), plate=None, plate_deferred=True).ok


def test_clear_gate_with_a_deferred_plate():
    g = clear_plate_gate(idle(), None, in_cron=False, cool_temp_c=30, auto_start_pending=[], person_confirms=True,
                         plate_deferred=True)
    assert g.ok and [i["code"] for i in g.items] == ["plate_deferred_clear"]
    assert "right before it is marked clear" in describe(g, "en") and "boş işaretlenmeden" in describe(g, "tr")
    g = clear_plate_gate(idle(), OCCUPIED, in_cron=False, cool_temp_c=30, auto_start_pending=[],
                         person_confirms=True, plate_deferred=True)
    assert not g.ok and "plate_occupied" in g.codes
    g = clear_plate_gate(idle(), None, in_cron=False, cool_temp_c=30, auto_start_pending=[q(3, manual=False)],
                         plate_deferred=True)
    assert not g.ok and "auto_start_pending" in g.codes
