"""Model customisation without a CAD stack: uniform scaling of STL (ASCII/binary) and 3MF, bounding
boxes, and optional OpenSCAD templates (name tag, label box).

Pure python + stdlib. Scaling keeps the part where it was on the plate: it scales about the
bottom-centre of the model (XY centre, lowest Z), so nothing sinks below or floats above the bed.
3MF files are scaled through their ``<build><item transform>`` (mesh data stays untouched; multi-plate
Bambu/Orca projects per plate); every other archive entry keeps its content. Sliced files
(``.gcode.3mf``) are refused: scale the model.
"""

from __future__ import annotations

import copy
import math
import os
import re
import shutil
import struct
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Iterable, Optional

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
BUILD_VOLUME_MM = (256.0, 256.0, 256.0)  # Bambu Lab A1
MIN_FACTOR, MAX_FACTOR = 0.05, 20.0

# Parts whose fit breaks when scaled (lids, snap-fits, hinges, threads); en + tr words.
MECHANISM_WORDS = ("lid", "snap", "hinge", "thread", "screw", "bolt", "nut", "clip", "kapak", "mentese",
                   "menteşe", "vida", "somun", "civata", "cıvata", "gecme", "geçme", "klips")

TEMPLATES: dict[str, dict] = {
    "name_tag": {
        "file": "name_tag.scad",
        "params": {"text": "Sam", "width": 80.0, "height": 25.0, "thickness": 3.0, "font_size": 10.0},
        "description": "Name tag: raised text on a rounded plate with a key-ring hole.",
    },
    "label_box": {
        "file": "label_box.scad",
        "params": {"text": "Box", "width": 60.0, "depth": 40.0, "height": 30.0, "wall": 2.0,
                   "font_size": 8.0},
        "description": "Open storage box with a raised label on the front wall.",
    },
}
_TEXT_LIMIT = 40
_NUM_LIMITS = {"thickness": (0.6, 20.0), "wall": (0.8, 10.0), "font_size": (2.0, 120.0)}

_CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_PROD_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
_MODEL_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]  # (mins, maxs)


class CustomizeError(RuntimeError):
    """Readable error for the agent / owner (bad file, missing OpenSCAD, ...)."""


# ---- helpers --------------------------------------------------------------------------------------
def _kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".gcode.3mf") or name.endswith(".gcode"):
        raise CustomizeError(f"{path.name} is a sliced file: scale the model file, not the sliced plate")
    if name.endswith(".stl"):
        return "stl"
    if name.endswith(".3mf"):
        return "3mf"
    raise CustomizeError(f"{path.name}: only .stl and .3mf models can be customised")


def _grow(acc: Optional[list[float]], x: float, y: float, z: float) -> list[float]:
    if acc is None:
        return [x, y, z, x, y, z]
    if x < acc[0]:
        acc[0] = x
    if y < acc[1]:
        acc[1] = y
    if z < acc[2]:
        acc[2] = z
    if x > acc[3]:
        acc[3] = x
    if y > acc[4]:
        acc[4] = y
    if z > acc[5]:
        acc[5] = z
    return acc


def _bounds_of(acc: Optional[list[float]], what: str) -> Bounds:
    if acc is None:
        raise CustomizeError(f"{what}: no geometry found")
    return (acc[0], acc[1], acc[2]), (acc[3], acc[4], acc[5])


def _pivot(b: Bounds) -> tuple[float, float, float]:
    (x0, y0, z0), (x1, y1, _) = b
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0, z0


def _fmt(v: float) -> str:
    s = format(v, ".9g")
    return "0" if s in ("-0", "0") else s


def check_factor(factor: float) -> float:
    try:
        f = float(factor)
    except (TypeError, ValueError):
        raise CustomizeError(f"scale factor {factor!r} is not a number") from None
    if not math.isfinite(f) or not MIN_FACTOR <= f <= MAX_FACTOR:
        raise CustomizeError(f"scale factor {f:g} is outside {MIN_FACTOR:g}..{MAX_FACTOR:g}")
    return f


