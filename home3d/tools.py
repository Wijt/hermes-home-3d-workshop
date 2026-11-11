"""Hermes tools (``home3d_*``). Every handler is ``handler(args: dict, **kwargs) -> str``: it returns a JSON
envelope (``{"ok": true, ...}`` / ``{"ok": false, "error": ...}``) and never raises.

Who asked is resolved from ``kwargs["session_id"]`` (the ``pre_llm_call`` hook maps session -> sender) and
recorded in the store with every request / job. An unknown sender is never the owner.

Safety: start, clear-plate confirm and resume need an approval PASS. The ``pre_tool_call`` hook issues one
(bound to tool, target and session) only for an owner session whose gate passed, and ``/home3d approve``
issues one for its own call. The handler uses it up FIRST (``store.consume_pass``) and refuses without it:
Hermes' ``ctx.dispatch_tool`` / ``registry.dispatch`` skip ``pre_tool_call``, so another plugin could
otherwise call these handlers directly. The handlers then re-check the pure gates. Stop and pause need no
pass: stopping must always work.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Optional

from . import customize
from .backends.base import PAUSE, BackendError, SliceOptions, to_jsonable
from .config import watch_script_path
from .gates import (clear_plate_gate, describe, printer_blocks, refusal, requester_name, resume_gate, same_person,
                    start_gate, stop_refusal, write_refusal)
from .gcode import assess_eject, inspect_gcode, material_family
from .hooks import LIGHT_FLAG, acked_codes, approval_target, watcher_fresh, watcher_stale_s

Tool = tuple[str, dict, Callable[..., str]]

MAX_FIND = 6
SIM_AUTOEJECT_PRESET = "sim-autoeject"
DEFAULT_PRINTER_PRESET = "Bambu Lab A1 0.4 nozzle"
DEFAULT_PROCESS_PRESETS = {"draft": "0.28mm Extra Draft @BBL A1", "standard": "0.20mm Standard @BBL A1",
                           "fine": "0.16mm High Quality @BBL A1"}
DEFAULT_FILAMENT_PRESETS = {"PLA": "Bambu PLA Basic @BBL A1", "PETG": "Generic PETG @BBL A1",
                            "TPU": "Generic TPU @BBL A1", "ABS": "Generic ABS @BBL A1",
                            "ASA": "Generic ASA @BBL A1", "PC": "Generic PC @BBL A1"}
QUALITY_ALIASES = {"draft": "draft", "fast": "draft", "quick": "draft", "hızlı": "draft", "hizli": "draft",
                   "standard": "standard", "normal": "standard", "default": "standard",
                   "fine": "fine", "high": "fine", "detailed": "fine", "ince": "fine", "kaliteli": "fine"}
WATCHER_STALE_S = 10 * 60
SEARCH_HINT = ("MakerWorld has no search API here: use your web search with 'site:makerworld.com <what>' "
               "(English keywords work best), then pass up to 6 model links or ids in 'urls'.")

# colour words (en + tr) -> hex, for filament colours and AMS tray matching
COLOURS = {
    "white": "#FFFFFF", "beyaz": "#FFFFFF", "black": "#000000", "siyah": "#000000",
    "red": "#D32F2F", "kırmızı": "#D32F2F", "kirmizi": "#D32F2F", "blue": "#1E5BD8", "mavi": "#1E5BD8",
    "green": "#2E9E44", "yeşil": "#2E9E44", "yesil": "#2E9E44", "yellow": "#F5D000", "sarı": "#F5D000",
    "sari": "#F5D000", "orange": "#F57C00", "turuncu": "#F57C00", "grey": "#8A8A8A", "gray": "#8A8A8A",
    "gri": "#8A8A8A", "pink": "#F48FB1", "pembe": "#F48FB1", "purple": "#7B3FB5", "mor": "#7B3FB5",
    "brown": "#7A4A24", "kahverengi": "#7A4A24", "kahve": "#7A4A24", "natural": "#E8DFC8",
    "naturel": "#E8DFC8", "beige": "#E8DFC8", "bej": "#E8DFC8", "silver": "#C0C0C0", "gümüş": "#C0C0C0",
    "gold": "#C9A227", "altın": "#C9A227", "altin": "#C9A227",
}
COLOUR_MATCH_MAX = 160.0  # RGB distance still counted as "that colour"
UPGRADE_FLOW = {"accept": ({"proposed", "rejected"}, "accepted"), "reject": ({"proposed", "accepted"}, "rejected"),
                "printing": ({"accepted"}, "printing"), "installed": ({"accepted", "printing"}, "installed")}


class ArgError(ValueError):
    """Bad tool arguments (message goes back to the agent)."""


# ---- small helpers --------------------------------------------------------------------------------
def _dump(obj: Any) -> str:
    try:
        return json.dumps(to_jsonable(obj), ensure_ascii=False, default=str)
    except Exception as e:  # never raise from a handler
        return json.dumps({"ok": False, "error": f"result not serialisable: {e}"})


def _int(a: dict, key: str, default: Optional[int] = None, *, required: bool = False) -> Optional[int]:
    v = a.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            raise ArgError(f"'{key}' is required")
        return default
    if isinstance(v, bool):
        raise ArgError(f"'{key}' must be a whole number")
    try:
        f = float(str(v).strip().lstrip("#"))
        if f != int(f):
            raise ValueError
    except (ValueError, OverflowError):
        raise ArgError(f"'{key}' must be a whole number, got {v!r}") from None
    return int(f)


def _float(a: dict, key: str) -> Optional[float]:
    v = a.get(key)
    if v is None or (isinstance(v, str) and not v.strip()) or isinstance(v, bool):
        return None
    try:
        return float(str(v).strip().rstrip("x%").replace(",", "."))
    except ValueError:
        raise ArgError(f"'{key}' must be a number, got {v!r}") from None


def _bool(a: dict, key: str, default: bool = False) -> bool:
    v = a.get(key)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on", "evet"}


def _str(a: dict, key: str, default: str = "") -> str:
    v = a.get(key)
    return default if v is None else str(v).strip()


def _choice(a: dict, key: str, choices: tuple, default: Optional[str] = None) -> str:
    v = _str(a, key).lower() or (default or "")
    if v not in choices:
        raise ArgError(f"'{key}' must be one of {', '.join(choices)}" + (f", got {v!r}" if v else ""))
    return v


def _who(rt, kw: dict, explicit: str = "") -> tuple[str, str]:
    """(requester name, sender id) of the person talking in this session. The name is never empty: a sender in no
    list is recorded as ``Guest (…1234)`` and a session without any sender as ``Guest`` (``gates.requester_name``),
    so no request or job is ever stored with an empty requester that could pass for the owner's."""
    sid = str(kw.get("session_id") or "")
    actor = rt.actor(sid)
    name = (explicit or "").strip() or requester_name(actor)
    return name, actor.sender


# Who may use which tool action (checked in ``_wrap`` for every caller: the agent, ``/home3d``, the CLI demo).
# WRITE: prepares a print or changes the queue; the owner and known people only, unless ``allow_guests``.
# STOP: stop / pause, under ``stop_policy``. Everything else (status, find, camera, lists) is open to everyone; the
# approval actions (start, resume, plate confirm) are gated by the pre_tool_call hook and the handler pass.
WRITE_ACTIONS: dict[str, Optional[frozenset]] = {
    "home3d_import": None, "home3d_customize": None, "home3d_slice": None,  # None = every call
    "home3d_design": frozenset({"upload"}), "home3d_queue": frozenset({"add", "remove"})}
STOP_TOOL_ACTIONS = {"home3d_stop": frozenset({"stop", "pause"})}
_DEFAULT_ACTION = {"home3d_queue": "list", "home3d_stop": "stop"}


def access_refusal(rt, name: str, args: dict, kw: dict) -> Optional[dict]:
    """The refusal of ``name`` with ``args`` for the actor of this session, or None when they may. Pure reads (the
    session's recorded sender, the settings); never touches the printer."""
    action = str(args.get("action") or _DEFAULT_ACTION.get(name, "")).strip().lower()
    stop_set = STOP_TOOL_ACTIONS.get(name)
    is_write = name in WRITE_ACTIONS and (WRITE_ACTIONS[name] is None or action in WRITE_ACTIONS[name])
    if not is_write and not (stop_set and action in stop_set):
        return None
    s = rt.settings
    actor = rt.actor(str(kw.get("session_id") or ""))
    if is_write:
        why, cmd = write_refusal(actor, s.allow_guests), "/home3d"
    else:
        why, cmd = stop_refusal(actor, s.stop_policy), f"/home3d {action}"
    if not why:
        return None
    return {"ok": False, "code": why, "refused": True, "error": refusal(why, "en", cmd=cmd, who=actor.label("en")),
            "message": refusal(why, s.language, cmd=cmd, who=actor.label(s.language))}


def _is_owner(rt, sender: str) -> bool:
    """The recorded sender is the owner (a local CLI/TUI session is recorded as ``LOCAL_SENDER`` and counts when
    ``local_is_owner``). An unknown sender ('') is never the owner."""
    return bool(sender) and rt.settings.is_owner(sender)


def _own_item_ids(rt) -> set[int]:
    """Queue ids of the workshop's ACTIVE jobs (queued or printing): what "ours" means in the queue."""
    return {int(i) for i in rt.store.active_job_ids()}


_NO_PASS_TR = "Bu işlem için sahibinin onayı gerekiyor (/home3d approve); onay bulunamadı, hiçbir şey yapılmadı."


def _use_pass(rt, tool: str, target: str, kw: dict) -> Optional[dict]:
    """Use the approval pass for this call FIRST; a refusal envelope when there is none (fails closed)."""
    return _take_pass(rt, tool, target, kw)[0]


