"""AI modelling: the agent writes parametric OpenSCAD, renders it to STL with preview images, looks at them,
iterates in versions and hands a version to the upload -> slice -> queue flow (``home3d_design``).

Files live under ``designs_dir()`` (``<data dir>/designs``), one folder per design slug::

    <slug>/<slug>_vN.scad   the source of version N (never overwritten: N = highest existing + 1)
    <slug>/<slug>_vN.stl    the rendered model (only when the render worked)
    <slug>/<slug>_vN_<view>.png   preview images (iso, top, front, side, plan, bottom)
    <slug>/<slug>_vN.json   facts: ok / error, size, volume, warnings, echo, params, previews

OpenSCAD has no shell and no network: the only way out of the design folder is a file name. Two guards:

- ``check_source`` (before the render) refuses ``include``/``use``/``import``/``surface``/extrude file paths that
  are absolute, go up (``..``) or leave the folder, and file names that are not one plain string literal. It reads
  the source the way OpenSCAD's lexer does (``include <...>`` paths first, then strings and comments).
- the render itself: OpenSCAD writes every file it read to a ``-d`` dependency list. A file outside the design
  folder (and OpenSCAD's own library folders) fails the version closed: no STL, no previews, no echo. This also
  covers file names that arrive through a ``-D`` parameter, which no static check can see.

Parameters go in only as ``-D name=value`` (checked names, quoted values). The render runs in its own process
group with a wall-clock limit (the whole group is stopped) and, on POSIX, a 4 GiB address-space limit, a CPU-time
limit (so an orphaned OpenSCAD still stops) and a file-size limit; one render runs at a time per process. The STL
is binary (``--export-format binstl``) and capped in size and triangles.

Stdlib only. Previews need an OpenGL context: without ``DISPLAY`` on Linux they are rendered under
``xvfb-run``; a preview that fails is a warning, never an error.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from . import customize
from .config import data_dir

try:  # POSIX only
    import resource as _resource
except ImportError:  # pragma: no cover - Windows
    _resource = None  # type: ignore[assignment]

MAX_SOURCE_BYTES = 200_000
MAX_PARAMS = 64
MAX_PARAM_STR = 200
MAX_PARAM_LIST = 16
DEFAULT_TIMEOUT_S = 180
MAX_TIMEOUT_S = 600
PREVIEW_TIMEOUT_S = 90
PREVIEW_MIN_TIMEOUT_S = 15  # a small timeout_s for a quick render must not starve the previews
MEM_LIMIT_BYTES = 4 << 30  # RLIMIT_AS for the render (CGAL can eat all memory on a bad minkowski)
CPU_GRACE_S = 5  # RLIMIT_CPU = time limit + this: the kernel stops an OpenSCAD whose parent died
MAX_STL_BYTES = 120 << 20  # RLIMIT_FSIZE for the render; a binary STL this big has about 2.5 M triangles
MAX_TRIANGLES = 2_000_000  # more is never needed for a household part (lower $fn)
MAX_BODY_COUNT_TRIANGLES = 600_000  # counting bodies needs a vertex map: skip it above this
PLA_DENSITY_G_CM3 = 1.24
MAX_ECHO = 20
MAX_WARNINGS = 20
SLUG_MAX = 40
DEFAULT_VIEWS = ("iso", "top")
PREVIEW_COLOUR = "SteelBlue"
# top/front/side are flat-lit orthographic views: good for outlines and gaps, blind to relief (text, pockets,
# compartments). plan is the top tilted 25 degrees (relief shows), bottom looks at the bed face from below.
VIEW_ARGS: dict[str, list[str]] = {
    "iso": ["--camera=0,0,0,55,0,25,0"],
    "top": ["--projection=o", "--camera=0,0,0,0,0,0,0"],
    "front": ["--projection=o", "--camera=0,0,0,90,0,0,0"],
    "side": ["--projection=o", "--camera=0,0,0,90,0,90,0"],
    "plan": ["--projection=o", "--camera=0,0,0,25,0,0,0"],
    "bottom": ["--camera=0,0,0,235,0,-30,0"],
}
COMMON_VIEW_ARGS = ["--autocenter", "--viewall", "--imgsize=900,700"]
XVFB_SCREEN = "-screen 0 1280x1024x24"
INSTALL_HINT = "install openscad (and xvfb for previews), e.g. 'sudo apt install openscad xvfb'"

PARAM_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PART_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

# ç ğ ı İ ö ş ü (and capitals) -> c g i i o s u; other accents fall to NFKD below
_TR = str.maketrans({"ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i", "ö": "o", "Ö": "o",
                     "ş": "s", "Ş": "s", "ü": "u", "Ü": "u"})

_render_lock = threading.Lock()
_meta_lock = threading.Lock()
_version_cache: dict[str, str] = {}
_display_broken = False  # DISPLAY was set but dead once: previews go through xvfb-run from then on

# warnings that mean OpenSCAD skipped part of the code: the render is "ok" but a piece of the model is missing
SUSPECT_WARNING_RE = re.compile(r"Ignoring unknown (variable|module|function)|Unable to convert|"
                                r"Mixing 2D and 3D|Ignoring [23]D child|undefined operation", re.I)


class DesignError(customize.CustomizeError):
    """A refusal or failure the agent can act on. ``code``: no_openscad | bad_args | refused | not_found | busy."""

    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code = code
        self.extra = extra


@dataclass
class DesignResult:
    ok: bool
    name: str
    version: int
    error: str = ""
    code: str = ""
    error_line: Optional[int] = None
    size_mm: Optional[list[float]] = None
    min_z_mm: Optional[float] = None
    volume_cm3: Optional[float] = None
    est_grams_max: Optional[float] = None
    triangles: int = 0
    simple: Optional[bool] = None
    bodies: Optional[int] = None
    inverted: Optional[bool] = None
    fits_build_volume: Optional[bool] = None
    warnings: list[str] = field(default_factory=list)
    suspect: list[str] = field(default_factory=list)
    echo: list[str] = field(default_factory=list)
    asserts_failed: list[str] = field(default_factory=list)
    previews: list[str] = field(default_factory=list)
    views: list[str] = field(default_factory=list)
    scad_path: str = ""
    stl_path: str = ""
    render_s: float = 0.0
    params: dict = field(default_factory=dict)
    part: str = ""
    from_version: Optional[int] = None
    request_id: Optional[int] = None
    openscad_version: str = ""
    created: float = 0.0

    @property
    def media(self) -> list[str]:
        return [f"MEDIA:{p}" for p in self.previews]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["media"] = self.media
        return d


# ---- names and folders -----------------------------------------------------------------------------
def designs_dir() -> Path:
    return data_dir() / "designs"


def slugify(name: Any) -> str:
    """Folder-safe name: Turkish letters transliterated, lower-case ``[a-z0-9-]``, at most 40 chars, never empty."""
    s = str(name or "").translate(_TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:SLUG_MAX].strip("-") or "design"


def _folder(slug: str) -> Path:
    return designs_dir() / slug


def _scad_name(slug: str, version: int) -> str:
    return f"{slug}_v{version}.scad"


def versions(slug: str) -> list[int]:
    """Version numbers of a design (ascending), from its ``<slug>_vN.scad`` files."""
    folder = _folder(slug)
    if not folder.is_dir():
        return []
    pat = re.compile(rf"^{re.escape(slug)}_v(\d+)\.scad$")
    out = []
    for p in folder.iterdir():
        m = pat.match(p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def _claim_version(folder: Path, slug: str, source: str) -> tuple[int, Path]:
    """Write the source as the next free version (exclusive create: two processes never share a number)."""
    folder.mkdir(parents=True, exist_ok=True)
    have = versions(slug)
    n = (have[-1] if have else 0) + 1
    for _ in range(1000):
        path = folder / _scad_name(slug, n)
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(source)
            return n, path
        except FileExistsError:
            n += 1
    raise DesignError("busy", f"could not claim a new version of '{slug}'")


def _meta_path(slug: str, version: int) -> Path:
    return _folder(slug) / f"{slug}_v{version}.json"


def _read_meta(slug: str, version: int) -> dict:
    try:
        data = json.loads(_meta_path(slug, version).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_meta(slug: str, version: int, meta: dict) -> None:
    path = _meta_path(slug, version)
    # a temp name of its own per process and thread: two writers never mix their bytes in one file
    tmp = path.with_name(f"{path.name}.part.{os.getpid()}.{threading.get_ident()}")
    try:
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


class _MetaLock:
    """Read-modify-write of one design's meta: a lock in this process plus ``flock`` on ``.<slug>.lock`` (POSIX),
    so the gateway and a CLI run never lose each other's library ids."""

    def __init__(self, slug: str):
        self.path = _folder(slug) / f".{slug}.lock"
        self.fh = None

    def __enter__(self):
        _meta_lock.acquire()
        try:
            import fcntl  # POSIX only
        except ImportError:  # pragma: no cover - Windows
            return self
        try:
            self.fh = open(self.path, "a")
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            if self.fh is not None:
                self.fh.close()
            self.fh = None
        return self

    def __exit__(self, *exc):
        try:
            if self.fh is not None:
                self.fh.close()  # closing drops the flock
        finally:
            _meta_lock.release()
        return False


