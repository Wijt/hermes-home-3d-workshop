"""Sliced-file inspection: header facts, first-layer footprint, eject marker, auto-eject eligibility.

Reads OrcaSlicer / Bambu Studio G-code (``; HEADER_BLOCK``, ``; CONFIG_BLOCK``, ``; Z_HEIGHT:`` layer
markers, ``; FEATURE:`` labels) and falls back to PrusaSlicer-style markers (``;Z:``, ``;TYPE:``) or the
nozzle Z when there are none. Pure functions, stdlib only; files of 30+ MB parse in well under a second
because only the needed layers are walked move by move.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Optional

EJECT_MARKERS = ("HOME3D AUTO-EJECT", "HERMES AUTO-EJECT")
EXPECTED_PRINTER_MODEL = "Bambu Lab A1"
PRESET_PUSH_Z_MM = 2.5  # the auto-eject end G-code sweeps the nozzle at this height
LARGE_FOOTPRINT_FACTOR = 4.0  # min side >= 4 x min_footprint_mm counts as a large, flat footprint

# Features that are not the part itself (excluded from footprints, used only if nothing else is there).
_NON_PART_WORDS = ("tower", "skirt", "brim")

# material family -> (nozzle C range, bed C range)
TEMP_RANGES = {
    "PLA": ((190, 230), (35, 65)),
    "PETG": ((220, 260), (60, 90)),
    "TPU": ((200, 250), (25, 60)),
    "ABS": ((240, 280), (80, 110)),
    "ASA": ((240, 280), (80, 110)),
    "PC": ((260, 300), (90, 120)),
}
# Bambu/Orca bed type -> config key holding the per-filament bed temperature
_BED_KEYS = {
    "cool plate": "cool_plate_temp",
    "engineering plate": "eng_plate_temp",
    "high temp plate": "hot_plate_temp",
    "smooth pei plate": "hot_plate_temp",
    "textured pei plate": "textured_plate_temp",
    "cool plate (supertack)": "supertack_plate_temp",
    "textured cool plate": "textured_cool_plate_temp",
}

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)"
_WORD_RE = re.compile(r"([XYZEIJR])(" + _NUM + r")")

BBox = tuple[float, float, float, float]  # xmin, xmax, ymin, ymax


@dataclass
class GcodeInfo:
    printer_model: str = ""
    print_time_s: Optional[int] = None
    filament_g: Optional[float] = None
    filament_types: list[str] = field(default_factory=list)
    nozzle_temps: list[float] = field(default_factory=list)
    bed_temps: list[float] = field(default_factory=list)
    max_z: Optional[float] = None
    layer_count: int = 0
    first_layer_bbox: Optional[BBox] = None  # part extrusion at the first Z (skirt/brim/tower excluded)
    has_eject_marker: bool = False
    prime_tower: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def footprint_mm(self) -> Optional[tuple[float, float]]:
        if not self.first_layer_bbox:
            return None
        x0, x1, y0, y1 = self.first_layer_bbox
        return (round(x1 - x0, 2), round(y1 - y0, 2))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["first_layer_bbox"] = list(self.first_layer_bbox) if self.first_layer_bbox else None
        d["footprint_mm"] = list(self.footprint_mm) if self.footprint_mm else None
        return d


@dataclass
class EjectAssessment:
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    push_z: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---- small helpers -------------------------------------------------------------------------------
def _num(s: str) -> Optional[float]:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _duration_s(text: str) -> Optional[int]:
    parts = re.findall(r"(\d+)\s*([dhms])\b", text or "")
    if not parts:
        return None
    mult = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(int(v) * mult[u] for v, u in parts)


def _split_list(value: str) -> list[str]:
    return [v.strip().strip('"') for v in re.split(r"[;,]", value or "") if v.strip().strip('"')]


def material_family(material: str) -> str:
    """'PLA Matte' / 'PLA+' / 'PHA' -> 'PLA', 'PETG HF' / 'PCTG' -> 'PETG', 'TPU 95A' -> 'TPU'."""
    m = (material or "").strip().upper()
    if not m:
        return ""
    if m.startswith(("PLA", "PHA")):
        return "PLA"
    if m.startswith(("PETG", "PET", "PCTG")):
        return "PETG"
    if m.startswith(("TPU", "TPE")) or "FLEX" in m:
        return "TPU"
    for fam in ("ABS", "ASA", "PC"):
        if m.startswith(fam):
            return fam
    return m.split()[0].split("-")[0]


def _config(text: str) -> dict[str, str]:
    """``; key = value`` pairs from the config block (or the whole file when there is no block)."""
    start = text.find("; CONFIG_BLOCK_START")
    end = text.find("; CONFIG_BLOCK_END", start + 1) if start >= 0 else -1
    chunk = text[start:end] if start >= 0 and end > start else text
    out: dict[str, str] = {}
    for m in re.finditer(r"^;\s*([A-Za-z0-9_]+) = (.*)$", chunk, re.M):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def _header(text: str, pattern: str) -> Optional[str]:
    """First match of ``pattern`` in the header/config (first 512 KB) or the footer (last 64 KB)."""
    rx = re.compile(pattern, re.M)
    for chunk in ((text[:524288], text[-65536:]) if len(text) > 589824 else (text,)):
        m = rx.search(chunk)
        if m:
            return m.group(1).strip()
    return None


def _markers(text: str) -> list[tuple[float, int, int]]:
    """Layer markers as (z, start, end) text spans; empty when the file has none."""
    found: list[tuple[float, int]] = []
    for tag in ("\n; Z_HEIGHT:", "\n;Z:"):
        pos = text.find(tag)
        while pos >= 0:
            eol = text.find("\n", pos + 1)
            z = _num(text[pos + len(tag):eol if eol >= 0 else len(text)].strip())
            if z is not None:
                found.append((z, pos + 1))
            pos = text.find(tag, pos + 1)
        if found:
            break
    spans = []
    for i, (z, start) in enumerate(found):
        end = found[i + 1][1] if i + 1 < len(found) else len(text)
        spans.append((z, start, end))
    return spans


def _cmd_values(text: str, cmds: tuple[str, ...], start: int = 0, end: Optional[int] = None) -> list[str]:
    """S values of G-code commands (``M140 S65``) at line starts in ``text[start:end]``."""
    end = len(text) if end is None else end
    out = []
    for cmd in cmds:
        tag = "\n" + cmd + " "
        pos = text.find(tag, start)
        while 0 <= pos < end:
            eol = text.find("\n", pos + 1)
            m = re.search(r"\bS(" + _NUM + ")", text[pos:eol if eol >= 0 else len(text)].split(";", 1)[0])
            if m:
                out.append(m.group(1))
            pos = text.find(tag, pos + 1)
    return out


def _mode_before(text: str, idx: int) -> tuple[bool, bool]:
    """(absolute XYZ, relative E) in effect at ``idx``; Bambu/Orca default is G90 + M83."""
    g90, g91 = text.rfind("\nG90", 0, idx), text.rfind("\nG91", 0, idx)
    m82, m83 = text.rfind("\nM82", 0, idx), text.rfind("\nM83", 0, idx)
    return (g90 >= g91), (m83 >= m82)


def _arc_points(x0: float, y0: float, x1: float, y1: float, i: float, j: float, cw: bool) -> list[tuple[float, float]]:
    """Axis extremes an arc passes through (so the bbox of an arc move is exact)."""
    cx, cy = x0 + i, y0 + j
    r = math.hypot(i, j)
    if r <= 0:
        return []
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    sweep = (a0 - a1) if cw else (a1 - a0)
    sweep %= 2 * math.pi
    if sweep < 1e-9:
        sweep = 2 * math.pi  # start == end: full circle
    pts = []
    for k in range(4):
        ang = k * math.pi / 2
        delta = ((a0 - ang) if cw else (ang - a0)) % (2 * math.pi)
        if delta <= sweep:
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def _grow(box: Optional[list[float]], pts: list[tuple[float, float]]) -> list[float]:
    box = box or [math.inf, -math.inf, math.inf, -math.inf]
    for px, py in pts:
        box[0], box[1] = min(box[0], px), max(box[1], px)
        box[2], box[3] = min(box[2], py), max(box[3], py)
    return box


def _walk(text: str, start: int, end: int, *, by_z: bool = False) -> dict:
    """Extrusion bboxes in ``text[start:end]`` -> {key: [part box, non-part box]}.

    ``key`` is None, or the nozzle Z of each move when ``by_z`` (files without layer markers).
    """
    absolute, rel_e = _mode_before(text, start)
    x = y = z = None
    last_e = 0.0
    feature = ""
    out: dict = {}
    for raw in text[start:end].splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[0] == ";":
            low = line.lower()
            if low.startswith("; feature:") or low.startswith(";type:"):
                feature = low.split(":", 1)[1].strip()
            continue
        code = line.split(";", 1)[0].split(None, 1)
        if not code:
            continue
        cmd = code[0].upper()
        if cmd in ("G0", "G1", "G2", "G3"):
            words = dict(_WORD_RE.findall(code[1].upper())) if len(code) > 1 else {}
            nx, ny, nz = (_num(words.get(k, "")) for k in ("X", "Y", "Z"))
            if not absolute:
                nx = x + nx if nx is not None and x is not None else None
                ny = y + ny if ny is not None and y is not None else None
                nz = z + nz if nz is not None and z is not None else None
            tx = nx if nx is not None else x
            ty = ny if ny is not None else y
            if nz is not None:
                z = nz
            e = _num(words.get("E", ""))
            extruding = False
            if e is not None:
                extruding = e > 0 if rel_e else e > last_e
                if not rel_e:
                    last_e = e
            moved = "X" in words or "Y" in words
            if extruding and cmd != "G0" and moved and tx is not None and ty is not None:
                key = (round(z, 3) if z is not None else None) if by_z else None
                if not (by_z and key is None):
                    pts = [(tx, ty)]
                    if x is not None and y is not None:
                        pts.append((x, y))
                        if cmd in ("G2", "G3") and ("I" in words or "J" in words):
                            pts += _arc_points(x, y, tx, ty, _num(words.get("I", "0")) or 0.0,
                                               _num(words.get("J", "0")) or 0.0, cmd == "G2")
                    slot = out.setdefault(key, [None, None])
                    k = 1 if any(w in feature for w in _NON_PART_WORDS) else 0
                    slot[k] = _grow(slot[k], pts)
            x, y = tx, ty
        elif cmd == "G90":
            absolute = True
        elif cmd == "G91":
            absolute = False
        elif cmd == "M82":
            rel_e = False
        elif cmd == "M83":
            rel_e = True
        elif cmd == "G92" and len(code) > 1:
            words = dict(_WORD_RE.findall(code[1].upper()))
            if "E" in words:
                last_e = _num(words["E"]) or 0.0
    return out


def _as_bbox(box: Optional[list[float]]) -> Optional[BBox]:
    if not box or box[0] == math.inf:
        return None
    return (round(box[0], 3), round(box[1], 3), round(box[2], 3), round(box[3], 3))


def _pick_box(slots: list) -> Optional[BBox]:
    part = other = None
    for p, o in slots:
        if p:
            part = _grow(part, [(p[0], p[2]), (p[1], p[3])])
        if o:
            other = _grow(other, [(o[0], o[2]), (o[1], o[3])])
    return _as_bbox(part) or _as_bbox(other)


def _layer_bbox(text: str, spans: list[tuple[float, int, int]], z: float) -> Optional[BBox]:
    slots = []
    for lz, start, end in spans:
        if abs(lz - z) < 1e-6:  # by-object prints revisit the same Z once per object
            slots += list(_walk(text, start, end).values())
    return _pick_box(slots)


def _by_z(text: str) -> dict:
    """No-marker fallback: {nozzle Z: [part box, other box]} for the whole file."""
    return _walk(text, 0, len(text), by_z=True)


# ---- public API --------------------------------------------------------------------------------
def footprint_at(text: str, z: float) -> Optional[BBox]:
    """XY bbox of the part's extrusion in the layer printed at height ``z`` (None above the top).

    Use it to pick a push height where the footprint is still full width (base/frame, not detail).
    """
    spans = _markers(text)
    if spans:
        zs = sorted({s[0] for s in spans})
        target = next((lz for lz in zs if lz >= z - 1e-6), None)
        if target is None:
            return None
        return _layer_bbox(text, spans, target)
    layers = _by_z(text)
    target = next((lz for lz in sorted(layers) if lz >= z - 1e-6), None)
    return _pick_box([layers[target]]) if target is not None else None


def _used_indices(text: str) -> Optional[list[int]]:
    """Zero-based indices of the filaments the plate uses (header ``; filament: 1,3``)."""
    raw = _header(text, r"^; filament: ([\d, ]+)$")
    return [int(v) - 1 for v in re.findall(r"\d+", raw)] if raw else None


def _pick(values: list[str], used: Optional[list[int]]) -> list[str]:
    """Per-filament config values of the used filaments only."""
    if used is None or len(values) <= 1:
        return values
    return [values[i] for i in used if 0 <= i < len(values)] or values


def _floats(values: list[str]) -> list[float]:
    out = []
    for v in values:
        f = _num(v)
        if f is not None and f > 0 and f not in out:
            out.append(f)
    return out


def _eject_marker(text: str, cfg: dict[str, str]) -> tuple[bool, bool]:
    """(marker in executed G-code, marker in the machine_end_gcode config value)."""
    cs = text.find("; CONFIG_BLOCK_START")
    ce = text.find("; CONFIG_BLOCK_END", cs + 1) if cs >= 0 else -1
    in_body = False
    for marker in EJECT_MARKERS:
        pos = text.find(marker)
        while pos >= 0:
            line_start = text.rfind("\n", 0, pos) + 1
            in_config = cs >= 0 and ce > cs and cs <= pos <= ce
            if not in_config and " = " not in text[line_start:pos]:
                in_body = True
                break
            pos = text.find(marker, pos + 1)
        if in_body:
            break
    end_gcode = cfg.get("machine_end_gcode", "")
    in_cfg = any(m in end_gcode for m in EJECT_MARKERS)
    return in_body, in_cfg


def inspect_gcode(text: str) -> GcodeInfo:
    """Facts the gates need from a sliced plate's G-code. Never raises on odd input."""
    info = GcodeInfo()
    text = text or ""
    if not text.strip():
        info.warnings.append("empty G-code")
        return info
    try:
        _inspect(text, info)
    except Exception as exc:  # odd G-code must not break slicing; keep what was parsed
        info.warnings.append(f"G-code parse error: {exc}")
    return info


