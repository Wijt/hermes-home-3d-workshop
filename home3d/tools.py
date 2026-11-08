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
from .gates import clear_plate_gate, describe, printer_blocks, resume_gate, start_gate
from .gcode import assess_eject, inspect_gcode, material_family
from .hooks import LIGHT_FLAG, acked_codes, approval_target

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
    """(requester name, sender id) of the person talking in this session."""
    sid = kw.get("session_id") or ""
    sender = rt.sender_id(sid) if sid else ""
    name = (explicit or "").strip() or (rt.requester_name(sid, "") if sid else "")
    return name, sender


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


def _plate_confirmed(store, job_name: str) -> bool:
    try:
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
    out["watcher"] = {"last_run_age_s": round(age) if age is not None else None,
                      "fresh": age is not None and age < WATCHER_STALE_S}
    err = store.kv_get("watcher_error")
    if err:
        out["watcher"]["error"] = str(err)[:200]
    if not out["watcher"]["fresh"]:
        out["watcher"]["hint"] = ("the watcher has not run recently: notifications and plate checks are off "
                                  "(owner: 'hermes home3d setup')")
    me, _ = _who(rt, kw)
    if me:
        out["speaking"] = me
    return out


def _h_camera(rt, a: dict, kw: dict) -> dict:
    be = rt.backend
    snap = be.snapshot(rt.media_dir, lit=True)
    path = str(Path(snap.path).resolve())
    out = {"ok": True, "path": path, "media_line": f"MEDIA:{path}", "lit": snap.lit, "note": snap.note,
           "hint": "Put media_line on its own line in your reply to attach the photo."}
    if _bool(a, "check_plate"):
        try:
            out["plate"] = _plate_dict(be.check_plate())
        except BackendError as e:
            out["plate_error"] = str(e)
    return out


def _is_a1(models: list) -> bool:
    for m in models or []:
        n = re.sub(r"^bambu\s*lab\s*", "", str(m).strip(), flags=re.I).replace(" ", "").upper()
        if n in ("A1", "N2S"):  # product name or MakerWorld device code
            return True
    return False


def _card(c) -> dict:
    a1 = [i for i in c.instances if _is_a1(i.printer_models)]
    d = {"model_id": c.model_id, "title": c.title, "url": c.url, "cover_url": c.cover_url,
         "creator": c.creator, "license": c.license, "likes": c.likes, "downloads": c.downloads,
         "prints": c.prints, "summary": (c.summary or "")[:240],
         "a1_profiles": [{"profile_id": i.profile_id, "title": i.title, "print_time_min": i.print_time_min,
                          "weight_g": i.weight_g, "plates": i.plates} for i in a1],
         "other_profiles": len(c.instances) - len(a1),
         "already_imported_library_ids": list(c.already_imported_library_ids)}
    if not a1:
        d["note"] = "no A1 print profile: it can still be imported and sliced with our A1 presets"
    return d


def _h_find_models(rt, a: dict, kw: dict) -> dict:
    raw = a.get("urls")
    if isinstance(raw, str):
        raw = re.split(r"[\s,]+", raw)
    elif not isinstance(raw, (list, tuple)):
        raw = [raw] if raw else []
    urls = list(dict.fromkeys(str(u).strip() for u in (raw or []) if str(u).strip()))
    if not urls:
        return {"ok": False, "error": "pass 1-6 MakerWorld links or model ids in 'urls'", "hint": SEARCH_HINT}
    cards, errors = [], []
    for u in urls[:MAX_FIND]:
        try:
            cards.append(_card(rt.backend.resolve_model(u)))
        except BackendError as e:
            errors.append({"input": u, "error": str(e)})
    out = {"ok": bool(cards), "cards": cards, "errors": errors, "hint": SEARCH_HINT,
           "next": ("Show the requester 2-4 options (cover picture, title, print time), let them choose, "
                    "then call home3d_import with model_id and an A1 profile_id.")}
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
        reasons = (["eject=off"] if eject == "off" else list(assess.reasons) if not pla_like and auto_p
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
        mine = job is not None and bool(who) and (job.get("requester") or "").lower() == who.lower()
        if not (_is_owner(rt, sender) or mine):
            return {"ok": False, "error": "only the owner or the person who asked can remove this item"}
        be.queue_remove(qid)
        by = who or "owner"
        store.upsert_job(qid, state="cancelled", outcome=f"removed by {by}")
        req = store.request_for_queue_item(qid)
        if req:
            store.update_request(req["id"], status="cancelled", outcome=f"removed from the queue by {by}")
        store.add_event("queue_removed", item.name, {"queue_item_id": qid, "who": by, "sender": sender})
        return {"ok": True, "removed": qid, "name": item.name}

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
                      allow_jump=jump, voice_request=bool(req and req.get("channel") == "voice"),
                      plate_confirmed=_plate_confirmed(store, status.job_name),
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
    job = store.get_job(qid) or {}
    store.add_event("start_requested", item.name or job.get("name", ""),
                    {"queue_item_id": qid, "who": who or "owner", "sender": sender})
    return {"ok": True, "queue_item_id": qid, "status": item.status, "name": item.name or job.get("name", ""),
            "requester": job.get("requester", ""), "eject_planned": bool(job.get("eject_planned")),
            "started_by": who or "owner", "warnings": warnings + gate.warnings,
            "next": "The watcher reports progress, the finish and the plate state; no need to poll."}


def _h_stop(rt, a: dict, kw: dict) -> dict:
    s, be, store = rt.settings, rt.backend, rt.store
    action = _choice(a, "action", ("stop", "pause", "resume"), "stop")
    pass_detail = ""
    if action == "resume":  # stop / pause need no pass: stopping must always work
        refused, pass_detail = _take_pass(rt, "home3d_stop", approval_target("resume"), kw)
        if refused:
            return refused
    reason = _str(a, "reason")
    who, sender = _who(rt, kw)
    by = who or "owner"
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
            return {"ok": False, "error": f"nothing is printing (state {st.state}): no command sent",
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
    if action == "check":
        try:
            snap = be.snapshot(rt.media_dir, lit=True)
            path = str(Path(snap.path).resolve())
            out.update(path=path, media_line=f"MEDIA:{path}")
        except BackendError as e:
            out["photo_error"] = str(e)
    plate = None
    try:
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
    store.confirm_plate(st.job_name or "", by)  # a person looked: after a failed print the next start may go
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
                "thresholds": {k: v.get("threshold") for k, v in kinds.items() if isinstance(v, dict)}}
    raw_kind = _str(a, "kind") or "other"
    normalize = getattr(upgrades, "normalize_kind", None)
    kind = normalize(raw_kind) if callable(normalize) else raw_kind.lower()
    who = _str(a, "who") or _who(rt, kw)[0]
    mid = upgrades.log_moment(store, raw_kind, _str(a, "detail"), job_name=_str(a, "job_name"), who=who,
                              source="agent")
    new = upgrades.evaluate(store, rt.settings) or []
    info = kinds.get(kind) if isinstance(kinds.get(kind), dict) else {}
    window = info.get("window_days", 30) if info else 30
    return {"ok": True, "id": mid, "kind": kind, "who": who,
            "count": store.human_needed_counts(window).get(kind, 0), "threshold": info.get("threshold"),
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
     "omitted and records who asked (request).",
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
      "queue_item_id": {"type": "integer", "description": "For remove."},
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
            out = fn(rt, args if isinstance(args, dict) else {}, kwargs)
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