def mechanism_words(name: str) -> list[str]:
    """Words in a file/model name that suggest a fitted mechanism (scaling breaks the fit)."""
    low = (name or "").lower()
    return [w for w in MECHANISM_WORDS if re.search(r"(?<![a-zçğıöşü])" + re.escape(w), low)]


def fits_build_volume(size: Iterable[float], volume: Iterable[float] = BUILD_VOLUME_MM) -> bool:
    return all(s <= v + 1e-6 for s, v in zip(size, volume))


# ---- STL ------------------------------------------------------------------------------------------
_VERTEX_RE = re.compile(rb"(vertex\s+)(\S+)(\s+)(\S+)(\s+)(\S+)", re.I)


def _stl_is_binary(data: bytes) -> bool:
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50 * n == len(data):
            return True
    head = data[:512].lstrip().lower()
    if head.startswith(b"solid") and b"facet" in data[:4096].lower():
        return False
    if len(data) < 84:
        raise CustomizeError("STL file is too short")
    return True


def _stl_bounds(data: bytes) -> Bounds:
    acc = None
    if _stl_is_binary(data):
        n = struct.unpack_from("<I", data, 80)[0]
        n = min(n, (len(data) - 84) // 50)
        for t in struct.iter_unpack("<12fH", memoryview(data)[84:84 + 50 * n]):
            acc = _grow(acc, t[3], t[4], t[5])
            acc = _grow(acc, t[6], t[7], t[8])
            acc = _grow(acc, t[9], t[10], t[11])
    else:
        for m in _VERTEX_RE.finditer(data):
            try:
                acc = _grow(acc, float(m.group(2)), float(m.group(4)), float(m.group(6)))
            except ValueError:
                raise CustomizeError("ASCII STL has a malformed vertex line") from None
    return _bounds_of(acc, "STL")


def _scale_stl(data: bytes, f: float) -> bytes:
    px, py, pz = _pivot(_stl_bounds(data))
    if _stl_is_binary(data):
        n = min(struct.unpack_from("<I", data, 80)[0], (len(data) - 84) // 50)
        out = bytearray(data[:84 + 50 * n])
        pack = struct.Struct("<12fH")
        for i, t in enumerate(pack.iter_unpack(memoryview(data)[84:84 + 50 * n])):
            v = list(t)
            for k in (3, 6, 9):
                v[k] = px + (v[k] - px) * f
                v[k + 1] = py + (v[k + 1] - py) * f
                v[k + 2] = pz + (v[k + 2] - pz) * f
            pack.pack_into(out, 84 + 50 * i, *v)
        return bytes(out)

    def sub(m: re.Match) -> bytes:
        x, y, z = (float(m.group(i)) for i in (2, 4, 6))
        vals = (px + (x - px) * f, py + (y - py) * f, pz + (z - pz) * f)
        return (m.group(1) + _fmt(vals[0]).encode() + m.group(3) + _fmt(vals[1]).encode() + m.group(5)
                + _fmt(vals[2]).encode())

    return _VERTEX_RE.sub(sub, data)


# ---- 3MF ------------------------------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_transform(raw: Optional[str]) -> tuple[float, ...]:
    if not raw or not raw.strip():
        return _IDENTITY
    vals = raw.split()
    if len(vals) != 12:
        raise CustomizeError(f"3MF transform needs 12 numbers, got {len(vals)}")
    try:
        return tuple(float(v) for v in vals)
    except ValueError:
        raise CustomizeError("3MF transform has a non-numeric value") from None


def _compose(a: tuple, b: tuple) -> tuple:
    """Transform that applies ``a`` first, then ``b`` (3MF row vectors: p' = p @ M + t)."""
    out = []
    for r in range(3):
        for c in range(3):
            out.append(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)))
    for c in range(3):
        out.append(sum(a[9 + k] * b[k * 3 + c] for k in range(3)) + b[9 + c])
    return tuple(out)


