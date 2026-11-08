"""Test bootstrap: import the plugin directory as package ``home3d_ws`` (like Hermes' loader does with
``hermes_plugins.<slug>``) and give every test its own data dir. Hermes core is NOT required."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PACKAGE = "home3d_ws"
ROOT = Path(__file__).resolve().parents[1]
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != ROOT]


def _load():
    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]
    spec = importlib.util.spec_from_file_location(PACKAGE, ROOT / "__init__.py",
                                                  submodule_search_locations=[str(ROOT)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = mod
    spec.loader.exec_module(mod)
    return mod


_load()


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("HOME3D_DATA_DIR", str(d))
    monkeypatch.setenv("HOME3D_SIM_SPEED", "0")  # simulated time only moves via advance()
    return d


@pytest.fixture
def pkg():
    return sys.modules[PACKAGE]