def _inspect(text: str, info: GcodeInfo) -> None:
    cfg = _config(text)

    model = cfg.get("printer_model", "").strip('"')
    if not model:
        m = re.search(r"Bambu Lab (A1 mini|A1|P1S|P1P|X1C|X1E|X1|H2D|H2S|P2S)", cfg.get("printer_settings_id", ""))
        model = f"Bambu Lab {m.group(1)}" if m else ""
    info.printer_model = model

    t = _header(text, r"total estimated time:\s*([^;\n]+)") \
        or _header(text, r"^; estimated printing time \(normal mode\) = (.+)$") \
        or _header(text, r"^; model printing time:\s*([^;\n]+)")
    info.print_time_s = _duration_s(t) if t else None

    g = _header(text, r"^; total filament weight \[g\]\s*[:=]\s*(" + _NUM + ")")
    if g is not None:
        info.filament_g = _num(g)
    else:
        used_g = _header(text, r"^; filament used \[g\] = (.+)$")
        vals = [_num(v) for v in _split_list(used_g or "")]
        vals = [v for v in vals if v is not None]
        info.filament_g = round(sum(vals), 2) if vals else None

    used = _used_indices(text)
    types = _pick(_split_list(cfg.get("filament_type", "")), used)
    info.filament_types = list(dict.fromkeys(types))

    spans = _markers(text)
    mz = _header(text, r"^; max_z_height:\s*(" + _NUM + ")")
    info.max_z = _num(mz) if mz is not None else (max(s[0] for s in spans) if spans else None)
    ln = _header(text, r"^; total layer number:\s*(\d+)")
    info.layer_count = int(ln) if ln else len({s[0] for s in spans})

    # first-layer footprint
    if spans:
        info.first_layer_bbox = _layer_bbox(text, spans, spans[0][0])
    else:
        layers = _by_z(text)
        if layers:
            info.first_layer_bbox = _pick_box([layers[min(layers)]])
            info.max_z = info.max_z if info.max_z is not None else max(layers)
            info.layer_count = info.layer_count or len(layers)

    # temperatures
    nozzle_cfg = _pick(_split_list(cfg.get("nozzle_temperature", "")), used)
    nozzle = _floats(nozzle_cfg)
    if not nozzle and spans:
        nozzle = _floats(_cmd_values(text, ("M104", "M109"), spans[0][1], spans[min(2, len(spans) - 1)][2]))
    info.nozzle_temps = nozzle
    bed = _floats(_cmd_values(text, ("M140", "M190")))
    if not bed:
        key = _BED_KEYS.get(cfg.get("curr_bed_type", "").strip('"').lower(), "")
        if key:
            bed = _floats(_pick(_split_list(cfg.get(key + "_initial_layer", "")), used)
                          + _pick(_split_list(cfg.get(key, "")), used))
    info.bed_temps = sorted(bed)

    in_body, in_cfg = _eject_marker(text, cfg)
    info.has_eject_marker = in_body or in_cfg
    if in_cfg and not in_body and "; EXECUTABLE_BLOCK_END" in text:
        info.warnings.append("eject block is in the printer preset but not in the executed G-code")

    info.prime_tower = (cfg.get("enable_prime_tower", cfg.get("prime_tower_enable", "0")).strip() in {"1", "true"}
                        or "; FEATURE: Prime tower" in text or "; FEATURE: Wipe tower" in text
                        or ";TYPE:Wipe tower" in text)

    # warnings
    if model and model.strip().lower() != EXPECTED_PRINTER_MODEL.lower():
        info.warnings.append(f"sliced for '{model}', not {EXPECTED_PRINTER_MODEL}")
    if info.prime_tower:
        info.warnings.append("prime tower is on (extra waste and an extra object on the plate)")
    if not spans and info.first_layer_bbox is None:
        info.warnings.append("no layers found")
    # nozzle per filament (config order) or, without config, every print temperature vs every material
    pairs = list(zip(types, [_num(v) for v in nozzle_cfg])) if len(nozzle_cfg) == len(types) else \
        [(ft, v) for ft in types for v in info.nozzle_temps]
    for ft, v in dict.fromkeys(pairs):
        fam = material_family(ft)
        if fam in TEMP_RANGES and v and not TEMP_RANGES[fam][0][0] <= v <= TEMP_RANGES[fam][0][1]:
            lo, hi = TEMP_RANGES[fam][0]
            info.warnings.append(f"nozzle {v:g} C is outside the {fam} range {lo}-{hi} C")
    first = material_family(types[0]) if types else ""
    if first in TEMP_RANGES:  # the bed follows the first filament
        lo, hi = TEMP_RANGES[first][1]
        bad = [v for v in info.bed_temps if not lo <= v <= hi]
        if bad:
            info.warnings.append(f"bed {', '.join(f'{v:g}' for v in bad)} C does not suit {first} ({lo}-{hi} C)")


