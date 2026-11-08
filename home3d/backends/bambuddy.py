"""Bambuddy backend: a Bambu Lab printer managed by a Bambuddy server on the LAN (REST API ``/api/v1``).

Stdlib only (``urllib.request``); Pillow is used lazily to re-encode camera frames. Every failure surfaces
as ``BackendError("<METHOD> <path>: <status> <short body>")`` (an HTTP error status is the subclass
``BambuddyHTTPError``); a refused start reads ``"Bambuddy refused to start queue item N: <reason> (HTTP 409)"``.
Parsing fails closed (unknown state -> UNKNOWN, ``connected`` must be literally true, unlit or failed plate
checks are never "empty"). See docs/DESIGN.md "Bambuddy mapping".
"""

from __future__ import annotations

import copy
import html
import http.client
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional

from .base import (DONE_QUEUE_STATUSES, FAILED, FINISH, IDLE, OFFLINE, PAUSE, PREPARE, RUNNING, UNKNOWN, Backend,
                   BackendError, HMSError, LibraryFile, ModelCard, ModelInstance, PlateCheck, PrinterStatus,
                   QueueItem, SliceOptions, SliceResult, Snapshot, Tray)

API_PREFIX = "/api/v1"
MAKERWORLD_MODEL_URL = "https://makerworld.com/en/models/{id}"
HMS_WIKI_URL = "https://wiki.bambulab.com/en/a1/troubleshooting/hmscode/{code}"

# Bambuddy's built-in plate check reports 18-25 % difference on an *empty* plate (bed parked, faint marks),
# so "not empty" below this is treated as uncertain, never as a decision.
PLATE_FALSE_POSITIVE_MAX_PCT = 26.0

DONE_QUEUE_STATES = DONE_QUEUE_STATUSES
PRESET_SOURCES = ("local", "standard", "cloud", "orca_cloud")
# Same markers as gcode.EJECT_MARKERS (kept local so the backend has no sibling imports).
EJECT_MARKERS = ("HOME3D AUTO-EJECT", "HERMES AUTO-EJECT")

# Slicing defaults from the real system (slice-api-recipe.md): Arachne walls, anti-string travel,
# slope-lift z-hop, no prime tower, no brim. ``SliceOptions.process_overrides`` wins over these.
DEFAULT_PROCESS_OVERRIDES = {
    "wall_generator": "arachne",
    "reduce_crossing_wall": "1",
    "reduce_infill_retraction": "0",
    "z_hop": "0.4",
    "z_hop_types": "Slope Lift",
    "enable_prime_tower": "0",
    "brim_type": "no_brim",
}

_KNOWN_STATES = {IDLE, PREPARE, RUNNING, PAUSE, FINISH, FAILED}
_STATE_ALIASES = {"SLICING": PREPARE, "INIT": PREPARE, "PRINTING": RUNNING, "PAUSED": PAUSE,
                  "FINISHED": FINISH, "COMPLETED": FINISH, "ERROR": FAILED}
_HMS_SEVERITY = {1: "fatal", 2: "serious", 3: "common", 4: "info"}
_JFIF_APP0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


class BambuddyHTTPError(BackendError):
    """Bambuddy answered with an HTTP error status. Still a ``BackendError``; ``status`` is the HTTP code and
    ``detail`` the short, readable reason (without the method/path prefix)."""

    def __init__(self, message: str, status: int, detail: str):
        super().__init__(message)
        self.status = int(status)
        self.detail = detail


def _urlopen(req: urllib.request.Request, timeout: float):
    """Indirection so tests can replace the network with a fake."""
    return urllib.request.urlopen(req, timeout=timeout)


# ---- small parsing helpers -----------------------------------------------------------------------
def _int(v: Any) -> Optional[int]:
    try:
        return None if v is None or v == "" else int(float(v))
    except (TypeError, ValueError):
        return None


def _float(v: Any) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _short(text: str, limit: int = 200) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _grams(v: Any) -> str:
    f = _float(v)
    return "?" if f is None else f"{f:.0f}" if f >= 10 else f"{f:.1f}"


def _slot_label(ams_id: Any, tray_id: Any) -> str:
    """Bambu naming: AMS units A, B, ... with slots 1-4; 255 = the external spool; 128+ = AMS HT units."""
    a, t = _int(ams_id), _int(tray_id)
    if a is None:
        return ""
    if a >= 255:
        return "external spool"
    if a >= 128:
        return f"AMS HT {a - 127}"
    return f"AMS {chr(65 + a) if a < 26 else a} slot {(t or 0) + 1}"


def _structured_detail(detail: dict) -> str:
    """Readable text for Bambuddy's structured refusals (queue start: 409 insufficient / unmatched filament)."""
    code = str(detail.get("code") or "")
    if code == "insufficient_filament":
        parts = []
        for d in detail.get("deficit") or []:
            if not isinstance(d, dict):
                continue
            where = _slot_label(d.get("ams_id"), d.get("tray_id"))
            what = str(d.get("filament_type") or "filament") + (f" in {where}" if where else "")
            left = d.get("remaining_grams")
            parts.append(f"{what} needs {_grams(d.get('required_grams'))} g, "
                         + ("amount left unknown" if left is None else f"{_grams(left)} g left"))
        return "not enough filament" + (": " + "; ".join(parts) if parts else "")
    if code == "unmatched_filament":
        missing = [str(m) for m in detail.get("missing") or [] if str(m).strip()]
        return "no loaded filament matches what the job needs" + (": " + ", ".join(missing) if missing else "")
    msg = detail.get("message") or detail.get("detail") or detail.get("error")
    if isinstance(msg, str) and msg.strip():
        return msg
    return code.replace("_", " ") if code else json.dumps(detail, ensure_ascii=False)


