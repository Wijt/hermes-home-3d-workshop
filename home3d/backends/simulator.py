"""Simulated Bambu Lab A1 behind the ``Backend`` contract (no hardware, no network).

State lives in one JSON file (``data_dir()/simulator.json`` or ``state_path``), guarded by ``fcntl.flock``
around every read-modify-write, so the agent's tools and the cron watcher process drive the same virtual
printer. Everything is deterministic: model cards, slice results and G-code are pure functions of ids and
dimensions, and time only moves with the virtual clock.

Virtual clock: ``sim_now = sim0 + (wall_now - real0) * speed`` (+ ``advance()`` offsets folded into
``sim0``). ``speed`` comes from ``$HOME3D_SIM_SPEED`` (default 60: one real second = one simulated minute;
0 = time only moves through ``advance()``). A speed change re-anchors the clock, so time never jumps.
Use ``SimulatorBackend.now()`` (not ``time.time()``) when comparing against simulated timestamps.

Auto-eject: settings are not passed to backends, so a slice gets the ``; HOME3D AUTO-EJECT`` end block
when its printer preset is ``"sim-autoeject"``, equals ``$HOME3D_SIM_AUTOEJECT_PRESET`` (comma-separated
ids allowed), equals ``autoeject_printer_preset`` in the watcher snapshot, or is listed in the
``autoeject_presets`` constructor argument.

Scenarios (``set_scenario``): ok | fail (FAILED at 40 %) | pause_hms (PAUSE + filament-runout HMS at
30 %) | eject_miss (eject runs but the part stays) | busy (a family job queued ahead) | offline (printer
unreachable; simulator extra). A scenario applies to the next start and, when set mid-print, to the
running job (a fail/pause threshold already passed triggers at the current progress).
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import struct
import threading
import time
import zipfile
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]

from ..config import data_dir, read_snapshot
from .base import (FAILED, FINISH, IDLE, OFFLINE, PAUSE, PREPARE, RUNNING, Backend, BackendError, HMSError,
                   LibraryFile, ModelCard, ModelInstance, PlateCheck, PrinterStatus, QueueItem, SliceOptions,
                   SliceResult, Snapshot, Tray)

STATE_FILE = "simulator.json"
STATE_VERSION = 1
SPEED_ENV = "HOME3D_SIM_SPEED"
AUTOEJECT_ENV = "HOME3D_SIM_AUTOEJECT_PRESET"
SIM_AUTOEJECT_PRESET = "sim-autoeject"
DEFAULT_SPEED = 60.0
SCENARIOS = ("ok", "fail", "pause_hms", "eject_miss", "busy", "offline")
FAIL_AT_PCT = 40.0
PAUSE_AT_PCT = 30.0
PREPARE_S = 120.0
EJECT_DELAY_S = 15 * 60.0  # M400 S900 cool-down before the push
ROOM_C = 25.0
BED_TAU_S = 300.0  # 65 C -> ~25.7 C after 20 sim-min
NOZZLE_TAU_S = 90.0
PLATE_MM = 256.0
SNAPSHOT_SIZE = (320, 240)
PRINTER_NAME = "Simulated A1"
EJECT_MARKER = "HOME3D AUTO-EJECT"
RUNOUT_HMS = {"code": "0700-2000-0002-0001", "severity": "common",
              "message": "AMS A Slot 1 filament has run out. Please insert a new filament.",
              "wiki_url": "https://wiki.bambulab.com/en/a1/troubleshooting/hmscode/0700_2000_0002_0001"}

# (title, (width x, depth y, height z) mm). A model id maps to ``CATALOG[id % len(CATALOG)]``.
CATALOG = (
    ("Flower gift box", (80.0, 80.0, 45.0)),
    ("Cable clip", (32.0, 18.0, 12.0)),
    ("Pill organiser", (120.0, 45.0, 22.0)),
    ("Name tag keychain", (50.0, 20.0, 2.4)),
    ("Plant pot", (90.0, 90.0, 80.0)),
    ("Phone stand", (70.0, 85.0, 60.0)),
    ("Pen holder", (36.0, 36.0, 100.0)),
    ("Coaster", (95.0, 95.0, 4.0)),
)
CREATORS = ("maker_ada", "printsmith", "layerlab", "tinkerhome", "filamentfox")
DEMO_MODEL_IDS = (1440000, 1440001)  # seeded library: "Flower gift box", "Cable clip"
FAMILY_MODEL_ID = 1440005  # "Phone stand", queued ahead of us by the "busy" scenario
# material -> (bed C, nozzle C, density g/cm3)
MATERIALS = {"PLA": (65, 220, 1.24), "PETG": (70, 250, 1.27), "TPU": (35, 230, 1.21),
             "ABS": (90, 260, 1.04), "ASA": (90, 260, 1.07)}
DEFAULT_TRAYS = (
    {"slot": 0, "material": "PLA", "color": "#FFFFFF", "name": "Bambu PLA Basic", "remain_pct": 85, "loaded": True},
    {"slot": 1, "material": "PLA", "color": "#C12E1F", "name": "Bambu PLA Basic", "remain_pct": 60, "loaded": True},
    {"slot": 2, "material": "PLA", "color": "#000000", "name": "Bambu PLA Matte", "remain_pct": 40, "loaded": True},
    {"slot": 3, "material": "PETG", "color": "#F5F5F5", "name": "Bambu PETG HF", "remain_pct": 70, "loaded": True},
)
_ACTIVE_QUEUE = ("pending", "printing")
_QUEUE_FIELDS = ("id", "status", "name", "position", "library_file_id", "manual_start", "print_time_s",
                 "scheduled_time", "created_at", "archive_id")
_thread_lock = threading.Lock()  # only used where fcntl is unavailable


def _wall() -> float:
    return time.time()


def _speed() -> float:
    try:
        return max(0.0, float(os.environ.get(SPEED_ENV, DEFAULT_SPEED)))
    except ValueError:
        return DEFAULT_SPEED


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _catalog(model_id: int) -> tuple[str, tuple[float, float, float]]:
    return CATALOG[model_id % len(CATALOG)]


def parse_model_id(url_or_id: str) -> int:
    """MakerWorld model id from a link or a bare id (``#profileId-N`` fragments are ignored)."""
    s = str(url_or_id or "").strip()
    m = re.search(r"/models/(\d+)", s) or re.fullmatch(r"#?(\d+)", s)
    if not m:
        raise BackendError(f"not a MakerWorld model link or id: {s[:80]!r}")
    return int(m.group(1))


def _estimate(dims, material: str, layer_h: float) -> tuple[int, float, float]:
    """(print_time_s, grams, used_mm3) for a box-shaped part: 2 walls, 0.8 mm skins, 15 % infill."""
    w, d, h = dims
    vol = w * d * h
    shell = min(vol, 2 * w * d * 0.8 + 2 * (w + d) * h * 0.84)
    used = shell + max(0.0, vol - shell) * 0.15
    density = MATERIALS.get(material, MATERIALS["PLA"])[2]
    flow = 8.0 * layer_h / 0.2  # mm3/s
    return int(round(360 + used / flow)), round(used / 1000 * density, 2), used


def _layer_zs(height: float, layer_h: float) -> list[float]:
    first = 0.2
    if height <= first + 1e-6:
        return [round(max(height, 0.1), 3)]
    zs, z = [first], first
    while z + layer_h < height - 1e-6:
        z = round(z + layer_h, 3)
        zs.append(z)
    if height - zs[-1] > 0.04:
        zs.append(round(height, 3))
    else:
        zs[-1] = round(height, 3)
    return zs


def _layer_height(process_preset: str) -> float:
    s = str(process_preset or "").lower()
    m = re.search(r"(0\.\d+)\s*mm", s)
    if m:
        return float(m.group(1))
    if "draft" in s:
        return 0.28
    if "fine" in s or "high quality" in s:
        return 0.16
    return 0.2


def _dur(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {sec}s"
    return f"{m}m {sec}s" if m else f"{sec}s"


def _num(v: float) -> str:
    out = f"{v:.3f}".rstrip("0").rstrip(".")
    return out or "0"


def _stem(name: str) -> str:
    return re.sub(r"(\.gcode)?\.(3mf|stl|step|stp|obj|gcode)$", "", name, flags=re.I) or name


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\- ()]+", "_", Path(name).name).strip() or "file"


def _slice_params(name: str, dims, *, material: str = "PLA", layer_h: float = 0.2,
                  printer_model: str = "Bambu Lab A1", eject: bool = False, bed_type: str = "Textured PEI Plate",
                  prime_tower: bool = False, colour: str = "#FFFFFF", printer_preset: str = "") -> dict:
    bed, nozzle, density = MATERIALS.get(material, MATERIALS["PLA"])
    time_s, grams, used = _estimate(dims, material, layer_h)
    zs = _layer_zs(dims[2], layer_h)
    return {"name": name, "dims": [float(x) for x in dims], "material": material, "layer_height": layer_h,
            "printer_model": printer_model, "eject": bool(eject), "bed_type": bed_type,
            "prime_tower": bool(prime_tower), "colour": colour, "printer_preset": printer_preset,
            "bed_temp": bed, "nozzle_temp": nozzle, "density": density, "print_time_s": time_s,
            "filament_g": grams, "filament_mm3": round(used, 1), "total_layers": len(zs), "max_z": zs[-1]}


def render_gcode(p: dict) -> str:
    """Synthetic OrcaSlicer/Bambu-style G-code for slice params (header, config, layers, end block)."""
    w, d, h = p["dims"]
    c = PLATE_MM / 2
    x0, x1, y0, y1 = (round(c - w / 2, 3), round(c + w / 2, 3), round(c - d / 2, 3), round(c + d / 2, 3))
    lh = p["layer_height"]
    zs = _layer_zs(h, lh)
    n = len(zs)
    total_s = p["print_time_s"]
    model_s = max(60, total_s - 360)
    bed, nozzle = p["bed_temp"], p["nozzle_temp"]
    length_mm = p["filament_mm3"] / (math.pi * 0.875 ** 2)
    out: list[str] = []
    a = out.append
    a("; HEADER_BLOCK_START")
    a("; generated by home-3d-workshop simulator (OrcaSlicer-style)")
    a(f"; model printing time: {_dur(model_s)}; total estimated time: {_dur(total_s)}")
    a(f"; total layer number: {n}")
    a(f"; total filament length [mm] : {length_mm:.2f}")
    a(f"; total filament volume [cm^3] : {p['filament_mm3'] / 1000:.2f}")
    a(f"; total filament weight [g] : {p['filament_g']:.2f}")
    a(f"; filament_density: {p['density']}")
    a("; filament_diameter: 1.75")
    a(f"; max_z_height: {zs[-1]:.2f}")
    a("; filament: 1")
    a("; HEADER_BLOCK_END")
    a("")
    a("; CONFIG_BLOCK_START")
    a(f"; curr_bed_type = {p['bed_type']}")
    a(f"; enable_prime_tower = {1 if p['prime_tower'] else 0}")
    a(f"; filament_colour = {p['colour']}")
    a(f"; filament_type = {p['material']}")
    a(f"; hot_plate_temp = {bed}")
    a(f"; hot_plate_temp_initial_layer = {bed}")
    a("; initial_layer_print_height = 0.2")
    a(f"; layer_height = {_num(lh)}")
    a("; nozzle_diameter = 0.4")
    a(f"; nozzle_temperature = {nozzle}")
    a(f"; nozzle_temperature_initial_layer = {nozzle}")
    a(f"; printer_model = {p['printer_model']}")
    a(f"; printer_settings_id = {p.get('printer_preset') or 'Bambu Lab A1 0.4 nozzle'}")
    a("; CONFIG_BLOCK_END")
    a("")
    a("; EXECUTABLE_BLOCK_START")
    a(f"M73 P0 R{math.ceil(total_s / 60)}")
    a(f"M140 S{bed} ; set bed temperature")
    a(f"M104 S{nozzle} ; set nozzle temperature")
    a("G28 ; home all axes")
    a(f"M190 S{bed} ; wait for bed temperature")
    a(f"M109 S{nozzle} ; wait for nozzle temperature")
    a("G90")
    a("G21")
    a("M83 ; use relative distances for extrusion")
    prev = 0.0
    for i, z in enumerate(zs, 1):
        e_mm = 0.42 * (z - prev) / (math.pi * 0.875 ** 2)  # line width x layer height / filament area
        a(";LAYER_CHANGE")
        a(f"; Z_HEIGHT: {_num(z)}")
        a(f"; LAYER_HEIGHT: {_num(z - prev)}")
        a(f"; layer num/total_layer_count: {i}/{n}")
        a(f"M73 L{i}")
        a(f"G1 Z{_num(z)} F720")
        a(f"G1 X{_num(x0)} Y{_num(y0)} F42000")
        a("; FEATURE: Outer wall")
        a("G1 F1200" if i == 1 else "G1 F6000")
        for (x, y), seg in (((x1, y0), w), ((x1, y1), d), ((x0, y1), w), ((x0, y0), d)):
            a(f"G1 X{_num(x)} Y{_num(y)} E{e_mm * seg:.5f}")
        prev = z
    a("; filament end gcode")
    a("G1 E-0.8 F1800 ; retract")
    a(f"G1 Z{_num(zs[-1] + 0.5)} F900 ; lower z a little")
    a("M140 S0 ; turn off bed")
    a("M106 S0 ; turn off fan")
    a("M104 S0 ; turn off hotend")
    a("M400 ; wait all motion done")
    a("M17 R ; restore z current")
    if p["eject"]:
        xs = (round(c, 3), round(max(0.0, x0 + 8), 3), round(min(PLATE_MM, x1 - 8), 3))
        a(f"; {EJECT_MARKER} v1 (simulated A1 profile)")
        a("; part is still homed here (before M18). Push it off the FRONT edge.")
        a("M106 P1 S255 ; part fan helps the bed/part cool")
        a("G90")
        a("G1 Z60 F600")
        a("G1 X128 Y262 F6000 ; behind the plate")
        a("M400 S900 ; cool down ~15 min so PLA releases from PEI")
        a("M106 P1 S0")
        a("M17 Y0.6 ; low Y current: a welded part makes Y skip instead of forcing")
        for x in xs:
            a(f"G1 X{_num(x)} Y262 F6000")
            a("G1 Z2.5 F600")
            a("G1 Y-0.5 F1500")
            a("G1 Z60 F600")
        a("M400")
        a("M17 X0.65 Y1.2 Z0.6 ; restore default motor currents")
        a(f"; {EJECT_MARKER} end")
    a("M400")
    a("M18 X Y Z")
    a("M73 P100 R0")
    a("; EXECUTABLE_BLOCK_END")
    a("")
    a(f"; filament used [mm] = {length_mm:.2f}")
    a(f"; filament used [cm3] = {p['filament_mm3'] / 1000:.2f}")
    a(f"; filament used [g] = {p['filament_g']:.2f}")
    return "\n".join(out) + "\n"


def _params_from_gcode(text: str, name: str) -> dict:
    """Minimal header parse for uploaded, already-sliced files (time, layers, max z, temps, eject)."""
    def grab(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.M)
        return m.group(1).strip() if m else None

    def secs(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        parts = dict((u, int(v)) for v, u in re.findall(r"(\d+)\s*([dhms])", s))
        return parts.get("d", 0) * 86400 + parts.get("h", 0) * 3600 + parts.get("m", 0) * 60 + parts.get("s", 0)

    material = (grab(r"^;\s*filament_type\s*=\s*([A-Za-z\-]+)") or "PLA").upper()
    max_z = float(grab(r"max_z_height:\s*([\d.]+)") or 10.0)
    layers = int(grab(r"total layer number:\s*(\d+)") or max(1, round(max_z / 0.2)))
    grams = grab(r"filament used \[g\]\s*=\s*([\d.]+)") or grab(r"total filament weight \[g\]\s*:\s*([\d.]+)")
    bed, nozzle, density = MATERIALS.get(material, MATERIALS["PLA"])
    return {"name": name, "dims": [40.0, 40.0, max_z], "material": material, "layer_height": 0.2,
            "printer_model": grab(r"^;\s*printer_model\s*=\s*(.+)$") or "", "bed_type": "",
            "eject": EJECT_MARKER in text or "HERMES AUTO-EJECT" in text, "prime_tower": False,
            "colour": "#FFFFFF", "printer_preset": "",
            "bed_temp": int(float(grab(r"^;\s*hot_plate_temp\s*=\s*([\d.]+)") or bed)),
            "nozzle_temp": int(float(grab(r"^;\s*nozzle_temperature\s*=\s*([\d.]+)") or nozzle)),
            "density": density, "print_time_s": secs(grab(r"total estimated time:\s*([^;\n]+)")) or 1800,
            "filament_g": float(grams) if grams else 0.0, "filament_mm3": 0.0,
            "total_layers": layers, "max_z": max_z}


# ---- files: PNG / 3MF / STL --------------------------------------------------------------------
def _png(width: int, height: int, rgb: bytes) -> bytes:
    """Minimal 8-bit RGB PNG (filter 0 on every row)."""
    stride = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


def _hex_rgb(colour: str, default=(226, 226, 220)) -> tuple[int, int, int]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?", str(colour or "").strip())
    if not m:
        return default
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    if 0.3 * r + 0.59 * g + 0.11 * b < 110:  # keep the part visible on the dark plate
        r, g, b = ((v + 255) // 2 for v in (r, g, b))
    return r, g, b


def render_plate_png(part: Optional[dict], lit: bool = True) -> bytes:
    """320x240 camera-ish frame: dark textured plate, light rectangle for a part (footprint to scale)."""
    W, H = SNAPSHOT_SIZE
    buf = bytearray(bytes((16, 16, 18)) * (W * H))

    def rect(xa: int, ya: int, xb: int, yb: int, col) -> None:
        xa, xb, ya, yb = max(0, xa), min(W, xb), max(0, ya), min(H, yb)
        if xa >= xb or ya >= yb:
            return
        row = bytes(col) * (xb - xa)
        for y in range(ya, yb):
            o = (y * W + xa) * 3
            buf[o:o + len(row)] = row

    size = 216
    px, py = (W - size) // 2, (H - size) // 2
    rect(px, py, px + size, py + size, (42, 42, 48))
    for k in range(1, 8):
        rect(px + k * size // 8, py, px + k * size // 8 + 1, py + size, (52, 52, 59))
        rect(px, py + k * size // 8, px + size, py + k * size // 8 + 1, (52, 52, 59))
    if part:
        w, d = part.get("dims", (40, 40, 10))[:2]
        scale = size / PLATE_MM
        pw, ph = max(4, round(w * scale)), max(4, round(d * scale))
        cx, cy = px + size // 2, py + size // 2
        xa, ya = cx - pw // 2, cy - ph // 2
        rect(xa - 2, ya - 2, xa + pw + 2, ya + ph + 2, (120, 120, 116))
        rect(xa, ya, xa + pw, ya + ph, _hex_rgb(part.get("colour", "")))
    if not lit:
        buf = buf.translate(bytes(int(i * 0.3) for i in range(256)))
    return _png(W, H, bytes(buf))


def _box_mesh(dims) -> tuple[list, list]:
    w, d, h = dims
    verts = [(x, y, z) for z in (0.0, h) for y in (0.0, d) for x in (0.0, w)]
    tris = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4),
            (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
    return verts, tris


def write_box_3mf(path: Path, dims) -> Path:
    verts, tris = _box_mesh(dims)
    vx = "".join(f'<vertex x="{_num(x)}" y="{_num(y)}" z="{_num(z)}"/>' for x, y, z in verts)
    tx = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
             f'<object id="1" type="model"><mesh><vertices>{vx}</vertices><triangles>{tx}</triangles></mesh>'
             '</object></resources><build><item objectid="1"/></build></model>\n')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/'
             '2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
             'relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.'
             '3dmanufacturing-3dmodel+xml"/></Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return path


def write_box_stl(path: Path, dims) -> Path:
    verts, tris = _box_mesh(dims)
    lines = ["solid box"]
    for a, b, c in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = verts[a], verts[b], verts[c]
        ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        lines.append(f"  facet normal {nx / ln:.6g} {ny / ln:.6g} {nz / ln:.6g}")
        lines.append("    outer loop")
        for vx_, vy_, vz_ in (verts[a], verts[b], verts[c]):
            lines.append(f"      vertex {vx_:.6g} {vy_:.6g} {vz_:.6g}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid box")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def _read_gcode_file(path: Path) -> str:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if n.lower().endswith(".gcode"))
            if not names:
                raise BackendError(f"{path.name}: no G-code inside the archive")
            return z.read(names[0]).decode("utf-8", "replace")
    return path.read_text(encoding="utf-8", errors="replace")


def _cool(start: float, dt: float, tau: float) -> float:
    return round(ROOM_C + (float(start) - ROOM_C) * math.exp(-max(dt, 0.0) / tau), 1)


class SimulatorBackend(Backend):
    """Deterministic, file-backed virtual printer (see module docstring)."""

    name = "simulator"

    def __init__(self, state_path: Optional[Path] = None, *, autoeject_presets: Iterable[str] = ()):
        self.state_path = Path(state_path) if state_path else data_dir() / STATE_FILE
        self.files_dir = self.state_path.with_name(self.state_path.stem + "-files")
        self.autoeject_presets = {str(p).strip() for p in autoeject_presets if str(p).strip()}

    # ---- state plumbing ---------------------------------------------------------------------
    @contextmanager
    def _state(self) -> Iterator[dict]:
        """Locked read-modify-write; the state is ticked to 'now' before the body runs. Saved only on success."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_name(self.state_path.name + ".lock")
        with open(lock_path, "a+") as lf:
            if fcntl is not None:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            else:  # pragma: no cover
                _thread_lock.acquire()
            try:
                try:
                    raw = self.state_path.read_text(encoding="utf-8")
                except OSError:
                    raw = ""
                try:
                    st = json.loads(raw) if raw else None
                except ValueError:
                    st = None
                if not isinstance(st, dict) or st.get("version") != STATE_VERSION:
                    st = self._fresh()
                self._sync_clock(st)
                self._tick(st, self._now(st))
                yield st
                out = json.dumps(st, ensure_ascii=False, indent=1, sort_keys=True)
                if out != raw:
                    tmp = self.state_path.with_name(self.state_path.name + ".tmp")
                    tmp.write_text(out, encoding="utf-8")
                    tmp.replace(self.state_path)
            finally:
                if fcntl is not None:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                else:  # pragma: no cover
                    _thread_lock.release()

    def _fresh(self) -> dict:
        w = _wall()
        st = {"version": STATE_VERSION, "clock": {"real0": w, "sim0": float(int(w)), "speed": _speed()},
              "scenario": "ok", "next": {"library": 1, "queue": 1, "archive": 1}, "library": [], "queue": [],
              "archives": [], "job": None, "plate": None, "trays": [dict(t) for t in DEFAULT_TRAYS],
              "snapshots": 0}
        for mid in DEMO_MODEL_IDS:
            self._add_model(st, mid, mid * 10 + 1)
        return st

    @staticmethod
    def _now(st: dict) -> float:
        c = st["clock"]
        return c["sim0"] + (_wall() - c["real0"]) * c["speed"]

    def _sync_clock(self, st: dict) -> None:
        sp = _speed()
        if sp != st["clock"]["speed"]:
            st["clock"] = {"real0": _wall(), "sim0": self._now(st), "speed": sp}

    @staticmethod
    def _next_id(st: dict, kind: str) -> int:
        n = int(st["next"][kind])
        st["next"][kind] = n + 1
        return n

    @staticmethod
    def _lib(st: dict, library_file_id: int) -> dict:
        for e in st["library"]:
            if e["id"] == int(library_file_id):
                return e
        raise BackendError(f"library file {library_file_id} not found")

    @staticmethod
    def _qrow(st: dict, queue_item_id: int) -> Optional[dict]:
        return next((q for q in st["queue"] if q["id"] == int(queue_item_id)), None)

    @staticmethod
    def _qitem(row: dict) -> QueueItem:
        return QueueItem(**{k: row.get(k) for k in _QUEUE_FIELDS})

    @staticmethod
    def _active(st: dict) -> Optional[dict]:
        job = st["job"]
        return job if job and job["end_state"] is None else None

    @staticmethod
    def _require_online(st: dict, what: str) -> None:
        if st["scenario"] == "offline":
            raise BackendError(f"{what}: printer is offline (simulated)")

    def _add_model(self, st: dict, model_id: int, profile_id: Optional[int]) -> dict:
        title, dims = _catalog(model_id)
        entry = {"id": self._next_id(st, "library"), "name": f"{title}.3mf", "kind": "3mf", "sliced": False,
                 "model_id": model_id, "profile_id": profile_id, "dims": list(dims)}
        st["library"].append(entry)
        return entry

    # ---- time model -------------------------------------------------------------------------
    @staticmethod
    def _phase(job: dict, t: float) -> tuple[str, float, float]:
        """(PREPARE|RUNNING, progress %, seconds since start excluding pauses) for an unfinished job."""
        tt = job["paused_at"] if job["paused_at"] is not None else t
        el = max(0.0, tt - job["started_at"] - job["paused_total"])
        if el < PREPARE_S:
            return PREPARE, 0.0, el
        dur = max(1.0, float(job["duration_s"]))
        return RUNNING, min(100.0, (el - PREPARE_S) / dur * 100.0), el

    def _tick(self, st: dict, t: float) -> None:
        job = self._active(st)
        if job is not None and job["paused_at"] is None:
            run0 = job["started_at"] + job["paused_total"] + PREPARE_S
            dur = float(job["duration_s"])
            if t >= run0:
                if not job["part_placed"]:
                    job["part_placed"] = True
                    st["plate"] = {"queue_item_id": job["queue_item_id"], "name": job["name"],
                                   "dims": job["params"]["dims"], "colour": job["params"].get("colour", "")}
                trig = job.get("trigger_pct")
                t_trig = run0 + dur * trig / 100.0 if trig is not None else None
                if t_trig is not None and t >= t_trig - 1e-6 and t_trig < run0 + dur:
                    job["trigger_pct"] = None
                    if job["scenario"] == "fail":
                        self._end_job(st, job, FAILED, t_trig, trig, "failed")
                    else:
                        job["paused_at"], job["pause_reason"] = t_trig, "hms"
                        job["hms"] = [dict(RUNOUT_HMS)]
                        st["trays"][0]["remain_pct"] = 0
                elif t >= run0 + dur:
                    self._end_job(st, job, FINISH, run0 + dur, 100.0, "completed")
        job = st["job"]
        if (job and job["end_state"] == FINISH and job["params"].get("eject") and job["scenario"] != "eject_miss"
                and job.get("ejected_at") is None and st["plate"]
                and st["plate"].get("queue_item_id") == job["queue_item_id"]
                and t >= job["ended_at"] + EJECT_DELAY_S):
            st["plate"] = None
            job["ejected_at"] = job["ended_at"] + EJECT_DELAY_S
        self._auto_start(st, t)

    def _end_job(self, st: dict, job: dict, state: str, t_end: float, progress: float, qstatus: str) -> None:
        job.update(end_state=state, ended_at=t_end, end_progress=round(progress, 1), paused_at=None, hms=[])
        row = self._qrow(st, job["queue_item_id"])
        aid = self._next_id(st, "archive")
        if row is not None:
            row["status"], row["archive_id"] = qstatus, aid
        st["archives"].append({"id": aid, "name": _stem(job["name"]), "status": qstatus,
                               "queue_item_id": job["queue_item_id"], "started_at": _iso(job["started_at"]),
                               "completed_at": _iso(t_end), "print_time_seconds": int(t_end - job["started_at"])})

    def _start_job(self, st: dict, row: dict, t: float) -> None:
        params = self._lib(st, row["library_file_id"]).get("params")
        if not params:
            raise BackendError(f"start: library file {row['library_file_id']} is not sliced")
        scenario = st["scenario"] if st["scenario"] in ("fail", "pause_hms", "eject_miss") else "ok"
        st["job"] = {"queue_item_id": row["id"], "name": row["name"], "library_file_id": row["library_file_id"],
                     "params": params, "duration_s": float(params["print_time_s"]), "started_at": t,
                     "paused_at": None, "paused_total": 0.0, "pause_reason": "", "hms": [],
                     "scenario": scenario, "trigger_pct": self._trigger_for(scenario),
                     "part_placed": False, "end_state": None, "ended_at": None, "end_progress": None,
                     "ejected_at": None}
        row["status"] = "printing"

    @staticmethod
    def _trigger_for(scenario: str, current: float = 0.0) -> Optional[float]:
        if scenario == "fail":
            return max(FAIL_AT_PCT, current)
        if scenario == "pause_hms":
            return max(PAUSE_AT_PCT, current)
        return None

    def _auto_start(self, st: dict, t: float) -> None:
        """Bambuddy's queue manager: non-manual items start by themselves once idle with a clear plate."""
        if st["scenario"] == "offline" or self._active(st) is not None or st["plate"]:
            return
        auto = [q for q in st["queue"] if q["status"] == "pending" and not q["manual_start"]]
        if auto:
            auto.sort(key=lambda q: (q["position"] if q["position"] is not None else 1e9, q["id"]))
            self._start_job(st, auto[0], t)

    def _status(self, st: dict, t: float) -> PrinterStatus:
        if st["scenario"] == "offline":
            return PrinterStatus(state=OFFLINE, connected=False, printer_name=PRINTER_NAME)
        trays = [Tray(**tr) for tr in st["trays"]]
        job = st["job"]
        if not job:
            return PrinterStatus(state=IDLE, bed_temp=ROOM_C, bed_target=0.0, nozzle_temp=ROOM_C,
                                 trays=trays, printer_name=PRINTER_NAME, chamber_light=False)
        p = job["params"]
        total = int(p["total_layers"])
        name = _stem(job["name"])

        def layer_at(prog: float) -> int:
            return max(1, min(total, math.ceil(prog / 100.0 * total - 1e-9)))

        if job["end_state"]:
            dt = t - job["ended_at"]
            prog = float(job["end_progress"] or 0.0)
            return PrinterStatus(state=job["end_state"], job_name=name, progress=prog, remaining_min=0,
                                 layer=layer_at(prog) if job["part_placed"] else 0, total_layers=total,
                                 bed_temp=_cool(p["bed_temp"], dt, BED_TAU_S), bed_target=0.0,
                                 nozzle_temp=_cool(p["nozzle_temp"], dt, NOZZLE_TAU_S),
                                 trays=trays, printer_name=PRINTER_NAME, chamber_light=False)
        phase, prog, el = self._phase(job, t)
        dur = float(job["duration_s"])
        if phase == PREPARE:
            f = el / PREPARE_S
            bed = round(ROOM_C + (p["bed_temp"] - ROOM_C) * f, 1)
            nozzle = round(ROOM_C + (p["nozzle_temp"] - ROOM_C) * f, 1)
            layer, remaining = 0, math.ceil(dur / 60)
        else:
            bed, nozzle = float(p["bed_temp"]), float(p["nozzle_temp"])
            layer, remaining = layer_at(prog), math.ceil(max(0.0, dur * (1 - prog / 100.0)) / 60)
        return PrinterStatus(state=PAUSE if job["paused_at"] is not None else phase, job_name=name,
                             progress=round(prog, 1), remaining_min=remaining, layer=layer, total_layers=total,
                             bed_temp=bed, bed_target=float(p["bed_temp"]), nozzle_temp=nozzle,
                             hms=[HMSError(**h) for h in job["hms"]], trays=trays, printer_name=PRINTER_NAME,
                             chamber_light=False)

    # ---- settings hints (no Settings object reaches a backend) ------------------------------
    @staticmethod
    def _hint() -> dict:
        try:
            snap = read_snapshot()
            return snap if isinstance(snap, dict) else {}
        except Exception:
            return {}

    def _is_autoeject(self, preset: str, hint: dict) -> bool:
        preset = str(preset or "").strip()
        if not preset:
            return False
        ids = {SIM_AUTOEJECT_PRESET, *self.autoeject_presets}
        ids.update(p.strip() for p in os.environ.get(AUTOEJECT_ENV, "").split(",") if p.strip())
        snap = str(hint.get("autoeject_printer_preset") or "").strip()
        if snap:
            ids.add(snap)
        return preset in ids

    @staticmethod
    def _material(options: SliceOptions, hint: dict) -> str:
        presets = [str(x) for x in (options.filament_presets or [])]
        inverse = {str(v): str(k).upper() for k, v in (hint.get("filament_presets") or {}).items()}
        for pid in presets:
            if pid in inverse:
                return inverse[pid] if inverse[pid] in MATERIALS else "PLA"
        for cand in [str((options.process_overrides or {}).get("filament_type", ""))] + presets:
            up = cand.upper()
            for m in ("PETG", "TPU", "ABS", "ASA", "PLA"):
                if m in up:
                    return m
        return "PLA"

    # ---- read ---------------------------------------------------------------------------------
    def now(self) -> float:
        """Current simulated timestamp (simulator-only helper)."""
        with self._state() as st:
            return self._now(st)

    def status(self) -> PrinterStatus:
        with self._state() as st:
            return self._status(st, self._now(st))

    def queue(self, include_done: bool = False) -> list[QueueItem]:
        with self._state() as st:
            rows = [q for q in st["queue"] if include_done or q["status"] in _ACTIVE_QUEUE]
        rows.sort(key=lambda q: (q["position"] if q["position"] is not None else 1e9, q["id"]))
        return [self._qitem(q) for q in rows]

    def snapshot(self, out_dir: Path, lit: bool = True) -> Snapshot:
        with self._state() as st:
            self._require_online(st, "snapshot")
            st["snapshots"] += 1
            n, part = st["snapshots"], st["plate"]
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"sim-snapshot-{n:04d}.png"
        path.write_bytes(render_plate_png(part, lit=lit))
        return Snapshot(path=path, lit=lit, note="simulated")

    def check_plate(self) -> PlateCheck:
        with self._state() as st:
            self._require_online(st, "check plate")
            part = st["plate"]
        # The simulated check is always "lit" (light_ok=True); the light itself stays off between uses
        # (status.chamber_light False), as on the real printer.
        if not part:
            return PlateCheck(is_empty=True, difference_pct=1.8, confidence=0.95,
                              message="Build plate appears empty (simulated)", light_ok=True)
        w, d = part["dims"][:2]
        diff = round(min(90.0, 30.0 + 400.0 * (w * d) / (PLATE_MM * PLATE_MM)), 1)
        return PlateCheck(is_empty=False, difference_pct=diff, confidence=0.9,
                          message="Objects detected on the build plate (simulated)", light_ok=True)

    def resolve_model(self, url_or_id: str) -> ModelCard:
        mid = parse_model_id(url_or_id)
        title, dims = _catalog(mid)
        t02, g02, _ = _estimate(dims, "PLA", 0.2)
        with self._state() as st:
            imported = [e["id"] for e in st["library"] if e.get("model_id") == mid and not e["sliced"]]
        return ModelCard(
            model_id=mid, title=title, url=f"https://makerworld.com/en/models/{mid}", cover_url="",
            creator=CREATORS[(mid // 7) % len(CREATORS)],
            license="Standard Digital File License" if mid % 2 == 0 else "CC BY",
            likes=40 + mid % 960, downloads=120 + mid % 4880, prints=15 + mid % 785,
            summary=f"Simulated MakerWorld card: {title.lower()}, {dims[0]:g} x {dims[1]:g} x {dims[2]:g} mm.",
            instances=[
                ModelInstance(profile_id=mid * 10 + 1, title=f"{title} - A1 0.4 nozzle",
                              printer_models=["A1", "P1S", "X1C"], print_time_min=round(t02 / 60),
                              weight_g=round(g02, 1), plates=1),
                ModelInstance(profile_id=mid * 10 + 2, title=f"{title} - A1 mini",
                              printer_models=["A1 mini"], print_time_min=round(t02 * 1.1 / 60),
                              weight_g=round(g02, 1), plates=1),
            ],
            already_imported_library_ids=imported)

    def library_gcode(self, library_file_id: int, max_bytes: int = 8_000_000) -> str:
        with self._state() as st:
            entry = dict(self._lib(st, library_file_id))
        if not entry["sliced"]:
            raise BackendError(f"library file {library_file_id} is not sliced (no G-code)")
        if entry.get("stored"):
            text = _read_gcode_file(self.files_dir / entry["stored"])
        else:
            text = render_gcode(entry["params"])
        data = text.encode("utf-8")
        return data[:max_bytes].decode("utf-8", "ignore") if len(data) > max_bytes else text

    def recent_archives(self, limit: int = 5) -> list[dict]:
        with self._state() as st:
            return [dict(a) for a in reversed(st["archives"])][:max(0, int(limit))]

    # ---- library writes ---------------------------------------------------------------------
    def import_model(self, model_id: int, profile_id: Optional[int] = None) -> LibraryFile:
        mid = int(model_id)
        valid = (mid * 10 + 1, mid * 10 + 2)
        if profile_id is not None and int(profile_id) not in valid:
            raise BackendError(f"import: profile {profile_id} does not belong to model {mid} "
                               f"(valid: {valid[0]}, {valid[1]}; a #profileId-N fragment is an instance id)")
        with self._state() as st:
            e = self._add_model(st, mid, int(profile_id) if profile_id is not None else valid[0])
        return LibraryFile(id=e["id"], name=e["name"], kind=e["kind"], sliced=False)

    def upload_file(self, path: Path) -> LibraryFile:
        src = Path(path)
        if not src.is_file():
            raise BackendError(f"upload: {src.name}: file not found")
        name = _safe_name(src.name)
        low = name.lower()
        kind = ("gcode.3mf" if low.endswith(".gcode.3mf") else "gcode" if low.endswith(".gcode")
                else (src.suffix.lstrip(".").lower() or "bin"))
        sliced = kind in ("gcode.3mf", "gcode")
        dims = [40.0, 40.0, 20.0]
        params = None
        if sliced:
            params = _params_from_gcode(_read_gcode_file(src), name)
            dims = params["dims"]
        else:
            try:
                from ..customize import model_bbox

                dims = [round(float(v), 3) for v in model_bbox(src)]
            except Exception:
                pass
        with self._state() as st:
            lid = self._next_id(st, "library")
            self.files_dir.mkdir(parents=True, exist_ok=True)
            stored = f"{lid}_{name}"
            shutil.copyfile(src, self.files_dir / stored)
            entry = {"id": lid, "name": name, "kind": kind, "sliced": sliced, "dims": dims, "stored": stored}
            if params:
                entry["params"] = params
            st["library"].append(entry)
        return LibraryFile(id=lid, name=name, kind=kind, sliced=sliced)

    def download_file(self, library_file_id: int, out_dir: Path) -> Path:
        with self._state() as st:
            entry = dict(self._lib(st, library_file_id))
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / _safe_name(entry["name"])
        if entry.get("stored"):
            shutil.copyfile(self.files_dir / entry["stored"], dest)
        elif entry["sliced"]:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("Metadata/plate_1.gcode", render_gcode(entry["params"]))
        elif dest.suffix.lower() == ".stl":
            write_box_stl(dest, entry["dims"])
        else:
            write_box_3mf(dest, entry["dims"])
        return dest

    def slice(self, library_file_id: int, options: SliceOptions, timeout_s: int = 900) -> SliceResult:
        hint = self._hint()
        options = options or SliceOptions()
        material = self._material(options, hint)
        preset = str(options.printer_preset or "")
        overrides = options.process_overrides or {}
        prime = str(overrides.get("enable_prime_tower", "")).lower() in {"1", "true"} or \
            len(options.filament_presets or []) > 1
        with self._state() as st:
            src = self._lib(st, library_file_id)
            if src["sliced"]:
                raise BackendError(f"slice: library file {library_file_id} is already sliced")
            name = f"{_stem(src['name'])}.gcode.3mf"
            params = _slice_params(
                name, src["dims"], material=material, layer_h=_layer_height(options.process_preset),
                printer_model="Bambu Lab A1 mini" if "mini" in preset.lower() else "Bambu Lab A1",
                eject=self._is_autoeject(preset, hint), bed_type=options.bed_type or "Textured PEI Plate",
                prime_tower=prime, colour=(options.filament_colours or ["#FFFFFF"])[0] or "#FFFFFF",
                printer_preset=preset)
            entry = {"id": self._next_id(st, "library"), "name": name, "kind": "gcode.3mf", "sliced": True,
                     "source_id": src["id"], "model_id": src.get("model_id"), "dims": list(src["dims"]),
                     "params": params}
            st["library"].append(entry)
        return SliceResult(library_file_id=entry["id"], name=name, print_time_s=params["print_time_s"],
                           filament_g=params["filament_g"], filament_types=[material],
                           gcode_text=render_gcode(params))

    # ---- queue / printer actions ------------------------------------------------------------
    @staticmethod
    def _next_pos(st: dict) -> int:
        return max([q["position"] or 0 for q in st["queue"] if q["status"] in _ACTIVE_QUEUE], default=0) + 1

    def queue_add(self, library_file_id: int, *, ams_mapping: Optional[list[int]] = None,
                  plate_id: Optional[int] = None, manual_start: bool = True) -> QueueItem:
        with self._state() as st:
            entry = self._lib(st, library_file_id)
            if not entry["sliced"]:
                raise BackendError(f"queue add: library file {library_file_id} is not a sliced file")
            row = {"id": self._next_id(st, "queue"), "status": "pending", "name": entry["name"],
                   "position": self._next_pos(st), "library_file_id": entry["id"],
                   "manual_start": bool(manual_start), "print_time_s": entry["params"]["print_time_s"],
                   "scheduled_time": None, "created_at": _iso(self._now(st)), "archive_id": None,
                   "ams_mapping": list(ams_mapping or []), "plate_id": plate_id, "owner": "plugin"}
            st["queue"].append(row)
            self._auto_start(st, self._now(st))
            return self._qitem(row)

    def queue_remove(self, queue_item_id: int) -> None:
        with self._state() as st:
            row = self._qrow(st, queue_item_id)
            if row is None:
                raise BackendError(f"queue item {queue_item_id} not found")
            if row["status"] == "printing":
                raise BackendError(f"queue item {queue_item_id} is printing; stop the print instead")
            st["queue"].remove(row)

    def start(self, queue_item_id: int) -> QueueItem:
        with self._state() as st:
            self._require_online(st, "start")
            row = self._qrow(st, queue_item_id)
            if row is None:
                raise BackendError(f"start: queue item {queue_item_id} not found")
            if row["status"] != "pending":
                raise BackendError(f"start: queue item {queue_item_id} is {row['status']}, not pending")
            if self._active(st) is not None:
                raise BackendError(f"start: printer is busy ({self._status(st, self._now(st)).state})")
            if st["plate"]:
                raise BackendError("start: the build plate is not clear (simulated safety stop)")
            self._start_job(st, row, self._now(st))
            return self._qitem(row)

    def stop(self) -> None:
        with self._state() as st:
            self._require_online(st, "stop")
            job = self._active(st)
            if job is None:
                raise BackendError(f"stop: nothing is printing (state {self._status(st, self._now(st)).state})")
            t = self._now(st)
            _, prog, _ = self._phase(job, t)
            self._end_job(st, job, FAILED, t, prog, "cancelled")

    def pause(self) -> None:
        with self._state() as st:
            self._require_online(st, "pause")
            job = self._active(st)
            if job is None:
                raise BackendError("pause: nothing is printing")
            if job["paused_at"] is None:
                job["paused_at"], job["pause_reason"] = self._now(st), "user"

    def resume(self) -> None:
        with self._state() as st:
            self._require_online(st, "resume")
            job = self._active(st)
            if job is None or job["paused_at"] is None:
                raise BackendError("resume: printer is not paused")
            t = self._now(st)
            job["paused_total"] += t - job["paused_at"]
            if job["pause_reason"] == "hms":
                st["trays"][0]["remain_pct"] = 100  # someone loaded a fresh spool
            job.update(paused_at=None, pause_reason="", hms=[])

    def mark_plate_cleared(self) -> None:
        with self._state() as st:
            self._require_online(st, "clear plate")
            self._clear_plate(st)

    def _clear_plate(self, st: dict) -> None:
        if self._active(st) is not None:
            raise BackendError("clear plate: printer is printing")
        st["plate"] = None
        self._auto_start(st, self._now(st))

    # ---- simulator-only helpers -------------------------------------------------------------
    def advance(self, minutes: float) -> PrinterStatus:
        """Move simulated time forward and return the new status."""
        if minutes < 0:
            raise BackendError("advance: minutes must be >= 0")
        with self._state() as st:
            st["clock"]["sim0"] += float(minutes) * 60.0
            t = self._now(st)
            self._tick(st, t)  # one pass handles finish -> eject -> auto-start in order
            return self._status(st, t)

    def set_scenario(self, name: str) -> None:
        if name not in SCENARIOS:
            raise BackendError(f"unknown scenario {name!r} (choose: {', '.join(SCENARIOS)})")
        with self._state() as st:
            t = self._now(st)
            st["scenario"] = name
            if name == "busy":
                self._add_family_job(st, t)
            if name in ("busy", "offline"):
                return
            job = st["job"]
            if job and job["end_state"] is None:
                _, prog, _ = self._phase(job, t)
                job["scenario"] = name
                already_paused = job["paused_at"] is not None and name == "pause_hms"
                job["trigger_pct"] = None if already_paused else self._trigger_for(name, prog)
                self._tick(st, t)  # a threshold already passed fires now
            elif job and job.get("ejected_at") is None:
                job["scenario"] = name  # only matters for a pending eject (ok vs eject_miss)

    def _add_family_job(self, st: dict, t: float) -> None:
        if any(q.get("owner") == "family" and q["status"] == "pending" for q in st["queue"]):
            return
        title, dims = _catalog(FAMILY_MODEL_ID)
        name = f"{title}.gcode.3mf"
        entry = {"id": self._next_id(st, "library"), "name": name, "kind": "gcode.3mf", "sliced": True,
                 "model_id": FAMILY_MODEL_ID, "dims": list(dims), "params": _slice_params(name, dims)}
        st["library"].append(entry)
        for q in st["queue"]:
            if q["status"] == "pending" and q["position"] is not None:
                q["position"] += 1
        st["queue"].append({"id": self._next_id(st, "queue"), "status": "pending", "name": name, "position": 1,
                            "library_file_id": entry["id"], "manual_start": True,
                            "print_time_s": entry["params"]["print_time_s"], "scheduled_time": None,
                            "created_at": _iso(t - 3600), "archive_id": None, "ams_mapping": [0],
                            "plate_id": 1, "owner": "family"})

    def human_clears_plate(self) -> None:
        """A person takes the part off (works even when the printer is offline)."""
        with self._state() as st:
            self._clear_plate(st)

    def reset(self) -> None:
        with self._state() as st:
            st.clear()
            st.update(self._fresh())
        shutil.rmtree(self.files_dir, ignore_errors=True)


__all__ = ["SimulatorBackend", "SCENARIOS", "SIM_AUTOEJECT_PRESET", "AUTOEJECT_ENV", "SPEED_ENV",
           "parse_model_id", "render_gcode", "render_plate_png", "write_box_3mf", "write_box_stl"]
