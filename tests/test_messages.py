"""messages.py: owner vs family texts (tr / en)."""

from __future__ import annotations

import re

import pytest

from home3d_ws.home3d import messages as M

FULL = dict(persona="Mıstık", owner="Sam", job="Gül kutusu", queue_item_id=12, requester="Mum",
            address_as="Anneciğim", progress=40, layer=12, total_layers=30, duration_min=130, grams=47.2,
            bed_temp=28, nozzle_temp=40, hms_code="0700-2000-0002-0001",
            hms_message="AMS A Slot 1 filament has run out.", wiki_url="https://wiki.bambulab.com/x",
            filament=True, reason="part still on the plate after 3 checks", eject_planned=True, plate_diff=1.8,
            next_job="Kalemlik", next_id=13, upgrade_title="Otomatik düşürme", upgrade_id=1,
            upgrade_label="parça alma", evidence=3, window_days=30,
            model_ref="https://makerworld.com/en/models/2335000",
            preview_url="http://192.168.1.50:8000/gcode-viewer?library_file=5&plate=1", offline_min=12,
            foreign=[{"id": 73, "name": "Soap dish", "since": "2025-11-04"}])

# English words / jargon that must never show up in a Turkish family line
_ENGLISH = re.compile(r"\b(auto|eject\w*|plate|print\w*|hms|layer|queue|failed|finish\w*|done|the|owner|"
                      r"paused?|status|nozzle|bed)\b", re.IGNORECASE)


def test_design_examples_verbatim():
    assert (M.render("finished_ejected", "family", "tr", job="Gül kutusu", address_as="Anneciğim")
            == '✅ Anneciğim, "Gül kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin.')
    assert (M.render("failed", "family", "tr", job="X", progress=40, owner="Sam")
            == '⚠️ Yazıcı durdu, "X" yarıda kaldı (%40). Sam\'a haber verdim.')


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("kind", M.KINDS)
def test_every_kind_renders_for_owner(kind, lang):
    text = M.render(kind, "owner", lang, **FULL)
    assert text and "None" not in text and "{" not in text


@pytest.mark.parametrize("kind", sorted(M.OWNER_ONLY))
def test_owner_only_kinds_have_no_family_text(kind):
    assert M.render(kind, "family", "tr", **FULL) == ""
    assert M.render(kind, "family", "en", **FULL) == ""


@pytest.mark.parametrize("kind", [k for k in M.KINDS if k not in M.OWNER_ONLY])
def test_family_lines_are_short_warm_and_plain_turkish(kind):
    text = M.render(kind, "family", "tr", **FULL)
    assert text
    assert len(text.splitlines()) <= 2
    assert len(text) < 200
    assert not _ENGLISH.search(text.replace("Gül kutusu", "")), text
    assert "0700" not in text and "http" not in text and "#12" not in text  # no codes, links, ids


def test_family_addresses_requester_and_falls_back_to_name():
    assert "Anneciğim," in M.render("finished", "family", "tr", job="Vazo", address_as="Anneciğim", requester="Mum")
    assert "Dad," in M.render("finished", "family", "en", job="Vase", requester="Dad")
    nobody = M.render("finished_ejected", "family", "tr", job="Vazo")
    assert nobody.startswith('✅ "Vazo" bitti') and "alabilirsiniz" in nobody


def test_failed_family_names_the_owner_never_hardcoded():
    assert "Dad'a haber verdim" in M.render("failed", "family", "tr", job="Vazo", owner="Dad")
    assert "Dad" not in M.render("failed", "family", "tr", job="Vazo", owner="Sam")
    generic = M.render("failed", "family", "tr", job="Vazo", owner="Owner")
    assert "Owner" not in generic and "haber verdim" in generic
    assert "I've told Sam." in M.render("failed", "family", "en", job="Vase", owner="Sam")


def test_paused_filament_mentions_runout_in_plain_words():
    tr = M.render("paused", "family", "tr", job="Vazo", progress=30, filament=True, owner="Sam")
    assert "filament bitti" in tr and "%30" in tr
    plain = M.render("paused", "family", "tr", job="Vazo", progress=30, owner="Sam")
    assert "filament" not in plain


def test_owner_texts_are_technical():
    failed = M.render("failed", "owner", "tr", **FULL)
    assert "katman 12/30" in failed and "0700-2000-0002-0001" in failed and "wiki.bambulab.com" in failed
    assert "#12" in failed and "tabla 28 °C" in failed
    started = M.render("started", "owner", "en", **FULL)
    assert "gcode-viewer" in started and "auto-eject: on" in started and "2 h 10 min" in started
    ready = M.render("ready_next", "owner", "tr", **FULL)
    assert "/home3d approve start 13" in ready
    up = M.render("upgrade_proposed", "owner", "en", **FULL)
    assert "#1" in up and "makerworld.com/en/models/2335000" in up and "3 times in 30 days" in up