def _apply(m: tuple, x: float, y: float, z: float) -> tuple[float, float, float]:
    return (x * m[0] + y * m[3] + z * m[6] + m[9],
            x * m[1] + y * m[4] + z * m[7] + m[10],
            x * m[2] + y * m[5] + z * m[8] + m[11])


_KEEP_TAGS = {"build", "resources", "model"}  # containers whose children are still needed / tiny


def _stream(fh):
    """``iterparse`` on end events yielding (local tag, element); each element is cleared after the caller
    has seen it, so a million-vertex model part never sits in memory as a tree."""
    for _, el in ET.iterparse(fh, events=("end",)):
        tag = _local(el.tag)
        yield tag, el
        if tag not in _KEEP_TAGS:
            el.clear()


class _Package:
    """Lazily parsed 3MF: per-object mesh bboxes / components, build items of the root model.

    Vertices are only read again (one pass per model part) for meshes placed with a transform that does
    not map axes to axes; everything else uses the transformed corners of the local bbox, which is exact.
    """

    def __init__(self, zf: zipfile.ZipFile):
        self.zf = zf
        self.names = {n.lstrip("/"): n for n in zf.namelist()}
        self.root = self._root_path()
        self.models: dict[str, dict[str, dict]] = {}
        self.verts: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
        self.build: list[dict] = []  # [{"objectid", "path", "transform"}]
        self._load(self.root, is_root=True)

    def _root_path(self) -> str:
        rels = self.names.get("_rels/.rels")
        if rels:
            try:
                for el in ET.fromstring(self.zf.read(rels)).iter():
                    if _local(el.tag) == "Relationship" and el.get("Type", "").rstrip("/") == _MODEL_REL:
                        target = el.get("Target", "").lstrip("/")
                        if target in self.names:
                            return target
            except ET.ParseError:
                pass
        if "3D/3dmodel.model" in self.names:
            return "3D/3dmodel.model"
        for n in self.names:
            if n.lower().endswith(".model"):
                return n
        raise CustomizeError("3MF has no 3D model part")

    def _member(self, path: str) -> str:
        member = self.names.get(path.lstrip("/"))
        if member is None:
            raise CustomizeError(f"3MF references a missing part: /{path.lstrip('/')}")
        return member

    def _load(self, path: str, is_root: bool = False) -> dict[str, dict]:
        path = path.lstrip("/")
        if path in self.models:
            return self.models[path]
        objects: dict[str, dict] = {}
        acc: Optional[list[float]] = None  # vertices of the object being read (end events come first)
        comps: list[dict] = []
        try:
            with self.zf.open(self._member(path)) as fh:
                for tag, el in _stream(fh):
                    if tag == "vertex":
                        acc = _grow(acc, *_vertex(el))
                    elif tag == "component":
                        comps.append({"objectid": el.get("objectid", ""),
                                      "path": (el.get(f"{{{_PROD_NS}}}path") or path).lstrip("/"),
                                      "transform": _parse_transform(el.get("transform"))})
                    elif tag == "object":
                        objects[el.get("id", "")] = {
                            "mesh": _bounds_of(acc, "3MF object") if acc is not None else None,
                            "components": comps}
                        acc, comps = None, []
                    elif tag == "item" and is_root:
                        self.build.append({"objectid": el.get("objectid", ""),
                                           "path": (el.get(f"{{{_PROD_NS}}}path") or path).lstrip("/"),
                                           "transform": _parse_transform(el.get("transform"))})
        except ET.ParseError as e:
            raise CustomizeError(f"3MF model part /{path} is not valid XML: {e}") from None
        self.models[path] = objects
        return objects

    def _load_vertices(self, path: str, ids: set[str]) -> None:
        """Vertices of the objects ``ids`` in one model part (one parse)."""
        pending: list[tuple[float, float, float]] = []
        with self.zf.open(self._member(path)) as fh:
            for tag, el in _stream(fh):
                if tag == "vertex":
                    pending.append(_vertex(el))
                elif tag == "object":
                    if el.get("id", "") in ids:
                        self.verts[(path, el.get("id", ""))] = pending
                    pending = []

    def _walk(self, path: str, objectid: str, m: tuple, visit: Callable, depth: int = 0) -> None:
        if depth > 16:
            raise CustomizeError("3MF components nest too deeply")
        obj = self._load(path).get(objectid)
        if obj is None:
            raise CustomizeError(f"3MF references a missing object {objectid}")
        if obj["mesh"] is not None:
            visit(path, objectid, obj, m)
        for c in obj["components"]:
            self._walk(c["path"], c["objectid"], _compose(c["transform"], m), visit, depth + 1)

    def item_bounds(self) -> list[Optional[list[float]]]:
        """World bbox ``[x0, y0, z0, x1, y1, z1]`` of every build item (None for an empty item)."""
        need: dict[str, set[str]] = {}

        def mark(path, oid, obj, m):
            if not _axis_aligned(m):
                need.setdefault(path, set()).add(oid)

        for item in self.build:
            self._walk(item["path"], item["objectid"], item["transform"], mark)
        for path, ids in need.items():
            missing = {i for i in ids if (path, i) not in self.verts}
            if missing:
                self._load_vertices(path, missing)
        out: list[Optional[list[float]]] = []
        for item in self.build:
            box: list = [None]

            def grow(path, oid, obj, m):
                if _axis_aligned(m):
                    (x0, y0, z0), (x1, y1, z1) = obj["mesh"]
                    pts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
                else:
                    pts = self.verts.get((path, oid), [])
                for x, y, z in pts:
                    box[0] = _grow(box[0], *_apply(m, x, y, z))

            self._walk(item["path"], item["objectid"], item["transform"], grow)
            out.append(box[0])
        return out

    def plate_groups(self) -> list[list[int]]:
        """Build item indices per plate (Bambu/Orca ``Metadata/model_settings.config``); one group otherwise."""
        n = len(self.build)
        cfg = self.names.get("Metadata/model_settings.config")
        plates: list[list[tuple[str, int]]] = []
        if cfg:
            try:
                for plate in ET.fromstring(self.zf.read(cfg)).iter():
                    if _local(plate.tag) != "plate":
                        continue
                    insts = []
                    for mi in plate:
                        if _local(mi.tag) != "model_instance":
                            continue
                        meta = {m.get("key"): m.get("value") for m in mi if _local(m.tag) == "metadata"}
                        try:
                            insts.append((str(meta.get("object_id", "")), int(meta.get("instance_id") or 0)))
                        except ValueError:
                            insts.append((str(meta.get("object_id", "")), 0))
                    plates.append(insts)
            except ET.ParseError:
                plates = []
        if len(plates) <= 1:
            return [list(range(n))] if n else []
        seen: dict[str, int] = {}
        groups: list[list[int]] = [[] for _ in plates]
        rest: list[int] = []
        for i, item in enumerate(self.build):  # the n-th item of an object is instance n
            oid = item["objectid"]
            key = (oid, seen.get(oid, 0))
            seen[oid] = key[1] + 1
            idx = next((p for p, insts in enumerate(plates) if key in insts), None)
            if idx is None:
                idx = next((p for p, insts in enumerate(plates) if any(o == oid for o, _ in insts)), None)
            (rest if idx is None else groups[idx]).append(i)
        return [g for g in groups if g] + ([rest] if rest else [])


