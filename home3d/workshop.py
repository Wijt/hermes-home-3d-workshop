"""The owner's "Workshop" screen, read side: one JSON overview built from the plugin's own store and backend.

``build_overview(rt)`` fills the contract the Desktop screen renders (``SCHEMA_VERSION``); ``resolve_file`` and
``file_payload`` serve the files it points at (design STLs, design previews, stored camera photos) as opaque
references. Pure Python, no HTTP framework: ``dashboard/plugin_api.py`` is a thin router over this module.

What it never does:

- write to the printer or the printer manager. The only backend calls are ``status()`` and ``queue()`` (two GETs on
  Bambuddy; the simulator advances its virtual clock on any read, as it does for every other reader);
- switch the chamber light or take a photo (on a real A1 that is a light cycle and up to 12 s): the camera section
  shows the newest photo already stored under ``<data dir>/media``;
- run OpenSCAD or any other subprocess in the request, or call a model ("model calls: 0" is the watcher's design);
- wait for the setup checks: ``home3d.checks`` runs in a background thread and its rows are cached for
  ``SETUP_MAX_AGE_S`` (``setup_checks``); apart from that cache, settings, data dir, store and backend are resolved
  per call through ``rt``.

Every section is built on its own: a section that fails comes back empty and its error is listed in
``problems`` (the screen stays usable when, say, the printer manager is down).

People and groups come from the ``groups`` setting and ``notify.route_for``; notices from the store's outbox; the
done box from ``Store.done_box``; open human-needed moments from ``Store.open_human_needed``; the setup list from
``home3d.checks``.

A file reference is the file's path relative to the plugin data dir (``designs/<slug>/<slug>_v2.stl``,
``media/watcher/sim-snapshot-0003.png``). It is opaque to the front end, which only passes it back to
``GET file?ref=``; ``resolve_file`` re-checks every reference (no absolute paths, no ``..``, only the
``designs`` and ``media`` folders, a suffix allowlist, a size cap, ``resolve(strict=True)`` inside the data dir).
"""

from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Optional

from .backends.base import ACTIVE_STATES, FAILED, FINISH, IDLE, OFFLINE, PAUSE
from .config import data_dir, watch_script_path