def _error_detail(body: bytes) -> str:
    raw = body.decode("utf-8", "replace") if body else ""
    try:
        data = json.loads(raw)
    except ValueError:
        return _short(raw)
    if isinstance(data, dict):
        detail = data.get("detail", data.get("message", data.get("error", data)))
        if isinstance(detail, list):  # FastAPI 422: [{"loc": [...], "msg": "..."}]
            detail = "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
        elif isinstance(detail, dict):
            detail = _structured_detail(detail)
        return _short(detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False))
    return _short(raw)


def _file_kind(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".gcode.3mf"):
        return "gcode.3mf"
    return name.rsplit(".", 1)[-1] if "." in name else ""


def _library_file(file_id: Any, filename: str, kind: str = "") -> LibraryFile:
    fid = _int(file_id)
    if fid is None:
        raise BackendError(f"Bambuddy returned no library file id for {filename or 'file'}")
    kind = kind or _file_kind(filename)
    return LibraryFile(id=fid, name=filename or "", kind=kind, sliced=kind in {"gcode.3mf", "gcode"})


def preset_ref(value: str) -> dict:
    """Preset string -> Bambuddy ``PresetRef``: numeric -> local id, ``source:id`` -> that source,
    anything else -> a standard (OrcaSlicer-bundled) preset by name."""
    v = str(value).strip()
    if v.isdigit():
        return {"source": "local", "id": v}
    src, sep, rest = v.partition(":")
    if sep and src in PRESET_SOURCES and rest.strip():
        return {"source": src, "id": rest.strip()}
    return {"source": "standard", "id": v}


def _hms_code(raw: Any) -> str:
    """``XXXX-XXXX-XXXX-XXXX`` (or ``XXXX-XXXX`` for short print errors) where the value allows it; ints are
    read as the numeric code. Anything else is kept as given (it still blocks: only known codes are ignored)."""
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        code = f"{raw:016X}" if raw >= 1 << 32 else f"{raw:08X}"
        return "-".join(code[i:i + 4] for i in range(0, len(code), 4))
    code = str(raw if raw is not None else "").strip().upper().replace("_", "").replace("-", "")
    if code.startswith("HMS"):
        code = code[3:]
    if code.startswith("0X"):
        code = code[2:]
    if re.fullmatch(r"[0-9A-F]{16}|[0-9A-F]{8}", code):
        return "-".join(code[i:i + 4] for i in range(0, len(code), 4))
    return str(raw if raw is not None else "").strip()


def _wiki(code: str) -> str:
    return HMS_WIKI_URL.format(code=code.replace("-", "_")) if len(code) == 19 else ""


def _parse_hms(h: dict) -> HMSError:
    code = _hms_code(h.get("full_code") or h.get("code") or "") or "unknown"
    sev = h.get("severity")
    severity = _HMS_SEVERITY.get(sev, "") if isinstance(sev, int) else str(sev or "")
    return HMSError(code=code, severity=severity, message=str(h.get("description") or h.get("message") or ""),
                    wiki_url=str(h.get("wiki_url") or _wiki(code)))


def _parse_hms_list(raw: Any) -> list[HMSError]:
    """``hms_errors`` -> HMSError list. Fails closed: dicts, bare string / int codes and anything else that
    is not empty become entries (an unreadable one is code ``unknown``, which blocks), never silently dropped."""
    if raw is None or raw == "" or raw == []:
        return []
    out: list[HMSError] = []
    for h in raw if isinstance(raw, list) else [raw]:
        if h is None or h == "":
            continue
        if isinstance(h, dict):
            out.append(_parse_hms(h))
        elif isinstance(h, (str, int)) and not isinstance(h, bool):
            code = _hms_code(h) or "unknown"
            out.append(HMSError(code=code, wiki_url=_wiki(code)))
        else:
            out.append(HMSError(code="unknown", message=_short(json.dumps(h, default=str), 120)))
    return out


def _tray_color(raw: Any) -> str:
    c = str(raw or "").strip().lstrip("#")
    return f"#{c[:6].upper()}" if re.fullmatch(r"[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", c) else ""


def _parse_tray(t: dict, slot: int) -> Tray:
    material = str(t.get("tray_type") or "")
    remain = _int(t.get("remain"))
    return Tray(slot=slot, material=material, color=_tray_color(t.get("tray_color")) if material else "",
                name=str(t.get("tray_sub_brands") or t.get("tray_id_name") or ""),
                remain_pct=remain if remain is not None and 0 <= remain <= 100 else None,
                loaded=bool(material) and t.get("exists") is not False)


def _parse_state(raw: Any) -> str:
    """Bambu ``gcode_state`` -> normalised state. Missing, null or unrecognised -> UNKNOWN (never IDLE): every
    gate blocks on it, so nothing starts on top of a printer whose state we cannot read."""
    s = str(raw if raw is not None else "").strip().upper()
    if s in _KNOWN_STATES or s == OFFLINE:
        return s
    return _STATE_ALIASES.get(s, UNKNOWN)


def _list(v: Any) -> list:
    return v if isinstance(v, list) else []


def _bool_or_none(v: Any) -> Optional[bool]:
    return v if isinstance(v, bool) else None