def _take_pass(rt, tool: str, target: str, kw: dict) -> tuple[Optional[dict], str]:
    """(refusal envelope or None, the pass detail). Uses the pass once; fails closed."""
    sid = str(kw.get("session_id") or "")
    granted = None
    try:
        if sid:
            take = getattr(rt.store, "take_pass", None)
            if callable(take):
                granted = take(tool, target, sid)
            elif rt.store.consume_pass(tool, target, sid):
                granted = {"detail": ""}
    except Exception:  # a store we cannot read authorises nothing
        granted = None
    if granted is not None:
        return None, str(granted.get("detail") or "")
    error = (f"{tool} must be approved through Hermes (pre_tool_call) or /home3d approve; no approval pass found "
             "(nothing was done)")
    out = {"ok": False, "blocked": True, "error": error, "codes": ["no_pass"]}
    try:
        if rt.settings.language == "tr":
            out["message"] = _NO_PASS_TR
    except Exception:
        pass
    return out, ""


def _plate_check(rt, status):
    """The plate check shared with the ``pre_tool_call`` hook (``rt.plate_check`` caches a confident "empty" so a
    start costs one camera check)."""
    try:
        return rt.plate_check(status=status)
    except TypeError:  # a runtime without the ``status`` shortcut
        return rt.plate_check()


def _plate_confirmed(store, job_name: str, status=None) -> bool:
    try:
        if status is not None:
            return bool(store.plate_confirmed(job_name or "", status=status))
        return bool(store.plate_confirmed(job_name or ""))
    except Exception:
        return False  # fail closed: after a failed print the start gate then wants a confirmation


def _after_failure(store) -> bool:
    """A failed print nobody has confirmed since (survives a power cycle / cancel to IDLE). Fails closed."""
    try:
        fn = getattr(store, "unconfirmed_failure", None)
        return bool(callable(fn) and fn() is not None)
    except Exception:
        return True


def _light_warning(plate) -> list[str]:
    if plate is not None and LIGHT_FLAG in str(getattr(plate, "message", "") or ""):
        return ["the chamber light could not be switched off again after the plate check (light_left_on)"]
    return []


def _model_id(value: Any) -> int:
    s = str(value or "").strip()
    m = re.search(r"/models/(\d+)", s) or re.fullmatch(r"#?(\d+)", s)
    if not m:
        raise ArgError(f"'model_id' must be a MakerWorld model id or link, got {value!r}")
    return int(m.group(1))


def _colour_hex(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if not s:
        return ""
    if s in COLOURS:
        return COLOURS[s]
    h = s.lstrip("#")
    if re.fullmatch(r"[0-9a-f]{3}", h):
        h = "".join(c * 2 for c in h)
    if re.fullmatch(r"[0-9a-f]{6}([0-9a-f]{2})?", h):
        return "#" + h[:6].upper()
    for word, hx in COLOURS.items():  # "dark red", "açık mavi"
        if re.search(r"\b" + re.escape(word) + r"\b", s):
            return hx
    return ""


def _rgb_distance(a: str, b: str) -> float:
    try:
        ra = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
        rb = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return 1e9
    return sum((x - y) ** 2 for x, y in zip(ra, rb)) ** 0.5


def _tray_dict(t) -> dict:
    return {"slot": t.slot, "material": t.material, "color": t.color, "name": t.name,
            "remain_pct": t.remain_pct, "loaded": t.loaded}


def _suggest_slot(trays: list, material: str, colour: str) -> tuple[Optional[int], str]:
    fam = material_family(material)
    usable = [t for t in trays or [] if t.loaded and (t.material or t.color)
              and (not t.material or material_family(t.material) == fam)]
    if not usable:
        return None, f"no {fam or material} spool is loaded in the AMS"
    if not colour:
        return usable[0].slot, ""
    best = min(usable, key=lambda t: _rgb_distance(t.color or "#808080", colour))
    if _rgb_distance(best.color or "#808080", colour) > COLOUR_MATCH_MAX:
        return None, f"no {fam} spool close to {colour} is loaded (loaded: " + \
            ", ".join(f"slot {t.slot} {t.color or '?'}" for t in usable) + ")"
    return best.slot, ""


def _filament_slots(text: str) -> tuple[int, list[int]]:
    """(number of filament slots in the sliced file, zero-based used slots)."""
    m = re.search(r"^;\s*filament_type = (.*)$", text or "", re.M)
    n = len([v for v in re.split(r"[;,]", m.group(1)) if v.strip()]) if m else 1
    u = re.search(r"^; filament: ([\d, ]+)$", text or "", re.M)
    used = [int(v) - 1 for v in re.findall(r"\d+", u.group(1))] if u else [0]
    used = [i for i in used if i >= 0] or [0]
    return max(n, max(used) + 1, 1), used


def _printer_summary(st) -> dict:
    return {
        "state": st.state, "connected": st.connected, "job_name": st.job_name,
        "progress": round(st.progress or 0.0, 1), "remaining_min": st.remaining_min,
        "layer": st.layer, "total_layers": st.total_layers, "bed_temp": st.bed_temp,
        "bed_target": st.bed_target, "nozzle_temp": st.nozzle_temp, "printer_name": st.printer_name,
        "hms": [{"code": h.code, "severity": h.severity, "message": h.message, "wiki_url": h.wiki_url}
                for h in st.blocking_hms],
        "ignored_hms": [h.code for h in st.hms if h.ignorable],
        "trays": [_tray_dict(t) for t in st.trays],
        "awaiting_plate_clear": getattr(st, "awaiting_plate_clear", None),
        "chamber_light": getattr(st, "chamber_light", None),
    }


def _plate_dict(p) -> Optional[dict]:
    if p is None:
        return None
    return {"is_empty": p.is_empty, "difference_pct": p.difference_pct, "confidence": p.confidence,
            "message": p.message, "needs_calibration": p.needs_calibration,
            "light_ok": getattr(p, "light_ok", None), "uncertain_band": bool(getattr(p, "uncertain_band", False)),
            "note": "the camera's opinion only: thin or first-layer parts can be missed"}


def _queue_entry(item, job: Optional[dict], active: set) -> dict:
    """``ours`` = an active workshop job; a stored job for a finished item is shown as history. A pending item whose
    id matches an old (cancelled / finished) workshop job is NOT ours."""
    ours = item.id in active
    if not ours and not item.is_done:
        job = None
    d = {"id": item.id, "status": item.status, "name": item.name, "position": item.position,
         "manual_start": item.manual_start,
         "print_time_min": round(item.print_time_s / 60) if item.print_time_s else None,
         "ours": ours}
    if job:
        d.update(requester=job.get("requester", ""), eject_planned=bool(job.get("eject_planned")),
                 request_id=job.get("request_id"))
    return d


def _request_summary(r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "requester", "channel", "text", "model_ref", "library_file_id",
                                  "sliced_file_id", "queue_item_id", "status", "outcome")} | \
        {"when": time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("ts") or 0))}


def _job_summary(j: dict) -> dict:
    return {k: j.get(k) for k in ("queue_item_id", "request_id", "name", "requester", "state", "eject_planned",
                                  "eject_reason", "max_z_mm", "outcome")}


def _kv_age_s(store, key: str) -> Optional[float]:
    try:
        updated = store.kv_updated(key)
    except Exception:
        return None
    return (time.time() - float(updated)) if updated is not None else None


def _watcher_info(age: Optional[float], stale_s: float = WATCHER_STALE_S) -> dict:
    """Watcher freshness for status: ``state`` is ``ok`` | ``stale`` (it ran, but not lately: older than ``stale_s``,
    ``hooks.watcher_stale_s``) | ``never_ran`` (the cron script is installed but no pass ran: the Hermes scheduler is
    not running) | ``not_installed``."""
    fresh = age is not None and age < stale_s
    out: dict = {"last_run_age_s": round(age) if age is not None else None, "fresh": fresh}
    if fresh:
        out["state"] = "ok"
        return out
    try:
        installed = watch_script_path().is_file()
    except OSError:
        installed = False
    if age is not None:
        out["state"] = "stale"
        out["hint"] = (f"the last watcher pass was {round(age / 60)} min ago: notifications and plate checks are "
                       "paused; is the Hermes scheduler running? (owner: start `hermes gateway`, check "
                       "`hermes cron status`)")
    elif installed:
        out["state"] = "never_ran"
        out["hint"] = ("the watcher is installed, but the Hermes scheduler is not running: no notifications or "
                       "plate checks (owner: start `hermes gateway`, check `hermes cron status`)")
    else:
        out["state"] = "not_installed"
        out["hint"] = ("the watcher is not set up: no notifications or plate checks (owner: 'hermes home3d setup', "
                       "with `hermes gateway` running)")
    return out


def _resolve_requests(store, action: str, queue_item_id: Optional[int] = None, outcome: str = "") -> None:
    """The action ran: family approval requests for it are settled (the watcher never announces them now)."""
    fn = getattr(store, "resolve_approval_requests", None)
    if callable(fn):
        try:
            fn(action, queue_item_id, outcome)
        except Exception:
            pass


def _request_for_file(store, library_file_id: int) -> Optional[dict]:
    for r in store.requests(limit=50):
        if r.get("library_file_id") == library_file_id and r.get("status") in ("open", "queued"):
            return r
    return None


def _process_preset(settings, quality: str) -> str:
    presets = settings.process_presets or {}
    return str(presets.get(quality) or presets.get("standard") or DEFAULT_PROCESS_PRESETS[quality])


def _filament_preset(settings, material: str) -> str:
    presets = {str(k).upper(): str(v) for k, v in (settings.filament_presets or {}).items() if str(v).strip()}
    m = material.upper()
    fam = material_family(m)
    if m in presets:
        return presets[m]
    if fam in presets:
        return presets[fam]
    return DEFAULT_FILAMENT_PRESETS.get(fam) or f"Generic {fam or m} @BBL A1"