def _vertex(el) -> tuple[float, float, float]:
    try:
        return float(el.get("x")), float(el.get("y")), float(el.get("z"))
    except (TypeError, ValueError):
        raise CustomizeError("3MF has a malformed vertex") from None


def _axis_aligned(m: tuple) -> bool:
    """True when the 3x3 part maps axes to axes (scale / mirror / 90-degree turns): bbox corners suffice."""
    return all(sum(1 for k in range(3) if abs(m[r * 3 + k]) > 1e-9) <= 1 for r in range(3))


def _union(boxes: Iterable[Optional[list[float]]]) -> Optional[list[float]]:
    acc = None
    for b in boxes:
        if b is not None:
            acc = _grow(acc, b[0], b[1], b[2])
            acc = _grow(acc, b[3], b[4], b[5])
    return acc


def _3mf_analyse(zf: zipfile.ZipFile) -> tuple[_Package, list[Optional[list[float]]], list[list[int]]]:
    pkg = _Package(zf)
    if not pkg.build:
        raise CustomizeError("3MF has no build items")
    boxes = pkg.item_bounds()
    if _union(boxes) is None:
        raise CustomizeError("3MF: no geometry found")
    return pkg, boxes, pkg.plate_groups()


_BUILD_RE = re.compile(r"<(?:[\w.-]+:)?build\b[^>]*>(.*?)</(?:[\w.-]+:)?build\s*>", re.S)
_ITEM_RE = re.compile(r"<(?:[\w.-]+:)?item\b[^>]*?/?>", re.S)
_TRANSFORM_ATTR_RE = re.compile(r"""(\stransform\s*=\s*)(["'])(.*?)\2""", re.S)