def parse_status(d: dict) -> PrinterStatus:
    """Bambuddy ``PrinterStatus`` JSON -> PrinterStatus. Fails closed: the printer counts as connected only when
    ``connected`` is literally true; a missing or unknown state is UNKNOWN; HMS entries are never dropped."""
    temps = d.get("temperatures")
    temps = temps if isinstance(temps, dict) else {}
    connected = d.get("connected") is True
    trays: list[Tray] = []
    for unit in _list(d.get("ams")):
        if not isinstance(unit, dict):
            continue
        uid = _int(unit.get("id")) or 0
        for t in _list(unit.get("tray")):
            if isinstance(t, dict):
                tid = _int(t.get("id")) or 0
                trays.append(_parse_tray(t, uid * 4 + tid if uid < 16 else uid))  # AMS HT units are 128+
    for t in _list(d.get("vt_tray")):  # external spool (ams_mapping 254)
        if isinstance(t, dict) and t.get("tray_type"):
            trays.append(_parse_tray(t, _int(t.get("id")) or 254))
    return PrinterStatus(
        state=_parse_state(d.get("state")) if connected else OFFLINE,
        connected=connected,
        job_name=str(d.get("subtask_name") or d.get("current_print") or d.get("gcode_file") or ""),
        progress=_float(d.get("progress")) or 0.0,
        remaining_min=_int(d.get("remaining_time")),
        layer=_int(d.get("layer_num")),
        total_layers=_int(d.get("total_layers")),
        bed_temp=_float(temps.get("bed")),
        bed_target=_float(temps.get("bed_target")),
        nozzle_temp=_float(temps.get("nozzle")),
        hms=_parse_hms_list(d.get("hms_errors")),
        trays=trays,
        printer_name=str(d.get("name") or ""),
        chamber_light=_bool_or_none(d.get("chamber_light")),
        awaiting_plate_clear=_bool_or_none(d.get("awaiting_plate_clear")),
    )


def parse_queue_item(d: dict) -> QueueItem:
    qid = _int(d.get("id"))
    if qid is None:
        raise BackendError(f"Bambuddy returned a queue item without id: {_short(json.dumps(d))}")
    return QueueItem(
        id=qid,
        status=str(d.get("status") or ""),
        name=str(d.get("library_file_name") or d.get("archive_name") or ""),
        position=_int(d.get("position")),
        library_file_id=_int(d.get("library_file_id")),
        manual_start=bool(d.get("manual_start")),
        print_time_s=_int(d.get("print_time_seconds")),
        scheduled_time=d.get("scheduled_time"),
        created_at=d.get("created_at"),
        archive_id=_int(d.get("archive_id")),
        # a dispatch Bambuddy could not carry out: status "failed", no ``started_at``, the reason here
        error_message=_short(d.get("error_message") or "", 300),
        started_at=str(d["started_at"]) if d.get("started_at") not in (None, "") else None,
    )


def parse_plate_check(d: dict) -> PlateCheck:
    """Bambuddy check-plate JSON -> PlateCheck. Fails closed: ``is_empty`` stays True only for a check that ran
    (no ``failure_reason``: Bambuddy then reports empty so that its own prints are not blocked), with the
    chamber light on (no ``light_warning``: an unlit frame cannot be compared with the lit references) and
    calibrated. "Not empty" inside the known false-positive band is uncertain, never a decision."""
    raw = d.get("is_empty")
    is_empty: Optional[bool] = raw if isinstance(raw, bool) else None
    diff = _float(d.get("difference_percent"))
    needs_cal = bool(d.get("needs_calibration"))
    failure = str(d.get("failure_reason") or "").strip()
    light_warning = bool(d.get("light_warning"))
    msg = str(d.get("message") or "").strip()
    band = False  # the only doubt is the false-positive band (a person may overrule it, see gates)
    if failure:
        is_empty = None
        msg = f"uncertain: the plate check could not run ({failure}). {msg}".strip()
    elif needs_cal:
        is_empty, msg = None, f"plate detection needs calibration. {msg}".strip()
    elif is_empty is False and diff is not None and diff < PLATE_FALSE_POSITIVE_MAX_PCT:
        is_empty, band = None, True
        msg = (f"uncertain: {diff:.1f}% difference is inside the known false-positive band "
               f"(<{PLATE_FALSE_POSITIVE_MAX_PCT:.0f}%); look at the photo. {msg}").strip()
    if light_warning:
        is_empty, band = None, False
        msg = f"uncertain: the chamber light was off, the camera cannot judge the plate. {msg}".strip()
    return PlateCheck(is_empty=is_empty, difference_pct=diff, confidence=_float(d.get("confidence")),
                      message=msg, needs_calibration=needs_cal, light_ok=not light_warning, uncertain_band=band)