def _printer_presets(rt) -> tuple[str, str]:
    """(auto-eject preset or '', standard preset)."""
    s = rt.settings
    auto = str(s.autoeject_printer_preset or "").strip()
    if not auto and getattr(rt.backend, "name", "") == "simulator":
        auto = SIM_AUTOEJECT_PRESET
    std = str(s.standard_printer_preset or "").strip() or DEFAULT_PRINTER_PRESET
    return auto, std


def _slice_once(be, fid: int, opts: SliceOptions):
    res = be.slice(fid, opts)
    text = res.gcode_text
    if not text:
        try:
            text = be.library_gcode(res.library_file_id)
        except BackendError:
            text = ""
    return res, text, inspect_gcode(text)


def _add_unique(dst: list, items) -> None:
    for w in items or []:
        if w and w not in dst:
            dst.append(w)


# ---- handlers ---------------------------------------------------------------------------------------
def _h_status(rt, a: dict, kw: dict) -> dict:
    be, store = rt.backend, rt.store
    out: dict = {"ok": True, "backend": getattr(be, "name", ""), "persona": rt.settings.persona_name}
    try:
        out["printer"] = _printer_summary(be.status())
    except BackendError as e:
        out["printer"] = {"state": "OFFLINE", "connected": False, "error": str(e)}
    jobs = {int(j["queue_item_id"]): j for j in store.jobs(limit=200)}
    active = _own_item_ids(rt)
    try:
        out["queue"] = [_queue_entry(q, jobs.get(q.id), active) for q in be.queue()]
    except BackendError as e:
        out["queue"], out["queue_error"] = [], str(e)
    out["jobs"] = [_job_summary(j) for j in store.jobs(limit=8)]
    out["open_requests"] = [_request_summary(r) for r in store.requests(status="open", limit=8)]
    w = store.kv_get("watcher") or {}
    plate = w.get("plate_state") if isinstance(w, dict) else None
    if isinstance(plate, dict):
        out["plate"] = {k: plate.get(k) for k in ("phase", "job_name", "eject_planned", "reason", "last_check")}
    updated = w.get("updated") if isinstance(w, dict) else None
    age = (time.time() - float(updated)) if isinstance(updated, (int, float)) else _kv_age_s(store, "watcher")
    out["watcher"] = _watcher_info(age, watcher_stale_s(rt.settings))
    err = store.kv_get("watcher_error")
    if err:
        out["watcher"]["error"] = str(err)[:200]
    me = rt.actor(str(kw.get("session_id") or "")).name  # '' when the session has no sender
    if me:
        out["speaking"] = me
    return out


def _h_camera(rt, a: dict, kw: dict) -> dict:
    be = rt.backend
    plate = None
    if _bool(a, "check_plate"):  # one light cycle for the photo and the plate check
        snap, plate = be.snapshot_and_check(rt.media_dir)
    else:
        snap = be.snapshot(rt.media_dir, lit=True)
    path = str(Path(snap.path).resolve())
    out = {"ok": True, "path": path, "media_line": f"MEDIA:{path}", "lit": snap.lit, "note": snap.note,
           "hint": "Put media_line on its own line in your reply to attach the photo."}
    if plate is not None:
        out["plate"] = _plate_dict(plate)
    return out


def _is_a1(models: list) -> bool:
    for m in models or []:
        n = re.sub(r"^bambu\s*lab\s*", "", str(m).strip(), flags=re.I).replace(" ", "").upper()
        if n in ("A1", "N2S"):  # product name or MakerWorld device code
            return True
    return False


def _card(c) -> dict:
    native = [i for i in c.instances if _is_a1(i.printer_models)]
    compat = [i for i in c.instances if i not in native and _is_a1(getattr(i, "compatible_models", []))]
    a1 = native + compat

    def entry(i, fit: str) -> dict:
        return {"profile_id": i.profile_id, "title": i.title, "print_time_min": i.print_time_min,
                "weight_g": i.weight_g, "plates": i.plates, "fit": fit,
                "made_for": (i.printer_models or [""])[0]}

    d = {"model_id": c.model_id, "title": c.title, "url": c.url, "cover_url": c.cover_url,
         "creator": c.creator, "license": c.license, "likes": c.likes, "downloads": c.downloads,
         "prints": c.prints, "summary": (c.summary or "")[:240],
         "a1_profiles": [entry(i, "native") for i in native] + [entry(i, "a1_compatible") for i in compat],
         "other_profiles": len(c.instances) - len(a1),
         "already_imported_library_ids": list(c.already_imported_library_ids)}
    if not a1:
        d["note"] = "no A1 print profile: it can still be imported and sliced with our A1 presets"
    elif not native:
        d["note"] = ("MakerWorld lists the A1 as compatible, but the profile was made for another printer: "
                     "import it, home3d_slice re-slices it with the A1 presets (time and grams change)")
    return d


def _search_hint(rt) -> str:
    """SEARCH_HINT; on the simulated printer also the built-in catalog ids (no web search needed to try it)."""
    try:
        if getattr(rt.backend, "name", "") != "simulator":
            return SEARCH_HINT
        from .backends import simulator

        ids = getattr(simulator, "CATALOG_IDS", ())
    except Exception:
        return SEARCH_HINT
    if not ids:
        return SEARCH_HINT
    listed = ", ".join(f"{mid} {title}" for mid, title in ids)
    return (SEARCH_HINT + " Simulated printer: any MakerWorld link works (the title comes from the link), and "
            f"these ids are its built-in catalog: {listed}.")


def _h_find_models(rt, a: dict, kw: dict) -> dict:
    raw = a.get("urls")
    if isinstance(raw, str):
        raw = re.split(r"[\s,]+", raw)
    elif not isinstance(raw, (list, tuple)):
        raw = [raw] if raw else []
    urls = list(dict.fromkeys(str(u).strip() for u in (raw or []) if str(u).strip()))
    if not urls:
        return {"ok": False, "error": "pass 1-6 MakerWorld links or model ids in 'urls'", "hint": _search_hint(rt)}
    cards, errors = [], []
    for u in urls[:MAX_FIND]:
        try:
            cards.append(_card(rt.backend.resolve_model(u)))
        except BackendError as e:
            errors.append({"input": u, "error": str(e)})
    out = {"ok": bool(cards), "cards": cards, "errors": errors, "hint": _search_hint(rt),
           "next": ("Show the requester 2-4 options (cover picture, title, print time), let them choose, "
                    "then call home3d_import with model_id, an A1 profile_id and request_text (2-3 words in the "
                    "requester's own language naming the thing, e.g. 'flower box'; family messages use it).")}
    if len(urls) > MAX_FIND:
        out["skipped"] = urls[MAX_FIND:]
    if not cards:
        out["error"] = "none of the links could be resolved"
    return out


def _h_import(rt, a: dict, kw: dict) -> dict:
    be, store = rt.backend, rt.store
    if a.get("model_id") in (None, ""):
        raise ArgError("'model_id' is required")
    if _int(a, "request_id") is None and not _str(a, "request_text"):
        # family messages name the print by it: never fall back to the (English) MakerWorld title
        raise ArgError("'request_text' is required for a new request: 2-3 words naming the thing in the "
                       "requester's own language, e.g. 'çiçek kutusu' (or pass request_id)")
    mid = _model_id(a.get("model_id"))
    profile_id = _int(a, "profile_id")
    requester, sender = _who(rt, kw, _str(a, "requester"))
    card, warnings, reused = None, [], False
    try:
        card = be.resolve_model(str(mid))
    except BackendError as e:
        warnings.append(f"could not read the model card: {e}")
    explicit = profile_id is not None
    if card and not explicit:
        a1 = [i for i in card.instances if _is_a1(i.printer_models)]
        if a1:
            profile_id = a1[0].profile_id
        else:
            warnings.append("no A1 profile: importing the default profile (slicing uses our A1 presets)")
    if card and card.already_imported_library_ids and not explicit:
        lib_id, name, reused = int(card.already_imported_library_ids[0]), card.title, True
    else:
        lib = be.import_model(mid, profile_id)
        lib_id, name = lib.id, lib.name
    url = card.url if card and card.url else f"https://makerworld.com/en/models/{mid}"
    request_id = _int(a, "request_id")
    if request_id is not None and store.get_request(request_id) is None:
        warnings.append(f"request {request_id} not found: recorded a new one")
        request_id = None
    if request_id is None:
        text = _str(a, "request_text")
        request_id = store.add_request(requester=requester, text=text, channel=_str(a, "channel") or "text",
                                       sender_id=sender, model_ref=url)
    store.update_request(request_id, library_file_id=lib_id, model_ref=url)
    return {"ok": True, "library_file_id": lib_id, "name": name, "model_id": mid, "profile_id": profile_id,
            "reused": reused, "request_id": request_id, "requester": requester, "warnings": warnings,
            "next": f"home3d_slice library_file_id={lib_id} request_id={request_id}"}