def _rewrite_build(xml: str, transforms: list[tuple]) -> str:
    m = _BUILD_RE.search(xml)
    if not m:
        raise CustomizeError("3MF root model has no <build> section")
    body = m.group(1)
    items = list(_ITEM_RE.finditer(body))
    if len(items) != len(transforms):
        raise CustomizeError(f"3MF build has {len(items)} items, expected {len(transforms)}")
    out, pos = [], 0
    for it, t in zip(items, transforms):
        tag = it.group(0)
        value = " ".join(_fmt(v) for v in t)
        if _TRANSFORM_ATTR_RE.search(tag):
            tag = _TRANSFORM_ATTR_RE.sub(lambda a: f"{a.group(1)}{a.group(2)}{value}{a.group(2)}", tag, count=1)
        else:
            tag = re.sub(r"^(<(?:[\w.-]+:)?item)\b", lambda a: f'{a.group(1)} transform="{value}"', tag, count=1)
        out.append(body[pos:it.start()])
        out.append(tag)
        pos = it.end()
    out.append(body[pos:])
    return xml[:m.start(1)] + "".join(out) + xml[m.end(1):]


def _scale_3mf(src: Path, f: float, out: Path) -> None:
    """Scale every plate's arrangement about that plate's bottom-centre (objects stay on their plate)."""
    with zipfile.ZipFile(src) as zin:
        pkg, boxes, groups = _3mf_analyse(zin)
        new: list[tuple] = [item["transform"] for item in pkg.build]
        for g in groups:
            acc = _union(boxes[i] for i in g)
            if acc is None:
                continue
            px, py, pz = _pivot(((acc[0], acc[1], acc[2]), (acc[3], acc[4], acc[5])))
            for i in g:
                m = pkg.build[i]["transform"]
                new[i] = tuple(v * f for v in m[:9]) + (m[9] * f + (1 - f) * px, m[10] * f + (1 - f) * py,
                                                        m[11] * f + (1 - f) * pz)
        root_member = pkg.names[pkg.root]
        xml = _rewrite_build(zin.read(root_member).decode("utf-8"), new)
        part = out.with_name(out.name + ".part")
        try:
            with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as zout:
                for info in zin.infolist():  # every other entry is copied unchanged (streamed)
                    if info.filename == root_member:
                        zout.writestr(info, xml.encode("utf-8"))
                        continue
                    dst = copy.copy(info)  # zout rewrites sizes/offsets: keep the source entry intact
                    with zin.open(info) as fi, zout.open(dst, "w", force_zip64=info.file_size > 2**31) as fo:
                        shutil.copyfileobj(fi, fo, 1 << 20)
            part.replace(out)
        finally:
            part.unlink(missing_ok=True)