SCHEMA_VERSION = 1
BACKEND_TIMEOUT_S = 10.0  # each printer-manager read; the dashboard request itself times out at 60 s
FILE_ROOTS = ("designs", "media")  # the only data-dir folders a file reference may point into
MIME = {".stl": "model/stl", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
MAX_FILE_BYTES = {".stl": 64 << 20}  # STL; images below
MAX_IMAGE_BYTES = 16 << 20
DONE_BOX_LIMIT = 10
NEEDS_HUMAN_DAYS = 30
NEEDS_HUMAN_LIMIT = 20
DESIGN_LIMIT = 12
DESIGN_VERSION_LIMIT = 12
NOTICE_RECENT = 12
PHOTO_MATCH_S = 180  # an outbox photo sent this long after a job's end event (and naming it) is that job's photo

_STATE = {IDLE: "idle", "PREPARE": "printing", "RUNNING": "printing", PAUSE: "paused", FINISH: "finished",
          FAILED: "failed", OFFLINE: "offline"}
_ACTION = {"start": "start", "clear_plate": "clear", "resume": "resume"}
_END_EVENTS = ("finished_ejected", "finished", "failed", "stopped", "plate_not_clear", "eject_unverified",
               "plate_clear")  # photo preference order
_JOB_SUFFIXES = (".gcode.3mf", ".3mf", ".gcode", ".stl")


class FileRefError(Exception):
    """A file reference that is refused or missing. ``status`` is the HTTP status the router answers with."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ---- small helpers ------------------------------------------------------------------------------------------------
def _int(v: Any) -> Optional[int]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _num(v: Any, digits: int = 1) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return round(float(v), digits)
    except (TypeError, ValueError):
        return None


def _stem(name: Any) -> str:
    n = str(name or "").strip()
    for suf in _JOB_SUFFIXES:
        if n.lower().endswith(suf):
            return n[: -len(suf)].strip()
    return n


def pretty_name(name: Any) -> str:
    """``flower_box_v2.gcode.3mf`` -> ``flower box v2`` (what the household calls it). A design's file name
    (``mum-key-tag_v1``, a slug) reads like its title in the Designs list: ``Mum key tag v1``."""
    n = " ".join(_stem(name).replace("_", " ").split())
    words = n.split(" ")
    if words and _SLUG.fullmatch(words[0]) and "-" in words[0]:
        words[0] = words[0].replace("-", " ").capitalize()
        n = " ".join(words)
    return n


_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")
_TOOL_TOKEN = re.compile(r"\bhome3d_[a-z_]+\b")


def _same_job(a: Any, b: Any) -> bool:
    x, y = _stem(a).lower(), _stem(b).lower()
    return bool(x) and x == y


def _data_root() -> Path:
    return data_dir().resolve()


def file_ref(path: Any) -> Optional[str]:
    """The reference of a file under one of ``FILE_ROOTS`` (None when it is elsewhere or missing)."""
    if not path:
        return None
    try:
        p = Path(str(path)).resolve(strict=True)
        rel = p.relative_to(_data_root())
    except (OSError, RuntimeError, ValueError):
        return None
    if not rel.parts or rel.parts[0] not in FILE_ROOTS or p.suffix.lower() not in MIME:
        return None
    return rel.as_posix()


def _settings(rt) -> Any:
    return rt.settings


# ---- merged code: groups, outbox, done box, setup checks -----------------------------------------------------------
def _origin(store: Any, job: Optional[dict]) -> dict:
    """Where a job's request came from (``platform``, ``chat_id``, ``sender_id``), as the watcher routes it."""
    req: dict = {}
    if job and job.get("request_id"):
        try:
            req = store.get_request(int(job["request_id"])) or {}
        except Exception:
            req = {}
    return req if (req.get("chat_id") or req.get("sender_id")) else (job or {})


def person_group(settings: Any, name: str, origin: Optional[dict] = None) -> str:
    """The configured group (``groups`` setting) a request belongs to, by ``notify.route_for``: the group whose chat
    it came from, else the group listing its sender. "" for the owner, a household member outside every group
    (``family_target``) and anyone not announced."""
    from . import notify

    o = origin or {}
    route = notify.route_for(settings, requester=str(name or ""), platform=str(o.get("platform") or ""),
                             chat_id=str(o.get("chat_id") or ""), sender_id=str(o.get("sender_id") or ""))
    return route.group if route.announce else ""


def groups(settings: Any) -> list[dict]:
    """The chat groups the workshop serves (``Settings.group_list``): ``[{"name", "tone", "language", "members"}]``
    with ``members`` a count. No target and no member id: the screen only names them."""
    return [{"name": g.name, "tone": g.tone, "language": settings.group_language(g), "members": len(g.members or [])}
            for g in settings.group_list()]


NOTICE_STATUSES = ("pending", "sent", "failed", "no_target", "dry_run")


def notices(rt, store: Any, *, owner: bool = True) -> dict:
    """Did everyone get told? From the store's outbox (``notify.outbox_summary`` counts and the newest records).

    ``{"pending", "failed", "dry_run", "no_target", "sent", "recent": [{"id", "ts", "to", "group", "audience",
    "kind", "job", "status", "attempts", "error", "text", "photo"}]}``. ``dry_run`` is a simulated notice (nothing was
    sent on purpose), not a failure. A target is never included; ``text`` and ``error`` only when the viewer is the
    owner (``owner``), otherwise the screen gets counts and who each notice was for."""
    from . import notify

    summary = notify.outbox_summary(store)
    if summary.get("error"):
        raise RuntimeError(summary["error"])
    counts = summary.get("counts") or {}
    out: dict = {s: int(counts.get(s) or 0) for s in NOTICE_STATUSES}
    recent = []
    for r in store.outbox(limit=NOTICE_RECENT):
        status = str(r.get("status") or "pending")
        status = status if status in NOTICE_STATUSES else "pending"
        text = " ".join(str(r.get("text") or "").split())
        err = str(r.get("last_error") or "")[:200]
        if status == "no_target":
            err = err or "no chat to send to: kept in the outbox"
        recent.append({"id": _int(r.get("id")), "ts": float(r.get("ts") or 0), "to": notify._to_label(r),
                       "group": str(r.get("group_name") or ""), "audience": str(r.get("audience") or ""),
                       "kind": ",".join(r.get("kinds") or []), "job": pretty_name(r.get("job_name")),
                       "status": status, "attempts": int(r.get("attempts") or 0),
                       "error": err if owner else "", "text": text[:160] if owner else "",
                       "photo": file_ref(r.get("media")) if owner else None})
    out["recent"] = recent
    return out


SETUP_MAX_AGE_S = 300.0  # a setup check result is reused this long
SETUP_WAIT_S = 2.0  # the first overview waits at most this long for a check run; later ones never wait
SETUP_RUN_TIMEOUT_S = 15.0  # one background run of home3d.checks (each backend request: 5 s)
_setup_lock = threading.Lock()
_setup_cache: dict = {}  # key -> (wall ts, rows)
_setup_running: dict = {}  # key -> threading.Event (set when the run ends)


def _setup_key(settings: Any) -> tuple:
    return (str(data_dir()), settings.backend, settings.bambuddy_url, settings.printer_id,
            settings.autoeject_printer_preset, settings.owner_target, settings.family_target,
            tuple(sorted(json.dumps(g, sort_keys=True, default=str) for g in settings.groups or [])),
            tuple(settings.owner_ids or []))


def setup_checks(rt, settings: Any) -> dict:
    """The setup list from ``home3d.checks.run_checks`` (the same rows as ``hermes home3d doctor --json``), cached.

    The checks probe the printer manager and run ``hermes cron list``: up to 15 s. The overview never waits for that:
    the rows are kept for ``SETUP_MAX_AGE_S`` per profile and settings; an older or missing result starts one
    background run, and the overview returns the last rows at once (or waits up to ``SETUP_WAIT_S`` the very first
    time). ``{"checks": [...], "checked_ts": wall ts or None, "pending": a run is going on}``. The checks only read
    (no photo, so no chamber light)."""
    from . import checks as checks_mod

    key = _setup_key(settings)
    now = time.time()
    with _setup_lock:
        hit = _setup_cache.get(key)
        running = _setup_running.get(key)
        if (hit is None or now - hit[0] >= SETUP_MAX_AGE_S) and running is None:
            running = threading.Event()
            _setup_running[key] = running

            def work(ev: threading.Event = running) -> None:
                try:
                    rows = checks_mod.run_checks(rt, timeout_s=SETUP_RUN_TIMEOUT_S)
                    with _setup_lock:
                        _setup_cache[key] = (time.time(), [_check_row(r) for r in rows if isinstance(r, dict)])
                except Exception:
                    pass
                finally:
                    with _setup_lock:
                        _setup_running.pop(key, None)
                    ev.set()

            threading.Thread(target=work, name="home3d-workshop-setup", daemon=True).start()
    if hit is None and running is not None:
        running.wait(SETUP_WAIT_S)
        with _setup_lock:
            hit = _setup_cache.get(key)
    with _setup_lock:
        pending = key in _setup_running
    return {"checks": list(hit[1]) if hit else [], "checked_ts": hit[0] if hit else None, "pending": pending}


def _check_row(r: dict) -> dict:
    st = str(r.get("status") or "").strip().lower()
    return {"id": str(r.get("id") or ""), "label": str(r.get("label") or r.get("id") or ""),
            "status": st if st in ("ok", "warn", "missing", "error") else "error",
            "detail": str(r.get("detail") or ""), "fix": str(r.get("fix") or "")}


# ---- sections -------------------------------------------------------------------------------------------------------
def _read_printer(be) -> tuple[Any, Optional[list], str, str]:
    """(status or None, active queue or None, status error, queue error). Short timeouts on a real manager."""
    try:
        be = be.with_timeout(BACKEND_TIMEOUT_S)
    except Exception:
        pass
    status = queue = None
    s_err = q_err = ""
    try:
        status = be.status()
    except Exception as e:  # BackendError, or anything a broken backend raises
        s_err = str(e) or type(e).__name__
    if status is not None and status.state != OFFLINE and status.connected:
        try:
            queue = be.queue()
        except Exception as e:
            q_err = str(e) or type(e).__name__
    return status, queue, s_err, q_err


def _printer(status: Any, err: str) -> dict:
    if status is None:
        return {"state": "offline", "job_name": "", "progress": 0, "remaining_min": None, "layer": None,
                "total_layers": None, "bed_temp": None, "nozzle_temp": None, "printer_name": "",
                "errors": [{"code": "", "text": err or "the printer manager did not answer"}],
                "awaiting_plate_clear": False}
    errors = [{"code": h.code, "text": h.message or "printer error", "url": h.wiki_url}
              for h in status.blocking_hms]
    state = _STATE.get(status.state, "unknown")
    if not status.connected:
        state = "offline"
    return {"state": state, "raw_state": status.state, "job_name": pretty_name(status.job_name),
            "progress": _num(status.progress) or 0, "remaining_min": _int(status.remaining_min),
            "layer": _int(status.layer), "total_layers": _int(status.total_layers),
            "bed_temp": _num(status.bed_temp), "nozzle_temp": _num(status.nozzle_temp),
            "printer_name": status.printer_name or "", "errors": errors,
            "awaiting_plate_clear": bool(status.awaiting_plate_clear)}


def _who(settings: Any, requester: Any, origin: Optional[dict] = None) -> dict:
    """``{"name", "group"}``; an empty requester is the owner (the store's convention). ``origin``: where the request
    came from (``_origin``), so the group is the one the watcher announces the job in."""
    name = str(requester or "").strip() or str(settings.owner_name or "Owner")
    try:
        group = person_group(settings, str(requester or "").strip(), origin)
    except Exception:
        group = ""
    return {"name": name, "group": group}


def _slice_meta(store: Any, sliced_file_id: Any) -> dict:
    sid = _int(sliced_file_id)
    if sid is None:
        return {}
    meta = store.kv_get(f"slice:{sid}") or {}
    return meta if isinstance(meta, dict) else {}


def _design_of(store: Any, meta: dict) -> Optional[tuple[str, int]]:
    """(slug, version) of the design a sliced file was made from (``home3d_design action=upload``), or None."""
    fid = _int(meta.get("source_file_id"))
    if fid is None:
        return None
    ref = store.kv_get(f"design_lib:{fid}")
    if not isinstance(ref, dict) or not ref.get("slug") or _int(ref.get("version")) is None:
        return None
    return str(ref["slug"]), int(ref["version"])


def _design_model(slug: str, version: int) -> Optional[dict]:
    from . import design

    try:
        v = design.load_version(slug, version)
    except Exception:
        return None
    stl = file_ref(v.get("stl_path"))
    previews = [r for r in (file_ref(p) for p in v.get("previews") or []) if r]
    if not stl and not previews:
        return None
    return {"stl": stl, "preview": previews[0] if previews else None, "design": slug, "version": version}


def _model_for(store: Any, job: Optional[dict], meta: Optional[dict] = None) -> Optional[dict]:
    if not job:
        return None
    meta = meta if meta is not None else _slice_meta(store, job.get("sliced_file_id"))
    d = _design_of(store, meta)
    return _design_model(*d) if d else None


def _facts(job: Optional[dict], meta: dict, item: Any, trays: list) -> dict:
    slot = _int(meta.get("suggested_ams_slot"))
    tray = next((t for t in trays if t.slot == slot), None) if slot is not None else None
    minutes = _int(meta.get("print_time_min"))
    if minutes is None and item is not None and getattr(item, "print_time_s", None):
        minutes = round(item.print_time_s / 60)
    return {"print_time_min": minutes, "grams": _num(meta.get("grams")),
            "material": str(meta.get("material") or ""), "color": str(meta.get("colour") or ""),
            "slot": slot, "slot_label": f"Slot {slot + 1}" if slot is not None else "",
            "slot_loaded": None if tray is None else {"material": tray.material, "color": tray.color,
                                                      "remain_pct": tray.remain_pct, "loaded": tray.loaded},
            "eject_planned": bool((job or {}).get("eject_planned") if job else meta.get("eject_planned")),
            "eject_reason": str((job or {}).get("eject_reason") or "; ".join(meta.get("eject_reasons") or [])),
            "max_z_mm": _num((job or {}).get("max_z_mm") if job else meta.get("max_z")),
            "quality": str(meta.get("quality") or "")}


# checklist groups: id -> (label, block codes, warn codes)
_START_CHECKS = (
    ("printer_free", "Printer is free", ("offline", "busy", "state_unknown", "in_cron"), ()),
    ("no_error", "No printer error", ("hms",), ("hms_ignored",)),
    ("still_waiting", "Job is still waiting in the queue", ("item_missing", "item_not_pending"),
     ("not_ours", "not_manual")),
    ("plate", "Plate is clear", ("awaiting_plate_clear", "after_failure", "after_job", "plate_unknown",
                                 "plate_occupied", "plate_uncertain", "plate_dark"),
     ("plate_deferred", "camera_only", "plate_unsure_confirmed", "needs_calibration")),
    ("turn", "Nobody else's job is skipped", ("jump",), ("jump_allowed",)),
)
_CLEAR_CHECKS = (
    ("printer_free", "Printer is not printing", ("offline", "busy", "state_unknown", "in_cron"), ()),
    ("bed_cool", "Bed has cooled down", ("bed_hot", "bed_unknown"), ()),
    ("plate", "Camera agrees the plate is clear", ("plate_unknown", "plate_occupied", "plate_uncertain",
                                                   "plate_dark"),
     ("plate_deferred_clear", "plate_unsure_person", "needs_calibration")),
    ("auto_start", "Nothing starts by itself", ("auto_start_pending",), ()),
)
_RESUME_CHECKS = (
    ("paused", "Print is paused", ("offline", "not_paused", "in_cron"), ()),
    ("no_error", "Printer error acknowledged", ("hms_unacknowledged",), ("hms_acknowledged", "hms_ignored")),
)
_OK_DETAIL = {"plate_deferred": "the camera checks the plate right before the start",
              "plate_deferred_clear": "the camera checks the plate right before it is marked clear"}


def _checklist(gate: Any, groups_spec: tuple) -> list[dict]:
    """The gate's items as a fixed, readable checklist (a passing check says so; a block says why)."""
    blocks = [i for i in gate.items if i.get("level") == "block"]
    warns = [i for i in gate.items if i.get("level") == "warn"]
    text = {id(i): t for i, t in zip(blocks, gate.reasons)}
    text.update({id(i): t for i, t in zip(warns, gate.warnings)})
    used: set[int] = set()
    out = []
    for cid, label, block_codes, warn_codes in groups_spec:
        b = [i for i in blocks if i["code"] in block_codes]
        w = [i for i in warns if i["code"] in warn_codes]
        used.update(id(i) for i in b + w)
        detail = "; ".join(text.get(id(i)) or _OK_DETAIL.get(i["code"], i["code"]) for i in (b or w))
        out.append({"id": cid, "label": label, "ok": not b, "detail": _tidy(detail)})
    for i in blocks + warns:  # anything a newer gate adds still shows up
        if id(i) not in used:
            out.append({"id": i["code"], "label": _tidy(text.get(id(i)) or i["code"]), "ok": i["level"] != "block",
                        "detail": ""})
    return out


def _tidy(text: str) -> str:
    """Gate texts name files as the printer manager does: drop the ``.gcode.3mf`` noise for the screen."""
    for suf in (".gcode.3mf", ".gcode"):
        text = text.replace(suf, "")
    return text


def _filament_check(facts: dict, trays: list) -> Optional[dict]:
    slot = facts.get("slot")
    want = facts.get("material") or ""
    if slot is None:
        return {"id": "filament", "label": "Filament is loaded", "ok": True,
                "detail": "no slot chosen: the printer manager picks the tray"}
    tray = next((t for t in trays if t.slot == slot), None)
    if tray is None or not tray.loaded:
        return {"id": "filament", "label": "Filament is loaded", "ok": False,
                "detail": f"slot {slot + 1} looks empty"}
    try:
        from .gcode import material_family

        same = not tray.material or not want or material_family(tray.material) == material_family(want)
    except Exception:
        same = not tray.material or not want or tray.material.upper().startswith(want.upper()[:3])
    detail = f"slot {slot + 1}: {tray.material or '?'} {tray.color or ''}".strip()
    if tray.remain_pct is not None:
        detail += f", {tray.remain_pct}% left"
    if not same:
        detail += f" (the job was sliced for {want})"
    return {"id": "filament", "label": "Filament is loaded", "ok": bool(same), "detail": detail}


def _gate_for(action: str, rt, settings: Any, status: Any, queue: list, qid: Optional[int]) -> Optional[Any]:
    from . import gates

    if status is None:
        return None
    store = rt.store
    if action == "start":
        confirmed = False
        if status.job_name:
            try:
                confirmed = bool(store.plate_confirmed(status.job_name, status))
            except Exception:
                confirmed = False
        return gates.start_gate(status, queue, qid if qid is not None else -1, plate=None, in_cron=False,
                                own_item_ids=store.active_job_ids(), plate_confirmed=confirmed,
                                after_failure=store.unconfirmed_failure() is not None, plate_deferred=True,
                                requesters=store.active_job_requesters(), owner_name=settings.owner_name)
    if action == "clear":
        return gates.clear_plate_gate(status, None, in_cron=False, cool_temp_c=float(settings.eject_cool_temp_c),
                                      auto_start_pending=queue, person_confirms=True, plate_deferred=True)
    if action == "resume":
        return gates.resume_gate(status, in_cron=False)
    return None


def _waiting_entry(rt, settings: Any, status: Any, queue: list, trays: list, *, action: str, rid: Optional[int],
                   qid: Optional[int], who: str, asked_ts: float, source: str) -> dict:
    store = rt.store
    job = store.get_job(qid) if qid is not None else None
    item = next((q for q in queue if q.id == qid), None) if qid is not None else None
    meta = _slice_meta(store, (job or {}).get("sliced_file_id"))
    facts = _facts(job, meta, item, trays) if action == "start" else {}
    gate = _gate_for(action, rt, settings, status, queue, qid)
    spec = {"start": _START_CHECKS, "clear": _CLEAR_CHECKS, "resume": _RESUME_CHECKS}[action]
    checklist = _checklist(gate, spec) if gate is not None else [
        {"id": "printer", "label": "Printer is reachable", "ok": False, "detail": "no printer status"}]
    if action == "start":
        fil = _filament_check(facts, trays)
        if fil:
            checklist.append(fil)
    codes = set(getattr(gate, "codes", []) or [])
    command = {"start": f"home3d approve start {qid}", "clear": "home3d approve clear",
               "resume": "home3d approve resume"}[action]
    alt = None
    if action == "start" and "jump" in codes and codes <= {"jump"}:
        alt = {"command": f"home3d approve start {qid} jump", "label": "Start ahead of the queue"}
    elif action == "resume" and "hms_unacknowledged" in codes and codes <= {"hms_unacknowledged"}:
        alt = {"command": "home3d approve resume ack", "label": "Resume despite the printer error"}
    if job:
        name = pretty_name(job.get("name") or (item.name if item else ""))
    elif item is not None:
        name = pretty_name(item.name)
    else:  # clear / resume: about the print on the printer
        name = pretty_name(status.job_name) if status is not None else ""
    req = None
    if job and job.get("request_id"):
        try:
            req = store.get_request(int(job["request_id"]))
        except Exception:
            req = None
    asked_name = who or (job or {}).get("requester") or ""
    return {"id": rid, "key": f"req-{rid}" if rid is not None else f"{action}-{qid}", "action": action,
            "source": source, "queue_item_id": qid, "name": name,
            "asked_by": _who(settings, asked_name, _origin(store, job) if job else None),
            "asked_ts": float(asked_ts or 0), "request_text": str((req or {}).get("text") or ""),
            "facts": facts, "checklist": checklist, "ready": bool(gate is not None and gate.ok),
            "command": command, "alt": alt, "model": _model_for(store, job, meta) if job else None}


def _waiting(rt, settings: Any, status: Any, queue: Optional[list]) -> list[dict]:
    """Open family approval requests (``resolved_ts`` NULL, announced or not) that still make sense, then the
    workshop's own manual-start jobs nobody has asked about yet: each one waits for the owner's click."""
    store = rt.store
    queue = queue or []
    trays = list(status.trays) if status is not None else []
    pending_ids = {q.id for q in queue if q.is_pending}
    out: list[dict] = []
    covered: set[tuple] = set()
    horizon = time.time() - 24 * 3600
    for r in sorted(store.approval_requests(limit=100), key=lambda r: r.get("id") or 0):
        if r.get("resolved_ts") is not None or float(r.get("ts") or 0) < horizon:
            continue
        action = _ACTION.get(str(r.get("action") or ""))
        qid = _int(r.get("queue_item_id"))
        if action is None:
            continue
        if action == "start" and qid not in pending_ids:
            continue  # it started, or was removed, meanwhile
        if action == "resume" and (status is None or status.state != PAUSE):
            continue
        if action == "clear" and (status is None or status.state in ACTIVE_STATES):
            continue
        key = (action, qid)
        if key in covered:
            continue  # two people asked for the same thing: one card, the first asker
        covered.add(key)
        out.append(_waiting_entry(rt, settings, status, queue, trays, action=action, rid=_int(r.get("id")),
                                  qid=qid, who=str(r.get("who") or ""), asked_ts=float(r.get("ts") or 0),
                                  source="request"))
    active = store.active_job_ids()
    for q in queue:
        if not q.is_pending or q.id not in active or ("start", q.id) in covered:
            continue
        job = store.get_job(q.id) or {}
        ts = float(job.get("updated") or 0)
        if job.get("request_id"):
            req = store.get_request(int(job["request_id"])) or {}
            ts = float(req.get("ts") or ts)
        out.append(_waiting_entry(rt, settings, status, queue, trays, action="start", rid=None, qid=q.id,
                                  who=str(job.get("requester") or ""), asked_ts=ts, source="queue"))
    return out


def _queue(rt, settings: Any, queue: Optional[list]) -> list[dict]:
    store = rt.store
    active = store.active_job_ids()
    out = []
    for q in queue or []:
        ours = q.id in active
        job = store.get_job(q.id) if ours else None
        meta = _slice_meta(store, (job or {}).get("sliced_file_id"))
        out.append({"id": q.id, "name": pretty_name(q.name),
                    "for": _who(settings, job.get("requester"), _origin(store, job)) if job else {"name": "", "group": ""},
                    "status": str(q.status or ""), "position": q.position, "manual_start": bool(q.manual_start),
                    "ours": ours, "print_time_min": round(q.print_time_s / 60) if q.print_time_s else
                    _int(meta.get("print_time_min")),
                    "eject_planned": bool(job.get("eject_planned")) if job else None,
                    "model": _model_for(store, job, meta) if job else None})
    return out


def _now(rt, settings: Any, status: Any, queue: Optional[list]) -> Optional[dict]:
    if status is None or not status.job_name or status.state not in (*ACTIVE_STATES, FINISH, FAILED):
        return None
    store = rt.store
    job = None
    printing = next((q for q in queue or [] if str(q.status or "").lower() == "printing"), None)
    if printing is not None:
        job = store.get_job(printing.id)
        if job is not None and job.get("state") not in ("queued", "printing", "finished", "cleared", "failed"):
            job = None
    if job is None:
        job = store.job_by_name(status.job_name)
    qid = _int((job or {}).get("queue_item_id")) if job else (printing.id if printing is not None else None)
    return {"queue_item_id": qid, "name": pretty_name(status.job_name),
            "for": _who(settings, job.get("requester"), _origin(store, job)) if job else None,
            "ours": job is not None, "eject_planned": bool(job.get("eject_planned")) if job else None,
            "started_ts": _num((job or {}).get("started_ts"), 0),
            "model": _model_for(store, job) if job else None}


def _media_root() -> Path:
    return data_dir() / "media"


def _latest_photo() -> tuple[Optional[Path], float]:
    root = _media_root()
    best, best_ts = None, 0.0
    if not root.is_dir():
        return None, 0.0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(IMAGE_SUFFIXES):
                continue
            p = Path(dirpath) / f
            try:
                ts = p.stat().st_mtime
            except OSError:
                continue
            if ts > best_ts:
                best, best_ts = p, ts
    return best, best_ts


def _camera(status: Any) -> dict:
    path, ts = _latest_photo()
    offline = status is None or status.state == OFFLINE or not status.connected
    note = ("Latest stored photo; this screen never switches the chamber light on." if path else
            "No photo yet: the watcher takes one near the end of each print.")
    if offline:
        note = "The printer is offline. " + note
    return {"available": not offline, "frame": file_ref(path), "taken_ts": ts or None, "note": note}


def _photo_for(store: Any, watcher_kv: dict, job: dict, events: list, outbox: list) -> Optional[str]:
    """The photo that went out with this job's end notice (the family's copy first: it shows the part, the owner's
    may show the empty plate after a push), else the watcher's remembered last-layer photo of it."""
    name = job.get("name") or ""
    words = [pretty_name(name).lower()]
    if job.get("request_id"):
        try:
            words.append(str((store.get_request(int(job["request_id"])) or {}).get("text") or "").strip().lower())
        except Exception:
            pass
    words = [w for w in words if w]
    # the finish notice first (its photo shows the part), plate notices after; newest first within a kind
    ends = sorted(((_END_EVENTS.index(e.get("kind")), -float(e.get("ts") or 0)) for e in events
                   if e.get("kind") in _END_EVENTS and _same_job(e.get("job_name"), name)))
    for _rank, neg_ts in ends:
        ets = -neg_ts
        # the watcher records the event, then sends (owner, then family; each up to 60 s + one retry)
        near = [r for r in outbox if r.get("media") and ets <= float(r.get("ts") or 0) <= ets + PHOTO_MATCH_S]
        named = [r for r in near if any(w in str(r.get("text") or "").lower() for w in words)]
        for r in sorted(named, key=lambda r: (r.get("audience") != "family", float(r.get("ts") or 0))):
            ref = file_ref(r.get("media"))
            if ref:
                return ref
    if _same_job(watcher_kv.get("photo_for_job"), name):
        ref = file_ref(watcher_kv.get("photo_path"))
        if ref:
            return ref
    prev = watcher_kv.get("prev_photo")
    if isinstance(prev, dict) and _same_job(prev.get("job"), name):
        return file_ref(prev.get("path"))
    return None


_LEFT_PLATE = {"pushed_off": ("pushed", "pushed off into the done box"),
               "on_plate": ("on_plate", "waiting on the plate for a person"),
               "taken_off": ("taken_off", "a person took it off the plate"),
               "unknown": ("unknown", "finished; how it left the plate is not known")}


def _done_box(rt, settings: Any) -> list[dict]:
    """The delivered parts (``Store.done_box``), newest first: ``id`` is the part id ``/home3d collected <id>`` takes,
    ``job_id`` the queue item it was printed as. ``finished_ts`` is wall time (the watcher records it so). The photo
    is the one recorded with the part, else the one that went out with the job's end notice."""
    store = rt.store
    rows = store.done_box(limit=DONE_BOX_LIMIT)
    if not rows:
        return []
    w = store.kv_get("watcher") or {}
    w = w if isinstance(w, dict) else {}
    events = outbox = None
    out = []
    for r in rows:
        qid = _int(r.get("queue_item_id"))
        kind, detail = _LEFT_PLATE.get(str(r.get("left_plate") or ""), _LEFT_PLATE["unknown"])
        photo = file_ref(r.get("photo"))
        if photo is None:
            job = (store.get_job(qid) if qid is not None else None) or {"name": r.get("job_name") or ""}
            if events is None:
                events, outbox = store.events(limit=300), store.outbox(limit=300)
            photo = _photo_for(store, w, job, events, outbox)
        name = str(r.get("title") or "").strip() or pretty_name(r.get("job_name"))
        requester = str(r.get("requester") or "").strip()
        part_id = _int(r.get("id"))
        out.append({"id": part_id, "job_id": qid, "name": name,
                    "for": {"name": requester or str(settings.owner_name or "Owner"),
                            "group": str(r.get("group_name") or "")},
                    "finished_ts": _num(r.get("ts"), 0), "outcome": kind, "detail": detail, "photo": photo,
                    "collected": bool(r.get("collected")), "collected_by": str(r.get("collected_by") or ""),
                    "collected_ts": _num(r.get("collected_ts"), 0), "command": f"home3d collected {part_id}"})
    return out


def _filament(status: Any) -> dict:
    if status is None:
        return {"slots": []}
    return {"slots": [{"slot": t.slot, "label": f"Slot {t.slot + 1}", "material": t.material or "",
                       "color": t.color or "", "name": t.name or "", "remain_pct": t.remain_pct,
                       "loaded": bool(t.loaded)} for t in status.trays]}


def _needs_human(store: Any) -> list[dict]:
    """The moments still waiting for a person (``Store.open_human_needed``) first, then the resolved ones of the
    last ``NEEDS_HUMAN_DAYS`` days, newest first within each."""
    from . import upgrades

    open_rows = store.open_human_needed(limit=NEEDS_HUMAN_LIMIT)
    seen = {r.get("id") for r in open_rows}
    closed = [r for r in store.human_needed(since_days=NEEDS_HUMAN_DAYS, limit=NEEDS_HUMAN_LIMIT)
              if r.get("id") not in seen and r.get("resolved")]
    out = []
    for r in (open_rows + closed)[:NEEDS_HUMAN_LIMIT]:
        kind = str(r.get("kind") or "other")
        label = upgrades.text_for(kind, "en")["label"]
        detail = upgrades.detail_text(r.get("detail"), "en")
        if _TOOL_TOKEN.search(detail or ""):
            detail = ""  # an internal note ("home3d_start start:5 waited ..."): the label and the job say it
        text = label[:1].upper() + label[1:] + (f": {detail}" if detail else "")
        out.append({"id": _int(r.get("id")), "kind": kind, "text": text, "ts": float(r.get("ts") or 0),
                    "open": not r.get("resolved"), "job": pretty_name(r.get("job_name")),
                    "who": str(r.get("who") or ""), "source": str(r.get("source") or ""),
                    "resolved_by": str(r.get("resolved_by") or "")})
    return out


def _upgrades(store: Any) -> list[dict]:
    order = {"proposed": 0, "accepted": 1, "printing": 2, "installed": 3, "rejected": 4}
    rows = sorted(store.upgrades(), key=lambda u: (order.get(u.get("status"), 9), -float(u.get("updated") or 0)))
    return [{"id": str(u.get("id")), "kind": str(u.get("kind") or ""), "title": str(u.get("title") or ""),
             "why": str(u.get("proposal") or ""), "count": int(u.get("evidence") or 0),
             "status": str(u.get("status") or ""), "model_ref": str(u.get("model_ref") or ""),
             "updated_ts": float(u.get("updated") or 0)} for u in rows]


_FACT_KEYS = ("ok", "error", "size_mm", "volume_cm3", "est_grams_max", "bodies", "triangles", "fits_build_volume",
              "simple", "part", "from_version", "render_s", "params", "library_file_ids", "created")


def _designs() -> list[dict]:
    from . import design

    out = []
    for row in design.list_designs(limit=DESIGN_LIMIT):
        slug = str(row.get("name") or "")
        versions = []
        for v in design.versions(slug)[-DESIGN_VERSION_LIMIT:]:
            try:
                d = design.load_version(slug, v)
            except Exception:
                continue
            meta = d.get("meta") or {}
            facts = {k: meta.get(k) for k in _FACT_KEYS if meta.get(k) not in (None, "", [], {})}
            facts["ok"] = bool(meta.get("ok"))
            facts["warnings"] = len(meta.get("warnings") or [])
            note = str(meta.get("error") or "") if not meta.get("ok") else (
                f"part: {meta['part']}" if meta.get("part") not in (None, "", "all") else "")
            versions.append({"version": v, "stl": file_ref(d.get("stl_path")),
                             "previews": [r for r in (file_ref(p) for p in d.get("previews") or []) if r],
                             "facts": facts, "note": note})
        out.append({"slug": slug, "title": pretty_name(slug.replace("-", " ")).capitalize(),
                    "latest_ok": row.get("latest_ok"), "updated": row.get("updated") or "", "versions": versions})
    return out


def _watcher(rt, settings: Any) -> dict:
    store = rt.store
    w = store.kv_get("watcher") or {}
    updated = w.get("updated") if isinstance(w, dict) else None
    if not isinstance(updated, (int, float)):
        updated = store.kv_updated("watcher")
    from . import hooks

    try:
        stale_s = float(hooks.watcher_stale_s(settings))
    except Exception:
        stale_s = 600.0
    fresh = isinstance(updated, (int, float)) and 0 <= time.time() - float(updated) < stale_s
    try:
        installed = watch_script_path().is_file()
    except OSError:
        installed = False
    err = store.kv_get("watcher_error")
    return {"fresh": bool(fresh), "last_pass_ts": float(updated) if isinstance(updated, (int, float)) else None,
            "interval": str(settings.watch_interval or "2m"), "model_calls": 0, "installed": installed,
            "stale_after_s": stale_s, "error": str(err)[:200] if err else ""}


def _viewer(settings: Any) -> dict:
    if getattr(settings, "local_is_owner", True):
        return {"is_owner": True, "reason": ""}
    return {"is_owner": False,
            "reason": "local sessions are not the owner (local_is_owner is off): approve from an owner chat"}


# ---- public API -----------------------------------------------------------------------------------------------------
def build_overview(rt) -> dict:
    """Everything the Workshop screen shows, in one JSON-ready dict (see the module doc for what it never does)."""
    settings = _settings(rt)
    problems: list[str] = []

    def section(name: str, fn: Callable[[], Any], empty: Any) -> Any:
        try:
            return fn()
        except Exception as e:  # one broken section never takes the screen down
            problems.append(f"{name}: {type(e).__name__}: {e}"[:300])
            return empty

    status, queue, s_err, q_err = _read_printer(rt.backend)
    if q_err:
        problems.append(f"queue: {q_err}"[:300])
    printer = _printer(status, s_err)
    viewer = _viewer(settings)
    watcher = section("watcher", lambda: _watcher(rt, settings),
                      {"fresh": False, "last_pass_ts": None, "interval": "", "model_calls": 0})
    out = {
        "schema": SCHEMA_VERSION,
        "generated_ts": time.time(),
        "backend": str(settings.backend),
        "persona": str(settings.persona_name or ""),
        "owner": str(settings.owner_name or ""),
        "simulated": settings.backend == "simulator",
        "printer": printer,
        "now": section("now", lambda: _now(rt, settings, status, queue), None),
        "camera": section("camera", lambda: _camera(status), {"available": False, "frame": None, "taken_ts": None,
                                                              "note": ""}),
        "waiting": section("waiting", lambda: _waiting(rt, settings, status, queue), []),
        "queue": section("queue", lambda: _queue(rt, settings, queue), []),
        "done_box": section("done_box", lambda: _done_box(rt, settings), []),
        "notices": section("notices", lambda: notices(rt, rt.store, owner=viewer["is_owner"]),
                           {**{s: 0 for s in NOTICE_STATUSES}, "recent": []}),
        "filament": section("filament", lambda: _filament(status), {"slots": []}),
        "needs_human": section("needs_human", lambda: _needs_human(rt.store), []),
        "upgrades": section("upgrades", lambda: _upgrades(rt.store), []),
        "designs": section("designs", _designs, []),
        "setup": section("setup", lambda: setup_checks(rt, settings), {"checks": [], "checked_ts": None,
                                                                         "pending": False}),
        "watcher": watcher,
        "groups": section("groups", lambda: groups(settings), []),
        "viewer": viewer,
    }
    if not viewer["is_owner"]:  # setup details name chat targets and URLs: only the owner reads them
        out["setup"]["checks"] = [{**c, "detail": ""} for c in out["setup"].get("checks") or []]
    out["problems"] = problems
    return out


def health(rt) -> dict:
    """Cheap: the package loaded, which backend is configured, where the data lives. No printer call."""
    settings = _settings(rt)
    return {"ok": True, "schema": SCHEMA_VERSION, "backend": str(settings.backend),
            "persona": str(settings.persona_name or ""), "simulated": settings.backend == "simulator"}


def resolve_file(rt, ref: Any) -> Path:
    """The file a reference names, after every check; raises ``FileRefError`` (400/403/404/413/415).

    ``rt`` is accepted for symmetry with ``build_overview`` (the data dir is resolved per call either way)."""
    raw = str(ref or "")
    if not raw.strip() or "\x00" in raw or "\\" in raw or len(raw) > 1024:
        raise FileRefError(400, "file reference required")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or raw.startswith("~") or any(p in ("..", "") for p in raw.split("/")) or ":" in rel.parts[0]:
        raise FileRefError(400, "bad file reference")
    if rel.parts[0] not in FILE_ROOTS:
        raise FileRefError(403, "outside the workshop's files")
    suffix = rel.suffix.lower()
    if suffix not in MIME:
        raise FileRefError(415, "only STL models and images")
    root = _data_root()
    try:
        resolved = (root / Path(*rel.parts)).resolve(strict=True)
    except (OSError, RuntimeError):
        raise FileRefError(404, "file not found") from None
    allowed = [(root / r).resolve() for r in FILE_ROOTS]
    if not resolved.is_relative_to(root) or not any(resolved.is_relative_to(a) for a in allowed):
        raise FileRefError(403, "outside the workshop's files")
    if resolved.suffix.lower() not in MIME:  # a symlink renamed to .png that points at something else
        raise FileRefError(415, "only STL models and images")
    if not resolved.is_file():
        raise FileRefError(404, "file not found")
    cap = MAX_FILE_BYTES.get(resolved.suffix.lower(), MAX_IMAGE_BYTES)
    if resolved.stat().st_size > cap:
        raise FileRefError(413, "file too large for the viewer")
    return resolved


def file_payload(rt, ref: Any) -> dict:
    """``{"name", "bytes", "mime", "dataUrl", "mtime"}`` of a checked reference (the Meshy ``/file`` shape)."""
    path = resolve_file(rt, ref)
    try:
        data = path.read_bytes()
        mtime = path.stat().st_mtime
    except OSError:
        raise FileRefError(404, "file not found") from None
    mime = MIME[path.suffix.lower()]
    return {"name": path.name, "bytes": len(data), "mime": mime, "mtime": int(mtime * 1000),
            "dataUrl": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"}


def dumps(overview: dict) -> str:
    """JSON text of an overview (what the fixture file holds)."""
    return json.dumps(overview, ensure_ascii=False, indent=1, default=str)


__all__ = ["SCHEMA_VERSION", "FileRefError", "build_overview", "health", "resolve_file", "file_payload", "file_ref",
           "pretty_name", "groups", "person_group", "notices", "setup_checks", "dumps"]