def _strip_html(text: str, limit: int = 600) -> str:
    text = re.sub(r"<(br|/p|/div|/li|/h\d)\s*/?>", "\n", str(text or ""), flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    out = "\n".join(line for line in lines if line)
    return out if len(out) <= limit else out[: limit - 1] + "…"


def _parse_instance(i: dict) -> Optional[ModelInstance]:
    pid = _int(i.get("profileId"))
    if pid is None:
        return None
    ext = i.get("extention") or i.get("extension") or {}
    info = (ext.get("modelInfo") if isinstance(ext, dict) else None) or {}
    compat = i.get("compatibility") or info.get("compatibility") or {}
    model = _printer_name(compat)
    others = i.get("otherCompatibility") or info.get("otherCompatibility") or []
    compatible = [n for n in dict.fromkeys(_printer_name(o) for o in others if isinstance(o, dict)) if n and n != model]
    plates = i.get("plates")
    if not isinstance(plates, list):
        plates = info.get("plates") if isinstance(info.get("plates"), list) else plates
    secs = _float(i.get("prediction")) or _float(i.get("printTime"))
    grams = _float(i.get("weight"))
    if isinstance(plates, list):
        if secs is None:
            secs = sum(_float(p.get("prediction")) or 0 for p in plates if isinstance(p, dict)) or None
        if grams is None:
            grams = sum(_float(p.get("weight")) or 0 for p in plates if isinstance(p, dict)) or None
    n_plates = len(plates) if isinstance(plates, list) else _int(plates)
    return ModelInstance(profile_id=pid, title=str(i.get("title") or ""), printer_models=[model] if model else [],
                         print_time_min=int(round(secs / 60)) if secs else None,
                         weight_g=round(grams, 2) if grams else None, plates=n_plates or None,
                         compatible_models=compatible)


def _printer_name(compat: Any) -> str:
    if not isinstance(compat, dict):
        return ""
    return str(compat.get("devProductName") or compat.get("devModelName") or "").strip()


def parse_model(d: dict, url: str = "") -> ModelCard:
    design = d.get("design") or {}
    model_id = _int(d.get("model_id")) or _int(design.get("id"))
    if model_id is None:
        raise BackendError("MakerWorld resolve returned no model id")
    # Bambuddy 1.3.0 returns the full MakerWorld design (``design.instances``: compatibility, other
    # compatible printers, print time, weight) plus a flattened top-level ``instances`` list whose
    # details are empty. Prefer the full one.
    rich = [i for i in design.get("instances") or [] if isinstance(i, dict)]
    flat = [i for i in d.get("instances") or [] if isinstance(i, dict)]
    raw_instances = rich or flat
    # "#profileId-NNN" in a pasted link is an *instance* id: put that instance first.
    frag = re.search(r"#profileId-(\d+)", url or "")
    if frag:
        raw_instances.sort(key=lambda i: str(i.get("id")) != frag.group(1))
    instances = [m for m in (_parse_instance(i) for i in raw_instances) if m is not None]
    creator = design.get("designCreator") or {}
    return ModelCard(
        model_id=model_id,
        title=str(design.get("title") or design.get("titleTranslated") or f"MakerWorld {model_id}"),
        url=url or MAKERWORLD_MODEL_URL.format(id=model_id),
        cover_url=str(design.get("coverUrl") or ""),
        creator=str(creator.get("name") or "") if isinstance(creator, dict) else str(creator),
        license=str(design.get("license") or ""),
        likes=_int(design.get("likeCount")),
        downloads=_int(design.get("downloadCount")),
        prints=_int(design.get("printCount")),
        summary=_strip_html(design.get("summary") or ""),
        instances=instances,
        already_imported_library_ids=[x for x in (_int(v) for v in d.get("already_imported_library_ids") or [])
                                      if x is not None],
    )


def makerworld_url(url_or_id: str) -> str:
    v = str(url_or_id or "").strip()
    if not v:
        raise BackendError("no MakerWorld link or model id given")
    if v.isdigit():
        return MAKERWORLD_MODEL_URL.format(id=v)
    if "://" not in v and v.lower().startswith(("makerworld.", "www.makerworld.")):
        return "https://" + v
    return v


def _filament_types(gcode: str) -> list[str]:
    m = re.search(r"^;\s*filament_type\s*=\s*(.+)$", gcode, flags=re.M)
    out: list[str] = []
    for t in (m.group(1).split(";") if m else []):
        t = t.strip().strip('"')
        if t and t not in out:
            out.append(t)
    return out


def ensure_jfif(data: bytes) -> bytes:
    """Insert a JFIF APP0 header into a bare JPEG (raw camera frames lack it; WhatsApp then rejects them)."""
    if data[:2] == b"\xff\xd8" and data[2:4] != b"\xff\xe0":
        return data[:2] + _JFIF_APP0 + data[2:]
    return data


def reencode_jpeg(data: bytes, max_px: int = 1280, quality: int = 88) -> tuple[bytes, str]:
    """Re-encode a camera frame to a messaging-safe JPEG; falls back to a header fix without Pillow."""
    try:
        from PIL import Image  # type: ignore

        im = Image.open(io.BytesIO(data))
        im = im.convert("RGB")
        im.thumbnail((max_px, max_px))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=quality)
        return out.getvalue(), f"re-encoded {im.width}x{im.height}"
    except Exception:
        if data[:2] != b"\xff\xd8":
            raise BackendError("camera snapshot is not a JPEG image")
        return ensure_jfif(data), "raw frame (Pillow unavailable)"


def truncate_gcode(text: str, max_bytes: int) -> str:
    """Keep the head and the tail (end G-code holds the eject marker) when G-code is huge."""
    raw = text.encode("utf-8")
    if max_bytes <= 0 or len(raw) <= max_bytes:
        return text
    head_n = max_bytes * 3 // 4
    head = raw[:head_n].decode("utf-8", "ignore").rsplit("\n", 1)[0]
    tail = raw[-(max_bytes - head_n):].decode("utf-8", "ignore").split("\n", 1)[-1]
    return f"{head}\n; HOME3D TRUNCATED {len(raw) - max_bytes} bytes\n{tail}"


