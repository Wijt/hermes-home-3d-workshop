"""home3d.checks: structured setup checks on the simulator and on a stubbed Bambuddy (no network)."""

from __future__ import annotations

import argparse
import io
import json
import time
import urllib.error
import urllib.parse

import pytest

from home3d_ws.home3d import checks, cli, design, notify
from home3d_ws.home3d.backends import bambuddy as bb
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.runtime import Runtime

KEYS = {"id", "label", "status", "detail", "fix"}
OPENSCAD_OK = {"openscad": "/usr/bin/openscad", "version": "2021.01", "xvfb": "/usr/bin/xvfb-run", "previews": True}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No real hermes, no real cron list, a fixed OpenSCAD answer, a private HERMES_HOME."""
    monkeypatch.setattr(cli, "hermes_home", lambda: tmp_path / "hermes")
    monkeypatch.setattr(notify, "hermes_bin", lambda: None)
    monkeypatch.setattr(design, "openscad_status", lambda: dict(OPENSCAD_OK))
    monkeypatch.delenv("HOME3D_DRY_RUN", raising=False)


def _rt(**over) -> Runtime:
    base = dict(backend="simulator", owner_ids=["owner@demo"])
    base.update(over)
    return Runtime(None, settings=Settings(**base))


def _by_id(result: list[dict]) -> dict[str, dict]:
    return {c["id"]: c for c in result}


def _shape_ok(result: list[dict]) -> None:
    assert [c["id"] for c in result] == list(checks.CHECK_IDS)
    for c in result:
        assert set(c) == KEYS and c["status"] in checks.STATUSES and c["label"]
        assert (c["fix"] == "") == (c["status"] == "ok"), c


# ---- simulator ---------------------------------------------------------------------------------------------------
def test_simulator_checks_and_capabilities(monkeypatch):
    res = checks.run_checks(_rt())
    _shape_ok(res)
    c = _by_id(res)
    for cid in ("backend", "printer", "slicing", "models", "camera", "auto_eject", "plate_clear_setting", "openscad",
                "owner_ids"):
        assert c[cid]["status"] == "ok", c[cid]
    assert "simulator" in c["backend"]["detail"] and "IDLE" in c["printer"]["detail"]
    assert c["watcher"]["status"] == "missing" and "hermes home3d setup" in c["watcher"]["fix"]
    assert c["delivery"]["status"] == "missing"  # no hermes binary, no targets
    caps = checks.capabilities(res)
    assert set(caps) == set(checks.CAPABILITIES)
    assert caps == {"slice": True, "find_models": True, "camera": True, "design": True, "auto_eject": True,
                    "notify": False}


def test_delivery_and_owner_checks(monkeypatch):
    monkeypatch.setattr(notify, "hermes_bin", lambda: "/usr/bin/hermes")
    monkeypatch.setattr(cli, "_cron_list", lambda binary, all_jobs=True, timeout=60: "")
    full = dict(owner_target="whatsapp:<owner>", family_target="whatsapp:<family>")
    c = _by_id(checks.run_checks(_rt(**full)))
    assert c["delivery"]["status"] == "ok" and checks.capabilities(list(c.values()))["notify"] is True
    c = _by_id(checks.run_checks(_rt(owner_target="whatsapp:<owner>")))
    assert c["delivery"]["status"] == "warn" and "family_target" in c["delivery"]["detail"]
    assert c["delivery"]["fix"]
    monkeypatch.setenv("HOME3D_DRY_RUN", "1")
    assert _by_id(checks.run_checks(_rt(**full)))["delivery"]["status"] == "warn"
    monkeypatch.delenv("HOME3D_DRY_RUN")
    assert _by_id(checks.run_checks(_rt()))["delivery"]["status"] == "missing"
    # who can approve
    assert _by_id(checks.run_checks(_rt(owner_ids=[])))["owner_ids"]["status"] == "warn"
    c = _by_id(checks.run_checks(_rt(owner_ids=[], local_is_owner=False)))["owner_ids"]
    assert c["status"] == "error" and "whoami" in c["fix"]


def test_openscad_check(monkeypatch):
    monkeypatch.setattr(design, "openscad_status", lambda: {"openscad": None, "version": "", "xvfb": None,
                                                            "previews": False})
    res = checks.run_checks(_rt())
    assert _by_id(res)["openscad"]["status"] == "missing" and checks.capabilities(res)["design"] is False
    monkeypatch.setattr(design, "openscad_status", lambda: dict(OPENSCAD_OK, xvfb=None, previews=False))
    res = checks.run_checks(_rt())
    assert _by_id(res)["openscad"]["status"] == "warn" and "xvfb" in _by_id(res)["openscad"]["fix"]
    assert checks.capabilities(res)["design"] is True


def test_watcher_check_reads_the_last_pass(monkeypatch):
    rt = _rt()
    rt.store.kv_set("watcher", {"state": "IDLE", "updated": time.time() - 60})
    c = _by_id(checks.run_checks(rt))["watcher"]
    assert c["status"] == "ok" and "last pass 1 min ago" in c["detail"]


def test_plate_clear_setting_from_a_stubbed_backend(monkeypatch):
    rt = _rt()
    monkeypatch.setattr(rt.backend, "settings", lambda: {"require_plate_clear": False}, raising=False)
    c = _by_id(checks.run_checks(rt))["plate_clear_setting"]
    assert c["status"] == "warn" and "Require plate clear" in c["fix"]


# ---- stubbed Bambuddy ---------------------------------------------------------------------------------------------
BASE = "http://bambuddy.local:8000"
STATUS_IDLE = {"id": 1, "name": "Workshop A1", "connected": True, "state": "IDLE", "hms_errors": []}


class _Resp(io.BytesIO):
    headers: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeBambuddy:
    """``_urlopen`` stand-in: answers GETs from ``routes`` (a value, an int HTTP status, or an exception)."""

    def __init__(self, routes: dict, delay: float = 0.0):
        self.routes, self.delay, self.calls = routes, delay, []

    def __call__(self, req, timeout=None):
        path = urllib.parse.urlsplit(req.full_url).path[len("/api/v1"):]
        self.calls.append((req.get_method(), path, timeout))
        if self.delay:
            time.sleep(self.delay)
        if path not in self.routes:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b'{"detail":"Not Found"}'))
        v = self.routes[path]
        if isinstance(v, Exception):
            raise v
        if isinstance(v, int):
            raise urllib.error.HTTPError(req.full_url, v, "err", {}, io.BytesIO(b"{}"))
        return _Resp(json.dumps(v).encode())


def _routes(**over) -> dict:
    r = {
        "/updates/version": {"version": "1.3.0"},
        "/printers/1/status": STATUS_IDLE,
        "/queue/": [],
        "/slicer/presets": {"local": {"printer": [{"id": "7", "name": "A1 eject"}, {"id": "8", "name": "A1"}]},
                            "standard": {}},
        "/local-presets/7": {"setting": {"machine_end_gcode": "M400\n; HOME3D AUTO-EJECT\nG1 Y250"}},
        "/local-presets/8": {"setting": {"machine_end_gcode": "M400"}},
        "/settings/": {"require_plate_clear": True},
        "/makerworld/status": {"has_cloud_token": True, "can_download": True},
        "/printers/1/camera/status": {"active": False},
    }
    r.update(over)
    return r


def _bb_rt(monkeypatch, routes: dict, delay: float = 0.0, **over):
    fake = FakeBambuddy(routes, delay)
    monkeypatch.setattr(bb, "_urlopen", fake)
    settings = dict(backend="bambuddy", bambuddy_url=BASE, printer_id=1, autoeject_printer_preset="7",
                    standard_printer_preset="8")
    settings.update(over)
    return _rt(**settings), fake


def test_bambuddy_all_ok_with_read_requests_only(monkeypatch):
    rt, fake = _bb_rt(monkeypatch, _routes())
    res = checks.run_checks(rt)
    _shape_ok(res)
    c = _by_id(res)
    for cid in ("backend", "printer", "slicing", "models", "camera", "auto_eject", "plate_clear_setting"):
        assert c[cid]["status"] == "ok", c[cid]
    assert "Bambuddy 1.3.0" in c["backend"]["detail"] and "IDLE" in c["printer"]["detail"]
    assert "2 slicer preset(s)" in c["slicing"]["detail"]
    assert {m for m, _p, _t in fake.calls} == {"GET"}  # read requests only: no photo, no light, no write
    assert not any("snapshot" in p or "check-plate" in p or "chamber-light" in p for _m, p, _t in fake.calls)
    assert all(t is not None and t <= checks.REQUEST_TIMEOUT_S for _m, _p, t in fake.calls)
    assert checks.capabilities(res) == {"slice": True, "find_models": True, "camera": True, "design": True,
                                        "auto_eject": True, "notify": False}


def test_bambuddy_problems_are_named(monkeypatch):
    status_off = dict(STATUS_IDLE, connected=False)
    rt, _fake = _bb_rt(monkeypatch, _routes(**{
        "/updates/version": 404,  # an older Bambuddy: reachable, version unknown
        "/printers/1/status": status_off,
        "/makerworld/status": {"has_cloud_token": False, "can_download": False},
        "/local-presets/7": {"setting": {"machine_end_gcode": "M400"}},  # the marker is missing
        "/settings/": {"require_plate_clear": False},
        "/printers/1/camera/status": 500,
    }))
    res = checks.run_checks(rt)
    _shape_ok(res)
    c = _by_id(res)
    assert c["backend"]["status"] == "ok" and "version unknown" in c["backend"]["detail"]
    assert c["printer"]["status"] == "error" and "OFFLINE" in c["printer"]["detail"]
    assert c["models"]["status"] == "missing" and "Bambu Cloud" in c["models"]["fix"]
    assert c["auto_eject"]["status"] == "error" and "AUTO-EJECT" in c["auto_eject"]["detail"]
    assert c["plate_clear_setting"]["status"] == "warn"
    assert c["camera"]["status"] == "error"
    caps = checks.capabilities(res)
    assert caps["find_models"] is False and caps["auto_eject"] is False and caps["camera"] is False
    assert caps["slice"] is True


def test_bambuddy_expired_sign_in_and_unset_eject_preset(monkeypatch):
    rt, _fake = _bb_rt(monkeypatch, _routes(**{"/makerworld/status": {"has_cloud_token": True,
                                                                        "can_download": False,
                                                                        "sign_in_expired": True}}),
                       autoeject_printer_preset="")
    c = _by_id(checks.run_checks(rt))
    assert c["models"]["status"] == "warn" and "again" in c["models"]["fix"]
    assert c["auto_eject"]["status"] == "missing" and "autoeject_printer_preset" in c["auto_eject"]["fix"]


def test_bambuddy_unreachable_never_raises(monkeypatch):
    rt, _fake = _bb_rt(monkeypatch, {p: urllib.error.URLError("connection refused") for p in _routes()})
    res = checks.run_checks(rt)
    _shape_ok(res)
    c = _by_id(res)
    assert c["backend"]["status"] == "error" and "not reachable" in c["backend"]["detail"]
    for cid in ("printer", "slicing", "models", "camera"):
        assert c[cid]["status"] == "error", c[cid]
    caps = checks.capabilities(res)
    assert not (caps["slice"] or caps["find_models"] or caps["camera"] or caps["auto_eject"])
    assert caps["design"] is True  # OpenSCAD does not need the printer


def test_no_bambuddy_url_is_missing(monkeypatch):
    rt = _rt(backend="bambuddy", bambuddy_url="")
    c = _by_id(checks.run_checks(rt))
    assert c["backend"]["status"] == "missing" and "bambuddy_url" in c["backend"]["fix"]
    assert c["printer"]["status"] == "error"


def test_a_slow_printer_manager_cannot_hold_the_checks(monkeypatch):
    rt, _fake = _bb_rt(monkeypatch, _routes(), delay=1.5)
    t0 = time.monotonic()
    res = checks.run_checks(rt, timeout_s=0.3)
    assert time.monotonic() - t0 < 1.2
    _shape_ok(res)
    c = _by_id(res)
    assert c["printer"]["status"] == "error" and "no answer within 0.3 s" in c["printer"]["detail"]
    assert c["owner_ids"]["status"] == "ok"  # local checks still answer


def test_a_check_that_crashes_is_an_error_not_an_exception(monkeypatch):
    rt, _fake = _bb_rt(monkeypatch, _routes())
    monkeypatch.setattr(bb.BambuddyBackend, "camera_status", lambda self: 1 / 0)
    c = _by_id(checks.run_checks(rt))
    assert c["camera"]["status"] == "error" and "ZeroDivisionError" in c["camera"]["detail"]
    assert c["printer"]["status"] == "ok"


# ---- doctor --json ------------------------------------------------------------------------------------------------
def _parse(argv):
    parser = argparse.ArgumentParser(prog="hermes home3d")
    cli.setup_parser(parser)
    return parser.parse_args(argv)


def test_doctor_json(capsys):
    assert cli.handle(_parse(["doctor", "--json"]), _rt()) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True and set(data) == {"ok", "rows", "checks", "capabilities"}
    assert [c["id"] for c in data["checks"]] == list(checks.CHECK_IDS)
    assert data["capabilities"]["slice"] is True
    rows = {r["label"]: r for r in data["rows"]}
    assert rows["printer"]["status"] == "ok" and rows["cron job"]["status"] == "warn"  # unknown: no hermes binary
    assert rows["watcher"]["status"] == "missing"


def test_doctor_text_still_prints_missing_as_warn(capsys):
    cli.handle(_parse(["doctor"]), _rt(owner_ids=[]))
    out = capsys.readouterr().out
    assert "[warn] watcher" in out and "never ran: hermes home3d setup" in out and "[missing]" not in out
    assert "[  ok] owner_ids" in out  # unchanged: only a local session can approve