# ---- public API -----------------------------------------------------------------------------------
def _read(src: Path, fn: Callable):
    try:
        return fn()
    except OSError as e:
        raise CustomizeError(f"cannot read {src.name}: {e.strerror or e}") from None
    except (struct.error, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as e:
        raise CustomizeError(f"{src.name} is damaged: {e}") from None


def _open_3mf(src: Path) -> zipfile.ZipFile:
    if not zipfile.is_zipfile(src):
        raise CustomizeError(f"{src.name} is not a 3MF (zip) archive")
    return zipfile.ZipFile(src)


def model_bounds(src: Path) -> Bounds:
    """(mins, maxs) of all geometry in mm (3MF: every build item with its transforms, all plates)."""
    src = Path(src)
    if _kind(src) == "stl":
        return _read(src, lambda: _stl_bounds(src.read_bytes()))

    def run():
        with _open_3mf(src) as zf:
            _, boxes, _ = _3mf_analyse(zf)
        return _bounds_of(_union(boxes), "3MF")

    return _read(src, run)


def model_bbox(src: Path) -> tuple[float, float, float]:
    """Size (x, y, z) of the model in mm. Multi-plate 3MF projects: the largest plate (per axis), since
    every plate is printed on its own."""
    src = Path(src)
    if _kind(src) == "stl":
        lo, hi = model_bounds(src)
        return tuple(round(hi[i] - lo[i], 4) for i in range(3))  # type: ignore[return-value]

    def run():
        with _open_3mf(src) as zf:
            _, boxes, groups = _3mf_analyse(zf)
        size = [0.0, 0.0, 0.0]
        for g in groups:
            acc = _union(boxes[i] for i in g)
            if acc is not None:
                size = [max(size[k], acc[k + 3] - acc[k]) for k in range(3)]
        return tuple(round(v, 4) for v in size)

    return _read(src, run)


def scale_model(src: Path, factor: float, out: Path) -> Path:
    """Uniformly scale an STL (ASCII/binary) or 3MF by ``factor`` about its bottom-centre (3MF: each plate
    about its own bottom-centre, so objects stay on their plate and on the bed)."""
    src, out = Path(src), Path(out)
    f = check_factor(factor)
    kind = _kind(src)
    if _kind(out) != kind:
        raise CustomizeError(f"output {out.name} must keep the .{kind} format")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if kind == "stl":
            out.write_bytes(_scale_stl(src.read_bytes(), f))
        else:
            if not zipfile.is_zipfile(src):
                raise CustomizeError(f"{src.name} is not a 3MF (zip) archive")
            _scale_3mf(src, f, out)
    except OSError as e:
        raise CustomizeError(f"cannot scale {src.name}: {e.strerror or e}") from None
    except (struct.error, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as e:
        raise CustomizeError(f"{src.name} is damaged: {e}") from None
    return out


def factor_for_size(size: Iterable[float], target_mm: float) -> float:
    """Factor that makes the largest dimension ``target_mm``."""
    largest = max(size)
    if largest <= 0:
        raise CustomizeError("model has zero size")
    return float(target_mm) / largest


def openscad_available() -> bool:
    return shutil.which("openscad") is not None


# Everything OpenSCAD and xvfb-run get from the parent's environment. A design is text a model wrote and OpenSCAD
# is a vendor binary, so neither runs with Hermes' provider keys (or anything else in os.environ) in reach.
_ENV_KEEP = ("PATH", "HOME", "LANG", "TMPDIR", "XDG_DATA_HOME")
_ENV_KEEP_PREFIX = "LC_"
_ENV_DISPLAY = ("DISPLAY", "XAUTHORITY")  # only for a preview drawn on a real display, never under xvfb-run
# Windows programs do not start without these; none of them holds a secret.
_ENV_KEEP_WINDOWS = ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                     "PATHEXT", "COMSPEC")


def openscad_env(display: bool = False) -> dict:
    """The explicit, minimal environment for ``openscad`` and ``xvfb-run``: PATH, HOME, LANG, LC_*, TMPDIR and
    XDG_DATA_HOME, plus DISPLAY and XAUTHORITY when ``display`` is true (a preview without xvfb-run, which sets
    its own). Nothing else is passed on: no provider keys, no OPENSCADPATH."""
    src = os.environ
    keep = _ENV_KEEP + (_ENV_KEEP_WINDOWS if os.name == "nt" else ()) + (_ENV_DISPLAY if display else ())
    env = {k: src[k] for k in keep if k in src}
    env.update({k: v for k, v in src.items() if k.startswith(_ENV_KEEP_PREFIX)})
    return env


def _check_param(name: str, value, default):
    """Validated python value of one template parameter (str / bool / float)."""
    if isinstance(default, str):
        text = re.sub(r"[\x00-\x1f]", " ", str(value)).strip()[:_TEXT_LIMIT]
        if not text:
            raise CustomizeError(f"template parameter '{name}' must not be empty")
        return text
    if isinstance(default, bool):
        return value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise CustomizeError(f"template parameter '{name}' must be a number, got {value!r}") from None
    lo, hi = _NUM_LIMITS.get(name, (1.0, max(BUILD_VOLUME_MM)))
    if not math.isfinite(v) or not lo <= v <= hi:
        raise CustomizeError(f"template parameter '{name}' = {v:g} is outside {lo:g}..{hi:g} mm")
    return v


def _scad_literal(value) -> str:
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, bool):
        return "true" if value else "false"
    return _fmt(float(value))