# ---- OpenSCAD discovery ------------------------------------------------------------------------------
def _openscad_exe() -> Optional[str]:
    exe = shutil.which("openscad")
    if exe:
        return exe
    if sys.platform == "darwin":
        mac = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
        if os.access(mac, os.X_OK):
            return mac
    return None


def _xvfb_exe() -> Optional[str]:
    return shutil.which("xvfb-run")


def _needs_xvfb() -> bool:
    """Linux/BSD without an X display: OpenSCAD's offscreen OpenGL needs one (it segfaults without)."""
    return not sys.platform.startswith(("darwin", "win")) and not os.environ.get("DISPLAY")


def _openscad_version(exe: str) -> str:
    if exe in _version_cache:
        return _version_cache[exe]
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20, errors="replace",
                           stdin=subprocess.DEVNULL)
        m = re.search(r"version\s+(\S+)", (p.stderr or "") + "\n" + (p.stdout or ""), re.I)
        v = m.group(1) if m else ""
    except (OSError, subprocess.SubprocessError):
        v = ""
    _version_cache[exe] = v
    return v


def openscad_status() -> dict:
    """``{"openscad": path|None, "version": str, "xvfb": path|None, "previews": bool}``."""
    exe = _openscad_exe()
    xvfb = _xvfb_exe()
    return {"openscad": exe, "version": _openscad_version(exe) if exe else "", "xvfb": xvfb,
            "previews": bool(exe) and (not _needs_xvfb() or bool(xvfb))}


# ---- source and parameter checks -------------------------------------------------------------------------
# One left-to-right pass like OpenSCAD's lexer in its INITIAL state: an ``include <...>`` / ``use <...>`` path is
# raw text (a '"' or '/*' in it is an ordinary character), then string literals (they may span lines: the lexer
# drops the newline), then comments. Matching them in one pass keeps a path from opening a fake string or comment
# that would hide the code after it. OpenSCAD also takes `include` right after a number or a '.' ("x=3include
# <f>"), so only a letter, '_' or '$' before it (an identifier that goes on) rules it out; any path with a '"', '*',
# a line break or other odd character is refused, so reading a bit too much as a path never hides code.
_LEX_RE = re.compile(r'(?P<inc>(?<![A-Za-z_$])(?P<kw>include|use)[ \t\r\n>]*<(?P<path>[^>]*)(?P<close>>)?)'
                     r'|(?P<str>"(?:[^"\\]|\\.)*")'
                     r'|(?P<com>//[^\n]*|/\*.*?\*/)', re.S)
_SAFE_PATH_RE = re.compile(r"^[\w./ +-]+$")
# built-ins that take a file as their FIRST positional argument (or as file= / the old filename=)
_FILE_FUNCS = ("import", "import_stl", "import_off", "import_dxf", "surface", "dxf_dim", "dxf_cross")
# extrusions that also read a DXF given as a positional string (any position: OpenSCAD fills `file` with it)
_EXTRUDE_FUNCS = ("linear_extrude", "rotate_extrude", "dxf_linear_extrude", "dxf_rotate_extrude")
_CALL_RE = re.compile(r"\b(" + "|".join(_FILE_FUNCS + _EXTRUDE_FUNCS) + r")\s*\(")
_NAMED_FILE_RE = re.compile(r"[(,]\s*(file|filename)\s*=(?!=)\s*")
_NAMED_ARG_RE = re.compile(r"^\$?[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")
_ONE_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"\s*(?=[,)])', re.S)