def test_owner_turkish_translates_known_eject_reasons():
    t = M.render("plate_not_clear", "owner", "tr", job="Vazo", reason="part still on the plate after 3 checks",
                 plate_diff=41)
    assert "3 kontrolden sonra parça hâlâ tablada" in t and "fark %41" in t
    assert M.reason_text("bed did not cool below 30 C", "tr") == "tabla 30 °C altına soğumadı"
    assert M.reason_text("something new", "tr") == "something new"


def test_owner_finished_says_what_happens_next():
    assert "Otomatik düşürme bekleniyor" in M.render("finished", "owner", "tr", job="Vazo", eject_planned=True)
    assert "/home3d approve clear" in M.render("finished", "owner", "tr", job="Vazo", eject_planned=False)


def test_started_family_explains_auto_eject_without_jargon():
    t = M.render("started", "family", "tr", job="Vazo", address_as="Anneciğim", duration_min=75, eject_planned=True)
    assert t.splitlines()[0] == '🖨️ Anneciğim, "Vazo" basılmaya başladı, yaklaşık 1 saat 15 dakika sürecek.'
    assert "kendisi düşürecek" in t


def test_helpers():
    assert [M.dative(n) for n in ("Ayşe", "Mehmet", "Ali Baba", "Anne", "Sam", "Işık", "Ümit", "Dad")] == [
        "Ayşe'ye", "Mehmet'e", "Ali Baba'ya", "Anne'ye", "Sam'a", "Işık'a", "Ümit'e", "Dad'a"]
    assert M.duration(135, "tr") == "2 saat 15 dakika"
    assert M.duration(60, "en") == "1 hour"
    assert M.duration(45, "en", short=True) == "45 min"
    assert M.duration(None, "tr") == "" and M.duration(0, "tr") == ""
    assert M.pct(39.6, "tr") == "%40" and M.pct(39.6, "en") == "40%" and M.pct(None, "tr") == ""
    assert M.grams(47.4) == "47 g" and M.grams(3.25) == "3.2 g"


def test_missing_job_name_and_unknown_kind_do_not_break():
    assert M.render("finished", "family", "en") == "✅ The print is done and waiting on the printer."
    assert M.render("finished", "family", "tr").startswith("✅ Baskı bitti")
    assert M.render("mystery", "family", "tr", job="X") == ""
    assert "mystery" in M.render("mystery", "owner", "tr", job="X")


# ---- fix round 1 ------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", [k for k in M.KINDS if k not in M.OWNER_ONLY])
def test_family_names_the_print_by_the_request_not_the_file(kind):
    ctx = dict(FULL, job="ROSE BOX v3 final red skirt", family_job="çiçek kutusu")
    text = M.render(kind, "family", "tr", **ctx)
    assert "çiçek kutusu" in text and "ROSE" not in text, text
    owner = M.render(kind, "owner", "tr", **ctx)
    assert "çiçek kutusu" not in owner  # the owner keeps the file name


def test_family_job_falls_back_to_the_file_name_and_is_shortened():
    assert '"Vazo"' in M.render("finished", "family", "tr", job="Vazo", family_job="")
    long = "Mıstık, çiçekler için küçük ama çok şık bir hediye kutusu basar mısın lütfen"
    short = M.short_text(long)
    assert len(short) <= M.FAMILY_JOB_MAX and short.endswith("…") and not short.endswith(" …")
    assert short in M.render("finished", "family", "tr", job="x", family_job=long)
    assert M.short_text('  "bir   vazo"  ') == "bir vazo" and M.short_text(None) == ""


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_paused_owner_text_gives_the_approve_command_never_a_tool_name(lang):
    with_hms = M.render("paused", "owner", lang, **FULL)
    assert "/home3d approve resume" in with_hms and "/home3d approve resume ack" in with_hms
    assert "home3d_stop" not in with_hms
    no_hms = M.render("paused", "owner", lang, job="Vazo", progress=30)
    assert "/home3d approve resume" in no_hms and " ack" not in no_hms and "home3d_stop" not in no_hms


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_plate_texts_say_the_camera_thinks_never_verified(lang):
    for kind in ("plate_clear", "ready_next", "finished_ejected"):
        text = M.render(kind, "owner", lang, **FULL)
        assert ("ameraya göre tabla boş" if lang == "tr" else "amera thinks the plate is empty") in text, text
        assert "verified" not in text.lower() and "doğrula" not in text.lower()
    assert "%1.8" in M.render("plate_clear", "owner", "tr", plate_diff=1.8)
    photo = M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13, photo=True)
    assert ("Fotoğrafa" if lang == "tr" else "Check the photo") in photo


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_ready_next_names_foreign_jobs_ahead_and_the_jump_command(lang):
    ahead = [{"id": 73, "name": "sabun tabagi v2"}]
    text = M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13, ahead=ahead)
    assert '"sabun tabagi v2" (#73)' in text and text.rstrip().endswith("/home3d approve start 13 jump")
    assert "approve start 73" not in text
    plain = M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13)
    assert plain.rstrip().endswith("/home3d approve start 13")


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_confirm_first_after_a_failed_print(lang):
    for kind in ("ready_next", "plate_clear"):
        text = M.render(kind, "owner", lang, next_job="Kalemlik", next_id=13, confirm_first=True)
        assert "/home3d approve clear" in text
        assert "/home3d approve clear" not in M.render(kind, "owner", lang, next_job="Kalemlik", next_id=13)