class BambuddyBackend(Backend):
    name = "bambuddy"
    # A real A1 with the auto-eject preset pushes the part off INSIDE its end G-code (M400 S900, then the sweeps)
    # while it still reports RUNNING at 100 %; FINISH comes after the push.
    eject_in_gcode = True

    timeout_cap: Optional[float] = None  # ``with_timeout``: no request waits longer than this
    timeout_s = 20.0
    slice_timeout_s = 60.0  # POST /slice, POST /makerworld/resolve
    transfer_timeout_s = 120.0  # import / upload / download (files can be 20+ MB)
    light_wait_s = 12.0  # camera exposure settles ~12-15 s after the chamber light turns on
    poll_first_s = 2.0
    poll_max_s = 5.0

    def __init__(self, base_url: str, printer_id: int = 1, api_key: str = "", public_url: str = ""):
        url = str(base_url or "").strip().rstrip("/")
        if not url:
            raise BackendError("bambuddy_url is not set")
        if "://" not in url:
            url = "http://" + url
        if url.endswith(API_PREFIX):
            url = url[: -len(API_PREFIX)]
        self.root = url
        self.api = url + API_PREFIX
        pub = str(public_url or "").strip().rstrip("/") or url
        self.public_url = pub[: -len(API_PREFIX)] if pub.endswith(API_PREFIX) else pub
        self.printer_id = int(printer_id)
        self.api_key = api_key or ""
        self._sleep = time.sleep
        self._clock = time.monotonic

    def with_timeout(self, seconds: float) -> "BambuddyBackend":
        """A copy whose every request (explicit per-call timeouts included) waits at most ``seconds`` per socket
        operation. The ``pre_tool_call`` hook reads status + queue through one so it stays inside Hermes' hook
        budget; the original is not changed."""
        clone = copy.copy(self)
        cap = max(0.1, float(seconds))
        clone.timeout_cap = cap if self.timeout_cap is None else min(cap, self.timeout_cap)
        return clone

    # ---- HTTP -----------------------------------------------------------------------------------
    def _request(self, method: str, path: str, *, params: Optional[dict] = None, json_body: Any = None,
                 data: Optional[bytes] = None, content_type: str = "", timeout: Optional[float] = None,
                 raw: bool = False) -> Any:
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        label = f"{method} {path}"
        url = self.api + path + (("&" if "?" in path else "?") + query if query else "")
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        wait = float(timeout or self.timeout_s)
        if self.timeout_cap is not None:
            wait = min(wait, float(self.timeout_cap))
        try:
            with _urlopen(req, wait) as resp:
                body = resp.read()
                resp_headers = getattr(resp, "headers", None)
        except urllib.error.HTTPError as e:
            try:
                detail = _error_detail(e.read())
            except Exception:
                detail = ""
            reason = detail or _short(e.reason or "")
            raise BambuddyHTTPError(f"{label}: {e.code} {reason}".strip(), e.code, reason) from None
        except urllib.error.URLError as e:
            raise BackendError(f"{label}: {_short(getattr(e, 'reason', e))}") from None
        except (OSError, ValueError, http.client.HTTPException) as e:  # timeouts, resets, bad URL
            raise BackendError(f"{label}: {_short(e) or type(e).__name__}") from None
        if raw:
            return body, resp_headers
        if not body or not body.strip():
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            raise BackendError(f"{label}: invalid JSON response: {_short(body.decode('utf-8', 'replace'), 120)}") \
                from None

    def _get(self, path: str, **kw: Any) -> Any:
        return self._request("GET", path, **kw)

    def _post(self, path: str, body: Any = None, **kw: Any) -> Any:
        return self._request("POST", path, json_body=body, **kw)

    @staticmethod
    def _check_success(resp: Any, what: str) -> Any:
        if isinstance(resp, dict) and resp.get("success") is False:
            raise BackendError(f"{what}: {_short(resp.get('message') or resp.get('detail') or 'failed')}")
        return resp

    @property
    def _printer(self) -> str:
        return f"/printers/{self.printer_id}"

    # ---- read -----------------------------------------------------------------------------------
    def status(self) -> PrinterStatus:
        d = self._get(f"{self._printer}/status")
        if not isinstance(d, dict):
            raise BackendError(f"GET {self._printer}/status: unexpected response")
        return parse_status(d)

    def queue(self, include_done: bool = False) -> list[QueueItem]:
        rows = self._get("/queue/", params={"printer_id": self.printer_id}) or []
        items = [parse_queue_item(r) for r in rows if isinstance(r, dict)]
        live = [q for q in items if not q.is_done]
        live.sort(key=lambda q: (q.status.strip().lower() != "printing",
                                 q.position if q.position is not None else 1 << 30, q.id))
        if not include_done:
            return live
        return live + [q for q in items if q.is_done]

    # ---- chamber light ----------------------------------------------------------------------------
    # The A1's AI failure detection and Bambuddy's own camera use the chamber light, and a person may have
    # switched it on: we only ever switch OFF a light that the printer status reported as off before we
    # switched it on, and never touch a light whose state we cannot read.
    def _light(self, on: bool) -> None:
        self._check_success(self._post(f"{self._printer}/chamber-light", params={"on": "true" if on else "false"}),
                            f"chamber light {'on' if on else 'off'}")

    # The printer status reports the light with a delay. Right after we switch it off, the status (and
    # Bambuddy's own light_warning) can still say "on", so a plate check then could judge a dark frame
    # without any warning. We remember when we switched it off ourselves and treat it as off for a while.
    light_status_lag_s = 30.0

    def _we_switched_off_recently(self) -> bool:
        ts = getattr(self, "_light_off_mono", None)
        return ts is not None and time.monotonic() - ts < self.light_status_lag_s

    def _light_state(self) -> Optional[bool]:
        """The chamber light right now (``chamber_light`` in the printer status); None when unknown."""
        if self._we_switched_off_recently():
            return False  # the status may still show our own earlier "on"
        try:
            d = self._get(f"{self._printer}/status")
        except BackendError:
            return None
        return _bool_or_none(d.get("chamber_light")) if isinstance(d, dict) else None

    def _light_off_safely(self) -> str:
        """Put the light back off after we switched it on (two tries). Returns "" or a note that carries the
        ``light_left_on`` flag so callers can tell the owner."""
        for attempt in range(2):
            try:
                self._light(False)
                self._light_off_mono = time.monotonic()
                return ""
            except BackendError as e:
                if attempt:
                    return f"light_left_on: the chamber light could not be switched off again ({e})"
        return ""

    def _lit_session(self, out_dir: Path, *, lit: bool, with_plate: bool) -> tuple[Snapshot, Optional[PlateCheck]]:
        """One light cycle: switch on (when off), wait, photo, optional plate check, then restore."""
        notes: list[str] = []
        lit_ok = False
        restore_off = False
        plate: Optional[PlateCheck] = None
        data = b""
        try:
            if lit:
                before = self._light_state()
                if before is True:
                    lit_ok = True  # already on: leave it exactly as it is
                elif before is False:
                    restore_off = True  # a failed "on" may still have switched it on
                    try:
                        self._light(True)
                        lit_ok = True
                        self._sleep(self.light_wait_s)
                    except BackendError as e:
                        notes.append(f"light on failed ({e})")
                else:
                    notes.append("chamber light state unknown: photo taken without switching the light")
            data, _ = self._get(f"{self._printer}/camera/snapshot", raw=True, timeout=30.0)
            if with_plate and lit_ok:
                try:  # same light cycle: the plate is judged on a lit frame
                    d = self._get(f"{self._printer}/camera/check-plate", timeout=30.0)
                    if isinstance(d, dict):
                        plate = parse_plate_check(d)
                except BackendError as e:
                    notes.append(f"plate check during the photo failed ({e})")
        finally:
            if restore_off:
                off_note = self._light_off_safely()
                if off_note:
                    notes.append(off_note)
                    if plate is not None:
                        plate.message = f"{plate.message} ({off_note})".strip()
        if not data:
            raise BackendError(f"GET {self._printer}/camera/snapshot: empty image")
        jpeg, how = reencode_jpeg(data)
        notes.insert(0, how)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
        path = out / f"snapshot_p{self.printer_id}_{stamp}.jpg"
        path.write_bytes(jpeg)
        return Snapshot(path=path, lit=lit_ok, note="; ".join(notes)), plate

    def snapshot(self, out_dir: Path, lit: bool = True) -> Snapshot:
        return self._lit_session(out_dir, lit=lit, with_plate=False)[0]

    def snapshot_and_check(self, out_dir: Path) -> tuple[Snapshot, PlateCheck]:
        snap, plate = self._lit_session(out_dir, lit=True, with_plate=True)
        if plate is None:  # light state unknown / did not come on / check failed: the careful path
            plate = self.check_plate()
        return snap, plate

    def check_plate(self, lit: bool = True) -> PlateCheck:
        """Bambuddy plate check. Its references are taken lit, so when it warns that the chamber light was
        off the check is repeated with the light on, and the light is put back off afterwards. An unlit
        result, a failed lit re-check or a light that did not come on gives ``is_empty=None`` and
        ``light_ok=False`` (never "empty")."""
        path = f"{self._printer}/camera/check-plate"
        if lit and self._we_switched_off_recently():
            # we put the light off ourselves moments ago and Bambuddy may not know yet: an answer now could
            # come from a dark frame without a light_warning. Do the lit check directly.
            return self._lit_check(path, False, None)
        d = self._get(path, timeout=30.0)
        if not isinstance(d, dict):
            raise BackendError(f"GET {path}: unexpected response")
        if not lit or not d.get("light_warning"):
            return parse_plate_check(d)
        # Bambuddy saw the light off. The status may say "on" (a person switched it on meanwhile, or the
        # report lags): then do not touch it, just look again.
        before = self._light_state()
        if before is None:  # never touch a light whose state we cannot read (it may be on for a print)
            pc = parse_plate_check(d)  # light_warning: uncertain, light_ok False
            pc.message = (f"{pc.message} (chamber light state unknown: not switched, no lit re-check)").strip()
            return pc
        return self._lit_check(path, before, d)

    def _lit_check(self, path: str, before: bool, unlit: Optional[dict]) -> PlateCheck:
        switch = before is False
        notes: list[str] = []
        lit_d: Any = None
        try:
            if switch:
                self._light(True)
            self._sleep(self.light_wait_s)
            lit_d = self._get(path, timeout=30.0)
        except BackendError as e:
            notes.append(f"lit re-check failed: {e}")
        finally:
            if switch:
                off_note = self._light_off_safely()
                if off_note:
                    notes.append(off_note)
        if isinstance(lit_d, dict):
            pc = parse_plate_check(lit_d)
            if lit_d.get("light_warning"):
                notes.insert(0, "the chamber light did not come on for the re-check")
        else:
            if not any(n.startswith("lit re-check failed") for n in notes):
                notes.insert(0, "lit re-check failed: no usable answer")
            pc = (parse_plate_check(unlit) if unlit is not None else
                  PlateCheck(is_empty=None, light_ok=False, message="uncertain: no lit plate check"))
        if notes:
            pc.message = f"{pc.message} ({'; '.join(notes)})".strip()
        return pc

    def resolve_model(self, url_or_id: str) -> ModelCard:
        url = makerworld_url(url_or_id)
        d = self._post("/makerworld/resolve", {"url": url}, timeout=self.slice_timeout_s)
        if not isinstance(d, dict):
            raise BackendError("POST /makerworld/resolve: unexpected response")
        return parse_model(d, url)

    def library_gcode(self, library_file_id: int, max_bytes: int = 8_000_000) -> str:
        body, _ = self._get(f"/library/files/{int(library_file_id)}/gcode", raw=True,
                            timeout=self.transfer_timeout_s)
        return truncate_gcode((body or b"").decode("utf-8", "replace"), max_bytes)

    def recent_archives(self, limit: int = 5) -> list[dict]:
        rows = self._get("/archives/", params={"limit": int(limit), "printer_id": self.printer_id}) or []
        return [{
            "id": r.get("id"),
            "name": r.get("print_name") or r.get("filename") or "",
            "filename": r.get("filename") or "",
            "status": r.get("status") or "",
            "started_at": r.get("started_at"),
            "completed_at": r.get("completed_at"),
            "print_time_s": _int(r.get("actual_time_seconds")) or _int(r.get("print_time_seconds")),
            "filament_g": _float(r.get("filament_used_grams")),
            "failure_reason": r.get("failure_reason"),
            "photos": list(r.get("photos") or []),
            "makerworld_url": r.get("makerworld_url"),
        } for r in rows if isinstance(r, dict)]

    def preview_url(self, library_file_id: int) -> str:
        return f"{self.public_url}/gcode-viewer?library_file={int(library_file_id)}&plate=1"

    # ---- extras (doctor / setup) -----------------------------------------------------------------
    def settings(self) -> dict:
        """Bambuddy's app settings (``GET /settings/``), e.g. ``require_plate_clear``: when it is false, Bambuddy's
        queue manager may start a queued auto-start item on a FINISH printer before anyone looked at the plate."""
        d = self._get("/settings/")
        if not isinstance(d, dict):
            raise BackendError("GET /settings/: unexpected response")
        return d

    def presets(self) -> dict:
        """``{source: {kind: [{"id", "name", "filament_type"}]}}`` for the local and standard tiers."""
        d = self._get("/slicer/presets", timeout=self.slice_timeout_s) or {}
        out: dict = {}
        for src in ("local", "standard"):
            tier = d.get(src) or {}
            out[src] = {kind: [{"id": str(p.get("id")), "name": p.get("name") or "",
                                "filament_type": p.get("filament_type")} for p in tier.get(kind) or []]
                        for kind in ("printer", "process", "filament")}
        return out

    def preset_has_eject_marker(self, preset_id: str) -> Optional[bool]:
        """True when a local printer preset's end G-code carries the auto-eject marker; None if unknown."""
        if not str(preset_id).strip().isdigit():
            return None
        d = self._get(f"/local-presets/{str(preset_id).strip()}") or {}
        setting = d.get("setting") or {}
        if isinstance(setting, str):
            try:
                setting = json.loads(setting)
            except ValueError:
                setting = {"machine_end_gcode": setting}
        end = setting.get("machine_end_gcode") if isinstance(setting, dict) else ""
        end = "\n".join(end) if isinstance(end, list) else str(end or "")
        return any(m in end for m in EJECT_MARKERS)

    # ---- library writes -------------------------------------------------------------------------
    def import_model(self, model_id: int, profile_id: Optional[int] = None) -> LibraryFile:
        st = self._get("/makerworld/status") or {}
        if not st.get("can_download"):
            why = "sign-in expired" if st.get("sign_in_expired") else "not signed in to Bambu Cloud"
            raise BackendError(f"MakerWorld downloads are not available in Bambuddy ({why})")
        body: dict = {"model_id": int(model_id)}
        if profile_id is not None:
            body["profile_id"] = int(profile_id)
        d = self._post("/makerworld/import", body, timeout=self.transfer_timeout_s) or {}
        return _library_file(d.get("library_file_id"), str(d.get("filename") or ""))

    def upload_file(self, path: Path) -> LibraryFile:
        p = Path(path)
        try:
            content = p.read_bytes()
        except OSError as e:
            raise BackendError(f"cannot read {p.name}: {e.strerror or e}") from None
        boundary = "home3d-" + uuid.uuid4().hex
        fname = p.name.replace('"', "_").replace("\r", "").replace("\n", "")
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n").encode("utf-8") + content + \
            f"\r\n--{boundary}--\r\n".encode("utf-8")
        d = self._request("POST", "/library/files", data=body, timeout=self.transfer_timeout_s,
                          content_type=f"multipart/form-data; boundary={boundary}") or {}
        return _library_file(d.get("id"), str(d.get("filename") or p.name), str(d.get("file_type") or ""))

    def download_file(self, library_file_id: int, out_dir: Path) -> Path:
        fid = int(library_file_id)
        body, headers = self._get(f"/library/files/{fid}/download", raw=True, timeout=self.transfer_timeout_s)
        name = ""
        disp = headers.get("Content-Disposition", "") if headers is not None else ""
        m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", disp, flags=re.I) or \
            re.search(r'filename="?([^";]+)"?', disp, flags=re.I)
        if m:
            name = urllib.parse.unquote(m.group(1).strip().strip('"'))
        if not name:
            try:
                name = str((self._get(f"/library/files/{fid}") or {}).get("filename") or "")
            except BackendError:
                name = ""
        name = Path(name.replace("\\", "/")).name if name else ""
        if not name or name in {".", ".."}:
            name = f"library_{fid}.bin"
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        dest = out / name
        dest.write_bytes(body or b"")
        return dest

    def slice_request_body(self, options: SliceOptions) -> dict:
        if not options.printer_preset:
            raise BackendError("slice: printer preset is not set")
        if not options.process_preset:
            raise BackendError("slice: process preset is not set")
        filaments = [f for f in options.filament_presets if str(f).strip()]
        if not filaments:
            raise BackendError("slice: filament preset is not set")
        body: dict = {
            "printer_preset": preset_ref(options.printer_preset),
            "process_preset": preset_ref(options.process_preset),
            "process_overrides": {**DEFAULT_PROCESS_OVERRIDES, **(options.process_overrides or {})},
            "export_3mf": True,
            "auto_orient": bool(options.auto_orient),
            "auto_arrange": bool(options.auto_arrange),
        }
        if len(filaments) == 1:
            body["filament_preset"] = preset_ref(filaments[0])
        else:
            body["filament_presets"] = [preset_ref(f) for f in filaments]
        if options.filament_colours:
            body["filament_colours"] = list(options.filament_colours)
        if options.bed_type:
            body["bed_type"] = options.bed_type
        if options.plate is not None:
            body["plate"] = int(options.plate)
        return body

    def slice(self, library_file_id: int, options: SliceOptions, timeout_s: int = 900) -> SliceResult:
        fid = int(library_file_id)
        d = self._post(f"/library/files/{fid}/slice", self.slice_request_body(options),
                       timeout=self.slice_timeout_s) or {}
        job_id = d.get("job_id")
        deadline = self._clock() + float(timeout_s)
        delay = self.poll_first_s
        job, polled = d, False
        while not isinstance(job.get("result"), dict):
            status = str(job.get("status") or "").lower()
            if status in {"failed", "error", "cancelled", "canceled"}:
                code = job.get("error_status")
                detail = job.get("error_detail") or job.get("error") or job.get("error_message") or "failed"
                raise BackendError(f"slice job {job_id} failed: {f'{code} ' if code else ''}{_short(detail)}")
            if job_id is None:
                raise BackendError(f"POST /library/files/{fid}/slice: no job id in response")
            done = status in {"completed", "done", "success", "succeeded"}
            if done and polled:
                raise BackendError(f"slice job {job_id} completed without a result")
            if not done:
                if self._clock() + delay > deadline:
                    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
                    stage = progress.get("stage") or ""
                    raise BackendError(f"slice job {job_id} timed out after {int(timeout_s)} s"
                                       + (f" (stage: {stage})" if stage else ""))
                self._sleep(delay)
                delay = min(self.poll_max_s, delay * 1.5)
            job, polled = self._get(f"/slice-jobs/{job_id}") or {}, True
        result = job["result"]
        out = _int(result.get("library_file_id"))
        if out is None:
            raise BackendError(f"slice job {job_id}: result has no library_file_id")
        try:
            gcode = self.library_gcode(out)
        except BackendError:
            gcode = ""  # the sliced file exists; callers can fetch the G-code again
        return SliceResult(library_file_id=out, name=str(result.get("name") or ""),
                           print_time_s=_int(result.get("print_time_seconds")),
                           filament_g=_float(result.get("filament_used_g")),
                           filament_types=_filament_types(gcode), gcode_text=gcode)

    # ---- queue / printer actions ------------------------------------------------------------------
    def queue_add(self, library_file_id: int, *, ams_mapping: Optional[list[int]] = None,
                  plate_id: Optional[int] = None, manual_start: bool = True) -> QueueItem:
        body: dict = {
            "library_file_id": int(library_file_id),
            "printer_id": self.printer_id,
            "manual_start": bool(manual_start),
            # Bambuddy defaults vibration_cali to true when omitted: always send all three explicitly.
            "bed_levelling": "off",
            "flow_cali": "off",
            "vibration_cali": False,
        }
        if ams_mapping is not None:
            body["ams_mapping"] = [int(x) for x in ams_mapping]
        if plate_id is not None:
            body["plate_id"] = int(plate_id)
        d = self._post("/queue/", body)
        if not isinstance(d, dict):
            raise BackendError("POST /queue/: unexpected response")
        return parse_queue_item(d)

    def queue_remove(self, queue_item_id: int) -> None:
        self._check_success(self._request("DELETE", f"/queue/{int(queue_item_id)}"), "remove queue item")

    def start(self, queue_item_id: int) -> QueueItem:
        qid = int(queue_item_id)
        try:
            d = self._post(f"/queue/{qid}/start")
        except BambuddyHTTPError as e:
            if 400 <= e.status < 500:  # 409 filament short / unmatched, 400 not pending, 403, 404
                raise BackendError(f"Bambuddy refused to start queue item {qid}: {e.detail or e.status} "
                                   f"(HTTP {e.status})") from None
            raise
        d = self._check_success(d, f"start queue item {qid}")
        if isinstance(d, dict) and _int(d.get("id")) == qid and d.get("status"):
            return parse_queue_item(d)
        return parse_queue_item(self._get(f"/queue/{qid}") or {})

    def _print_cmd(self, cmd: str) -> None:
        self._check_success(self._post(f"{self._printer}/print/{cmd}"), f"print {cmd}")

    def stop(self) -> None:
        self._print_cmd("stop")

    def pause(self) -> None:
        self._print_cmd("pause")

    def resume(self) -> None:
        self._print_cmd("resume")

    def mark_plate_cleared(self) -> None:
        self._check_success(self._post(f"{self._printer}/clear-plate"), "clear plate")