def _lex(text: str) -> tuple[str, str, list[tuple[str, str, int, bool]]]:
    """(code, masked, includes). ``code``: comments blanked (newlines kept, so line numbers stay right), strings
    and include paths kept. ``masked``: the same with string contents and include paths blanked too (same length),
    for searching calls. ``includes``: (keyword, raw path, offset, closed) for every include/use."""
    code: list[str] = []
    masked: list[str] = []
    includes: list[tuple[str, str, int, bool]] = []
    pos = 0
    for m in _LEX_RE.finditer(text):
        code.append(text[pos:m.start()])
        masked.append(text[pos:m.start()])
        tok = m.group(0)
        if m.group("inc"):
            includes.append((m.group("kw"), m.group("path"), m.start(), bool(m.group("close"))))
            code.append(tok)
            p0, p1 = m.start("path") - m.start(), m.end("path") - m.start()
            masked.append(tok[:p0] + re.sub(r"[^\n]", "_", tok[p0:p1]) + tok[p1:])
        elif m.group("str"):
            code.append(tok)
            masked.append('"' + re.sub(r"[^\n]", "_", tok[1:-1]) + '"')
        else:
            blank = re.sub(r"[^\n]", " ", tok)
            code.append(blank)
            masked.append(blank)
        pos = m.end()
    code.append(text[pos:])
    masked.append(text[pos:])
    return "".join(code), "".join(masked), includes


def _strip_comments(text: str) -> str:
    """Comments become spaces (newlines kept, so line numbers stay right); string literals stay."""
    return _lex(text)[0]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _path_problem(path: str, folder: Optional[Path]) -> str:
    p = path.strip()
    if not p:
        return "an empty file name"
    if "\\" in p:
        return f"'{p}': backslashes are not allowed in file names"
    if re.search(r"[\x00-\x1f\x7f]", p):
        return f"{p!r}: line breaks and control characters are not allowed in file names"
    if p.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", p):
        return f"'{p}' must be relative to the design folder (no '/', '~' or drive at the start)"
    if any(part == ".." for part in p.split("/")):
        return f"'{p}' must not go up with '..'"
    if not _SAFE_PATH_RE.match(p):
        return f"'{p}': only letters, digits, space, '.', '_', '-', '+' and '/' are allowed in file names"
    if folder is not None:
        base = folder.resolve()
        try:
            (base / p).resolve().relative_to(base)
        except ValueError:
            return f"'{p}' leaves the design folder"
        except OSError as e:
            return f"'{p}' cannot be checked: {e}"
    return ""