def _h_customize(rt, a: dict, kw: dict) -> dict:
    be, store = rt.backend, rt.store
    template = _str(a, "template")
    params = a.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params) if params.strip() else {}
        except ValueError:
            raise ArgError("'params' must be an object") from None
    if not isinstance(params, dict):
        raise ArgError("'params' must be an object")
    request_id = _int(a, "request_id")
    work = rt.work_dir / f"customize-{int(time.time() * 1000)}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        if template:
            values, ignored = customize.template_values(template, params)
            slug = re.sub(r"[^A-Za-z0-9]+", "_", str(values.get("text", "")))[:24].strip("_") or "model"
            path = customize.render_template(template, params, work / f"{template}_{slug}.stl")
            size = customize.model_bbox(path)
            lib = be.upload_file(path)
            if request_id is not None:
                store.update_request(request_id, library_file_id=lib.id, model_ref=f"template:{template}")
            return {"ok": True, "library_file_id": lib.id, "name": lib.name, "template": template,
                    "values": values, "ignored_params": ignored, "size_mm": list(size),
                    "next": f"home3d_slice library_file_id={lib.id}"}

        fid = _int(a, "library_file_id", required=True)
        scale, target = _float(a, "scale"), _float(a, "target_size_mm")
        if scale is None and target is None:
            raise ArgError("give 'scale' (e.g. 1.5) or 'target_size_mm', or a 'template'")
        if scale is not None and str(a.get("scale", "")).strip().endswith("%"):
            scale = scale / 100.0  # "150%"
        src = be.download_file(fid, work)
        size = customize.model_bbox(src)
        mech = customize.mechanism_words(src.name + " " + _str(a, "name"))
        if mech and not _bool(a, "confirm_mechanism"):
            return {"ok": False, "needs_confirmation": True, "size_mm": list(size),
                    "error": (f"'{src.name}' looks like a fitted part ({', '.join(mech)}): scaled lids, snap-fits, "
                              "hinges and threads stop fitting. Ask the requester, then call again with "
                              "confirm_mechanism=true.")}
        factor = customize.check_factor(scale if scale is not None else customize.factor_for_size(size, target))
        new_size = [round(v * factor, 2) for v in size]
        if not customize.fits_build_volume(new_size):
            return {"ok": False, "size_mm": list(size), "scaled_size_mm": new_size,
                    "error": f"scaled size {new_size} mm does not fit the {customize.BUILD_VOLUME_MM[0]:g} mm "
                             "build volume"}
        name = src.name
        suffix = ".3mf" if name.lower().endswith(".3mf") else ".stl"
        stem = name[: -len(suffix)]
        out = customize.scale_model(src, factor, work / f"{stem}_{round(factor * 100)}pct{suffix}")
        lib = be.upload_file(out)
        if request_id is None:
            r = _request_for_file(store, fid)
            request_id = r["id"] if r else None
        if request_id is not None:
            store.update_request(request_id, library_file_id=lib.id)
        warnings = [f"thin parts get weaker below 1:1 (factor {factor:.2f})"] if factor < 0.5 else []
        return {"ok": True, "library_file_id": lib.id, "name": lib.name, "source_file_id": fid,
                "factor": round(factor, 4), "size_before_mm": list(size), "size_mm": new_size,
                "request_id": request_id, "warnings": warnings,
                "next": f"home3d_slice library_file_id={lib.id}"}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _design_bodies(store, fid: int) -> Optional[int]:
    """Separate bodies of the design version uploaded as library file ``fid`` (None: not a design, or unknown)."""
    try:
        ref = store.kv_get(f"design_lib:{fid}")
        if not isinstance(ref, dict) or not ref.get("slug"):
            return None
        from . import design
        meta = design.load_version(str(ref["slug"]), int(ref["version"]))["meta"]
        bodies = meta.get("bodies")
        return int(bodies) if isinstance(bodies, int) and not isinstance(bodies, bool) else None
    except Exception:  # noqa: BLE001 - a missing or broken design record never blocks a slice
        return None


def _h_slice(rt, a: dict, kw: dict) -> dict:
    s, be, store = rt.settings, rt.backend, rt.store
    fid = _int(a, "library_file_id", required=True)
    q_raw = _str(a, "quality").lower() or "standard"
    if q_raw not in QUALITY_ALIASES:
        raise ArgError("'quality' must be draft, standard or fine")
    quality = QUALITY_ALIASES[q_raw]
    material = (_str(a, "material") or "PLA").upper()
    colour_raw = _str(a, "colour") or _str(a, "color")
    colour = _colour_hex(colour_raw)
    eject = _choice(a, "eject", ("auto", "on", "off"), "auto")
    warnings: list[str] = []
    if colour_raw and not colour:
        warnings.append(f"unknown colour {colour_raw!r}: use a colour name or #RRGGBB")

    process, filament = _process_preset(s, quality), _filament_preset(s, material)
    auto_p, std_p = _printer_presets(rt)
    base = dict(process_preset=process, filament_presets=[filament], bed_type=s.bed_type,
                filament_colours=[colour] if colour else [])
    use_auto = eject != "off" and bool(auto_p)
    if eject == "on" and not auto_p:
        warnings.append("eject=on but no auto-eject printer preset is configured: sliced without eject")
    pla_like = material_family(material) == "PLA"
    if eject == "auto" and not pla_like:
        use_auto = False  # PETG/TPU/... are never pushed off: skip the auto-eject slice entirely
    parts = _design_bodies(store, fid)
    multi = eject == "auto" and parts is not None and parts > 1
    if multi:
        use_auto = False  # a box and its lid, letters and their strip: the push knocks the small one off or misses it

    printer_preset = auto_p if use_auto else std_p
    res, text, info = _slice_once(be, fid, SliceOptions(printer_preset=printer_preset, **base))
    assess = assess_eject(info, material)
    planned, reasons, discarded = False, [], None
    if use_auto:
        if not info.has_eject_marker:
            reasons = ["the auto-eject printer preset produced no eject block: remove the part by hand"]
            warnings.append("auto-eject preset has no HOME3D/HERMES AUTO-EJECT marker (check autoeject_printer_preset)")
        elif eject == "on":
            planned, reasons = True, list(assess.reasons)
            if not assess.eligible:
                warnings.append("auto-eject forced (eject=on) although: " + "; ".join(assess.reasons))
        elif assess.eligible:
            planned, reasons = True, list(assess.reasons)
        else:
            discarded, reasons = res.library_file_id, list(assess.reasons)
            printer_preset = std_p
            res, text, info = _slice_once(be, fid, SliceOptions(printer_preset=std_p, **base))
            if info.has_eject_marker:
                planned = True
                warnings.append("the standard printer preset also pushes the part off (eject marker found)")
    else:
        reasons = (["eject=off"] if eject == "off"
                   else [f"several separate parts ({parts} bodies in the design): remove them by hand"] if multi
                   else list(assess.reasons) if not pla_like and auto_p
                   else ["no auto-eject printer preset configured"])
        if info.has_eject_marker:
            planned = True
            warnings.append("the standard printer preset contains the auto-eject block: the part will be pushed")
    _add_unique(warnings, info.warnings)
    fams = {material_family(t) for t in info.filament_types if t}
    if fams and material_family(material) not in fams:
        warnings.append(f"asked for {material} but the sliced file uses {', '.join(sorted(fams))}")

    secs = info.print_time_s or res.print_time_s
    grams = res.filament_g if res.filament_g is not None else info.filament_g
    slots, used = _filament_slots(text)
    suggested, trays = None, []
    try:
        st = be.status()
        trays = [_tray_dict(t) for t in st.trays]
        if st.trays:
            suggested, why = _suggest_slot(st.trays, material, colour)
            if why:
                warnings.append(why)
    except BackendError as e:
        warnings.append(f"AMS not readable: {e}")

    request_id = _int(a, "request_id")
    if request_id is None:
        r = _request_for_file(store, fid)
        request_id = r["id"] if r else None
    if request_id is not None and store.get_request(request_id) is not None:
        store.update_request(request_id, sliced_file_id=res.library_file_id)
    requester, _ = _who(rt, kw)
    if request_id is not None and not requester:
        requester = (store.get_request(request_id) or {}).get("requester", "")
    meta = {"name": res.name, "source_file_id": fid, "request_id": request_id, "requester": requester,
            "material": material, "colour": colour, "quality": quality, "eject_planned": planned,
            "eject_reasons": reasons, "max_z": info.max_z, "print_time_min": round(secs / 60) if secs else None,
            "grams": grams, "filament_slots": slots, "used_slots": used, "suggested_ams_slot": suggested,
            "printer_preset": printer_preset, "ts": time.time()}
    store.kv_set(f"slice:{res.library_file_id}", meta)
    return {"ok": True, "sliced_file_id": res.library_file_id, "name": res.name, "source_file_id": fid,
            "print_time_min": meta["print_time_min"], "grams": round(grams, 1) if grams is not None else None,
            "material": material, "colour": colour, "quality": quality,
            "presets": {"printer": printer_preset, "process": process, "filament": filament},
            "eject": {"mode": eject, "planned": planned, "reasons": reasons,
                      "push_z": assess.push_z if planned else None},
            "discarded_sliced_file_id": discarded, "max_z_mm": info.max_z,
            "footprint_mm": list(info.footprint_mm) if info.footprint_mm else None,
            "warnings": warnings, "preview_url": be.preview_url(res.library_file_id),
            "suggested_ams_slot": suggested, "ams_trays": trays, "request_id": request_id,
            "next": (f"Tell the requester time and grams, then home3d_queue action=add "
                     f"sliced_file_id={res.library_file_id}"
                     + (f" ams_slot={suggested}" if suggested is not None else " ams_slot=<tray>"))}