def assess_eject(info: GcodeInfo, material: str = "PLA", *, min_height_mm: float = 3.0,
                 min_footprint_mm: float = 15.0, max_aspect: float = 2.5) -> EjectAssessment:
    """Can the nozzle safely push this part off the plate after the print (auto-eject preset)?

    Rules from the real A1 setup: only sturdy, flat PLA-like parts. PETG stays welded when cold, TPU
    bends; the push at Z2.5 passes over parts under ~3 mm; tall-narrow parts tip over instead of
    sliding; tiny footprints roll or fall wrong. Round / fragile shapes are not detectable here.
    """
    reasons: list[str] = []
    materials = [m for m in [material, *info.filament_types] if m]
    for m in dict.fromkeys(material_family(x) for x in materials):
        if m == "PETG":
            reasons.append("PETG stays welded to the plate when cold: remove by hand")
        elif m == "TPU":
            reasons.append("flexible filament bends instead of releasing: remove by hand")
        elif m and m != "PLA":
            reasons.append(f"{m}: only PLA-like parts are pushed off")

    h = info.max_z
    fp = info.footprint_mm
    if h is None:
        reasons.append("part height unknown")
    if fp is None:
        reasons.append("first-layer footprint unknown")
    if h is not None and fp is not None:
        w, d = fp
        short = min(w, d)
        large = short >= min_footprint_mm * LARGE_FOOTPRINT_FACTOR
        need_h = min(min_height_mm, PRESET_PUSH_Z_MM + 0.3) if large else min_height_mm
        if h < need_h:
            reasons.append(f"only {h:g} mm tall: the push at Z{PRESET_PUSH_Z_MM:g} passes over it "
                           "(add a push tab or print on a sled)")
        if short < min_footprint_mm:
            reasons.append(f"footprint {w:g} x {d:g} mm is under {min_footprint_mm:g} mm: it rolls or falls wrong")
        elif short > 0 and h / short > max_aspect:
            reasons.append(f"tall and narrow ({h:g} mm on {short:g} mm, ratio {h / short:.1f} > {max_aspect:g}): "
                           "it tips over")
    if reasons:
        return EjectAssessment(False, reasons, None)
    w, d = fp  # type: ignore[misc]
    return EjectAssessment(True, [f"sturdy PLA part, {w:g} x {d:g} mm footprint, {h:g} mm tall",
                                  "check shape: round, fragile or several separate parts should not be pushed"],
                           PRESET_PUSH_Z_MM)
