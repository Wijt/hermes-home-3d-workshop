"""Workshop backend: read-only routes for the owner's "Workshop" screen in Hermes Desktop.

Mounted at ``/api/plugins/home-3d-workshop/`` once the plugin is enabled; the Desktop half calls it with
``ctx.rest(...)`` and the app's own auth.

Routes (all GET, all read-only):
    GET /health        cheap: the plugin's package loads, which backend is configured (no printer call)
    GET /overview      everything the screen shows (``home3d.workshop.build_overview``: printer, who it prints for,
                       what waits for the owner's approval with its facts and safety checklist, queue, done box,
                       notices, filament, human-needed moments, upgrade proposals, design versions, setup, watcher)
    GET /file?ref=     one file the overview named (design STL, design preview, stored camera photo) as a data URL

No route starts, stops, pauses, resumes, clears, queues, slices, imports or uploads anything, and none writes to the
printer or to Bambuddy: every signed-in dashboard user could call a route, and it would bypass the plugin's owner
check. Printer actions stay with ``/home3d approve ...``, ``/home3d stop`` and the other slash commands, which the
Desktop screen runs as the local user (``slash.exec``). ``/overview`` never switches the chamber light or takes a
photo either: it shows the newest stored one.

The host imports this file on its own (no package), so the plugin's ``home3d`` package is loaded by path under a
private module name; nothing here imports ``home3d`` relatively. Settings, data dir, store and backend are resolved
per request (the host sets ``HERMES_HOME`` per profile); no state is kept between requests. Routes are plain
``def``: FastAPI runs them in a worker thread, off the gateway's event loop.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

_PKG = "hermes_home3d_workshop_dashboard"
_ROOT = Path(__file__).resolve().parents[1]
_load_lock = threading.Lock()


def _home3d(sub: str):
    """``home3d.<sub>`` of this plugin folder, loaded once under a private package name."""
    with _load_lock:
        if _PKG not in sys.modules:
            spec = importlib.util.spec_from_file_location(_PKG, _ROOT / "__init__.py",
                                                          submodule_search_locations=[str(_ROOT)])
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load the plugin package from {_ROOT}")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[_PKG] = mod
            try:
                spec.loader.exec_module(mod)
            except BaseException:
                sys.modules.pop(_PKG, None)
                raise
    return importlib.import_module(f"{_PKG}.home3d.{sub}")


def _runtime():
    """A fresh Runtime per request: live settings from config.yaml (else the watcher snapshot), this profile's
    data dir, its store and a backend built from those settings."""
    return _home3d("runtime").Runtime(None)


def _unavailable(exc: BaseException) -> HTTPException:
    return HTTPException(status_code=503, detail=f"workshop package not loadable: {type(exc).__name__}: {exc}"[:300])


@router.get("/health")
def health():
    try:
        workshop = _home3d("workshop")
        return workshop.health(_runtime())
    except Exception as exc:  # the screen shows this as "backend not ready"
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


@router.get("/overview")
def overview():
    try:
        workshop = _home3d("workshop")
        rt = _runtime()
    except Exception as exc:
        raise _unavailable(exc) from None
    return workshop.build_overview(rt)


@router.get("/file")
def file(ref: str = ""):
    try:
        workshop = _home3d("workshop")
        rt = _runtime()
    except Exception as exc:
        raise _unavailable(exc) from None
    try:
        return workshop.file_payload(rt, ref)
    except workshop.FileRefError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from None