def _h_queue(rt, a: dict, kw: dict) -> dict:
    be, store = rt.backend, rt.store
    action = _choice(a, "action", ("add", "list", "remove"), "list")
    who, sender = _who(rt, kw)
    if action == "list":
        jobs = {int(j["queue_item_id"]): j for j in store.jobs(limit=500)}
        active = _own_item_ids(rt)
        items = be.queue(include_done=_bool(a, "include_done"))
        return {"ok": True, "items": [_queue_entry(q, jobs.get(q.id), active) for q in items]}

    if action == "remove":
        qid = _int(a, "queue_item_id", required=True)
        item = next((q for q in be.queue() if q.id == qid), None)
        if item is None:
            return {"ok": False, "error": f"queue item {qid} not found"}
        if not item.is_pending:
            return {"ok": False, "error": f"queue item {qid} is {item.status}: only waiting items can be removed "
                                          "(use home3d_stop for the running print)"}
        job = store.get_job(qid)
        if job is None or qid not in _own_item_ids(rt):
            # a family job queued in the printer manager (or an old, closed workshop id): never removed from here, by
            # anyone (removing it would also get a later start past the jump check)
            return {"ok": False, "code": "not_ours",
                    "error": f"queue item {qid} was not queued through the workshop; remove it in Bambuddy yourself "
                             "(the workshop never removes, postpones or reorders other people's jobs)"}
        requester = str(job.get("requester") or "")
        # a session without any sender is nobody: it never owns a job, not even another anonymous one
        mine = bool(sender) and bool(who) and same_person(requester, who)
        if not mine:
            # another person's job: never from here, not even for the owner (it would postpone their job and let a
            # later start pass the jump check). The person who asked removes it, or the owner does it in Bambuddy.
            return {"ok": False, "code": "not_theirs",
                    "error": f"queue item {qid} is {requester or 'the owner'}'s: the workshop never removes another "
                             f"person's job. {requester or 'The owner'} can ask to remove it, or the owner removes "
                             "it in Bambuddy by hand"}
        be.queue_remove(qid)
        by = who or "owner"
        store.upsert_job(qid, state="cancelled", outcome=f"removed by {by}")
        req = store.request_for_queue_item(qid)
        if req:
            store.update_request(req["id"], status="cancelled", outcome=f"removed from the queue by {by}")
        store.add_event("queue_removed", item.name, {"queue_item_id": qid, "who": by, "sender": sender,
                                                     "requester": requester})
        return {"ok": True, "removed": qid, "name": item.name, "requester": requester}

    sid = _int(a, "sliced_file_id", required=True)
    meta = store.kv_get(f"slice:{sid}") or {}
    warnings: list[str] = []
    if not meta:  # sliced outside the workshop: read the facts from the G-code
        try:
            text = be.library_gcode(sid)
            info = inspect_gcode(text)
            slots, used = _filament_slots(text)
            meta = {"eject_planned": info.has_eject_marker, "max_z": info.max_z, "filament_slots": slots,
                    "used_slots": used, "eject_reasons": ["eject block found in the G-code"]
                    if info.has_eject_marker else ["no eject block in the G-code"],
                    "material": (info.filament_types or ["PLA"])[0]}
        except BackendError as e:
            warnings.append(f"could not read the G-code ({e}): eject not planned")
    slot = _int(a, "ams_slot")
    if slot is None and meta.get("suggested_ams_slot") is not None:
        slot = int(meta["suggested_ams_slot"])
        warnings.append(f"no ams_slot given: using the suggested slot {slot}")
    mapping = None
    if slot is not None:
        if not 0 <= slot <= 255:
            raise ArgError("'ams_slot' must be a zero-based tray index (0-3 for one AMS)")
        n = max(1, int(meta.get("filament_slots") or 1))
        used = [i for i in (meta.get("used_slots") or [0]) if 0 <= int(i) < n] or [0]
        mapping = [-1] * n
        for i in used:
            mapping[int(i)] = slot
        try:
            tray = next((t for t in be.status().trays if t.slot == slot), None)
            want = material_family(str(meta.get("material") or "PLA"))
            if tray is None or not tray.loaded:
                warnings.append(f"AMS slot {slot} looks empty")
            elif tray.material and material_family(tray.material) != want:
                warnings.append(f"AMS slot {slot} holds {tray.material}, the file was sliced for {want}")
        except BackendError:
            pass
    else:
        warnings.append("no AMS slot: Bambuddy picks the tray")

    request_id = _int(a, "request_id")
    if request_id is None:
        request_id = meta.get("request_id")
    req = store.get_request(int(request_id)) if request_id is not None else None
    requester = _str(a, "requester") or (req or {}).get("requester") or meta.get("requester") or who
    item = be.queue_add(sid, ams_mapping=mapping, manual_start=True)
    planned = bool(meta.get("eject_planned"))
    store.upsert_job(item.id, request_id=req["id"] if req else None, name=item.name or meta.get("name", ""),
                     requester=requester or "", sliced_file_id=sid, eject_planned=1 if planned else 0,
                     eject_reason="; ".join(meta.get("eject_reasons") or []), max_z_mm=meta.get("max_z"),
                     state="queued")
    if req:
        store.update_request(req["id"], queue_item_id=item.id, sliced_file_id=sid, status="queued")
    ahead = []
    try:
        own = _own_item_ids(rt)
        items = be.queue()
        idx = next((i for i, q in enumerate(items) if q.id == item.id), len(items))
        ahead = [{"id": q.id, "name": q.name, "ours": q.id in own} for q in items[:idx] if not q.is_done]
    except BackendError:
        pass
    return {"ok": True, "queue_item_id": item.id, "name": item.name, "status": item.status, "manual_start": True,
            "ams_mapping": mapping, "eject_planned": planned, "requester": requester,
            "request_id": req["id"] if req else None, "ahead": ahead, "warnings": warnings,
            "next": (f"Starting needs the owner's approval: home3d_start queue_item_id={item.id} from the owner's "
                     f"chat, or the owner sends /home3d approve start {item.id} (never jump someone else's job).")}


def _h_start(rt, a: dict, kw: dict) -> dict:
    s, be, store = rt.settings, rt.backend, rt.store
    qid = _int(a, "queue_item_id", required=True)
    jump = _bool(a, "allow_jump")
    refused = _use_pass(rt, "home3d_start", approval_target("start", qid, jump), kw)
    if refused:
        return refused
    who, sender = _who(rt, kw)
    status, queue = be.status(), be.queue()
    plate, warnings = None, []
    skipped = printer_blocks(status, "start")  # the printer already blocks: no camera / chamber light
    if not skipped:
        try:
            plate = _plate_check(rt, status)
        except BackendError as e:
            warnings.append(f"plate check failed: {e}")
    warnings += _light_warning(plate)
    req = store.request_for_queue_item(qid)
    gate = start_gate(status, queue, qid, plate=plate, in_cron=rt.in_cron(), own_item_ids=_own_item_ids(rt),
                      requesters=store.active_job_requesters(), owner_name=s.owner_name,
                      allow_jump=jump, voice_request=bool(req and req.get("channel") == "voice"),
                      plate_confirmed=_plate_confirmed(store, status.job_name, status),
                      after_failure=_after_failure(store), plate_skipped=skipped)
    if not gate.ok:
        return {"ok": False, "blocked": True, "error": describe(gate, "en"), "message": describe(gate, s.language),
                "codes": gate.codes, "reasons": gate.reasons, "warnings": warnings + gate.warnings,
                "plate": _plate_dict(plate)}
    item = be.start(qid)
    forget = getattr(rt, "forget_plate_check", None)
    if callable(forget):
        forget()  # the plate is in use now
    store.upsert_job(qid, state="printing", started_ts=rt.now())
    if req:
        store.update_request(req["id"], status="printing")
    _resolve_requests(store, "start", qid, f"started by {who or 'owner'}")
    job = store.get_job(qid) or {}
    store.add_event("start_requested", item.name or job.get("name", ""),
                    {"queue_item_id": qid, "who": who or "owner", "sender": sender})
    watching = watcher_fresh(store, s)
    if not watching:
        warnings.append("the watcher is not running: nobody is told about the finish or the plate")
    return {"ok": True, "queue_item_id": qid, "status": item.status, "name": item.name or job.get("name", ""),
            "requester": job.get("requester", ""), "eject_planned": bool(job.get("eject_planned")),
            "started_by": who or "owner", "warnings": warnings + gate.warnings, "watcher_running": watching,
            "next": ("The watcher reports the finish and the plate state; no need to poll." if watching else
                     "The watcher is not running: nobody is told about the finish or the plate. Tell the owner: "
                     "hermes home3d setup, and `hermes gateway` must run. Check back with home3d_status.")}


def _h_stop(rt, a: dict, kw: dict) -> dict:
    s, be, store = rt.settings, rt.backend, rt.store
    action = _choice(a, "action", ("stop", "pause", "resume"), "stop")
    pass_detail = ""
    if action == "resume":  # stop / pause need no pass: stopping must always work
        refused, pass_detail = _take_pass(rt, "home3d_stop", approval_target("resume"), kw)
        if refused:
            return refused
    reason = _str(a, "reason")
    actor = rt.actor(str(kw.get("session_id") or ""))
    sender = actor.sender
    by = actor.label("en")  # who really did it: never "owner" by default
    try:
        st = be.status()
    except BackendError as e:
        if action != "stop":
            raise
        be.stop()  # stopping must never depend on a status read
        store.add_event("stop_request", "", {"who": by, "sender": sender, "reason": reason, "status_error": str(e)})
        return {"ok": True, "action": "stop", "by": by, "reason": reason, "warnings": [f"status unknown: {e}"]}
    payload = {"who": by, "sender": sender, "reason": reason, "state_before": st.state,
               "progress": round(st.progress or 0, 1), "layer": st.layer}
    if action in ("stop", "pause"):
        if not st.is_active:
            return {"ok": False, "code": "nothing_printing", "error": f"nothing is printing (state {st.state}): no command sent",
                    "state": st.state}
        if action == "pause" and st.state == PAUSE:
            return {"ok": True, "action": "pause", "note": "already paused", "state": st.state}
        (be.stop if action == "stop" else be.pause)()
        store.add_event(f"{action}_request", st.job_name, payload)
        if action == "stop":
            job = store.job_by_name(st.job_name)
            if job:
                store.upsert_job(job["queue_item_id"], state="cancelled", finished_ts=rt.now(),
                                 outcome=f"stopped by {by}" + (f": {reason}" if reason else ""))
                req = store.request_for_queue_item(job["queue_item_id"])
                if req:
                    store.update_request(req["id"], status="cancelled",
                                         outcome=f"stopped by {by}" + (f": {reason}" if reason else ""))
        return {"ok": True, "action": action, "job": st.job_name, "by": by, "reason": reason,
                "progress": payload["progress"],
                "next": "Check the plate with home3d_camera before anything else." if action == "stop" else
                "Resume needs the owner's approval: home3d_stop action=resume from the owner's chat, or the owner "
                "sends /home3d approve resume."}
    # resume: the pass was used above; re-check the gate (an active printer error needs the owner's ack). The ack
    # only covers the error codes the owner was shown when approving (recorded in the pass): a printer error that
    # appeared while the prompt waited is not acknowledged.
    shown = acked_codes(pass_detail)
    now_codes = {str(h.code or "").strip().upper() for h in st.blocking_hms}
    ack = _bool(a, "ack_hms") and _is_owner(rt, sender) and bool(shown) and now_codes <= shown
    gate = resume_gate(st, in_cron=rt.in_cron(), hms_acknowledged=ack)
    if not gate.ok:
        return {"ok": False, "blocked": True, "error": describe(gate, "en"), "message": describe(gate, s.language),
                "codes": gate.codes, "reasons": gate.reasons, "warnings": gate.warnings, "state": st.state}
    be.resume()
    _resolve_requests(store, "resume", None, f"resumed by {by}")
    if ack and st.blocking_hms:
        payload["hms_acknowledged"] = [h.code for h in st.blocking_hms]
    store.add_event("resume_request", st.job_name, payload)
    return {"ok": True, "action": "resume", "job": st.job_name, "by": by, "warnings": gate.warnings}