def test_queue_foreign_is_owner_only_and_never_suggests_a_start():
    text = M.render("queue_foreign", "owner", "en", foreign=[{"id": 73, "name": "Soap dish", "since": "2025-11-04"}])
    assert '"Soap dish" (#73, added 2025-11-04)' in text and "approve start" not in text
    assert "eklenme 2025-11-04" in M.render("queue_foreign", "owner", "tr", **FULL)
    assert M.render("queue_foreign", "owner", "en") == ""
    assert M.render("queue_foreign", "family", "tr", **FULL) == ""


def test_eject_unverified_tells_the_owner_how_to_confirm_an_empty_plate():
    """e2e NEW-1: the camera may stay unsure on an empty plate; the owner's way out is /home3d approve clear."""
    for lang, word in (("en", "if it is empty"), ("tr", "boşsa")):
        text = M.render("eject_unverified", "owner", lang, persona="Mıstık", owner="Sam", job="kutu",
                        reason="plate check inconclusive after 3 checks", plate_diff=19.9)
        assert "/home3d approve clear" in text and word in text


# ---- fix round 2 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["tr", "en"])
def test_finish_text_for_the_real_eject_order(lang):
    """hw/F6: with the push inside the end G-code, FINISH means the push already ran."""
    text = M.render("finished", "owner", lang, job="Vazo", queue_item_id=7, eject_planned=True, eject_in_gcode=True)
    assert ("Baskının sonunda itildi; kamerayla kontrol ediyorum." if lang == "tr"
            else "Pushed off at the end of the print; checking the camera.") in text
    assert "bekleniyor" not in text and "pending" not in text
    combined = M.render("finished", "owner", lang, job="Vazo", queue_item_id=7, eject_planned=True,
                        eject_in_gcode=True, eject_result_follows=True)
    assert len(combined.splitlines()) == 1  # the camera's opinion follows in the same message


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_a_missed_end_promises_nothing_about_the_plate(lang):
    fam = M.render("finished", "family", lang, job="Vazo", address_as="Anneciğim", missed_end="busy")
    assert fam == ('✅ Anneciğim, "Vazo" bitti.' if lang == "tr" else '✅ Anneciğim, "Vazo" is done.')
    busy = M.render("finished", "owner", lang, job="Vazo", queue_item_id=7, missed_end="busy")
    idle = M.render("finished", "owner", lang, job="Vazo", queue_item_id=7, missed_end="idle")
    assert ("başka bir işe geçti" if lang == "tr" else "went straight on to another job") in busy
    assert ("kamerayla kontrol edeceğim" if lang == "tr" else "check the plate with the camera") in idle


def test_start_failed_quotes_the_printer_managers_error():
    text = M.render("start_failed", "owner", "en", job="towel hook", queue_item_id=200, requester="Mum",
                    error="The printer rejected the print command: MQTT command verification failed.")
    assert text.startswith('⚠️ The start did not happen: "towel hook" (#200) · for Mum')
    assert "Bambuddy: The printer rejected the print command" in text and "queue it again" in text
    assert M.render("start_failed", "family", "en", job="x") == ""
    long = M.render("start_failed", "owner", "tr", job="x", error="e" * 1000)
    assert "Başlatma gerçekleşmedi" in long and len(long) < 500