def template_values(name: str, params: Optional[dict] = None) -> tuple[dict, list[str]]:
    """Validated defaults merged with ``params`` -> (values, ignored parameter names)."""
    if name not in TEMPLATES:
        raise CustomizeError(f"unknown template '{name}' (known: {', '.join(sorted(TEMPLATES))})")
    defaults = TEMPLATES[name]["params"]
    params = dict(params or {})
    ignored = sorted(k for k in params if k not in defaults)
    values = {k: _check_param(k, params[k] if params.get(k) is not None else d, d) for k, d in defaults.items()}
    if name == "name_tag" and params.get("font_size") is None:  # shrink long names so they fit the plate
        usable = values["width"] - 12.0
        n = max(1, len(values["text"]))
        values["font_size"] = round(max(3.0, min(values["font_size"], usable / (0.7 * n), values["height"] * 0.6)), 2)
    return values, ignored


def render_template(name: str, params: dict, out: Path) -> Path:
    """Render an OpenSCAD template to STL/3MF (needs the ``openscad`` binary)."""
    values, _ = template_values(name, params)
    exe = shutil.which("openscad")
    if not exe:
        raise CustomizeError("OpenSCAD is not installed, so templates cannot be rendered "
                             "(install it, e.g. 'sudo apt install openscad', or scale an existing model)")
    scad = TEMPLATE_DIR / TEMPLATES[name]["file"]
    if not scad.is_file():
        raise CustomizeError(f"template file {scad.name} is missing")
    out = Path(out)
    if out.suffix.lower() not in (".stl", ".3mf"):
        out = out.with_suffix(".stl")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-o", str(out)]
    for k, v in values.items():
        cmd += ["-D", f"{k}={_scad_literal(v)}"]
    cmd.append(str(scad))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
                              env=openscad_env())
    except subprocess.TimeoutExpired:
        raise CustomizeError("OpenSCAD took longer than 5 minutes") from None
    except OSError as e:
        raise CustomizeError(f"cannot run OpenSCAD: {e}") from None
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        lines = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()]
        detail = next((ln for ln in reversed(lines) if "ERROR" in ln.upper()), lines[-1] if lines else "")
        raise CustomizeError(f"OpenSCAD failed for '{name}': {detail[:200] or f'exit {proc.returncode}'}")
    return out


__all__ = ["TEMPLATES", "BUILD_VOLUME_MM", "CustomizeError", "scale_model", "model_bbox", "model_bounds",
           "openscad_available", "openscad_env", "render_template", "template_values", "factor_for_size",
           "mechanism_words", "fits_build_volume", "check_factor"]