def _h_clear_plate(rt, a: dict, kw: dict) -> dict:
    s, be, store = rt.settings, rt.backend, rt.store
    action = _choice(a, "action", ("check", "confirm"), "check")
    if action == "confirm":
        refused = _use_pass(rt, "home3d_clear_plate", approval_target("clear_plate"), kw)
        if refused:
            return refused
    who, sender = _who(rt, kw)
    st = be.status()
    out: dict = {"ok": True, "action": action, "state": st.state, "bed_temp": st.bed_temp,
                 "cool_temp_c": s.eject_cool_temp_c}
    plate = None
    if action == "check":
        try:  # one light cycle: the photo the owner sees and the plate judgement come from the same light
            snap, plate = be.snapshot_and_check(rt.media_dir)
            path = str(Path(snap.path).resolve())
            out.update(path=path, media_line=f"MEDIA:{path}")
        except BackendError as e:
            out["photo_error"] = str(e)
    try:
        if plate is None:
            plate = be.check_plate() if action == "check" else _plate_check(rt, st)
    except BackendError as e:
        out["plate_error"] = str(e)
    queue = be.queue()
    auto = [q for q in queue if q.is_pending and not q.manual_start]
    # a confirm is always the owner's own statement (approved through the hook or /home3d approve), and "check"
    # reports whether such a confirm could pass
    gate = clear_plate_gate(st, plate, in_cron=rt.in_cron(), cool_temp_c=s.eject_cool_temp_c,
                            auto_start_pending=auto, person_confirms=True)
    out.update(plate=_plate_dict(plate), can_confirm=gate.ok, reasons=gate.reasons,
               warnings=gate.warnings + _light_warning(plate), message=describe(gate, s.language))
    if action == "check":
        return out
    if not gate.ok:
        out.update(ok=False, blocked=True, error=describe(gate, "en"), codes=gate.codes)
        return out
    be.mark_plate_cleared()
    by = who or "owner"
    _resolve_requests(store, "clear_plate", None, f"plate marked clear by {by}")
    store.confirm_plate(st.job_name or "", by, status=st)  # a person looked: after a failed print the start may go
    for j in store.jobs(state="finished", limit=20):
        store.upsert_job(j["queue_item_id"], state="cleared")
    store.add_event("plate_clear_confirmed", st.job_name,
                    {"who": by, "sender": sender, "plate": _plate_dict(plate), "after_state": st.state})
    out.update(cleared=True, by=by, confirmed_for=st.job_name or "")
    try:  # the watcher may stay quiet (camera unsure): say which workshop job is next
        own = _own_item_ids(rt)
        nxt = next((q for q in queue if q.is_pending and q.manual_start and q.id in own), None)
        if nxt is not None:
            out["next_job"] = {"id": nxt.id, "name": nxt.name}
    except Exception:
        pass
    return out


def _person_notes(store, name: str) -> list:
    return (store.kv_get(f"person:{name.strip().lower()}") or {}).get("notes", [])


def _h_household(rt, a: dict, kw: dict) -> dict:
    s, store = rt.settings, rt.store
    action = _choice(a, "action", ("who", "history", "remember", "note"), "who")
    sid = kw.get("session_id") or ""
    me = rt.person(sid) if sid else None
    person = _str(a, "person") or (me.name if me else "")
    text = _str(a, "text")
    if action == "who":
        people = [{"name": p.name, "role": p.role, "address_as": p.address_as, "has_id": bool(p.id),
                   "notes": _person_notes(store, p.name)[-5:]} for p in s.people()]
        return {"ok": True, "persona": s.persona_name, "language": s.language, "people": people,
                "speaking": ({"name": me.name, "role": me.role, "address_as": me.greeting_name} if me else None),
                "household_notes": (store.kv_get("household:notes") or [])[-5:]}
    if action == "history":
        reqs = store.requests(requester=person or None, limit=15)
        qids = {r["queue_item_id"] for r in reqs if r.get("queue_item_id") is not None}
        jobs = [_job_summary(j) for j in store.jobs(limit=200) if j["queue_item_id"] in qids
                or (person and (j.get("requester") or "").lower() == person.lower())][:15]
        return {"ok": True, "person": person or "everyone", "requests": [_request_summary(r) for r in reqs],
                "jobs": jobs, "notes": _person_notes(store, person)[-10:] if person else []}
    if not text:
        raise ArgError("'text' is required")
    by = me.name if me else "owner"
    if action == "remember":
        if not person:
            raise ArgError("'person' is required (nobody is identified in this chat)")
        key = f"person:{person.lower()}"
        data = store.kv_get(key) or {}
        notes = (data.get("notes") or [])[-29:] + [{"ts": time.time(), "text": text[:300], "by": by}]
        store.kv_set(key, {"name": person, "notes": notes})
        return {"ok": True, "person": person, "remembered": text[:300], "count": len(notes)}
    request_id = _int(a, "request_id")
    if request_id is not None:
        if store.get_request(request_id) is None:
            return {"ok": False, "error": f"request {request_id} not found"}
        store.update_request(request_id, outcome=text[:500])
        return {"ok": True, "request_id": request_id, "noted": text[:500]}
    notes = (store.kv_get("household:notes") or [])[-49:] + [{"ts": time.time(), "text": text[:300], "by": by}]
    store.kv_set("household:notes", notes)
    return {"ok": True, "noted": text[:300], "count": len(notes)}