def _call_args(masked: str, open_pos: int) -> list[tuple[int, int]]:
    """(start, end) of each top-level argument of the call whose '(' is at ``open_pos`` (in ``masked``, where
    strings hold no brackets or commas). An unclosed call runs to the end of the text."""
    out: list[tuple[int, int]] = []
    depth = 0
    start = open_pos + 1
    for i in range(open_pos + 1, len(masked)):
        ch = masked[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                if masked[start:i].strip():
                    out.append((start, i))
                return out
            depth -= 1
        elif ch == "," and depth == 0:
            out.append((start, i))
            start = i + 1
    if masked[start:].strip():
        out.append((start, len(masked)))
    return out


def check_source(text: str, folder: Optional[Path] = None) -> list[str]:
    """Problems that stop a render (empty list = fine). ``folder`` is the design folder paths must stay in.

    Static and early: the render's dependency list (``-d``) is the guard that cannot be fooled by the lexer or by
    a file name that arrives in a ``-D`` parameter."""
    if not isinstance(text, str):
        return ["the OpenSCAD source must be text"]
    problems: list[str] = []
    size = len(text.encode("utf-8"))
    if size > MAX_SOURCE_BYTES:
        problems.append(f"the source is {size} bytes, more than {MAX_SOURCE_BYTES}: split it or simplify")
    if "\x00" in text:
        problems.append("the source contains a NUL character")
    if not text.strip():
        problems.append("the source is empty")
    code, masked, includes = _lex(text)
    for kw, path, pos, closed in includes:
        line = _line_of(code, pos)
        if not closed:
            problems.append(f"line {line}: {kw} <...> is not closed with '>'")
            continue
        why = _path_problem(path, folder)
        if why:
            problems.append(f"line {line}: {kw} <{path.strip()}>: {why}")

    def literal_file(pos: int, what: str, line: int) -> None:
        """The argument at ``pos`` must be exactly one string literal (then ',' or ')'): no expression after it."""
        s = _ONE_LITERAL_RE.match(code, pos)
        if not s:
            problems.append(f"line {line}: {what} needs one plain string literal file name (a file in the design "
                            "folder), not a variable or an expression")
            return
        why = _path_problem(s.group(1), folder)
        if why:
            problems.append(f"line {line}: {what} \"{s.group(1)}\": {why}")

    for m in _NAMED_FILE_RE.finditer(masked):
        literal_file(m.end(), f"{m.group(1)}=", _line_of(code, m.start()))
    for m in _CALL_RE.finditer(masked):
        func = m.group(1)
        line = _line_of(code, m.start())
        args = _call_args(masked, m.end() - 1)
        positional = [(a, b) for a, b in args if not _NAMED_ARG_RE.match(masked[a:b].strip())]
        if func in _FILE_FUNCS:
            if not args:
                continue  # an empty call
            if not positional:
                continue  # only named arguments: file= / filename= are checked above
            a, b = positional[0]
            a += len(masked[a:b]) - len(masked[a:b].lstrip())
            literal_file(a, f"{func}()", line)
            continue
        for a, b in positional:  # extrusions: a positional string is a DXF file name
            if '"' not in masked[a:b]:
                continue  # a number or a variable (the dependency list checks what it holds)
            a += len(masked[a:b]) - len(masked[a:b].lstrip())
            literal_file(a, f"{func}()", line)
    return problems


def _scad_value(name: str, value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        try:
            f = float(value)
        except (OverflowError, ValueError):
            raise DesignError("bad_args", f"param '{name}' must be a finite number") from None
        if not math.isfinite(f):
            raise DesignError("bad_args", f"param '{name}' must be a finite number")
        return customize._fmt(f)
    if isinstance(value, str):
        if len(value) > MAX_PARAM_STR:
            raise DesignError("bad_args", f"param '{name}' is longer than {MAX_PARAM_STR} characters")
        if re.search(r"[\x00-\x1f\x7f]", value):
            raise DesignError("bad_args", f"param '{name}' contains a control character (newline, tab, ...)")
        return customize._scad_literal(value)
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_PARAM_LIST or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                   for v in value):
            raise DesignError("bad_args", f"param '{name}': a list may hold at most {MAX_PARAM_LIST} numbers")
        return "[" + ", ".join(_scad_value(name, v) for v in value) + "]"
    raise DesignError("bad_args", f"param '{name}' must be a number, true/false, a short string or a list of "
                                  f"numbers, got {type(value).__name__}")


def check_params(params: Optional[dict]) -> list[str]:
    """``-D`` arguments for ``params`` (``["-D", "width=80", ...]``); raises ``DesignError`` on a bad one."""
    if params is None:
        return []
    if not isinstance(params, dict):
        raise DesignError("bad_args", "'params' must be an object of name: value")
    if len(params) > MAX_PARAMS:
        raise DesignError("bad_args", f"at most {MAX_PARAMS} params")
    out: list[str] = []
    for name, value in params.items():
        if not isinstance(name, str) or not PARAM_NAME_RE.match(name):
            raise DesignError("bad_args", f"param name {name!r} is not an OpenSCAD variable name")
        out += ["-D", f"{name}={_scad_value(name, value)}"]
    return out


# ---- OpenSCAD log -------------------------------------------------------------------------------------
_LINE_NO_RE = re.compile(r"\bline\s+(\d+)")


def _unquote_echo(msg: str) -> str:
    """``"FOOTPRINT: 88 x 85 mm"`` (one string, the usual ``echo(str(...))``) -> without its quotes. Several values
    (``"w", 5`` or ``"a", "b"``) stay as OpenSCAD printed them."""
    if len(msg) >= 2 and msg[0] == '"' and msg[-1] == '"' and '", ' not in msg[1:-1]:
        return msg[1:-1]
    return msg


def parse_log(text: str, folder: Optional[Path] = None) -> dict:
    """Errors, warnings, echo, failed asserts and the CGAL facts from OpenSCAD's stderr."""
    if folder is not None:  # messages name files relative to the design folder
        for base in {str(folder) + os.sep, str(folder.resolve()) + os.sep}:
            text = text.replace(base, "")
    errors: list[str] = []
    warnings: list[str] = []
    echo: list[str] = []
    asserts: list[str] = []
    simple: Optional[bool] = None
    volumes: Optional[int] = None
    empty = not_3d = out_of_memory = False
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if ln.startswith("ECHO:"):
            echo.append(_unquote_echo(ln[5:].strip()))
        elif ln.startswith("ERROR:"):
            msg = ln[6:].strip()
            errors.append(msg)
            if msg.startswith("Assertion") and "failed" in msg:
                asserts.append(msg)
        elif ln.startswith(("WARNING:", "EXPORT-WARNING:", "DEPRECATED:")):
            msg = ln.split(":", 1)[1].strip()
            if msg and msg not in warnings:
                warnings.append(msg)
        elif ln.startswith("Simple:"):
            simple = ln.split(":", 1)[1].strip().lower().startswith("yes")
        elif ln.startswith("Volumes:"):
            try:
                volumes = int(ln.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif "top level object is empty" in ln:
            empty = True
        elif "not a 3D object" in ln:
            not_3d = True
        if "bad_alloc" in ln or "Cannot allocate memory" in ln:
            out_of_memory = True
    m = _LINE_NO_RE.search(errors[0]) if errors else None
    return {"errors": errors, "error_line": int(m.group(1)) if m else None, "warnings": warnings[:MAX_WARNINGS],
            "echo": echo[:MAX_ECHO], "echo_total": len(echo), "asserts_failed": asserts, "simple": simple,
            "volumes": volumes, "empty": empty, "not_3d": not_3d, "out_of_memory": out_of_memory}


# ---- STL facts ------------------------------------------------------------------------------------------
def _triangles(data: bytes) -> Iterable[tuple[tuple[float, float, float], ...]]:
    if customize._stl_is_binary(data):
        n = min(struct.unpack_from("<I", data, 80)[0], (len(data) - 84) // 50)
        for t in struct.iter_unpack("<12fH", memoryview(data)[84:84 + 50 * n]):
            yield (t[3], t[4], t[5]), (t[6], t[7], t[8]), (t[9], t[10], t[11])
        return
    tri: list[tuple[float, float, float]] = []
    for m in customize._VERTEX_RE.finditer(data):
        try:
            tri.append((float(m.group(2)), float(m.group(4)), float(m.group(6))))
        except ValueError:
            raise customize.CustomizeError("ASCII STL has a malformed vertex line") from None
        if len(tri) == 3:
            yield tri[0], tri[1], tri[2]
            tri = []


def stl_facts(path: Path, *, count_bodies: bool = True) -> dict:
    """Size, lowest z, triangle count, enclosed volume (signed tetrahedra) and, when asked, the number of
    separate bodies (mesh pieces that share no vertex) of an ASCII or binary STL."""
    data = Path(path).read_bytes()
    acc: Optional[list[float]] = None
    vol6 = 0.0
    count = 0
    parent: dict = {}

    def find(k):
        root = k
        while parent[root] != root:
            root = parent[root]
        while parent[k] != root:
            parent[k], k = root, parent[k]
        return root

    for a, b, c in _triangles(data):
        count += 1
        for v in (a, b, c):
            acc = customize._grow(acc, *v)
        vol6 += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                 + a[2] * (b[0] * c[1] - b[1] * c[0]))
        if count_bodies:
            keys = [(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for v in (a, b, c)]
            for k in keys:
                parent.setdefault(k, k)
            r0 = find(keys[0])
            for k in keys[1:]:
                rk = find(k)
                if rk != r0:
                    parent[rk] = r0
    if acc is None:
        return {"triangles": 0, "size_mm": [0.0, 0.0, 0.0], "min_z_mm": None, "volume_cm3": 0.0, "bodies": 0,
                "inverted": False}
    bodies = len({find(k) for k in list(parent)}) if count_bodies else None
    return {"triangles": count,
            "size_mm": [round(acc[3 + i] - acc[i], 2) + 0.0 for i in range(3)],
            "min_z_mm": round(acc[2], 3) + 0.0,  # + 0.0: never "-0.0"
            "volume_cm3": round(abs(vol6) / 6.0 / 1000.0, 3),
            # a closed mesh whose faces wind the wrong way encloses a NEGATIVE volume (an inside-out polyhedron)
            "inverted": vol6 < -1e-9,
            "bodies": bodies}


def stl_triangle_count(path: Path) -> Optional[int]:
    """The triangle count from a binary STL header (None for ASCII or an unreadable file): cheap, before parsing."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(84)
        size = Path(path).stat().st_size
    except OSError:
        return None
    if len(head) < 84:
        return None
    n = struct.unpack_from("<I", head, 80)[0]
    return n if 84 + 50 * n == size else None


# ---- subprocess ------------------------------------------------------------------------------------------
def _limits(mem: Optional[int] = None, cpu_s: Optional[float] = None, fsize: Optional[int] = None):
    """preexec_fn: cap the child's address space, CPU seconds and file size (POSIX). Values are computed here, in
    the parent; the child only calls setrlimit (no imports, no locks). RLIMIT_CPU stops the child even when the
    parent dies mid-render (SIGXCPU) and nobody is left to enforce the wall-clock limit; RLIMIT_FSIZE stops a
    runaway STL (SIGXFSZ). Limits are inherited, so xvfb-run's Xvfb and OpenSCAD get them too."""
    if _resource is None:
        return None
    plan: list[tuple[int, int, int]] = []
    wanted = []
    if mem:
        wanted.append((_resource.RLIMIT_AS, int(mem), None))
    if cpu_s:
        soft = int(math.ceil(cpu_s))
        wanted.append((_resource.RLIMIT_CPU, soft, soft + CPU_GRACE_S))
    if fsize and hasattr(_resource, "RLIMIT_FSIZE"):
        wanted.append((_resource.RLIMIT_FSIZE, int(fsize), None))
    for which, soft, hard_want in wanted:
        try:
            _cur, hard = _resource.getrlimit(which)
        except (OSError, ValueError):
            continue
        inf = _resource.RLIM_INFINITY
        new_hard = hard if hard_want is None else (hard_want if hard == inf else min(hard_want, hard))
        new_soft = soft if new_hard == inf else min(soft, new_hard)
        plan.append((which, new_soft, new_hard))
    if not plan:
        return None
    setrlimit = _resource.setrlimit

    def fn() -> None:
        for which, soft, hard in plan:
            try:
                setrlimit(which, (soft, hard))
            except (OSError, ValueError):
                pass

    return fn


def _limit_memory(limit: int):
    """preexec_fn that only caps the address space (kept for callers of the round-4 API)."""
    return _limits(mem=limit)


def _signal_group(proc: subprocess.Popen, sig: int) -> bool:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, sig)  # start_new_session: the group id is the child's pid
            return True
        except (ProcessLookupError, PermissionError, OSError):
            return False
    return False


def _kill_group(proc: subprocess.Popen, grace_s: float = 2.0) -> None:
    """SIGTERM to the whole group first (Xvfb then removes its lock file and socket, xvfb-run its temp files), then
    SIGKILL for anything still there."""
    if os.name == "posix":
        if _signal_group(proc, signal.SIGTERM):
            deadline = time.monotonic() + grace_s
            while time.monotonic() < deadline:
                if proc.poll() is not None and not _signal_group(proc, 0):
                    return  # the child and everything in its group are gone
                time.sleep(0.05)
            if _signal_group(proc, signal.SIGKILL) or proc.poll() is not None:
                return
    try:
        proc.kill()
    except OSError:
        pass


def _child_env() -> dict:
    """The parent's environment without OPENSCADPATH: library lookups stay in OpenSCAD's own library folders."""
    env = dict(os.environ)
    env.pop("OPENSCADPATH", None)
    return env


def _run(cmd: list[str], cwd: Path, timeout: float, *, mem_limit: Optional[int] = None,
         cpu_limit_s: Optional[float] = None, fsize_limit: Optional[int] = None) -> dict:
    kwargs: dict = dict(cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, errors="replace", env=_child_env())
    if os.name == "posix":
        kwargs["start_new_session"] = True
        fn = _limits(mem=mem_limit, cpu_s=cpu_limit_s, fsize=fsize_limit)
        if fn is not None:
            kwargs["preexec_fn"] = fn
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as e:
        return {"rc": None, "out": "", "err": "", "timed_out": False, "seconds": 0.0, "os_error": str(e)}
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:  # something outside the group still holds the pipes
            out, err = "", ""
    except BaseException:  # Ctrl-C, SystemExit, ...: never leave OpenSCAD running on its own
        _kill_group(proc, grace_s=0.5)
        raise
    rc = proc.returncode
    if rc is not None and os.name == "posix" and rc in (-getattr(signal, "SIGXCPU", 24), 128 + 24):
        timed_out = True  # the CPU limit stopped it: the same thing as the wall-clock limit
    return {"rc": rc, "out": out or "", "err": err or "", "timed_out": timed_out,
            "seconds": round(time.monotonic() - t0, 2), "os_error": ""}


def _too_big(r: dict) -> bool:
    """The file-size limit stopped the child (SIGXFSZ), directly or under xvfb-run's shell."""
    rc = r.get("rc")
    return rc is not None and os.name == "posix" and rc in (-getattr(signal, "SIGXFSZ", 25), 128 + 25)


_X_DEAD_RE = re.compile(r"Unable to open a connection to the X server|cannot open display|"
                        r"could not connect to display", re.I)


def _preview_once(exe: str, folder: Path, wrapper: Path, png: Path, view: str, timeout: float,
                  use_xvfb: bool) -> dict:
    cmd = [exe, "-o", png.name, *VIEW_ARGS[view], *COMMON_VIEW_ARGS, wrapper.name]
    auth = None
    if use_xvfb:
        # -f: the X cookie goes to a file of ours (no mktemp folder left in /tmp when a preview is stopped)
        auth = folder / f".xauth_{os.getpid()}_{threading.get_ident()}"
        cmd = [_xvfb_exe() or "xvfb-run", "-a", "-f", str(auth), "-s", XVFB_SCREEN, *cmd]
    try:
        # llvmpipe may draw on several cores at once: a generous CPU limit, only there for an orphaned preview
        return _run(cmd, folder, timeout, cpu_limit_s=4 * timeout + 10, fsize_limit=MAX_STL_BYTES)
    finally:
        if auth is not None:
            for extra in ("", "-c", "-l", "-n"):
                Path(str(auth) + extra).unlink(missing_ok=True)


def _preview(exe: str, folder: Path, stl_name: str, png: Path, view: str, timeout: float) -> str:
    """Render one preview image from the STL (a tiny ``import()`` wrapper: no CGAL again). '' or a warning."""
    global _display_broken
    use_xvfb = _needs_xvfb() or _display_broken
    if use_xvfb and not _xvfb_exe():
        return "previews are off: no display and no xvfb-run (install xvfb)"
    wrapper = folder / f".preview_{os.getpid()}_{threading.get_ident()}_{view}.scad"
    wrapper.write_text(f'color("{PREVIEW_COLOUR}") import("{stl_name}");\n', encoding="utf-8")
    try:
        r = _preview_once(exe, folder, wrapper, png, view, timeout, use_xvfb)
        text = (r["err"] or "") + "\n" + (r["out"] or "")  # xvfb-run sends OpenSCAD's stderr to stdout
        if (not use_xvfb and r["rc"] not in (0, None) and _X_DEAD_RE.search(text) and _xvfb_exe()
                and not sys.platform.startswith(("darwin", "win"))):
            _display_broken = True  # a stale DISPLAY (the session that set it is gone): use xvfb-run from now on
            png.unlink(missing_ok=True)
            r = _preview_once(exe, folder, wrapper, png, view, timeout, True)
            text = (r["err"] or "") + "\n" + (r["out"] or "")
    finally:
        wrapper.unlink(missing_ok=True)
    if r["os_error"]:
        return f"preview {view} failed: {r['os_error']}"
    if r["timed_out"]:
        png.unlink(missing_ok=True)
        return f"preview {view} took longer than {timeout:g} s"
    if r["rc"] != 0 or not png.is_file() or png.stat().st_size == 0:
        png.unlink(missing_ok=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        detail = next((ln for ln in lines if "ERROR" in ln or "Can't" in ln or "Unable" in ln),
                      lines[-1] if lines else f"exit {r['rc']}")
        return f"preview {view} failed: {detail[:160]}"
    return ""


# ---- render -------------------------------------------------------------------------------------------
def _norm_views(views: Any) -> list[str]:
    if views is None:
        return list(DEFAULT_VIEWS)
    if isinstance(views, str):
        try:
            parsed = json.loads(views) if views.strip().startswith("[") else None
        except ValueError:
            parsed = None
        views = parsed if isinstance(parsed, list) else [v for v in re.split(r"[\s,\[\]\"']+", views) if v]
    if not isinstance(views, (list, tuple)):
        raise DesignError("bad_args", f"'views' must be a list of {', '.join(VIEW_ARGS)}")
    out: list[str] = []
    for v in views:
        key = str(v).strip().lower()
        if key not in VIEW_ARGS:
            raise DesignError("bad_args", f"unknown view {v!r} ({', '.join(VIEW_ARGS)})")
        if key not in out:
            out.append(key)
    return out


def _norm_timeout(timeout_s: Any) -> float:
    try:
        t = float(timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S)
    except (TypeError, ValueError):
        raise DesignError("bad_args", "'timeout_s' must be a number of seconds") from None
    if not math.isfinite(t):
        raise DesignError("bad_args", "'timeout_s' must be a number of seconds")
    return max(1.0, min(float(MAX_TIMEOUT_S), t))


def _failure_message(log: dict, r: dict, timeout: float) -> tuple[str, str]:
    """(code, error) for a render that produced no model."""
    if r["os_error"]:
        return "render_failed", f"cannot run OpenSCAD: {r['os_error']}"
    if r["timed_out"]:
        return "timeout", (f"OpenSCAD took longer than {int(timeout)} s and was stopped: simplify (lower $fn, hull "
                           "instead of minkowski, fewer boolean operations) or raise timeout_s (max 600)")
    if _too_big(r):
        return "too_big", (f"the model is too detailed: its STL passed {MAX_STL_BYTES >> 20} MB. Lower $fn "
                           "(48-64 is plenty), use fewer pieces")
    if log["out_of_memory"]:
        return "render_failed", f"OpenSCAD ran out of memory (limit {MEM_LIMIT_BYTES >> 30} GiB): simplify the model"
    if log["asserts_failed"]:
        return "assert_failed", log["asserts_failed"][0]
    if log["errors"]:
        return "render_failed", log["errors"][0]
    if log["not_3d"]:
        return "render_failed", "the result is 2D, not a 3D object: linear_extrude() or rotate_extrude() it"
    if log["empty"]:
        return "render_failed", "nothing to render: the top level object is empty (is the render call missing?)"
    lines = [ln.strip() for ln in (r["err"] or "").splitlines() if ln.strip()]
    if r["rc"] is not None and r["rc"] < 0:
        return "render_failed", f"OpenSCAD crashed (signal {-r['rc']})"
    return "render_failed", (lines[-1][:200] if lines else f"OpenSCAD exited with {r['rc']}")


def _library_dirs(exe: str) -> list[Path]:
    """OpenSCAD's own library folders (``use <MCAD/units.scad>``): the only files outside the design folder a
    design may read. OPENSCADPATH is not passed to the child, so other folders are never searched."""
    cands: list[Path] = []
    try:
        real = Path(exe).resolve()
        cands += [real.parent.parent / "share" / "openscad" / "libraries",  # /usr/bin -> /usr/share/openscad
                  real.parent.parent / "Resources" / "libraries"]  # macOS: OpenSCAD.app/Contents/Resources
    except (OSError, RuntimeError):
        pass
    cands += [Path("/usr/share/openscad/libraries"), Path("/usr/local/share/openscad/libraries")]
    try:
        home = Path.home()
        cands.append(Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / "OpenSCAD" / "libraries")
        cands.append(home / "Documents" / "OpenSCAD" / "libraries")
    except (OSError, RuntimeError, KeyError):
        pass
    out: list[Path] = []
    for c in cands:
        try:
            r = c.resolve()
        except (OSError, RuntimeError):
            continue
        if r not in out and r != Path(r.anchor):
            out.append(r)
    return out


def parse_deps(text: str) -> list[str]:
    """File names from OpenSCAD's ``-d`` output (make syntax: ``target: \\`` then one name per line; ``\\ `` is
    a space inside a name, a trailing ``\\`` continues the line)."""
    body = text.split(":", 1)[1] if ":" in text else ""
    out: list[str] = []
    cur: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else ""
        if ch == "\\" and nxt in ("\n", "\r"):
            i += 2
            if cur:
                out.append("".join(cur))
                cur = []
            continue
        if ch == "\\" and nxt in (" ", "\t"):
            cur.append(nxt)
            i += 2
            continue
        if ch in " \t\r\n":
            if cur:
                out.append("".join(cur))
                cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if cur:
        out.append("".join(cur))
    return out


def _outside_files(deps: list[str], folder: Path, libs: list[Path]) -> list[str]:
    """The dependencies that are neither in the design folder nor in an OpenSCAD library folder."""
    base = folder.resolve()
    bad: list[str] = []
    for d in deps:
        try:
            real = (base / d).resolve()  # a relative name is relative to the folder (OpenSCAD ran there)
        except (OSError, RuntimeError):
            bad.append(d)
            continue
        if any(real == root or root in real.parents for root in [base, *libs]):
            continue
        bad.append(d)
    return bad


def load_version(slug: str, version: Optional[int] = None) -> dict:
    """Source + facts of one version (latest when ``version`` is None). Raises ``DesignError('not_found')``."""
    slug = slugify(slug)
    have = versions(slug)
    if not have:
        raise DesignError("not_found", f"no design named '{slug}' (home3d_design action=list shows them)")
    v = have[-1] if version is None else int(version)
    if v not in have:
        raise DesignError("not_found", f"'{slug}' has no version {v} (versions: {', '.join(map(str, have))})")
    folder = _folder(slug)
    scad = folder / _scad_name(slug, v)
    try:
        source = scad.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise DesignError("not_found", f"cannot read {scad.name}: {e.strerror or e}") from None
    meta = _read_meta(slug, v)
    stl = folder / f"{slug}_v{v}.stl"
    previews = [str(p) for p in (folder / f"{slug}_v{v}_{view}.png" for view in VIEW_ARGS) if p.is_file()]
    return {"name": slug, "version": v, "versions": have, "source": source, "meta": meta,
            "scad_path": str(scad.resolve()), "stl_path": str(stl.resolve()) if stl.is_file() else "",
            "previews": [str(Path(p).resolve()) for p in previews]}


def ok_versions(slug: str) -> list[dict]:
    """Every version that rendered to an STL (ascending): version, part, size_mm, suspect."""
    slug = slugify(slug)
    folder = _folder(slug)
    out = []
    for v in versions(slug):
        meta = _read_meta(slug, v)
        if meta.get("ok") and (folder / f"{slug}_v{v}.stl").is_file():
            out.append({"version": v, "part": meta.get("part") or "", "size_mm": meta.get("size_mm"),
                        "suspect": bool(meta.get("suspect"))})
    return out


def latest_ok_version(slug: str) -> Optional[int]:
    """The newest version that rendered to an STL."""
    slug = slugify(slug)
    folder = _folder(slug)
    for v in reversed(versions(slug)):
        if _read_meta(slug, v).get("ok") and (folder / f"{slug}_v{v}.stl").is_file():
            return v
    return None


def render(name: str, scad: Optional[str] = None, *, from_version: Optional[int] = None,
           params: Optional[dict] = None, views: Any = DEFAULT_VIEWS, part: Optional[str] = None,
           timeout_s: Any = DEFAULT_TIMEOUT_S, request_id: Optional[int] = None) -> DesignResult:
    """Write a new version of design ``name`` and render it to STL + previews.

    ``scad`` is the full source; without it, ``from_version``'s source is copied and its params / part are kept
    (``params`` are merged over them, a ``None`` value drops one; ``part=""`` drops the part). ``part`` is
    passed as ``-D part="<value>"``. A refused source or bad argument raises ``DesignError`` and writes nothing;
    a failed render is a version too (``ok=False``, its source kept for the next try)."""
    status = openscad_status()
    exe = status["openscad"]
    if not exe:
        raise DesignError("no_openscad", f"OpenSCAD is not installed, so the agent cannot design parts: {INSTALL_HINT}")
    slug = slugify(name)
    folder = _folder(slug)
    view_list = _norm_views(views)
    timeout = _norm_timeout(timeout_s)

    merged: dict = {}
    inherited_part = ""
    if scad is not None and not isinstance(scad, str):
        raise DesignError("bad_args", "'scad' must be the OpenSCAD source as text")
    if scad is not None and scad.strip():
        source = scad
    elif from_version is not None:
        src = load_version(slug, int(from_version))
        source = src["source"]
        merged = dict(src["meta"].get("params") or {})
        inherited_part = str(src["meta"].get("part") or "")
    else:
        raise DesignError("bad_args", "give 'scad' (the full OpenSCAD source) or 'from_version' (re-render that "
                                      "version with new params)")
    if params is not None and not isinstance(params, dict):
        raise DesignError("bad_args", "'params' must be an object of name: value")
    kept_part_note = ""
    for k, v in (params or {}).items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    defines = check_params(merged)
    the_part = inherited_part if part is None else str(part).strip()
    if part is None and inherited_part:
        kept_part_note = (f"part '{inherited_part}' kept from v{int(from_version)} (from_version keeps the part; "
                          "part=\"\" renders the whole design)")
    if the_part:
        if not PART_RE.match(the_part):
            raise DesignError("bad_args", "'part' must be a short name like lid or body ([A-Za-z0-9_-], 40 chars)")
        if "part" in merged:
            raise DesignError("bad_args", "give the part either as 'part' or as params.part, not both")
        defines += ["-D", f"part={customize._scad_literal(the_part)}"]
    problems = check_source(source, folder)
    if problems:
        raise DesignError("refused", "the OpenSCAD source was refused: " + "; ".join(problems[:5]),
                          problems=problems)

    if not _render_lock.acquire(timeout=timeout):
        raise DesignError("busy", "another design is rendering right now: try again in a minute")
    try:
        version, scad_path = _claim_version(folder, slug, source)
        stl = folder / f"{slug}_v{version}.stl"
        deps = folder / f".{slug}_v{version}.deps"
        res = DesignResult(ok=False, name=slug, version=version, scad_path=str(scad_path.resolve()),
                           params=merged, part=the_part,
                           from_version=int(from_version) if from_version is not None else None,
                           request_id=request_id, openscad_version=status["version"], created=time.time())
        cmd = [exe, "-o", stl.name, "--export-format", "binstl", "-d", deps.name, *defines, scad_path.name]
        try:
            r = _run(cmd, folder, timeout, mem_limit=MEM_LIMIT_BYTES, cpu_limit_s=timeout + CPU_GRACE_S,
                     fsize_limit=MAX_STL_BYTES)
            dep_names: Optional[list[str]] = None
            try:
                dep_names = parse_deps(deps.read_text(encoding="utf-8", errors="surrogateescape"))
            except OSError:
                pass
        finally:
            deps.unlink(missing_ok=True)
        produced = r["rc"] == 0 and not r["timed_out"] and stl.is_file() and stl.stat().st_size > 0
        outside = _outside_files(dep_names, folder, _library_dirs(exe)) if dep_names is not None else []
        if outside or (produced and dep_names is None):
            # fail closed: nothing of what OpenSCAD read (geometry, echo, warnings, errors) leaves this function
            stl.unlink(missing_ok=True)
            res.code = "refused"
            res.error = ("the design read files outside its folder: " + ", ".join(outside[:3])
                         + ". Only files in the design folder (and OpenSCAD's own libraries) may be used"
                         if outside else "OpenSCAD did not list the files it read, so the result is not used")
            res.render_s = r["seconds"]
            _save_meta(res)
            return res
        log = parse_log(r["err"] + "\n" + r["out"], folder)
        res.render_s = r["seconds"]
        res.warnings = list(log["warnings"])
        res.echo = list(log["echo"])
        if log["echo_total"] > MAX_ECHO:
            res.warnings.append(f"{log['echo_total'] - MAX_ECHO} more echo lines were cut")
        if kept_part_note:
            res.warnings.insert(0, kept_part_note)
        res.asserts_failed = list(log["asserts_failed"])
        res.simple = log["simple"]
        res.suspect = [w for w in log["warnings"] if SUSPECT_WARNING_RE.search(w)]
        facts = None
        if produced:
            tris = stl_triangle_count(stl)
            if stl.stat().st_size > MAX_STL_BYTES or (tris is not None and tris > MAX_TRIANGLES):
                res.code, res.error = "too_big", (
                    f"the model is too detailed ({tris or 'too many'} triangles, at most {MAX_TRIANGLES}): lower "
                    "$fn (48-64 is plenty) or use fewer pieces")
            else:
                try:
                    facts = stl_facts(stl, count_bodies=log["volumes"] is None
                                      and (tris is None or tris <= MAX_BODY_COUNT_TRIANGLES))
                except MemoryError:
                    res.code, res.error = "too_big", "the STL is too big to measure: lower $fn or use fewer pieces"
                except (OSError, customize.CustomizeError, struct.error) as e:
                    res.code, res.error = "render_failed", f"the STL could not be read: {e}"
                else:
                    if not facts["triangles"]:
                        res.code, res.error = "render_failed", "the STL has no triangles (empty model)"
                        facts = None
        else:
            res.code, res.error = _failure_message(log, r, timeout)
            res.error_line = log["error_line"]
        if facts is None:
            stl.unlink(missing_ok=True)
        else:
            res.ok = True
            res.stl_path = str(stl.resolve())
            res.triangles = facts["triangles"]
            res.size_mm = facts["size_mm"]
            res.min_z_mm = facts["min_z_mm"]
            res.volume_cm3 = facts["volume_cm3"]
            res.inverted = bool(facts.get("inverted"))
            res.est_grams_max = round(facts["volume_cm3"] * PLA_DENSITY_G_CM3, 1)
            res.bodies = (log["volumes"] - 1) if log["volumes"] is not None else facts["bodies"]
            res.fits_build_volume = customize.fits_build_volume(res.size_mm)
            _fact_warnings(res)
            if view_list:
                if not status["previews"]:
                    res.warnings.append("previews are off: no display and no xvfb-run (install xvfb)")
                else:
                    limit = max(PREVIEW_MIN_TIMEOUT_S, min(timeout, PREVIEW_TIMEOUT_S))
                    for view in view_list:
                        png = folder / f"{slug}_v{version}_{view}.png"
                        warn = _preview(exe, folder, stl.name, png, view, limit)
                        if warn:
                            if warn not in res.warnings:
                                res.warnings.append(warn)
                            if warn.startswith("previews are off"):
                                break
                        else:
                            res.previews.append(str(png.resolve()))
                            res.views.append(view)
        _save_meta(res)
        return res
    finally:
        _render_lock.release()


def _save_meta(res: DesignResult) -> None:
    try:
        _write_meta(res.name, res.version, res.to_dict())
    except OSError as e:
        res.warnings.append(f"facts not saved: {e.strerror or e}")


def _fact_warnings(res: DesignResult) -> None:
    w = res.warnings
    if res.simple is False:
        w.append("not a clean solid (Simple: no): parts touch only at an edge or face. Overlap them by 0.01-0.1 mm, "
                 "or keep a layout_gap between separate parts")
    if res.bodies is not None and res.bodies > 1:
        w.append(f"{res.bodies} separate bodies: they print as separate parts (keep a gap of at least 1 mm between "
                 "them; check that nothing floats)")
    if res.fits_build_volume is False:
        bx, by, bz = customize.BUILD_VOLUME_MM
        w.append(f"bigger than the build volume {bx:g} x {by:g} x {bz:g} mm: scale down, split or lay it flat")
    if res.min_z_mm is not None and abs(res.min_z_mm) > 0.01:
        w.append(f"the lowest point is at z = {res.min_z_mm:g} mm, not 0: the slicer drops it onto the bed; make sure "
                 "the intended face is down")
    if res.volume_cm3 is not None and res.volume_cm3 <= 0.0:
        w.append("the enclosed volume is 0: the mesh may be open or inside out")
    elif res.inverted:
        w.append("the mesh is inside out (negative volume): reverse the point order of each ring or face of the "
                 "polyhedron, or union it with a small overlapping part so OpenSCAD checks it")
    if res.suspect:
        w.append("OpenSCAD ignored part of the code (see the warnings above: a typo, an unknown name or 2D mixed "
                 "with 3D): a piece of the model is missing. Fix it before you show or upload this version")


def record_upload(slug: str, version: int, library_file_id: int) -> None:
    """Remember in the version's facts which library file it was uploaded as (best effort, locked: two uploads of
    the same version at once keep both ids and a valid file)."""
    try:
        with _MetaLock(slug):
            meta = _read_meta(slug, version)
            if not meta:
                return
            ups = [int(x) for x in meta.get("library_file_ids") or [] if str(x).isdigit()]
            if int(library_file_id) not in ups:
                ups.append(int(library_file_id))
            meta["library_file_ids"] = ups
            _write_meta(slug, version, meta)
    except OSError:
        pass


def list_designs(limit: int = 20) -> list[dict]:
    """Designs, most recently changed first: name, versions, latest, latest that rendered, size, preview."""
    root = designs_dir()
    if not root.is_dir():
        return []
    rows = []
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        slug = folder.name
        have = versions(slug)
        if not have:
            continue
        latest = have[-1]
        ok_v = latest_ok_version(slug)
        try:
            mtime = max(p.stat().st_mtime for p in folder.iterdir())
        except (OSError, ValueError):
            mtime = 0.0
        meta = _read_meta(slug, ok_v) if ok_v is not None else {}
        prev = [p for p in meta.get("previews") or [] if Path(p).is_file()]
        rows.append({"name": slug, "versions": len(have), "latest": latest, "latest_ok": ok_v,
                     "latest_failed": not _read_meta(slug, latest).get("ok"),
                     "size_mm": meta.get("size_mm"), "part": meta.get("part") or "",
                     "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)) if mtime else "",
                     "preview": prev[0] if prev else None, "_mtime": mtime})
    rows.sort(key=lambda r: r["_mtime"], reverse=True)
    for r in rows:
        r.pop("_mtime", None)
    return rows[:max(1, int(limit))]


__all__ = ["DesignError", "DesignResult", "designs_dir", "slugify", "check_source", "check_params", "parse_log",
           "parse_deps", "stl_facts", "stl_triangle_count", "render", "load_version", "latest_ok_version",
           "ok_versions", "list_designs", "openscad_status", "record_upload", "versions", "VIEW_ARGS",
           "DEFAULT_VIEWS", "MAX_SOURCE_BYTES", "INSTALL_HINT", "SUSPECT_WARNING_RE"]
