"""upgrades.py: human-needed moments -> upgrade proposals."""

from __future__ import annotations

import time

from home3d_ws.home3d import upgrades as U
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.store import Store


def _age(store: Store, days: float) -> None:
    """Move every logged moment ``days`` into the past."""
    store._exec("UPDATE human_needed SET ts = ts - ?", (days * 86400,))


def test_kinds_contract():
    for kind in ("remove_part", "clean_plate", "filament_swap", "camera_check", "failure_check", "measure",
                 "post_process", "approve_start", "other"):
        spec = U.KINDS[kind]
        assert {"label", "threshold", "window_days", "title", "proposal", "model_ref"} <= set(spec)
        assert spec["threshold"] >= 1 and spec["window_days"] >= 1
    rp = U.KINDS["remove_part"]
    assert (rp["threshold"], rp["window_days"]) == (3, 30)
    assert rp["model_ref"] == "https://makerworld.com/en/models/2335000"
    assert "tilt" in rp["proposal"] and "auto-eject preset" in rp["proposal"]


def test_log_moment_normalises_unknown_kinds():
    store = Store()
    U.log_moment(store, "remove-part", "took the vase off", job_name="Vase", who="Dad", source="person")
    U.log_moment(store, "unbox_spool", "new spool arrived")
    rows = {r["kind"]: r for r in store.human_needed()}
    assert rows["remove_part"]["who"] == "Dad" and rows["remove_part"]["source"] == "person"
    assert rows["other"]["detail"].startswith("[unbox_spool]")


def test_threshold_creates_one_proposal_then_only_bumps_evidence():
    store, settings = Store(), Settings(language="en")
    for _ in range(2):
        U.log_moment(store, "remove_part", source="watcher")
    assert U.evaluate(store, settings) == []
    U.log_moment(store, "remove_part", source="watcher")
    created = U.evaluate(store, settings)
    assert len(created) == 1
    p = created[0]
    assert p["kind"] == "remove_part" and p["evidence"] == 3 and p["status"] == "proposed"
    assert p["model_ref"].endswith("/2335000") and p["window_days"] == 30
    assert store.upgrade_for_kind("remove_part")["title"] == U.KINDS["remove_part"]["title"]

    U.log_moment(store, "remove_part")
    assert U.evaluate(store, settings) == []
    assert store.upgrade_for_kind("remove_part")["evidence"] == 4
    assert len(store.upgrades()) == 1


def test_turkish_household_gets_turkish_titles():
    store = Store()
    for _ in range(3):
        U.log_moment(store, "remove_part")
    (p,) = U.evaluate(store, Settings(language="tr"))
    assert p["title"] == U.KINDS["remove_part"]["title_tr"]
    assert "eğ" in p["proposal"] and p["label"] == U.KINDS["remove_part"]["label_tr"]


def test_old_moments_outside_the_window_do_not_count():
    store, settings = Store(), Settings()
    for _ in range(3):
        U.log_moment(store, "remove_part")
    _age(store, 31)
    assert U.evaluate(store, settings) == []
    U.log_moment(store, "remove_part")
    assert U.evaluate(store, settings) == []


def test_rejected_proposal_needs_fresh_evidence():
    store, settings = Store(), Settings()
    for _ in range(2):
        U.log_moment(store, "camera_check")
    (p,) = U.evaluate(store, settings)
    store.update_upgrade(p["id"], status="rejected")
    time.sleep(0.01)
    assert U.evaluate(store, settings) == []  # old moments are not evidence again
    U.log_moment(store, "camera_check")
    assert U.evaluate(store, settings) == []
    U.log_moment(store, "camera_check")
    (again,) = U.evaluate(store, settings)
    assert again["id"] != p["id"] and again["evidence"] == 2


def test_installed_upgrade_is_not_proposed_again():
    store, settings = Store(), Settings()
    for _ in range(3):
        U.log_moment(store, "remove_part")
    (p,) = U.evaluate(store, settings)
    for status in ("accepted", "printing", "installed"):
        store.update_upgrade(p["id"], status=status)
    for _ in range(3):
        U.log_moment(store, "remove_part")
    assert U.evaluate(store, settings) == []
    assert store.upgrade_for_kind("remove_part")["evidence"] == 6


# ---- fix round 2 ----------------------------------------------------------------------------------------
def test_waiting_for_the_owner_is_logged_but_never_proposed():
    """cat/F4: approve_start used to propose a "standing approval window", which the plugin forbids."""
    store = Store()
    for _ in range(12):
        U.log_moment(store, "approve_start", "home3d_start 7 waited for the owner's approval", source="hook")
    assert len(store.human_needed("approve_start")) == 12  # still counted for /home3d moments
    assert U.evaluate(store, Settings(language="en")) == [] and store.upgrades() == []
    assert not U.proposes("approve_start") and U.proposes("remove_part")
    spec = U.KINDS["approve_start"]
    text = (spec["title"] + spec["proposal"] + spec["proposal_tr"]).lower()
    assert "window" not in text and "standing" not in text and "pencere" not in text


def test_turkish_labels_for_statuses_and_moment_details():
    assert U.status_label("proposed", "tr") == "önerildi" and U.status_label("installed", "tr") == "takıldı"
    assert U.status_label("proposed", "en") == "proposed"
    assert U.detail_text("part still on the plate after 3 checks", "tr") == "3 kontrolden sonra parça hâlâ tablada"
    assert U.detail_text("home3d_start 7 waited for the owner's approval", "tr") == \
        "home3d_start 7: sahibin onayını bekledi"
    assert U.detail_text("home3d_stop  waited for the owner's approval", "tr") == "home3d_stop: sahibin onayını bekledi"
    assert U.detail_text("something else", "tr") == "something else"
    assert U.detail_text("part still on the plate after 3 checks", "en") == "part still on the plate after 3 checks"