def _h_human_needed(rt, a: dict, kw: dict) -> dict:
    from . import upgrades

    store = rt.store
    action = _choice(a, "action", ("log", "list"), "list")
    kinds = getattr(upgrades, "KINDS", {}) or {}
    if action == "list":
        kind = _str(a, "kind") or None
        rows = store.human_needed(kind=kind, since_days=30, limit=30)
        counts = store.human_needed_counts(30)
        return {"ok": True, "moments": [{k: r.get(k) for k in ("id", "kind", "detail", "job_name", "who", "source")}
                                        | {"when": time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"]))}
                                        for r in rows],
                "counts_30d": counts,
                "thresholds": {k: v.get("threshold") for k, v in kinds.items()
                               if isinstance(v, dict) and v.get("propose", True)},
                "never_proposed": sorted(k for k, v in kinds.items()
                                         if isinstance(v, dict) and not v.get("propose", True))}
    raw_kind = _str(a, "kind") or "other"
    normalize = getattr(upgrades, "normalize_kind", None)
    kind = normalize(raw_kind) if callable(normalize) else raw_kind.lower()
    who = _str(a, "who") or _who(rt, kw)[0]
    mid = upgrades.log_moment(store, raw_kind, _str(a, "detail"), job_name=_str(a, "job_name"), who=who,
                              source="agent")
    new = upgrades.evaluate(store, rt.settings) or []
    info = kinds.get(kind) if isinstance(kinds.get(kind), dict) else {}
    window = info.get("window_days", 30) if info else 30
    proposes = bool(info.get("propose", True)) if info else True
    return {"ok": True, "id": mid, "kind": kind, "who": who,
            "count": store.human_needed_counts(window).get(kind, 0),
            "threshold": info.get("threshold") if proposes else None,
            "proposes": proposes,
            "new_proposals": new,
            "next": "Tell the owner about the new upgrade proposal." if new else ""}


def _h_upgrades(rt, a: dict, kw: dict) -> dict:
    from . import upgrades

    store = rt.store
    action = _choice(a, "action", ("list", "evaluate", "accept", "reject", "printing", "installed"), "list")
    if action == "list":
        rows = store.upgrades(status=_str(a, "status") or None)
        return {"ok": True, "upgrades": [{k: r.get(k) for k in ("id", "kind", "title", "proposal", "model_ref",
                                                                 "evidence", "status", "notes")} for r in rows],
                "counts_30d": store.human_needed_counts(30)}
    if action == "evaluate":
        return {"ok": True, "new_proposals": upgrades.evaluate(store, rt.settings) or []}
    who, sender = _who(rt, kw)
    if not _is_owner(rt, sender):
        return {"ok": False, "error": "only the owner decides on upgrades"}
    uid = _int(a, "upgrade_id", required=True)
    row = next((r for r in store.upgrades() if int(r["id"]) == uid), None)
    if row is None:
        return {"ok": False, "error": f"upgrade {uid} not found"}
    allowed, new_status = UPGRADE_FLOW[action]
    if row["status"] not in allowed:
        return {"ok": False, "error": f"upgrade {uid} is {row['status']}: cannot mark it {new_status}"}
    note = _str(a, "note")
    fields: dict = {"status": new_status}
    if note:
        fields["notes"] = ((row.get("notes") or "") + f"\n{new_status}: {note}").strip()
    store.update_upgrade(uid, **fields)
    nxt = {"accepted": (f"Print the parts through the normal flow (home3d_find_models urls=[{row['model_ref']}]), "
                        "then mark it printing." if row.get("model_ref") else "Plan the parts, then mark it printing."),
           "printing": "Mark it installed once it is fitted and tested.",
           "installed": ("Configure what it enables (e.g. autoeject_printer_preset for auto-eject)."
                         if row.get("kind") == "remove_part" else "Watch whether the moments stop."),
           "rejected": "It will not be proposed again; new moments only add evidence."}[new_status]
    return {"ok": True, "upgrade_id": uid, "kind": row["kind"], "title": row["title"], "status": new_status,
            "next": nxt}


DESIGN_NEXT_RENDER = ("Look at the previews yourself first (vision); send the person one picture and the size in cm; "
                      "on their OK: home3d_design action=upload name={name} version={version}")
DESIGN_NEXT_NO_PREVIEW = ("No preview picture this time (see warnings): check the numbers, tell the person the size in "
                          "cm and that you have no picture; on their OK: home3d_design action=upload name={name} "
                          "version={version}")
DESIGN_NEXT_SUSPECT = ("OpenSCAD ignored part of the code (see suspect and warnings: a typo, an unknown name, 2D mixed "
                       "with 3D), so part of the model is missing. Fix it and render again before you show or upload "
                       "this version.")
DESIGN_NEXT_FAILED = ("Fix the code (error, error_line) and render again with the full scad; earlier versions are kept "
                      "(from_version re-renders one with new params).")
DESIGN_SOURCE_LIMIT = 60_000  # characters of source returned by action=get


def _obj(a: dict, key: str) -> Optional[dict]:
    v = a.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            raise ArgError(f"'{key}' must be an object") from None
    if not isinstance(v, dict):
        raise ArgError(f"'{key}' must be an object")
    return v


def _design_out(res) -> dict:
    out = res.to_dict()
    out["size_cm"] = [round(v / 10.0, 1) for v in res.size_mm] if res.size_mm else None
    if not res.ok:
        out["next"] = DESIGN_NEXT_FAILED
    elif res.suspect:
        out["next"] = DESIGN_NEXT_SUSPECT
    else:
        tmpl = DESIGN_NEXT_RENDER if res.previews else DESIGN_NEXT_NO_PREVIEW
        out["next"] = tmpl.format(name=res.name, version=res.version)
    return out


def _versions_text(rows: list[dict]) -> str:
    def one(r: dict) -> str:
        size = "x".join(f"{float(v):g}" for v in r["size_mm"]) + " mm" if r.get("size_mm") else "size unknown"
        what = f"part {r['part']}" if r.get("part") else "whole design"
        return f"v{r['version']} ({what}, {size}{', code partly ignored' if r.get('suspect') else ''})"
    return ", ".join(one(r) for r in rows[-8:])


def _h_design(rt, a: dict, kw: dict) -> dict:
    from . import design

    action = _choice(a, "action", ("render", "get", "list", "upload"))
    try:
        if action == "list":
            status = design.openscad_status()
            return {"ok": True, "designs": design.list_designs(limit=_int(a, "limit", 20) or 20),
                    "openscad": status["version"] or None, "previews": status["previews"]}
        name = _str(a, "name")
        if not name:
            raise ArgError("'name' is required: a few words naming the part, e.g. 'phone stand'")
        if action == "render":
            scad = a.get("scad")
            if scad is not None and not isinstance(scad, str):
                raise ArgError("'scad' must be the OpenSCAD source as text")
            part = a.get("part")
            res = design.render(name, scad, from_version=_int(a, "from_version"), params=_obj(a, "params"),
                                views=a.get("views"), part=None if part is None else str(part),
                                timeout_s=_int(a, "timeout_s", design.DEFAULT_TIMEOUT_S),
                                request_id=_int(a, "request_id"))
            return _design_out(res)
        if action == "get":
            v = design.load_version(name, _int(a, "version"))
            meta = v["meta"]
            source = v["source"]
            out = {"ok": True, "name": v["name"], "version": v["version"], "versions": v["versions"],
                   "rendered": bool(meta.get("ok")), "error": meta.get("error") or "",
                   "error_line": meta.get("error_line"), "size_mm": meta.get("size_mm"),
                   "volume_cm3": meta.get("volume_cm3"), "est_grams_max": meta.get("est_grams_max"),
                   "params": meta.get("params") or {}, "part": meta.get("part") or "",
                   "bodies": meta.get("bodies"), "simple": meta.get("simple"), "inverted": meta.get("inverted"),
                   "suspect": meta.get("suspect") or [],
                   "warnings": meta.get("warnings") or [], "echo": meta.get("echo") or [],
                   "library_file_ids": meta.get("library_file_ids") or [],
                   "scad": source[:DESIGN_SOURCE_LIMIT], "scad_path": v["scad_path"], "stl_path": v["stl_path"],
                   "previews": v["previews"], "media": [f"MEDIA:{p}" for p in v["previews"]]}
            if len(source) > DESIGN_SOURCE_LIMIT:
                out["scad_truncated"] = True
            return out
        return _design_upload(rt, design, name, a, kw)
    except design.DesignError as e:
        out = {"ok": False, "code": e.code, "error": str(e)}
        out.update(e.extra)
        if e.code == "no_openscad":
            out["hint"] = design.INSTALL_HINT
        return out


def _design_upload(rt, design, name: str, a: dict, kw: dict) -> dict:
    be, store = rt.backend, rt.store
    slug = design.slugify(name)
    version = _int(a, "version")
    if version is None:
        rendered = design.ok_versions(slug)
        if not rendered:
            if not design.versions(slug):
                raise design.DesignError("not_found", f"no design named '{slug}' (home3d_design action=list)")
            raise design.DesignError("not_found", f"no version of '{slug}' rendered to a model yet: fix it and "
                                                  "render again first")
        # never guess: design names are shared between chats, and a later render may be one part or a picture
        if len(rendered) > 1 or rendered[0]["part"] not in ("", "all"):
            raise design.DesignError("bad_args", f"give the version the person approved: '{slug}' has "
                                                 f"{_versions_text(rendered)}", versions=rendered)
        version = rendered[0]["version"]
    v = design.load_version(slug, version)
    meta = v["meta"]
    if not meta.get("ok") or not v["stl_path"]:
        raise design.DesignError("not_found", f"{slug} v{version} did not render to a model "
                                              f"({meta.get('error') or 'no STL'}): render it again first")
    lib = be.upload_file(Path(v["stl_path"]))
    store.kv_set(f"design_lib:{lib.id}", {"slug": slug, "version": int(version)})
    design.record_upload(slug, int(version), lib.id)
    ref = f"design:{slug}_v{version}"
    warnings: list[str] = []
    if meta.get("suspect"):
        warnings.append(f"v{version} rendered with part of its code ignored: " + "; ".join(meta["suspect"][:3]))
    if meta.get("part") not in (None, "", "all"):
        warnings.append(f"v{version} is only part '{meta['part']}' of the design")
    request_id = _int(a, "request_id")
    if request_id is None and meta.get("request_id") is not None:
        request_id = int(meta["request_id"])
    if request_id is not None and store.get_request(request_id) is None:
        warnings.append(f"request {request_id} not found")
        request_id = None
    if request_id is None and _str(a, "request_text"):
        requester, sender = _who(rt, kw, _str(a, "requester"))
        request_id = store.add_request(requester=requester, text=_str(a, "request_text"), channel="text",
                                       sender_id=sender, model_ref=ref)
    if request_id is not None:
        store.update_request(request_id, library_file_id=lib.id, model_ref=ref)
    size = meta.get("size_mm")
    bodies = meta.get("bodies")
    nxt = f"home3d_slice library_file_id={lib.id}" + (f" request_id={request_id}" if request_id else "")
    if isinstance(bodies, int) and bodies > 1:
        nxt += f" ({bodies} separate parts: the slice keeps them on the plate for the owner to take off)"
    return {"ok": True, "library_file_id": lib.id, "name": lib.name, "design": slug, "version": int(version),
            "part": meta.get("part") or "", "bodies": bodies,
            "size_mm": size, "size_cm": [round(float(x) / 10.0, 1) for x in size] if size else None,
            "est_grams_max": meta.get("est_grams_max"), "request_id": request_id, "warnings": warnings,
            "next": nxt}


# ---- schemas ----------------------------------------------------------------------------------------
def _schema(name: str, description: str, props: Optional[dict] = None, required: Optional[list] = None) -> dict:
    params: dict = {"type": "object", "properties": props or {}}
    if required:
        params["required"] = required
    return {"name": name, "description": description, "parameters": params}


_INT = {"type": "integer"}

SPECS: list[tuple[str, str, dict, list, Callable]] = [
    ("home3d_status",
     "Show 3D printer, queue and household job status. Printer state, progress, temperatures, HMS errors, "
     "AMS trays, the print queue with who asked, recent jobs, open requests, plate state and watcher freshness.",
     {}, [], _h_status),
    ("home3d_camera",
     "Take a lit photo from the 3D printer camera. Returns the image path and a MEDIA: line to put in the "
     "reply; check_plate=true also asks the camera whether the build plate is empty.",
     {"check_plate": {"type": "boolean", "description": "Also run the empty-plate check."}}, [], _h_camera),
    ("home3d_find_models",
     "Look up MakerWorld 3D models from links or ids. MakerWorld has no search here: find candidates with web "
     "search 'site:makerworld.com <thing>' first, then pass up to 6 links. Returns cards (title, cover, "
     "license, likes, A1 profiles with print time and grams) to offer 2-4 options.",
     {"urls": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_FIND,
               "description": "MakerWorld model links or numeric model ids."}}, ["urls"], _h_find_models),
    ("home3d_import",
     "Import a MakerWorld model into the printer library. Picks the A1 print profile when profile_id is "
     "omitted and records who asked (request). A new request needs request_text: 2-3 words naming the thing in "
     "the requester's own language (or pass request_id).",
     {"model_id": {"type": "integer", "description": "MakerWorld model id (from home3d_find_models)."},
      "profile_id": {"type": "integer", "description": "Print profile id from a card's a1_profiles "
                                                      "(a #profileId-N URL fragment is NOT a profile id)."},
      "requester": {"type": "string", "description": "Who asked (defaults to the person talking)."},
      "request_text": {"type": "string", "description": "Required for a new request: 2-3 words naming the thing, "
                                                           "in the requester's own language (e.g. 'çiçek kutusu', not "
                                                           "their whole sentence); family messages name the print by "
                                                           "it."},
      "channel": {"type": "string", "enum": ["text", "voice", "photo", "link", "cli"]},
      "request_id": {"type": "integer", "description": "Existing request to attach to."}},
     ["model_id"], _h_import),
    ("home3d_customize",
     "Scale a 3D model or render a name tag template. Scale a library model (scale factor or target_size_mm "
     "for the largest side) or render an OpenSCAD template (name_tag, label_box); uploads the result and "
     "returns the new library_file_id and size. Fitted parts (lids, threads) need confirm_mechanism=true.",
     {"library_file_id": {"type": "integer", "description": "Model to scale (not a sliced file)."},
      "scale": {"type": "number", "description": "Uniform factor, e.g. 1.5 or 0.8."},
      "target_size_mm": {"type": "number", "description": "Make the largest dimension this many mm."},
      "template": {"type": "string", "enum": sorted(customize.TEMPLATES)},
      "params": {"type": "object", "description": "Template parameters, e.g. {\"text\": \"Sam\", \"width\": 80}."},
      "name": {"type": "string", "description": "Model title, used to spot fitted parts (lid, thread, ...)."},
      "confirm_mechanism": {"type": "boolean", "description": "The requester agreed to scale a fitted part."},
      "request_id": _INT}, [], _h_customize),
    ("home3d_design",
     "Design a 3D-printable part in OpenSCAD. Write parametric .scad code, render it to STL with preview images, "
     "iterate in versions, then upload it for slicing. render (name + scad, or name + from_version + params) "
     "returns size, volume, warnings, echo and preview images (media: MEDIA lines; look at them first); get "
     "returns a version's code; list; upload returns a library_file_id for home3d_slice.",
     {"action": {"type": "string", "enum": ["render", "get", "list", "upload"]},
      "name": {"type": "string", "description": "Design name, a few words (e.g. 'phone stand'); the folder slug "
                                                "it returns as name works too."},
      "scad": {"type": "string", "description": "render: the full OpenSCAD source (parameters with units first, "
                                                "assert/echo checks). Omit it to re-render from_version."},
      "from_version": {"type": "integer", "description": "render: reuse this version's code, params and part, "
                                                         "with 'params' applied on top (a quick tweak)."},
      "params": {"type": "object", "description": "render: top-level variables to override (-D), e.g. "
                                                  "{\"width\": 80, \"label\": \"Sam\"}: numbers, true/false, short "
                                                  "strings, lists of numbers; null drops an inherited one."},
      "views": {"type": "array", "items": {"type": "string", "enum": ["iso", "top", "front", "side", "plan",
                                                                       "bottom"]},
                "description": "render: preview images (default iso and top; [] for none). top/front/side are flat "
                               "outlines that hide raised or cut-in detail; plan (top tilted 25 deg) and iso show "
                               "text, pockets and compartments; bottom shows the bed face."},
      "part": {"type": "string", "description": "render: sets the .scad variable part (e.g. \"lid\") to render "
                                                "one part of a multi-part design; \"\" clears an inherited one."},
      "version": {"type": "integer", "description": "get/upload: version number (get: the latest). upload: the "
                                                    "version the person approved; needed when more than one "
                                                    "rendered."},
      "request_id": _INT,
      "request_text": {"type": "string", "description": "upload without request_id: 2-3 words naming the thing in "
                                                        "the requester's language (records a new request)."},
      "requester": {"type": "string", "description": "upload: who asked (defaults to the person talking)."},
      "timeout_s": {"type": "integer", "description": "render: OpenSCAD time limit in seconds (default 180, max "
                                                      "600)."}},
     ["action"], _h_design),
    ("home3d_slice",
     "Slice a 3D model for printing with the right presets. Picks process/filament presets, uses the "
     "auto-eject printer preset only when the part is safe to push off (eject=auto), inspects the G-code and "
     "returns print time, grams, eject plan + reasons, warnings, preview link and a suggested AMS slot.",
     {"library_file_id": {"type": "integer", "description": "Library model to slice."},
      "quality": {"type": "string", "enum": ["draft", "standard", "fine"]},
      "material": {"type": "string", "description": "PLA (default), PETG, TPU, ..."},
      "colour": {"type": "string", "description": "Colour name or #RRGGBB (used to pick the AMS tray)."},
      "eject": {"type": "string", "enum": ["auto", "on", "off"],
                "description": "auto (default): push the part off only when it is safe."},
      "request_id": _INT}, ["library_file_id"], _h_slice),
    ("home3d_queue",
     "Add, list or remove 3D print queue items. add always queues with manual start (nothing starts by "
     "itself) and records the job, requester and eject plan; ams_slot is the zero-based AMS tray.",
     {"action": {"type": "string", "enum": ["add", "list", "remove"]},
      "sliced_file_id": {"type": "integer", "description": "For add: sliced_file_id from home3d_slice."},
      "ams_slot": {"type": "integer", "description": "Zero-based AMS tray (defaults to the suggested slot)."},
      "request_id": _INT, "requester": {"type": "string"},
      "queue_item_id": {"type": "integer", "description": "For remove: only the asking person's own waiting item."},
      "include_done": {"type": "boolean", "description": "For list: include finished items."}},
     ["action"], _h_queue),
    ("home3d_start",
     "Start a queued 3D print (owner approval required). Re-checks the safety gates (printer idle, no HMS "
     "error, the camera thinks the plate is empty, after a failed print the owner confirmed the plate, nobody "
     "else's job ahead) before starting. Only works when approved through Hermes or /home3d approve.",
     {"queue_item_id": {"type": "integer"},
      "allow_jump": {"type": "boolean", "description": "Owner explicitly allows skipping jobs ahead."}},
     ["queue_item_id"], _h_start),
    ("home3d_stop",
     "Stop, pause or resume the current 3D print. Anyone may stop or pause (\"dur\" = stop now); the reason "
     "and who asked are logged. Resume needs the owner's approval; with an active printer error (HMS) the "
     "owner must also acknowledge it (ack_hms=true).",
     {"action": {"type": "string", "enum": ["stop", "pause", "resume"]},
      "reason": {"type": "string", "description": "Why, in a few words."},
      "ack_hms": {"type": "boolean", "description": "Resume only, owner only: resume although a printer error "
                                                    "(HMS) is still active."}},
     ["action"], _h_stop),
    ("home3d_clear_plate",
     "Check or confirm the 3D printer build plate is clear. check = photo + plate check + bed temperature; "
     "confirm = tell the printer manager the plate is clear and record that a person confirmed it (needed "
     "before the next start after a failed print; gated, owner approval).",
     {"action": {"type": "string", "enum": ["check", "confirm"]}}, ["action"], _h_clear_plate),
    ("home3d_household",
     "Recall who asked for which 3D prints at home. who = household members and who is talking; history = "
     "a person's requests and jobs; remember = a fact about a person; note = a household note or a request "
     "outcome (request_id).",
     {"action": {"type": "string", "enum": ["who", "history", "remember", "note"]},
      "person": {"type": "string"}, "text": {"type": "string"}, "request_id": _INT},
     ["action"], _h_household),
    ("home3d_human_needed",
     "Log a moment a person had to step in at the printer. Kinds: remove_part, clean_plate, filament_swap, "
     "camera_check, failure_check, measure, post_process, approve_start, other. Repeated moments become "
     "upgrade proposals.",
     {"action": {"type": "string", "enum": ["log", "list"]}, "kind": {"type": "string"},
      "detail": {"type": "string"}, "who": {"type": "string"}, "job_name": {"type": "string"}},
     ["action"], _h_human_needed),
    ("home3d_upgrades",
     "List and manage 3D printer upgrade proposals. Proposals come from repeated human-needed moments; the "
     "owner moves them proposed -> accepted -> printing -> installed (or rejected).",
     {"action": {"type": "string", "enum": ["list", "evaluate", "accept", "reject", "printing", "installed"]},
      "upgrade_id": _INT, "note": {"type": "string"}, "status": {"type": "string"}},
     ["action"], _h_upgrades),
]


