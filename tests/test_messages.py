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
            preview_url="http://192.168.1.50:8000/gcode-viewer?library_file=5&plate=1", offline_min=12)

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
