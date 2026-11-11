"""``dashboard/plugin_api.py`` as the Hermes dashboard loads it: the file on its own (no package), under a
temporary ``HERMES_HOME`` with this plugin's settings in its ``config.yaml``, mounted on a FastAPI app.

Skipped when FastAPI (or httpx, for the test client) is not installed: the plugin itself never needs them.
"""

from __future__ import annotations

import base64
import importlib.util
import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard" / "plugin_api.py"
PREFIX = "/api/plugins/home-3d-workshop"
CONFIG = """plugins:
  enabled: [home-3d-workshop]
  entries:
    home-3d-workshop:
      settings:
        backend: simulator
        persona_name: {persona}
        owner_name: Sam
        language: en
"""


def _profile(root: Path, persona: str) -> Path:
    home = root / persona.lower()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(CONFIG.format(persona=persona), encoding="utf-8")
    return home


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.delenv("HOME3D_DATA_DIR", raising=False)  # resolve the data dir the way the gateway does
    monkeypatch.delenv("HOME3D_HERMES_CONFIG", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(_profile(tmp_path, "Mistik")))
    spec = importlib.util.spec_from_file_location("home3d_workshop_plugin_api_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.tmp = tmp_path
    return mod


@pytest.fixture
def client(api):
    app = FastAPI()
    app.include_router(api.router, prefix=PREFIX)
    return TestClient(app)


def _data(api) -> Path:
    return Path(api._home3d("config").data_dir())


def test_only_read_routes_exist(api):
    routes = {(r.path, frozenset(r.methods)) for r in api.router.routes}
    assert routes == {("/health", frozenset({"GET"})), ("/overview", frozenset({"GET"})),
                      ("/file", frozenset({"GET"}))}


def test_write_methods_are_refused(client):
    for path in ("overview", "file", "health", "start", "stop", "approve", "queue"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(f"{PREFIX}/{path}").status_code in (404, 405), (method, path)


def test_the_module_never_imports_home3d_relatively_or_by_name():
    text = SRC.read_text(encoding="utf-8")
    code = re.sub(r'""".*?"""', "", text, flags=re.S)
    assert not re.search(r"^\s*from\s+\.", code, re.M)
    assert not re.search(r"^\s*(from|import)\s+home3d\b", code, re.M)
    for word in ("eval(", "exec(", "subprocess", "os.system", "@router.post", "@router.put", "@router.delete"):
        assert word not in code, word


def test_health_is_cheap_and_names_the_backend(client, api, monkeypatch):
    sim = api._home3d("backends.simulator").SimulatorBackend
    monkeypatch.setattr(sim, "status", lambda self: pytest.fail("health read the printer"))
    r = client.get(f"{PREFIX}/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "schema": 1, "backend": "simulator", "persona": "Mistik", "simulated": True}


def test_overview_reads_this_profiles_settings_and_data(client, api):
    r = client.get(f"{PREFIX}/overview")
    assert r.status_code == 200
    ov = r.json()
    assert ov["persona"] == "Mistik" and ov["owner"] == "Sam" and ov["backend"] == "simulator"
    assert ov["printer"]["state"] == "idle" and ov["problems"] == []
    assert _data(api) == api.tmp / "mistik" / "plugin-data" / "home-3d-workshop"
    assert (_data(api) / "workshop.db").is_file()


def test_settings_and_data_dir_are_resolved_per_request(client, api, monkeypatch):
    assert client.get(f"{PREFIX}/overview").json()["persona"] == "Mistik"
    monkeypatch.setenv("HERMES_HOME", str(_profile(api.tmp, "Robo")))
    assert client.get(f"{PREFIX}/overview").json()["persona"] == "Robo"
    assert (api.tmp / "robo" / "plugin-data" / "home-3d-workshop" / "workshop.db").is_file()


def test_overview_shows_a_print_driven_on_the_simulator(client, api):
    be = api._home3d("backends.simulator").SimulatorBackend()
    so = api._home3d("backends.base").SliceOptions
    lib = be.import_model(1440007)
    sl = be.slice(lib.id, so(printer_preset="sim-autoeject"))
    item = be.queue_add(sl.library_file_id)
    be.start(item.id)
    be.advance(20)
    ov = client.get(f"{PREFIX}/overview").json()
    assert ov["printer"]["state"] == "printing" and ov["printer"]["job_name"] == "Coaster"
    assert ov["queue"][0]["id"] == item.id and ov["queue"][0]["ours"] is False  # not queued through the workshop
    assert ov["now"]["for"] is None and ov["waiting"] == []


def test_file_returns_a_data_url_and_refuses_everything_else(client, api, tmp_path):
    folder = _data(api) / "designs" / "bracket"
    folder.mkdir(parents=True)
    stl = folder / "bracket_v1.stl"
    stl.write_bytes(b"solid x\nendsolid x\n")
    (folder / "bracket_v1.scad").write_text("cube(1);")
    (tmp_path / "outside.png").write_bytes(b"x")
    (_data(api) / "media").mkdir()
    (_data(api) / "media" / "escape.png").symlink_to(tmp_path / "outside.png")

    r = client.get(f"{PREFIX}/file", params={"ref": "designs/bracket/bracket_v1.stl"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "bracket_v1.stl" and body["mime"] == "model/stl" and body["bytes"] == stl.stat().st_size
    assert base64.b64decode(body["dataUrl"].split(",", 1)[1]) == stl.read_bytes()

    for ref, code in {"": 400, "../../config.yaml": 400, "designs/../workshop.db": 400,
                      str(stl): 400, "workshop.db": 403, "watcher-config.json": 403,
                      "designs/bracket/bracket_v1.scad": 415, "designs/bracket/nope.stl": 404,
                      "media/escape.png": 403}.items():
        r = client.get(f"{PREFIX}/file", params={"ref": ref})
        assert r.status_code == code, (ref, r.status_code, r.text)
        assert "dataUrl" not in r.text


def test_a_package_that_cannot_load_is_a_clear_503(client, api, monkeypatch):
    def broken(sub):
        raise ImportError("home3d is missing")

    monkeypatch.setattr(api, "_home3d", broken)
    r = client.get(f"{PREFIX}/overview")
    assert r.status_code == 503 and "not loadable" in r.json()["detail"]
    assert client.get(f"{PREFIX}/health").json()["ok"] is False