def _wrap(rt, name: str, fn: Callable) -> Callable[..., str]:
    def handler(args: dict, **kwargs) -> str:
        try:
            a = args if isinstance(args, dict) else {}
            out = access_refusal(rt, name, a, kwargs) or fn(rt, a, kwargs)
            if isinstance(out, dict):
                out.setdefault("ok", True)
        except ArgError as e:
            out = {"ok": False, "error": str(e)}
        except BackendError as e:
            out = {"ok": False, "error": str(e), "backend_error": True}
        except customize.CustomizeError as e:
            out = {"ok": False, "error": str(e)}
        except Exception as e:  # handlers never raise into Hermes
            out = {"ok": False, "error": f"{name} failed: {type(e).__name__}: {e}"}
        return _dump(out)

    handler.__name__ = name
    handler.__qualname__ = name
    return handler


def build_tools(rt) -> list[Tool]:
    """(name, schema, handler) for every ``home3d_*`` tool, bound to the shared Runtime."""
    return [(name, _schema(name, desc, props, req), _wrap(rt, name, fn)) for name, desc, props, req, fn in SPECS]


__all__ = ["build_tools", "SPECS", "SEARCH_HINT", "DEFAULT_PROCESS_PRESETS", "DEFAULT_FILAMENT_PRESETS",
           "DEFAULT_PRINTER_PRESET"]
