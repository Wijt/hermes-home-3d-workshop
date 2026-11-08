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