def test_approval_request_texts_give_the_exact_command_and_never_promise_a_start():
    start = M.render("approval_request", "owner", "en", who="Mum", action="start", queue_item_id=7, job="Gül kutusu",
                     duration_min=80, grams=35.2)
    assert start == '🙋 Mum asks to start #7 "Gül kutusu" (1 h 20 min, 35 g).\nTo start it: /home3d approve start 7'
    tr = M.render("approval_request", "owner", "tr", who="Annem", action="start", queue_item_id=7, job="Gül kutusu",
                  duration_min=80, grams=35.2)
    assert tr == ('🙋 Annem #7 "Gül kutusu" işinin başlatılmasını istiyor (1 sa 20 dk, 35 g).\n'
                  'Başlatmak için: /home3d approve start 7')
    ahead = M.render("approval_request", "owner", "en", who="Mum", queue_item_id=7, job="x",
                     ahead=[{"id": 73, "name": "soap dish"}])
    assert '"soap dish" (#73)' in ahead and ahead.endswith("/home3d approve start 7 jump")
    for action, cmd in (("resume", "/home3d approve resume"), ("clear_plate", "/home3d approve clear")):
        for lang in ("tr", "en"):
            text = M.render("approval_request", "owner", lang, who="Dad", action=action)
            assert text.endswith(cmd) and "Dad" in text
    for lang in ("tr", "en"):
        text = M.render("approval_request", "owner", lang, who="Mum", queue_item_id=7)
        assert "başlayacak" not in text and "will start" not in text


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_ready_next_says_to_mark_the_plate_clear_first_when_bambuddy_waits_for_it(lang):
    """With Bambuddy's "Require plate clear" on, a start is blocked until the plate is marked clear: the owner text
    says so before the start command (once: a failed print's confirm line already names the command)."""
    text = M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13, awaiting_clear=True)
    line = ("Bambuddy tablanın boş işaretlenmesini bekliyor: önce /home3d approve clear" if lang == "tr"
            else "Bambuddy waits for the plate to be marked clear: first /home3d approve clear")
    assert line in text and text.index(line) < text.index("/home3d approve start 13")
    assert text.rstrip().endswith("/home3d approve start 13")
    both = M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13, awaiting_clear=True,
                    confirm_first=True)
    assert both.count("/home3d approve clear") == 1
    assert "/home3d approve clear" not in M.render("ready_next", "owner", lang, next_job="Kalemlik", next_id=13)


# ---- review round 3 ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_r3_new_owner_texts(lang):
    tr = lang == "tr"
    stop = M.render("stopped", "owner", lang, job="towel hook", queue_item_id=103, progress=20, layer=5,
                    total_layers=40, requester="Mum", stopped_by="Sam", stop_reason="wrong colour")
    assert ("Sam durdurdu: wrong colour" if tr else "Stopped by Sam: wrong colour") in stop
    assert "/home3d approve clear" in stop and M.render("stopped", "family", lang, job="x") == ""
    back = M.render("online", "owner", lang, offline_min=43, state="RUNNING", job="vase", progress=55)
    assert ("43 dakika" if tr else "after 43 min") in back and ("baskıda" if tr else "printing") in back
    assert M.render("online", "family", lang) == ""
    fin = M.render("finished", "owner", lang, job="family hook", eject_unknown="foreign", camera_empty=True,
                   plate_diff=1.8)
    assert ("Atölye üzerinden eklenmedi" if tr else "Not queued through the workshop") in fin
    assert "approve clear" not in fin and ("No auto-eject" not in fin)
    fin = M.render("finished", "owner", lang, job="family hook", eject_unknown="unknown")
    assert "approve clear" in fin and ("bilinmiyor" if tr else "No eject plan known") in fin
    ask = M.render("approval_request", "owner", lang, action="resume", who="Mum", not_paused="FINISH")
    assert "approve resume" not in ask and ("bitti" if tr else "finished") in ask
    ready = M.render("ready_next", "owner", lang, next_job="Hook", next_id=8, camera_said=True, plate_diff=1.8)
    assert ("Kameraya" not in ready) if tr else ("camera" not in ready)


def test_started_by_tells_the_owner_who_started_what_and_how_to_stop_it():
    """start_policy known: a listed person started their own job, so the owner gets one line."""
    ctx = dict(who="Mum", job="Mum key tag v1", queue_item_id=7, duration_min=13)
    assert M.render("started_by", "owner", "en", **ctx) == \
        '▶️ Mum started "Mum key tag v1" (13 min). Stop it with /home3d stop.'
    assert M.render("started_by", "owner", "tr", **ctx) == \
        '▶️ Mum kendi işini başlattı: "Mum key tag v1" (13 dk). Durdurmak için: /home3d stop'
    assert M.render("started_by", "owner", "en", who="Mum", queue_item_id=7) == \
        "▶️ Mum started #7. Stop it with /home3d stop."
    assert M.render("started_by", "family", "en", **ctx) == "" and M.render("started_by", "team", "tr", **ctx) == ""
