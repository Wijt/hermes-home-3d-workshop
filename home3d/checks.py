"""Setup checks: what works on this install, as data a UI (or ``hermes home3d doctor --json``) can show.

``run_checks(rt)`` returns one dict per check, always in the order of ``CHECK_IDS``::

    {"id": "printer", "label": "Printer", "status": "ok" | "warn" | "missing" | "error",
     "detail": "IDLE · A1", "fix": ""}

``missing`` means "not set up yet" (a setting, a program, the watcher job); ``warn`` means it is set up but
something is off; ``error`` means it does not work. ``fix`` says what to do ("" when the status is ok).

Every check makes read requests only (GET; no photo, so the chamber light is never switched), never raises and
is bounded in time: backend requests are capped at ``REQUEST_TIMEOUT_S`` each and the whole run returns within
``timeout_s`` (a check still running then is reported as an error). The rules are the ones ``doctor`` prints:
the checks call the same ``cli._doctor_*`` helpers and only turn their rows into these dicts.

``capabilities(checks)`` sums them up as booleans: slice, find_models, camera, design, auto_eject, notify.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from .backends.base import BackendError

STATUSES = ("ok", "warn", "missing", "error")
_RANK = {"ok": 0, "warn": 1, "missing": 2, "error": 3}
CHECK_TIMEOUT_S = 15.0  # the whole run
REQUEST_TIMEOUT_S = 5.0  # each backend request
CRON_TIMEOUT_S = 10.0  # hermes cron list

CHECK_IDS = ("backend", "printer", "slicing", "models", "camera", "auto_eject", "plate_clear_setting", "openscad",
             "watcher", "delivery", "owner_ids")
LABELS = {
    "backend": "Printer manager", "printer": "Printer", "slicing": "Slicing", "models": "Model search and import",
    "camera": "Camera", "auto_eject": "Auto-eject preset", "plate_clear_setting": "Require plate clear (Bambuddy)",
    "openscad": "OpenSCAD and previews", "watcher": "Watcher job", "delivery": "Delivery targets",
    "owner_ids": "Owner ids",
}
CAPABILITIES = ("slice", "find_models", "camera", "design", "auto_eject", "notify")


def _check(cid: str, status: str, detail: str = "", fix: str = "") -> dict:
    status = status if status in STATUSES else "error"
    return {"id": cid, "label": LABELS.get(cid, cid), "status": status, "detail": str(detail or ""),
            "fix": "" if status == "ok" else str(fix or "")}


def _rows(fn: Callable[..., Any], *args: Any, **kw: Any) -> list[tuple[str, str, str]]:
    """Run a ``cli._doctor_*`` helper and collect its ``(status, label, detail)`` rows."""
    from .cli import DOCTOR_STATUS

    rows: list[tuple[str, str, str]] = []
    fn(*args, lambda level, label, detail="": rows.append((DOCTOR_STATUS.get(level, "error"), label, detail)),
       **kw)
    return rows


def _worst(rows: list[tuple[str, str, str]], default: str = "ok") -> str:
    return max((r[0] for r in rows), key=lambda s: _RANK.get(s, 3), default=default)


def _join(rows: list[tuple[str, str, str]]) -> str:
    return "; ".join(f"{label}: {detail}" if detail else label for _s, label, detail in rows)


def _is_sim(be: Any) -> bool:
    return getattr(be, "name", "") == "simulator"


# ---- the checks (each returns one or more check dicts; may raise: run_checks turns that into an error) ----------
def _c_backend(rt, be, be_error: str) -> list[dict]:
    s = rt.settings
    if be is None:
        missing = "not set" in be_error
        return [_check("backend", "missing" if missing else "error", be_error,
                       "Set bambuddy_url in the plugin settings (or backend: simulator to try it without a printer)"
                       if missing else "Check the backend settings")]
    if _is_sim(be):
        return [_check("backend", "ok", "simulator (a simulated printer: no hardware, nothing is printed)")]
    fn = getattr(be, "version", None)
    where = f"{s.bambuddy_url}, printer {s.printer_id}"
    if not callable(fn):
        be.status()
        return [_check("backend", "ok", f"{getattr(be, 'name', 'backend')} ({where})")]
    try:
        version = fn()
    except BackendError as e:
        if getattr(e, "status", None) is None:  # no HTTP answer at all
            return [_check("backend", "error", f"not reachable at {s.bambuddy_url}: {e}",
                           "Check that Bambuddy is running and that bambuddy_url points at it")]
        version = ""  # it answered: an older Bambuddy without the version endpoint
    return [_check("backend", "ok", f"Bambuddy {version or '(version unknown)'} ({where})")]


def _c_printer(rt, be, be_error: str) -> list[dict]:
    if be is None:
        return [_check("printer", "error", be_error, "Fix the printer manager first")]
    from .cli import _doctor_printer

    rows = _rows(_doctor_printer, be)
    status = _worst(rows)
    fix = ""
    if status == "error":
        fix = "Turn the printer on and check that the printer manager shows it connected"
    elif status == "warn":
        fix = "Clear the printer error (HMS) on the printer or in Bambuddy"
    return [_check("printer", status, " · ".join(d for _s, _l, d in rows if d), fix)]


def _c_presets(rt, be, be_error: str) -> list[dict]:
    """Slicing and the auto-eject preset: both read the slicer presets (one ``_doctor_presets`` pass)."""
    if be is None:
        return [_check("slicing", "error", be_error, "Fix the printer manager first"),
                _check("auto_eject", "error", be_error, "Fix the printer manager first")]
    from .cli import _doctor_presets

    rows = _rows(_doctor_presets, rt, be)
    if _is_sim(be):
        slicing = _check("slicing", "ok", "simulated slicer")
    else:
        pr = [r for r in rows if r[1] == "presets"]
        if not pr:
            slicing = _check("slicing", "warn", "unknown: this backend does not list slicer presets",
                             "Check slicing in the printer manager")
        elif pr[0][0] == "ok":
            slicing = _check("slicing", "ok", pr[0][2])
        else:
            slicing = _check("slicing", "error", pr[0][2],
                             "Check Bambuddy's slicer (Settings) and that the slicer presets load")
    eject_rows = [r for r in rows if r[1] != "presets"]
    status = _worst(eject_rows)
    fix = {"missing": "Set autoeject_printer_preset to a printer preset whose end G-code has the HOME3D AUTO-EJECT "
                      "block (see the README)",
           "warn": "Check the preset ids in autoeject_printer_preset, standard_printer_preset and process_presets",
           "error": "Fix the preset named here: the auto-eject preset needs the AUTO-EJECT end block, the standard "
                    "one must not have it"}.get(status, "")
    return [slicing, _check("auto_eject", status, _join(eject_rows), fix)]


def _c_models(rt, be, be_error: str) -> list[dict]:
    if be is None:
        return [_check("models", "error", be_error, "Fix the printer manager first")]
    if _is_sim(be):
        return [_check("models", "ok", "simulated MakerWorld catalog")]
    fn = getattr(be, "makerworld_status", None)
    if not callable(fn):
        return [_check("models", "warn", "unknown: this backend cannot report MakerWorld access", "")]
    try:
        d = fn()
    except BackendError as e:
        if getattr(e, "status", None) == 404:
            return [_check("models", "warn", "unknown: this Bambuddy has no /makerworld/status",
                           "Update Bambuddy, or try an import")]
        return [_check("models", "error", str(e), "Check that Bambuddy is reachable")]
    if d.get("can_download"):
        return [_check("models", "ok", "MakerWorld lookups and imports through Bambuddy (Bambu Cloud sign-in OK)")]
    if d.get("sign_in_expired"):
        return [_check("models", "warn", "the Bambu Cloud sign-in in Bambuddy has expired: imports fail",
                       "Sign in to Bambu Cloud again in Bambuddy")]
    return [_check("models", "missing", "Bambuddy has no Bambu Cloud sign-in: MakerWorld imports fail",
                   "Sign in to Bambu Cloud in Bambuddy (Settings)")]


def _c_camera(rt, be, be_error: str) -> list[dict]:
    if be is None:
        return [_check("camera", "error", be_error, "Fix the printer manager first")]
    if _is_sim(be):
        return [_check("camera", "ok", "simulated camera and plate check")]
    fn = getattr(be, "camera_status", None)
    if not callable(fn):
        return [_check("camera", "warn", "unknown: this backend cannot report its camera",
                       "Run hermes home3d doctor --plate for a real plate check")]
    try:
        d = fn()
    except BackendError as e:
        return [_check("camera", "error", f"camera not reachable: {e}",
                       "Check the printer's camera in Bambuddy (LAN mode, camera on)")]
    active = d.get("active")
    note = "the camera answers" + ("" if active is None else f" (stream {'active' if active else 'idle'})")
    return [_check("camera", "ok", note + "; not tested with a photo (hermes home3d doctor --plate takes one)")]


def _c_plate_clear(rt, be, be_error: str) -> list[dict]:
    if be is None:
        return [_check("plate_clear_setting", "error", be_error, "Fix the printer manager first")]
    from .cli import _doctor_plate_clear_setting

    rows = _rows(_doctor_plate_clear_setting, rt, be)
    if not rows:
        return [_check("plate_clear_setting", "ok", "not needed (simulator)" if _is_sim(be)
                       else "not needed (this backend has no queue manager of its own)")]
    status = _worst(rows)
    return [_check("plate_clear_setting", status, _join(rows),
                   "Turn on 'Require plate clear' in Bambuddy's settings" if status != "ok" else "")]


def _c_openscad(rt, be, be_error: str) -> list[dict]:
    from .cli import _doctor_openscad

    rows = _rows(_doctor_openscad)
    status = _worst(rows)
    fix = {"missing": "Install openscad (and xvfb, for the preview pictures)",
           "warn": "Install xvfb (xvfb-run) so the agent can look at its designs"}.get(status, "")
    return [_check("openscad", status, " · ".join(d for _s, _l, d in rows), fix)]


def _c_watcher(rt, be, be_error: str) -> list[dict]:
    from .cli import _doctor_watcher
    from .notify import hermes_bin

    rows = _rows(_doctor_watcher, rt, hermes_bin(), timeout=CRON_TIMEOUT_S)
    status = _worst(rows)
    last = [r for r in rows if r[1] == "watcher"]
    if last and last[0][0] == "ok" and status != "error":
        status = "ok"  # it runs: a job list we could not read does not change that
    fix = {"missing": "Run hermes home3d setup", "warn": "Start the Hermes scheduler (hermes gateway) and check "
                                                         "hermes home3d doctor"}.get(status, "Run hermes home3d doctor")
    return [_check("watcher", status, _join(rows), fix)]


def _c_delivery(rt, be, be_error: str) -> list[dict]:
    from .cli import _doctor_targets
    from .notify import _env_dry_run, hermes_bin

    rows = _rows(_doctor_targets, rt.settings)
    binary = hermes_bin()
    detail = _join(rows)
    set_ = [r for r in rows if r[0] == "ok"]
    if not binary:
        return [_check("delivery", "missing", "hermes binary not found: notices stay in the outbox; " + detail,
                       "Run inside Hermes, or put the hermes command on PATH")]
    if not set_:
        return [_check("delivery", "missing", detail, "Set owner_target and family_target (platform:chat id)")]
    if _env_dry_run():
        return [_check("delivery", "warn", "HOME3D_DRY_RUN is on: nothing is sent; " + detail,
                       "Unset HOME3D_DRY_RUN to send notices")]
    if len(set_) < len(rows):
        return [_check("delivery", "warn", detail, "Set the empty target (platform:chat id)")]
    return [_check("delivery", "ok", detail)]


def _c_owner_ids(rt, be, be_error: str) -> list[dict]:
    from .cli import _doctor_owner_ids

    s = rt.settings
    rows = _rows(_doctor_owner_ids, s)
    status = _worst(rows)
    if status == "ok" and not s.owner_ids:
        status = "warn"  # only a local session can approve
    return [_check("owner_ids", status, _join(rows),
                   "Add the owner's chat id to owner_ids (the owner sends /home3d whoami to see it)")]


_GROUPS: tuple[tuple[tuple[str, ...], Callable[..., list[dict]]], ...] = (
    (("backend",), _c_backend), (("printer",), _c_printer), (("slicing", "auto_eject"), _c_presets),
    (("models",), _c_models), (("camera",), _c_camera), (("plate_clear_setting",), _c_plate_clear),
    (("openscad",), _c_openscad), (("watcher",), _c_watcher), (("delivery",), _c_delivery),
    (("owner_ids",), _c_owner_ids),
)


def run_checks(rt, timeout_s: float = CHECK_TIMEOUT_S, request_timeout_s: float = REQUEST_TIMEOUT_S) -> list[dict]:
    """All setup checks, in ``CHECK_IDS`` order. Never raises; returns within about ``timeout_s``."""
    be: Optional[Any] = None
    be_error = ""
    try:
        be = rt.backend.with_timeout(request_timeout_s)
    except Exception as e:  # BackendError (no URL), or anything a broken setting raises
        be_error = str(e) or type(e).__name__
    results: dict[str, dict] = {}
    lock = threading.Lock()

    def run(ids: tuple[str, ...], fn: Callable[..., list[dict]]) -> None:
        try:
            out = fn(rt, be, be_error)
        except Exception as e:  # a check never takes the others down
            out = [_check(i, "error", f"check failed: {type(e).__name__}: {e}", "Run hermes home3d doctor")
                   for i in ids]
        with lock:
            for c in out:
                results.setdefault(c["id"], c)

    threads = []
    for ids, fn in _GROUPS:
        t = threading.Thread(target=run, args=(ids, fn), name=f"home3d-check-{ids[0]}", daemon=True)
        t.start()
        threads.append(t)
    deadline = time.monotonic() + max(0.1, float(timeout_s))
    for t in threads:
        t.join(max(0.0, deadline - time.monotonic()))
    with lock:
        return [dict(results[i]) if i in results else
                _check(i, "error", f"no answer within {timeout_s:g} s", "Check the printer manager and try again")
                for i in CHECK_IDS]


def capabilities(checks: list[dict]) -> dict:
    """``{"slice", "find_models", "camera", "design", "auto_eject", "notify"}`` as booleans from ``run_checks``."""
    st = {c.get("id"): c.get("status") for c in checks or [] if isinstance(c, dict)}

    def usable(cid: str) -> bool:
        return st.get(cid) in ("ok", "warn")

    reachable = usable("backend")
    return {"slice": reachable and usable("slicing"),
            "find_models": reachable and usable("models"),
            "camera": reachable and usable("camera"),
            "design": usable("openscad"),
            "auto_eject": reachable and st.get("auto_eject") == "ok",
            "notify": usable("delivery")}


__all__ = ["run_checks", "capabilities", "CHECK_IDS", "CAPABILITIES", "STATUSES"]
