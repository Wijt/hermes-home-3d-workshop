"""design.py + the ``home3d_design`` tool: AI modelling in OpenSCAD.

Most tests put a FAKE ``openscad`` (and ``xvfb-run``) on PATH: a small Python script that follows ``// FAKE:``
directives in the rendered .scad (echo, warn, error, assert, sleep, box size, ...), writes an ASCII STL box and logs
how it was called. The ``real_openscad`` tests use the real binary and are skipped when it is missing, unless
``HOME3D_REQUIRE_OPENSCAD=1`` (the CI job that installs OpenSCAD sets it, so a skip there is a failure).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from home3d_ws.home3d import customize, design
from home3d_ws.home3d import tools as tools_mod
from home3d_ws.home3d.backends.simulator import SimulatorBackend
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store

ROOT = Path(__file__).resolve().parents[1]

FAKE_OPENSCAD = r'''#!__PYTHON__
import json, os, re, subprocess, sys, time
try:
    import resource
    RLIMIT = resource.getrlimit(resource.RLIMIT_AS)[0]
    RLIMIT_CPU = list(resource.getrlimit(resource.RLIMIT_CPU))
    RLIMIT_FSIZE = resource.getrlimit(resource.RLIMIT_FSIZE)[0]
except Exception:
    RLIMIT = RLIMIT_CPU = RLIMIT_FSIZE = None
args = sys.argv[1:]
if "--version" in args:
    print("OpenSCAD version 2021.01", file=sys.stderr)
    sys.exit(0)
out = args[args.index("-o") + 1]
src_path = args[-1]
src = open(src_path, encoding="utf-8").read()
log = os.environ.get("FAKE_OPENSCAD_LOG")
entry = {"argv": args, "cwd": os.getcwd(), "rlimit_as": RLIMIT, "rlimit_cpu": RLIMIT_CPU,
         "rlimit_fsize": RLIMIT_FSIZE, "openscadpath": os.environ.get("OPENSCADPATH"), "pid": os.getpid(),
         "sid": os.getsid(0) if hasattr(os, "getsid") else None, "t0": time.time()}
directives = [d.strip() for d in re.findall(r"//\s*FAKE:\s*(.*)", src)]
if "-d" in args and not any(d.split(" ")[0] in ("error", "nodeps") for d in directives):
    # like OpenSCAD: every file it read, in make syntax (not after a parse error)
    deps = [src_path] + [d.split(" ", 1)[1] for d in directives if d.startswith("dep ")]
    with open(args[args.index("-d") + 1], "w") as fh:
        fh.write(out + ":" + "".join(" \\\n\t" + x.replace(" ", "\\ ") for x in deps) + "\n")

def done(code):
    entry["t1"] = time.time()
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    sys.exit(code)

if out.endswith(".png"):
    if os.environ.get("FAKE_OPENSCAD_DEADX") and not os.environ.get("FAKE_UNDER_XVFB"):
        print("Unable to open a connection to the X server.", file=sys.stderr)
        done(1)
    if os.environ.get("FAKE_OPENSCAD_NOPNG"):
        print("Can't create OpenGL OffscreenView. Code: -1.", file=sys.stderr)
        done(1)
    with open(out, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    done(0)

box = [40.0, 20.0, 10.0]
simple, volumes, two, z0, invert, binary = "yes", 2, False, 0.0, False, False
for d in directives:
    word, _, rest = d.strip().partition(" ")
    if word == "echo":
        print("ECHO: " + rest, file=sys.stderr)
    elif word == "warn":
        print("WARNING: " + rest, file=sys.stderr)
    elif word == "error":
        print("ERROR: Parser error: syntax error in file %s, line %s" % (src_path, rest), file=sys.stderr)
        print("Can't parse file '%s'!" % src_path, file=sys.stderr)
        done(1)
    elif word == "assert":
        print("ERROR: Assertion '(w > 10)' failed: \"w too small\" in file %s, line 4" % src_path, file=sys.stderr)
        print("TRACE: called by 'assert' in file %s, line 4" % src_path, file=sys.stderr)
        print("Current top level object is empty.", file=sys.stderr)
        done(1)
    elif word == "empty":
        print("Current top level object is empty.", file=sys.stderr)
        done(1)
    elif word == "flat":
        print("Current top level object is not a 3D object.", file=sys.stderr)
        done(1)
    elif word == "sleep":
        pidfile = os.environ.get("FAKE_CHILD_PIDFILE")
        child = subprocess.Popen(["sleep", "300"])
        if pidfile:
            open(pidfile, "w").write(str(child.pid))
        time.sleep(float(rest))
    elif word == "pause":
        time.sleep(float(rest))
    elif word == "trap":
        import signal
        def bye(*_, path=rest):
            open(path, "w").write("cleaned up")
            sys.exit(0)
        signal.signal(signal.SIGTERM, bye)
    elif word == "box":
        box = [float(v) for v in rest.split()]
    elif word == "simple":
        simple = rest.strip()
    elif word == "volumes":
        volumes = int(rest)
    elif word == "two":
        two = True
    elif word == "lift":
        z0 = float(rest)
    elif word == "noout":
        done(0)
    elif word == "invert":
        invert = True
    elif word == "binary":
        binary = True
    elif word == "die":
        import signal
        if log:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        signal.signal(int(rest), signal.SIG_DFL)  # Python ignores SIGXFSZ; OpenSCAD does not
        os.kill(os.getpid(), int(rest))
        time.sleep(5)
    elif word == "spill":
        with open(out, "wb") as fh:
            fh.write(b"x" * int(rest))

TRIS = []

def quad(fh, a, b, c, d):
    for tri in ((a, b, c), (a, c, d)):
        TRIS.append(tri[::-1] if invert else tri)

def cube(fh, x0, y0, z0, w, d, h):
    p = lambda i, j, k: (x0 + w * i, y0 + d * j, z0 + h * k)
    quad(fh, p(0,0,0), p(0,1,0), p(1,1,0), p(1,0,0))
    quad(fh, p(0,0,1), p(1,0,1), p(1,1,1), p(0,1,1))
    quad(fh, p(0,0,0), p(1,0,0), p(1,0,1), p(0,0,1))
    quad(fh, p(0,1,0), p(0,1,1), p(1,1,1), p(1,1,0))
    quad(fh, p(0,0,0), p(0,0,1), p(0,1,1), p(0,1,0))
    quad(fh, p(1,0,0), p(1,1,0), p(1,1,1), p(1,0,1))

cube(None, 0.0, 0.0, z0, *box)
if two:
    cube(None, box[0] + 5.0, 0.0, z0, 5.0, 5.0, 5.0)
if binary:
    import struct
    with open(out, "wb") as fh:
        fh.write(b"OpenSCAD Model".ljust(80, b"\0") + struct.pack("<I", len(TRIS)))
        for tri in TRIS:
            fh.write(struct.pack("<12fH", 0, 0, 0, *[c for v in tri for c in v], 0))
else:
    with open(out, "w") as fh:
        fh.write("solid OpenSCAD_Model\n")
        for tri in TRIS:
            fh.write("facet normal 0 0 0\n outer loop\n")
            for v in tri:
                fh.write("  vertex %r %r %r\n" % v)
            fh.write(" endloop\nendfacet\n")
        fh.write("endsolid OpenSCAD_Model\n")
print("Total rendering time: 0:00:00.010", file=sys.stderr)
print("   Top level object is a 3D object:", file=sys.stderr)
if simple != "none":
    print("   Simple:        " + simple, file=sys.stderr)
    print("   Volumes:         %d" % volumes, file=sys.stderr)
done(0)
'''

FAKE_XVFB = r'''#!__PYTHON__
import os, sys
args = sys.argv[1:]
log = os.environ.get("FAKE_XVFB_LOG")
if log:
    open(log, "a").write(" ".join(args) + "\n")
while args and args[0].startswith("-"):
    opt = args.pop(0)
    if opt in ("-s", "-n", "-f", "-e", "-p", "--server-args", "--server-num"):
        args.pop(0)
os.environ["FAKE_UNDER_XVFB"] = "1"
os.dup2(1, 2)  # like xvfb-run: the command's stderr arrives on stdout
os.execvp(args[0], args)
'''

SCAD = ("// FAKE: echo \"size\", 40\n// FAKE: warn x was assigned on line 3 but was overwritten on line 7\n"
        "cube([40, 20, 10]);\n")


def _write_exe(path: Path, text: str) -> None:
    path.write_text(text.replace("__PYTHON__", sys.executable), encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A fake openscad + xvfb-run first on PATH, no DISPLAY; returns a helper to read the call log."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    _write_exe(bindir / "openscad", FAKE_OPENSCAD)
    _write_exe(bindir / "xvfb-run", FAKE_XVFB)
    log, xlog = tmp_path / "openscad.log", tmp_path / "xvfb.log"
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("FAKE_OPENSCAD_LOG", str(log))
    monkeypatch.setenv("FAKE_XVFB_LOG", str(xlog))
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("FAKE_OPENSCAD_NOPNG", raising=False)
    monkeypatch.delenv("FAKE_OPENSCAD_DEADX", raising=False)
    monkeypatch.delenv("FAKE_UNDER_XVFB", raising=False)
    monkeypatch.setattr(design.sys, "platform", "linux")
    monkeypatch.setattr(design, "_display_broken", False)
    design._version_cache.clear()

    class Fake:
        exe = bindir / "openscad"

        @staticmethod
        def calls() -> list[dict]:
            if not log.is_file():
                return []
            return [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]

        @staticmethod
        def renders() -> list[dict]:
            return [c for c in Fake.calls() if c["argv"][c["argv"].index("-o") + 1].endswith(".stl")]

        @staticmethod
        def xvfb_calls() -> list[str]:
            return xlog.read_text(encoding="utf-8").splitlines() if xlog.is_file() else []

    yield Fake
    design._version_cache.clear()


def sim_rt(tmp_path) -> Runtime:
    s = Settings(backend="simulator", language="en", owner_name="Owner", owner_ids=["owner@demo"],
                 household=[{"id": "mum@demo", "name": "Mum"}, {"id": "dad@demo", "name": "Dad"}])
    store = Store(tmp_path / "w.db")
    store.remember_sender("s-mum", "mum@demo", "whatsapp")
    return Runtime(settings=s, store=store, backend=SimulatorBackend(tmp_path / "sim.json"))


def call(rt, args, session="s-mum") -> dict:
    handler = {n: h for n, _, h in tools_mod.build_tools(rt)}["home3d_design"]
    raw = handler(args, session_id=session, task_id="t1")
    assert isinstance(raw, str)
    return json.loads(raw)


# ---- names --------------------------------------------------------------------------------------------------
def test_slugify():
    assert design.slugify("Çiçek Saksısı İçin Ölçülü Şık Üçgen") == "cicek-saksisi-icin-olculu-sik-ucgen"
    assert design.slugify("IŞIK ğ") == "isik-g"
    assert design.slugify("Café  déjà-vu!") == "cafe-deja-vu"
    assert design.slugify("phone_stand v2") == "phone-stand-v2"
    assert design.slugify("") == design.slugify(None) == design.slugify("!!!") == design.slugify("日本") == "design"
    long = design.slugify("a" * 39 + " b" + "c" * 30)
    assert len(long) <= 40 and not long.endswith("-") and long == "a" * 39
    for s in ("Kalem Kutusu", "x" * 80, "anneme-vazo"):
        slug = design.slugify(s)
        assert re.fullmatch(r"[a-z0-9-]{1,40}", slug) and design.slugify(slug) == slug


def test_designs_dir_is_under_the_data_dir(data_dir):
    assert design.designs_dir() == data_dir / "designs"


# ---- source checks ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("src, why", [
    ('include </etc/passwd>', "relative"),
    ('use <~/lib.scad>', "relative"),
    ('use <../other/lib.scad>', "'..'"),
    ('include <fonts/../../x.scad>', "'..'"),
    ('import("/home/someone/secret.stl");', "relative"),
    ('import(file = "/tmp/x.stl", convexity = 3);', "relative"),
    ('surface(file="C:/x.png");', "relative"),
    ('surface("../x.dat");', "'..'"),
    ('f = "/etc/x.stl"; import(f);', "string literal"),
    ('import(str("/et", "c/x.stl"));', "string literal"),
    ('linear_extrude(file = name);', "string literal"),
    ('import("a\\x2fb.stl");', "backslash"),
    ('import_stl("/x.stl");', "relative"),
    ('dxf_dim(file="/x.dxf", name="w");', "relative"),
    # round 4 review: a file as the positional argument of an extrusion (any position)
    ('linear_extrude("/abs/any.dxf", height = 7);', "relative"),
    ('rotate_extrude("/abs/any.dxf");', "relative"),
    ('linear_extrude(height = 7, "/abs/any.dxf");', "relative"),
    ('dxf_linear_extrude("/abs/any.dxf", height = 3);', "relative"),
    ('dxf_rotate_extrude("/abs/any.dxf");', "relative"),
    ('linear_extrude(c ? "/abs/x.dxf" : "a.dxf", height = 3);', "one plain string literal"),
    ('import(filename = "/abs/x.stl");', "relative"),  # the deprecated name OpenSCAD still reads
    # an expression after the first literal: OpenSCAD evaluates all of it
    ('import("part.stl" == "" ? "part.stl" : "/abs/x.stl");', "one plain string literal"),
    ('surface(file = "relief.png" != "" ? "/any/image.png" : "relief.png", center = true);',
     "one plain string literal"),
    ('import("a.stl" /* c */ + "/x");', "one plain string literal"),
    # include/use paths are raw text to OpenSCAD: a quote or comment opener in one must not hide code
    ('include <x/*.scad>\ninclude </abs/secret.scad>\n// */', "only letters"),
    ('use <q".scad>\nimport("/abs/secret.stl");\necho("x");', "only letters"),
    ('x = 3include <q".scad>; import("/abs/secret.stl"); y = ";', "only letters"),
    ('include <lib.scad', "not closed"),
])
def test_check_source_refuses_paths_that_leave_the_folder(tmp_path, src, why):
    problems = design.check_source("cube(1);\n" + src, tmp_path)
    assert problems and why in " ".join(problems), problems
    assert problems[0].startswith("line 2:"), problems


def test_check_source_accepts_files_inside_the_folder_and_ignores_comments(tmp_path):
    ok = textwrap.dedent('''\
        use <fonts/Brand.ttf>
        include <lib/common.scad>
        // import("/etc/passwd");  include </etc/passwd>
        /* use <../../x.scad>
           surface("/x.png"); */
        echo("import(/etc/passwd) in a string is only text");
        import("part.stl", convexity = 4);
        import(file = "shapes/logo.svg");
        surface(file = "relief.png", center = true);
        file = 3;  // a variable called file is not a file argument
        cube(file);
        ''')
    assert design.check_source(ok, tmp_path) == []


def test_check_source_include_tricks_are_all_found(tmp_path):
    """Round 4: everything after a path with '/*' or '"' is still checked (OpenSCAD reads those as plain text)."""
    probs = design.check_source('include <x/*.scad>\ninclude </abs/secret.scad>\n// */\ncube(1);', tmp_path)
    assert any(p.startswith("line 1:") for p in probs) and any(p.startswith("line 2:") and "relative" in p
                                                               for p in probs)
    probs = design.check_source('use <q".scad>\nimport("/abs/secret.stl");\necho("x");', tmp_path)
    assert any(p.startswith("line 2:") and "/abs/secret.stl" in p for p in probs)


def test_check_source_still_accepts_ordinary_code(tmp_path):
    ok = textwrap.dedent('''\
        include <lib/common.scad>
        use <fonts/Brand Name.ttf>
        fuse = 2; pause = 4;
        if (fuse < 3 && pause > 1) cube(1);
        linear_extrude(height = 5) square(3);
        linear_extrude(5, center = true, twist = 10) circle(2);
        rotate_extrude(angle = 90, $fn = 32) translate([5, 0]) square(1);
        linear_extrude("logo.dxf", height = 2);
        linear_extrude(file = "logo.dxf", height = 2);
        import("part.stl");
        import(file = "part.stl", convexity = 3);
        echo(str("a", "b"), len("xyz"));
        label = "use <not/a/file> or include </etc/passwd>";
        ''')
    assert design.check_source(ok, tmp_path) == []


def test_check_source_reads_strings_like_openscad_does(tmp_path):
    """OpenSCAD strings may span lines: a quote that only looks like an opening quote must not hide a call."""
    sneaky = 'x = "a\nb"; import("/etc/passwd.stl"); y = "c";\ncube(1);'
    problems = design.check_source(sneaky, tmp_path)
    assert len(problems) == 1 and problems[0].startswith("line 2:") and "/etc/passwd.stl" in problems[0]
    assert "line breaks" in " ".join(design.check_source('import("a\nb.stl");', tmp_path))
    assert design.check_source('echo("a // b"); /* "x */ cube(1); s = "\\"import(\\"/x\\")";', tmp_path) == []


def test_check_source_follows_symlinks_out_of_the_folder(tmp_path):
    folder = tmp_path / "d"
    folder.mkdir()
    (tmp_path / "outside.stl").write_text("solid x\nendsolid x\n")
    (folder / "inside.stl").symlink_to(tmp_path / "outside.stl")
    assert "leaves the design folder" in " ".join(design.check_source('import("inside.stl");', folder))
    assert design.check_source('import("inside.stl");', None) == []  # lexical rules only without a folder


def test_check_source_limits():
    assert "more than 200000" in " ".join(design.check_source("x" * 200_001))
    assert design.check_source("cube(1);" + " " * (200_000 - 8)) == []
    assert "empty" in " ".join(design.check_source("  \n"))
    assert "NUL" in " ".join(design.check_source("cube(1);\x00"))
    assert design.check_source(123) == ["the OpenSCAD source must be text"]  # type: ignore[arg-type]


def test_check_params_formats_minus_d_values():
    d = design.check_params({"width": 80, "depth": 12.5, "hole": True, "label": 'Sam "the" \\ box',
                             "size": [40, 20.5, 3], "_x1": -0.0001})
    assert d == ["-D", "width=80", "-D", "depth=12.5", "-D", "hole=true",
                 "-D", 'label="Sam \\"the\\" \\\\ box"', "-D", "size=[40, 20.5, 3]", "-D", "_x1=-0.0001"]
    assert design.check_params(None) == [] and design.check_params({}) == []


@pytest.mark.parametrize("params, why", [
    ({"1x": 3}, "variable name"), ({"a-b": 3}, "variable name"), ({"x;cube(9)": 1}, "variable name"),
    ({"x": float("nan")}, "finite"), ({"x": float("inf")}, "finite"), ({"x": "a" * 201}, "longer than 200"),
    ({"x": "two\nlines"}, "control character"), ({"x": {"y": 1}}, "must be a number"),
    ({"x": ["a", "b"]}, "list"), ({"x": list(range(17))}, "list"), ({"x": None}, "must be a number"),
    ({f"p{i}": i for i in range(65)}, "at most 64"),
    ({"x": "/" + "a" * 4096}, "longer than 4096"), ({"x": "a" * 4096}, "longer than 200"),
    ({f"p{i}": "/" + "a" * 4000 for i in range(9)}, "together"),
])
def test_check_params_refuses(params, why):
    with pytest.raises(design.DesignError) as e:
        design.check_params(params)
    assert e.value.code == "bad_args" and why in str(e.value)


def test_check_params_needs_an_object():
    with pytest.raises(design.DesignError):
        design.check_params([("x", 1)])  # type: ignore[arg-type]


# ---- log + STL facts -------------------------------------------------------------------------------------------
def test_parse_log_reads_errors_warnings_echo_and_cgal_facts(tmp_path):
    folder = tmp_path / "d"
    text = "\n".join([
        'ECHO: "width", 40', *[f"ECHO: {i}" for i in range(30)],
        f"WARNING: Ignoring unknown variable 'x' in file {folder}/a_v1.scad, line 7",
        "WARNING: Ignoring unknown variable 'x' in file a_v1.scad, line 7",
        "EXPORT-WARNING: Exported object may not be a valid 2-manifold and may need repair",
        "DEPRECATED: Using ranges of the form [begin:end] with begin value greater than the end value is deprecated.",
        "ERROR: Assertion '(w > 10)' failed: \"w too small\" in file a_v1.scad, line 12",
        "ERROR: second error, line 99", "   Simple:         no", "   Volumes:         4",
        "Current top level object is empty.", "std::bad_alloc"])
    log = design.parse_log(text, folder)
    assert log["echo"][0] == '"width", 40' and len(log["echo"]) == 20 and log["echo_total"] == 31
    assert log["warnings"][0] == "Ignoring unknown variable 'x' in file a_v1.scad, line 7"
    assert len(log["warnings"]) == 3  # the same warning once, path made relative
    assert log["errors"][0].startswith("Assertion") and log["error_line"] == 12
    assert log["asserts_failed"] == [log["errors"][0]]
    assert log["simple"] is False and log["volumes"] == 4 and log["empty"] and log["out_of_memory"]
    assert str(folder) not in json.dumps(log)
    clean = design.parse_log("   Simple:        yes\n   Volumes:         2\n")
    assert clean["simple"] is True and clean["volumes"] == 2 and clean["errors"] == [] and clean["error_line"] is None


def _binary_boxes(path: Path, boxes) -> None:
    tris = []
    for x0, y0, z0, w, d, h in boxes:
        v = [(x0 + w * i, y0 + d * j, z0 + h * k) for k in (0, 1) for j in (0, 1) for i in (0, 1)]
        for a, b, c in [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4),
                        (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]:
            tris.append((v[a], v[b], v[c]))
    out = bytearray(b"binary".ljust(80, b" ")) + struct.pack("<I", len(tris))
    for a, b, c in tris:
        out += struct.pack("<12fH", 0, 0, 0, *a, *b, *c, 0)
    path.write_bytes(bytes(out))


def test_stl_facts_binary_and_ascii(tmp_path):
    one = tmp_path / "one.stl"
    _binary_boxes(one, [(0, 0, 0, 40, 20, 10)])
    f = design.stl_facts(one)
    assert f == {"triangles": 12, "size_mm": [40.0, 20.0, 10.0], "min_z_mm": 0.0, "volume_cm3": 8.0, "bodies": 1,
                 "inverted": False}
    two = tmp_path / "two.stl"
    _binary_boxes(two, [(0, 0, 2, 10, 10, 10), (20, 0, 2, 5, 5, 5)])
    f = design.stl_facts(two)
    assert f["bodies"] == 2 and f["min_z_mm"] == 2.0 and f["volume_cm3"] == pytest.approx(1.125)
    assert design.stl_facts(two, count_bodies=False)["bodies"] is None
    ascii_stl = tmp_path / "a.stl"
    ascii_stl.write_text("solid t\n" + "".join(
        f"facet normal 0 0 0\nouter loop\nvertex {a}\nvertex {b}\nvertex {c}\nendloop\nendfacet\n"
        for a, b, c in [("0 0 0", "0 10 0", "10 0 0"), ("0 0 0", "10 0 0", "0 0 10"),
                        ("0 0 0", "0 0 10", "0 10 0"), ("10 0 0", "0 10 0", "0 0 10")]) + "endsolid t\n")
    f = design.stl_facts(ascii_stl)
    assert f["triangles"] == 4 and f["size_mm"] == [10.0, 10.0, 10.0] and f["bodies"] == 1
    assert f["volume_cm3"] == pytest.approx(1000 / 6 / 1000, abs=1e-3)


# ---- render with the fake OpenSCAD ---------------------------------------------------------------------------
def test_openscad_status(fake, monkeypatch):
    st = design.openscad_status()
    assert st["openscad"] == str(fake.exe) and st["version"] == "2021.01" and st["previews"] is True
    assert st["xvfb"] and st["xvfb"].endswith("xvfb-run")
    monkeypatch.setattr(design, "_xvfb_exe", lambda: None)
    assert design.openscad_status()["previews"] is False
    monkeypatch.setenv("DISPLAY", ":0")
    assert design.openscad_status()["previews"] is True


def test_render_writes_a_new_version_with_facts_previews_and_meta(fake, data_dir):
    res = design.render("Telefon Standı", SCAD)
    folder = data_dir / "designs" / "telefon-standi"
    assert res.ok and res.name == "telefon-standi" and res.version == 1 and res.code == "" and res.error == ""
    assert res.size_mm == [40.0, 20.0, 10.0] and res.min_z_mm == 0.0 and res.triangles == 12
    assert res.volume_cm3 == 8.0 and res.est_grams_max == 9.9  # 8 cm3 x 1.24 g/cm3: solid, an upper bound
    assert res.simple is True and res.bodies == 1 and res.fits_build_volume is True
    assert res.echo == ['"size", 40'] and res.warnings == ["x was assigned on line 3 but was overwritten on line 7"]
    assert res.suspect == [] and res.inverted is False
    assert res.openscad_version == "2021.01" and res.render_s >= 0
    assert res.scad_path == str(folder / "telefon-standi_v1.scad") and Path(res.scad_path).read_text() == SCAD
    assert res.stl_path == str(folder / "telefon-standi_v1.stl") and Path(res.stl_path).is_file()
    assert res.views == ["iso", "top"]
    assert res.previews == [str(folder / "telefon-standi_v1_iso.png"), str(folder / "telefon-standi_v1_top.png")]
    assert all(Path(p).is_file() for p in res.previews)
    assert res.media == [f"MEDIA:{p}" for p in res.previews]
    meta = json.loads((folder / "telefon-standi_v1.json").read_text())
    assert meta["ok"] is True and meta["size_mm"] == [40.0, 20.0, 10.0] and meta["media"] == res.media
    # OpenSCAD ran in the design folder on relative names; the previews import the STL (no CGAL again)
    (main,) = fake.renders()
    assert main["cwd"] == str(folder) and main["argv"] == ["-o", "telefon-standi_v1.stl", "--export-format", "binstl",
                                                           "-d", ".telefon-standi_v1.deps", "telefon-standi_v1.scad"]
    assert not list(folder.glob(".*.deps"))  # the dependency list was read and removed
    pngs = [c for c in fake.calls() if c not in fake.renders()]
    assert len(pngs) == 2 and all("--autocenter" in c["argv"] and "--viewall" in c["argv"]
                                  and "--imgsize=900,700" in c["argv"] for c in pngs)
    assert "--camera=0,0,0,55,0,25,0" in pngs[0]["argv"] and "--projection=o" in pngs[1]["argv"]
    # xvfb-run keeps its X cookie in a file of ours (-f), removed afterwards: no mktemp folder left in /tmp
    assert len(fake.xvfb_calls()) == 2 and all(c.startswith(f"-a -f {folder}/.xauth_") for c in fake.xvfb_calls())
    assert not list(folder.glob(".preview_*")) and not list(folder.glob(".xauth_*"))


def test_versions_are_never_overwritten_and_from_version_keeps_code_and_params(fake, data_dir):
    v1 = design.render("box", SCAD, params={"width": 50, "label": "Mum"}, views=[])
    v2 = design.render("box", from_version=1, params={"width": 60, "depth": 30}, views=[])
    v3 = design.render("box", from_version=2, params={"label": None}, part="lid", views=["front", "side"])
    v4 = design.render("box", from_version=3, views=[])
    v5 = design.render("box", from_version=3, part="", views=[])
    v6 = design.render("box", "// FAKE: box 10 10 10\ncube(10);", from_version=5, params={"h": 2}, views=[])
    assert [r.version for r in (v1, v2, v3, v4, v5, v6)] == [1, 2, 3, 4, 5, 6]
    assert v2.params == {"width": 60, "label": "Mum", "depth": 30} and v2.from_version == 1
    assert v3.params == {"width": 60, "depth": 30} and v3.part == "lid" and v3.views == ["front", "side"]
    assert v4.part == "lid" and v5.part == "" and v6.params == {"h": 2} and v6.size_mm == [10.0, 10.0, 10.0]
    # a kept part is said out loud: the designer re-rendered "the whole piece" and silently got the fit test
    assert v4.warnings[0] == "part 'lid' kept from v3 (from_version keeps the part; part=\"\" renders the whole design)"
    assert not any("kept from" in w for w in v3.warnings + v5.warnings)
    argv = [c["argv"] for c in fake.renders()]
    head = ["--export-format", "binstl", "-d"]
    assert argv[0] == ["-o", "box_v1.stl", *head, ".box_v1.deps", "-D", "width=50", "-D", 'label="Mum"', "box_v1.scad"]
    assert argv[2] == ["-o", "box_v3.stl", *head, ".box_v3.deps", "-D", "width=60", "-D", "depth=30",
                       "-D", 'part="lid"', "box_v3.scad"]
    assert 'part="lid"' in argv[3] and not any(a.startswith("part=") for a in argv[4])
    folder = data_dir / "designs" / "box"
    assert (folder / "box_v1.scad").read_text() == SCAD == (folder / "box_v5.scad").read_text()
    assert design.versions("box") == [1, 2, 3, 4, 5, 6]
    got = design.load_version("box", 2)
    assert got["source"] == SCAD and got["meta"]["params"]["width"] == 60 and got["stl_path"].endswith("box_v2.stl")
    assert design.load_version("Box")["version"] == 6
    with pytest.raises(design.DesignError) as e:
        design.load_version("box", 9)
    assert e.value.code == "not_found" and "1, 2, 3, 4, 5, 6" in str(e.value)
    with pytest.raises(design.DesignError) as e:
        design.render("box", from_version=9)
    assert e.value.code == "not_found"
    with pytest.raises(design.DesignError) as e:
        design.render("box", params={"width": 1})
    assert e.value.code == "bad_args" and "from_version" in str(e.value)


def test_a_claimed_version_number_is_skipped(fake, data_dir):
    folder = data_dir / "designs" / "cup"
    folder.mkdir(parents=True)
    (folder / "cup_v1.scad").write_text("cube(1);")
    (folder / "cup_v7.scad").write_text("cube(1);")
    assert design.render("cup", SCAD, views=[]).version == 8
    assert (folder / "cup_v1.scad").read_text() == "cube(1);"


@pytest.mark.parametrize("directive, code, error, line", [
    ("error 3", "render_failed", "Parser error: syntax error in file box_v1.scad, line 3", 3),
    ("assert", "assert_failed", "Assertion '(w > 10)' failed", 4),
    ("empty", "render_failed", "nothing to render", None),
    ("flat", "render_failed", "2D", None),
    ("noout", "render_failed", "OpenSCAD exited with 0", None),
])
def test_a_failed_render_is_a_kept_version_without_an_stl(fake, data_dir, directive, code, error, line):
    res = design.render("box", f"// FAKE: {directive}\ncube(1);")
    assert res.ok is False and res.code == code and error in res.error and res.error_line == line
    assert res.version == 1 and res.stl_path == "" and res.previews == [] and res.size_mm is None
    folder = data_dir / "designs" / "box"
    assert (folder / "box_v1.scad").is_file() and not (folder / "box_v1.stl").exists()
    assert str(folder) not in res.error
    meta = json.loads((folder / "box_v1.json").read_text())
    assert meta["ok"] is False and meta["code"] == code
    if directive == "assert":
        assert res.asserts_failed and "w too small" in res.asserts_failed[0]
    assert design.latest_ok_version("box") is None


def test_fact_warnings(fake):
    res = design.render("w", "// FAKE: simple no\n// FAKE: volumes 3\n// FAKE: two\n// FAKE: lift 2\ncube(1);",
                        views=[])
    assert res.ok and res.simple is False and res.bodies == 2 and res.min_z_mm == 2.0
    text = " | ".join(res.warnings)
    assert "Simple: no" in text and "2 separate bodies" in text and "z = 2 mm" in text
    big = design.render("w", "// FAKE: box 300 20 10\ncube(1);", views=[])
    assert big.fits_build_volume is False and "bigger than the build volume 256 x 256 x 256 mm" in " ".join(big.warnings)
    nocgal = design.render("w", "// FAKE: simple none\n// FAKE: two\ncube(1);", views=[])
    assert nocgal.simple is None and nocgal.bodies == 2  # counted from the mesh when OpenSCAD did not say


def test_preview_failures_are_warnings_never_errors(fake, monkeypatch):
    monkeypatch.setenv("FAKE_OPENSCAD_NOPNG", "1")
    res = design.render("p", SCAD, views=["iso", "side"])
    assert res.ok and res.stl_path and res.previews == [] and res.media == []
    assert sum("preview" in w and "failed" in w for w in res.warnings) == 2
    assert "OffscreenView" in " ".join(res.warnings)
    monkeypatch.delenv("FAKE_OPENSCAD_NOPNG")
    monkeypatch.setattr(design, "_xvfb_exe", lambda: None)
    res = design.render("p", SCAD)
    assert res.ok and res.previews == [] and any("previews are off" in w for w in res.warnings)
    monkeypatch.setenv("DISPLAY", ":0")  # a display: OpenSCAD runs without xvfb-run
    before = len(fake.xvfb_calls())
    res = design.render("p", SCAD, views=["top"])
    assert res.ok and len(res.previews) == 1 and len(fake.xvfb_calls()) == before


def test_bad_views_parts_and_timeouts(fake, data_dir):
    for kw, why in [({"views": ["iso", "back"]}, "unknown view"), ({"views": 3}, "views"),
                    ({"part": "lid; cube(1)"}, "part"), ({"part": "x" * 41}, "part"),
                    ({"timeout_s": "soon"}, "timeout_s"), ({"timeout_s": float("nan")}, "timeout_s"),
                    ({"params": {"part": "lid"}, "part": "body"}, "not both"), ({"params": [1]}, "params")]:
        with pytest.raises(design.DesignError) as e:
            design.render("b", SCAD, **kw)
        assert e.value.code == "bad_args" and why in str(e.value), (kw, str(e.value))
    with pytest.raises(design.DesignError):
        design.render("b", 42)  # type: ignore[arg-type]
    assert not (data_dir / "designs" / "b").exists()  # nothing was written for a refused call
    assert design.render("b", SCAD, views="top, iso,top").views == ["top", "iso"]
    assert design.render("b", SCAD, views='["side", "front"]').views == ["side", "front"]  # a JSON string
    assert design.render("b", SCAD, views=[]).previews == []


def test_a_refused_source_writes_nothing(fake, data_dir):
    with pytest.raises(design.DesignError) as e:
        design.render("leak", 'import("/etc/passwd");\ncube(1);')
    assert e.value.code == "refused" and e.value.extra["problems"][0].startswith("line 1:")
    assert not (data_dir / "designs" / "leak").exists() and fake.calls() == []


def test_render_runs_in_its_own_session_with_a_memory_limit(fake):
    design.render("m", SCAD, views=[])
    (c,) = fake.renders()
    if os.name == "posix":
        assert c["sid"] == c["pid"]  # start_new_session: its own process group, killed as a whole
        assert c["rlimit_as"] is not None and 0 < c["rlimit_as"] <= design.MEM_LIMIT_BYTES == 4 << 30


@pytest.mark.skipif(os.name != "posix" or not shutil.which("sleep"), reason="process groups are POSIX")
def test_a_render_over_the_time_limit_is_killed_with_its_children(fake, tmp_path, monkeypatch):
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CHILD_PIDFILE", str(pidfile))
    t0 = time.monotonic()
    res = design.render("slow", "// FAKE: sleep 60\ncube(1);", timeout_s=1)
    assert time.monotonic() - t0 < 20
    assert res.ok is False and res.code == "timeout" and "longer than 1 s" in res.error and res.stl_path == ""
    child = int(pidfile.read_text())

    def alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        stat = Path(f"/proc/{pid}/stat")
        try:  # a killed process nobody has reaped yet (a container without an init) is a zombie: dead
            return stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"
        except (OSError, IndexError):
            return True

    for _ in range(50):  # the grandchild (sleep 300) died with the group
        if not alive(child):
            break
        time.sleep(0.1)
    else:
        pytest.fail("the grandchild survived the timeout")


def test_timeout_is_clamped():
    assert design._norm_timeout(None) == 180 and design._norm_timeout(5000) == 600 and design._norm_timeout(0) == 1


def test_one_render_at_a_time(fake):
    results = []
    threads = [threading.Thread(target=lambda: results.append(design.render("par", "// FAKE: pause 0.4\ncube(1);",
                                                                            views=[])))
               for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert sorted(r.version for r in results) == [1, 2, 3] and all(r.ok for r in results)
    spans = sorted((c["t0"], c["t1"]) for c in fake.renders())
    assert all(a[1] <= b[0] + 0.05 for a, b in zip(spans, spans[1:])), spans


def test_render_is_busy_when_the_lock_does_not_come_free(fake, monkeypatch):
    assert design._render_lock.acquire(timeout=5)
    try:
        with pytest.raises(design.DesignError) as e:
            design.render("busy", SCAD, timeout_s=1, views=[])
        assert e.value.code == "busy"
    finally:
        design._render_lock.release()


def test_no_openscad(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(design.sys, "platform", "linux")
    st = design.openscad_status()
    assert st == {"openscad": None, "version": "", "xvfb": None, "previews": False}
    with pytest.raises(design.DesignError) as e:
        design.render("x", SCAD)
    assert e.value.code == "no_openscad" and "install openscad (and xvfb for previews)" in str(e.value)
    out = call(sim_rt(tmp_path), {"action": "render", "name": "x", "scad": SCAD})
    assert out["ok"] is False and out["code"] == "no_openscad" and "xvfb" in out["hint"]


def test_list_designs(fake):
    assert design.list_designs() == []
    design.render("first", SCAD, views=["iso"])
    time.sleep(0.02)
    design.render("second", SCAD, views=[])
    design.render("second", "// FAKE: error 1\nx", views=[])
    rows = design.list_designs()
    assert [r["name"] for r in rows] == ["second", "first"]
    assert rows[0]["versions"] == 2 and rows[0]["latest"] == 2 and rows[0]["latest_ok"] == 1
    assert rows[0]["latest_failed"] is True and rows[0]["preview"] is None
    assert rows[1]["preview"].endswith("first_v1_iso.png") and rows[1]["size_mm"] == [40.0, 20.0, 10.0]
    assert len(design.list_designs(limit=1)) == 1


# ---- round 4 review: the dependency guard, limits, honest facts ---------------------------------------------------
def test_parse_deps_reads_make_syntax():
    text = "box_v1.stl: \\\n\t/d/designs/box/sp\\ ace/a\\ b.scad \\\r\n\t/usr/share/openscad/libraries/MCAD/units.scad \\\n\tbox_v1.scad\n"
    assert design.parse_deps(text) == ["/d/designs/box/sp ace/a b.scad",
                                       "/usr/share/openscad/libraries/MCAD/units.scad", "box_v1.scad"]
    assert design.parse_deps("") == [] and design.parse_deps("x.stl:\n") == []


def test_a_file_read_outside_the_folder_fails_closed(fake, data_dir, tmp_path):
    """The -d dependency list is the guard a static check cannot be: a path in a -D param, a lexer trick."""
    secret = tmp_path / "secret" / "secret.dxf"
    src = f"// FAKE: echo \"leaked\"\n// FAKE: warn something about {secret}\n// FAKE: dep {secret}\ncube(1);"
    res = design.render("leak", src, params={"outline": str(secret)})
    folder = data_dir / "designs" / "leak"
    assert res.ok is False and res.code == "refused" and str(secret) in res.error and "outside its folder" in res.error
    assert res.echo == [] and res.warnings == [] and res.previews == [] and res.size_mm is None
    assert not (folder / "leak_v1.stl").exists() and not list(folder.glob("*.png"))
    assert not list(folder.glob(".*.deps"))
    meta = json.loads((folder / "leak_v1.json").read_text())
    assert meta["ok"] is False and meta["code"] == "refused" and meta["echo"] == []
    assert len(fake.renders()) == 1 and [c for c in fake.calls() if c not in fake.renders()] == []  # no previews
    assert design.latest_ok_version("leak") is None


def test_a_long_file_path_param_reaches_the_dependency_guard(fake, data_dir, tmp_path):
    """A legitimate file path can be longer than a text label (a deep temporary directory): its length must not be
    what refuses it. A path outside the folder is still refused, by the dependency list; one inside is used."""
    deep = tmp_path.joinpath(*["a-rather-long-directory-name"] * 12)
    secret = deep / "secret.dxf"
    assert len(str(secret)) > design.MAX_PARAM_STR
    assert design.check_params({"outline": str(secret)}) == ["-D", f'outline="{secret}"']
    res = design.render("longleak", f"// FAKE: dep {secret}\ncube(1);", params={"outline": str(secret)}, views=[])
    assert res.ok is False and res.code == "refused" and "outside its folder" in res.error and str(secret) in res.error
    folder = data_dir / "designs" / "longpath"
    inside = folder.joinpath(*["a-rather-long-directory-name"] * 8) / "part.stl"
    inside.parent.mkdir(parents=True)
    inside.write_text("solid x\nendsolid x\n")
    assert len(str(inside)) > design.MAX_PARAM_STR
    res = design.render("longpath", f"// FAKE: dep {inside}\ncube(1);", params={"part": str(inside)}, views=[])
    assert res.ok, res.error


def test_a_render_without_a_dependency_list_is_not_used(fake, data_dir):
    res = design.render("nodeps", "// FAKE: nodeps\ncube(1);")
    assert res.ok is False and res.code == "refused" and "did not list the files" in res.error
    assert not (data_dir / "designs" / "nodeps" / "nodeps_v1.stl").exists() and res.previews == []


def test_files_inside_the_folder_and_in_openscad_libraries_are_fine(fake, data_dir, tmp_path, monkeypatch):
    lib = tmp_path / "libs"
    (lib / "MCAD").mkdir(parents=True)
    (lib / "MCAD" / "units.scad").write_text("M3 = 3;")
    monkeypatch.setattr(design, "_library_dirs", lambda exe: [lib.resolve()])
    folder = data_dir / "designs" / "inside"
    folder.mkdir(parents=True)
    (folder / "part.stl").write_text("solid x\nendsolid x\n")
    res = design.render("inside", f"// FAKE: dep {folder}/part.stl\n// FAKE: dep sub dir/a b.scad\n"
                                  f"// FAKE: dep {lib}/MCAD/units.scad\ncube(1);", views=[])
    assert res.ok, res.error
    (folder / "link.stl").symlink_to(tmp_path / "secret.stl")  # a link inside that points outside
    res = design.render("inside", f"// FAKE: dep {folder}/link.stl\ncube(1);", views=[])
    assert res.ok is False and res.code == "refused"


def test_the_library_folders_never_include_the_whole_disk():
    libs = design._library_dirs("/usr/bin/openscad")
    assert Path("/usr/share/openscad/libraries") in libs
    assert all(str(p).rstrip("/").endswith("libraries") for p in libs)


def test_render_limits_cpu_and_file_size_and_drops_openscadpath(fake, monkeypatch):
    monkeypatch.setenv("OPENSCADPATH", "/")
    design.render("lim", SCAD, views=[], timeout_s=30)
    (c,) = fake.renders()
    assert c["openscadpath"] is None  # library lookups stay in OpenSCAD's own folders
    if os.name == "posix":
        assert c["rlimit_cpu"] == [35, 40]  # time limit + 5 s, hard + 5 s more: an orphaned render still stops
        assert c["rlimit_fsize"] == design.MAX_STL_BYTES


@pytest.mark.skipif(os.name != "posix", reason="signals are POSIX")
@pytest.mark.parametrize("sig, code", [(24, "timeout"), (25, "too_big")])
def test_cpu_and_file_size_signals_are_explained(fake, sig, code):
    res = design.render("sig", f"// FAKE: die {sig}\ncube(1);", views=[])
    assert res.ok is False and res.code == code and res.stl_path == ""
    assert ("longer than" in res.error) if code == "timeout" else ("$fn" in res.error)


def test_too_many_triangles_is_refused_before_parsing(fake, monkeypatch, data_dir):
    monkeypatch.setattr(design, "MAX_TRIANGLES", 5)
    monkeypatch.setattr(design, "stl_facts", lambda *a, **k: pytest.fail("parsed a too-big STL"))
    res = design.render("dense", "// FAKE: binary\ncube(1);", views=[])
    assert res.ok is False and res.code == "too_big" and "12 triangles" in res.error
    assert not (data_dir / "designs" / "dense" / "dense_v1.stl").exists()


def test_a_binary_stl_is_measured(fake):
    res = design.render("bin", "// FAKE: binary\ncube(1);", views=[])
    assert res.ok and res.size_mm == [40.0, 20.0, 10.0] and res.triangles == 12 and res.volume_cm3 == 8.0


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_a_timeout_asks_politely_first(fake, tmp_path):
    """SIGTERM before SIGKILL: Xvfb removes its lock file and socket, xvfb-run its files."""
    flag = tmp_path / "cleaned"
    res = design.render("polite", f"// FAKE: trap {flag}\n// FAKE: pause 60\ncube(1);", timeout_s=1, views=[])
    assert res.code == "timeout" and flag.read_text() == "cleaned up"


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_an_interrupted_render_does_not_leave_openscad_running(tmp_path, monkeypatch):
    import subprocess
    procs = []

    class Interrupted(subprocess.Popen):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            procs.append(self)

        def communicate(self, *a, **k):
            if not procs[0].__dict__.get("_asked"):
                procs[0].__dict__["_asked"] = True
                raise KeyboardInterrupt  # Ctrl-C in the gateway while OpenSCAD runs
            return super().communicate(*a, **k)

    monkeypatch.setattr(design.subprocess, "Popen", Interrupted)
    with pytest.raises(KeyboardInterrupt):
        design._run([sys.executable, "-c", "import time; time.sleep(60)"], tmp_path, 30)
    assert procs[0].wait(timeout=10) is not None


def test_ignored_code_is_flagged_and_not_sent_as_done(fake, tmp_path):
    src = ("// FAKE: warn Ignoring unknown variable 'wal' in file t.scad, line 3\n"
           "// FAKE: warn Unable to convert cube(size=[undef, 5, 5], ...) parameter to a number in file t.scad, line 3\n"
           "cube([wal, 5, 5]);")
    res = design.render("typo", src, views=[])
    assert res.ok and len(res.suspect) == 2 and "a piece of the model is missing" in " ".join(res.warnings)
    rt = sim_rt(tmp_path)
    out = call(rt, {"action": "render", "name": "typo", "scad": src, "views": ["iso"]})
    assert out["ok"] and out["suspect"] and out["next"] == tools_mod.DESIGN_NEXT_SUSPECT
    up = call(rt, {"action": "upload", "name": "typo", "version": 2})
    assert up["ok"] and any("ignored" in w for w in up["warnings"])
    for benign in ("x was assigned on line 3 but was overwritten on line 7", "Viewall and autocenter disabled"):
        assert not design.SUSPECT_WARNING_RE.search(benign)
    for bad in ("Ignoring unknown module 'modul_typo' in file a.scad, line 4", "Ignoring unknown function 'f'",
                "Mixing 2D and 3D objects is not supported", "Ignoring 2D child object for 3D operation",
                "undefined operation (undefined + number)"):
        assert design.SUSPECT_WARNING_RE.search(bad), bad


def test_an_inside_out_mesh_is_flagged(fake):
    res = design.render("inv", "// FAKE: invert\ncube(1);", views=[])
    assert res.ok and res.inverted is True and res.volume_cm3 == 8.0
    assert "inside out (negative volume)" in " ".join(res.warnings)
    assert design.render("inv", "cube(1);", views=[]).inverted is False


def test_echo_of_one_string_loses_its_quotes():
    log = design.parse_log('ECHO: "FOOTPRINT: 88 x 85 mm"\nECHO: "a", "b"\nECHO: "w", 5\nECHO: 5\nECHO: ""\n')
    assert log["echo"] == ["FOOTPRINT: 88 x 85 mm", '"a", "b"', '"w", 5', "5", ""]


def test_stl_facts_never_says_minus_zero(tmp_path):
    import math as _m
    f = tmp_path / "z.stl"
    _binary_boxes(f, [(0, 0, -0.0, 10, 10, 10)])
    facts = design.stl_facts(f)
    assert facts["min_z_mm"] == 0.0 and _m.copysign(1, facts["min_z_mm"]) == 1.0


def test_a_huge_integer_param_is_bad_args():
    with pytest.raises(design.DesignError) as e:
        design.check_params({"a": 10 ** 400})
    assert e.value.code == "bad_args" and "finite" in str(e.value)
    with pytest.raises(design.DesignError):
        design.check_params({"a": [1, 10 ** 400]})


def test_previews_get_their_own_minimum_time(fake, monkeypatch):
    seen = []
    monkeypatch.setattr(design, "_preview", lambda exe, folder, stl, png, view, timeout: seen.append(timeout) or "")
    design.render("quick", SCAD, timeout_s=2, views=["iso"])
    design.render("quick", SCAD, timeout_s=500, views=["iso"])
    assert seen == [design.PREVIEW_MIN_TIMEOUT_S, design.PREVIEW_TIMEOUT_S]


def test_a_stale_display_falls_back_to_xvfb(fake, monkeypatch):
    monkeypatch.setenv("DISPLAY", ":77")  # the SSH or desktop session that set it is gone
    monkeypatch.setenv("FAKE_OPENSCAD_DEADX", "1")
    res = design.render("deadx", SCAD, views=["iso", "top"])
    assert res.ok and res.views == ["iso", "top"] and not any("preview" in w for w in res.warnings)
    assert design._display_broken is True and len(fake.xvfb_calls()) == 2  # retried once, then straight to xvfb


def test_new_views_plan_and_bottom(fake):
    res = design.render("views", SCAD, views=["plan", "bottom"])
    assert res.views == ["plan", "bottom"]
    pngs = [c["argv"] for c in fake.calls() if c not in fake.renders()]
    assert "--camera=0,0,0,25,0,0,0" in pngs[0] and "--projection=o" in pngs[0]
    assert "--camera=0,0,0,235,0,-30,0" in pngs[1]


def test_record_upload_keeps_every_id_under_concurrency(fake, data_dir):
    design.render("race", SCAD, views=[])
    ids = list(range(1, 201))
    threads = [threading.Thread(target=lambda chunk=ids[i::4]: [design.record_upload("race", 1, n) for n in chunk])
               for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    meta = json.loads((data_dir / "designs" / "race" / "race_v1.json").read_text())
    assert meta["ok"] is True and sorted(meta["library_file_ids"]) == ids
    assert not list((data_dir / "designs" / "race").glob("*.part*"))


def test_tool_next_names_the_exact_version_or_says_there_is_no_picture(fake, tmp_path):
    rt = sim_rt(tmp_path)
    out = call(rt, {"action": "render", "name": "Pen Cup", "scad": SCAD})
    assert out["next"].endswith("home3d_design action=upload name=pen-cup version=1")
    out = call(rt, {"action": "render", "name": "Pen Cup", "scad": SCAD, "views": []})
    assert out["next"] == tools_mod.DESIGN_NEXT_NO_PREVIEW.format(name="pen-cup", version=2)


def test_tool_upload_never_guesses_a_part_or_another_chats_version(fake, tmp_path):
    rt = sim_rt(tmp_path)
    call(rt, {"action": "render", "name": "pill box", "scad": SCAD, "part": "lid", "views": []})
    out = call(rt, {"action": "upload", "name": "pill box"})
    assert out["ok"] is False and out["code"] == "bad_args" and "v1 (part lid" in out["error"]
    up = call(rt, {"action": "upload", "name": "pill box", "version": 1})
    assert up["ok"] and up["part"] == "lid" and any("only part 'lid'" in w for w in up["warnings"])
    # Mum's 'phone stand' and Dad's 'Phone Stand!' share a folder: Mum's OK must not upload Dad's render
    call(rt, {"action": "render", "name": "phone stand", "scad": SCAD, "views": []})
    call(rt, {"action": "render", "name": "Phone Stand!", "scad": "// FAKE: box 20 20 150\ncube(1);", "views": []},
         session="s-dad")
    out = call(rt, {"action": "upload", "name": "phone stand"})
    assert out["ok"] is False and "v1 (whole design, 40x20x10 mm)" in out["error"] and "20x20x150" in out["error"]


def test_slice_never_pushes_off_a_multi_part_design(fake, tmp_path):
    rt = sim_rt(tmp_path)
    rt.settings.autoeject_printer_preset = rt.settings.autoeject_printer_preset or "auto-eject"
    call(rt, {"action": "render", "name": "box and lid", "scad": "// FAKE: two\n// FAKE: volumes 3\ncube(1);",
              "views": []})
    up = call(rt, {"action": "upload", "name": "box and lid", "version": 1})
    assert up["ok"] and up["bodies"] == 2 and "2 separate parts" in up["next"]
    slice_tool = {n: h for n, _, h in tools_mod.build_tools(rt)}["home3d_slice"]
    out = json.loads(slice_tool({"library_file_id": up["library_file_id"]}, session_id="s-mum"))
    assert out["ok"] and out["eject"]["planned"] is False
    assert out["eject"]["reasons"] == ["several separate parts (2 bodies in the design): remove them by hand"]
    forced = json.loads(slice_tool({"library_file_id": up["library_file_id"], "eject": "off"}, session_id="s-mum"))
    assert forced["eject"]["reasons"] == ["eject=off"]


# ---- the tool ------------------------------------------------------------------------------------------------
def test_tool_render_get_list_upload_slice_on_the_simulator(fake, tmp_path):
    rt = sim_rt(tmp_path)
    out = call(rt, {"action": "render", "name": "Kalem Kutusu", "scad": SCAD, "params": {"width": 70}})
    assert out["ok"] is True and out["name"] == "kalem-kutusu" and out["version"] == 1
    for key in ("size_mm", "volume_cm3", "est_grams_max", "triangles", "simple", "bodies", "fits_build_volume",
                "warnings", "echo", "previews", "media", "scad_path", "stl_path", "render_s"):
        assert key in out, key
    assert out["size_cm"] == [4.0, 2.0, 1.0] and out["media"][0].startswith("MEDIA:/")
    assert out["next"] == tools_mod.DESIGN_NEXT_RENDER.format(name="kalem-kutusu", version=1)
    assert out["next"].endswith("home3d_design action=upload name=kalem-kutusu version=1")
    assert "Look at the previews yourself first" in out["next"]

    tweak = call(rt, {"action": "render", "name": "kalem-kutusu", "from_version": 1, "params": '{"depth": 30}',
                      "views": ["top"], "request_id": None})
    assert tweak["ok"] and tweak["version"] == 2 and tweak["params"] == {"width": 70, "depth": 30}
    failed = call(rt, {"action": "render", "name": "kalem kutusu", "scad": "// FAKE: error 2\ncube(", "views": []})
    assert failed["ok"] is False and failed["code"] == "render_failed" and failed["error_line"] == 2
    assert failed["version"] == 3 and failed["next"] == tools_mod.DESIGN_NEXT_FAILED

    got = call(rt, {"action": "get", "name": "Kalem Kutusu"})
    assert got["ok"] and got["version"] == 3 and got["rendered"] is False and got["error_line"] == 2
    got = call(rt, {"action": "get", "name": "kalem-kutusu", "version": 1})
    assert got["scad"] == SCAD and got["params"] == {"width": 70} and got["versions"] == [1, 2, 3]
    assert got["bodies"] == 1 and got["simple"] is True and got["inverted"] is False and got["suspect"] == []
    assert got["media"] == out["media"] and "scad_truncated" not in got

    listed = call(rt, {"action": "list"})
    assert listed["ok"] and listed["openscad"] == "2021.01" and listed["previews"] is True
    assert listed["designs"][0]["name"] == "kalem-kutusu" and listed["designs"][0]["latest_ok"] == 2

    # two versions rendered: the upload never guesses which one the person approved
    guess = call(rt, {"action": "upload", "name": "kalem-kutusu", "request_text": "kalem kutusu"})
    assert guess["ok"] is False and guess["code"] == "bad_args" and "v1 (whole design, 40x20x10 mm)" in guess["error"]
    assert [v["version"] for v in guess["versions"]] == [1, 2]
    up = call(rt, {"action": "upload", "name": "kalem-kutusu", "version": 2, "request_text": "kalem kutusu"},
              session="s-mum")
    assert up["ok"] and up["version"] == 2 and up["design"] == "kalem-kutusu" and up["part"] == ""
    lib = up["library_file_id"]
    assert up["name"] == "kalem-kutusu_v2.stl" and up["size_mm"] == [40.0, 20.0, 10.0]
    assert up["next"] == f"home3d_slice library_file_id={lib} request_id={up['request_id']}"
    assert rt.store.kv_get(f"design_lib:{lib}") == {"slug": "kalem-kutusu", "version": 2}
    req = rt.store.get_request(up["request_id"])
    assert req["library_file_id"] == lib and req["model_ref"] == "design:kalem-kutusu_v2"
    assert req["text"] == "kalem kutusu" and req["sender_id"] == "mum@demo"
    assert call(rt, {"action": "get", "name": "kalem-kutusu", "version": 2})["library_file_ids"] == [lib]

    again = call(rt, {"action": "upload", "name": "kalem-kutusu", "version": 1, "request_id": up["request_id"]})
    assert again["ok"] and again["version"] == 1 and again["request_id"] == up["request_id"]
    assert rt.store.get_request(up["request_id"])["library_file_id"] == again["library_file_id"]

    sliced = json.loads({n: h for n, _, h in tools_mod.build_tools(rt)}["home3d_slice"](
        {"library_file_id": again["library_file_id"]}, session_id="s-mum"))  # the request now points at v1
    assert sliced["ok"] is True and sliced["request_id"] == up["request_id"] and sliced["grams"]


def test_tool_upload_refusals(fake, tmp_path):
    rt = sim_rt(tmp_path)
    assert call(rt, {"action": "upload", "name": "nothing"})["code"] == "not_found"
    call(rt, {"action": "render", "name": "bad", "scad": "// FAKE: error 1\nx", "views": []})
    out = call(rt, {"action": "upload", "name": "bad"})
    assert out["ok"] is False and out["code"] == "not_found" and "rendered" in out["error"]
    out = call(rt, {"action": "upload", "name": "bad", "version": 1})
    assert out["ok"] is False and "did not render" in out["error"]
    call(rt, {"action": "render", "name": "good", "scad": SCAD, "views": [], "request_id": 999})
    out = call(rt, {"action": "upload", "name": "good"})
    assert out["ok"] and out["request_id"] is None and out["warnings"] == ["request 999 not found"]
    assert out["next"] == f"home3d_slice library_file_id={out['library_file_id']}"


def test_tool_render_records_the_request_for_upload(fake, tmp_path):
    rt = sim_rt(tmp_path)
    rid = rt.store.add_request(requester="Mum", text="vazo", sender_id="mum@demo")
    call(rt, {"action": "render", "name": "vazo", "scad": SCAD, "views": [], "request_id": rid})
    up = call(rt, {"action": "upload", "name": "vazo"})
    assert up["request_id"] == rid and rt.store.get_request(rid)["library_file_id"] == up["library_file_id"]


def test_tool_refusals_come_back_as_envelopes(fake, tmp_path):
    rt = sim_rt(tmp_path)
    out = call(rt, {"action": "render", "name": "x", "scad": 'include </etc/passwd>\ncube(1);'})
    assert out["ok"] is False and out["code"] == "refused" and out["problems"][0].startswith("line 1:")
    out = call(rt, {"action": "render", "name": "x", "scad": SCAD, "params": {"bad-name": 1}})
    assert out["ok"] is False and out["code"] == "bad_args"
    assert call(rt, {"action": "render", "scad": SCAD})["error"].startswith("'name' is required")
    assert call(rt, {"action": "get", "name": "nope"})["code"] == "not_found"


@pytest.mark.parametrize("bad", [None, "text", {}, {"action": "explode"}, {"action": "render"},
                                 {"action": "render", "name": "x"}, {"action": "render", "name": "x", "scad": 5},
                                 {"action": "render", "name": "x", "scad": SCAD, "params": "[1, 2]"},
                                 {"action": "render", "name": "x", "scad": SCAD, "params": "{bad json"},
                                 {"action": "render", "name": "x", "scad": SCAD, "views": "back"},
                                 {"action": "render", "name": "x", "scad": SCAD, "views": {"a": 1}},
                                 {"action": "render", "name": "x", "scad": SCAD, "part": ["lid"]},
                                 {"action": "render", "name": "x", "scad": SCAD, "timeout_s": "abc"},
                                 {"action": "render", "name": "x", "from_version": "two"},
                                 {"action": "render", "name": ["x"], "scad": SCAD},
                                 {"action": "get", "name": "x", "version": 1.5},
                                 {"action": "upload", "name": "x", "version": "v2"},
                                 {"action": "list", "limit": "many"}])
def test_tool_handler_never_raises(fake, tmp_path, bad):
    out = call(sim_rt(tmp_path), bad)
    assert "ok" in out
    if out["ok"] is False:
        assert out["error"]


def test_tool_handler_never_raises_on_internal_errors(fake, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(design, "render", boom)
    out = call(sim_rt(tmp_path), {"action": "render", "name": "x", "scad": SCAD})
    assert out["ok"] is False and "disk on fire" in out["error"]


def test_tool_schema():
    spec = {name: (desc, props, req) for name, desc, props, req, _ in tools_mod.SPECS}
    desc, props, req = spec["home3d_design"]
    assert desc.startswith("Design a 3D-printable part in OpenSCAD. Write parametric .scad code, render it to STL "
                           "with preview images, iterate in versions, then upload it for slicing.")
    assert req == ["action"] and props["action"]["enum"] == ["render", "get", "list", "upload"]
    assert set(props) == {"action", "name", "scad", "from_version", "params", "views", "part", "version",
                          "request_id", "request_text", "requester", "timeout_s"}
    assert props["views"]["items"]["enum"] == list(design.VIEW_ARGS)
    names = [n for n, *_ in tools_mod.SPECS]
    assert names.index("home3d_design") == names.index("home3d_customize") + 1


# ---- the real OpenSCAD -------------------------------------------------------------------------------------------
REQUIRE_REAL = os.environ.get("HOME3D_REQUIRE_OPENSCAD") == "1"

SAMPLE = textwrap.dedent('''\
    // Phone stand (sample design for the tests). Units: mm. Prints on its back, no supports.
    width = 70;          // across the front face
    depth = 80;
    angle = 65;          // phone lean, degrees from the table
    thickness = 4;
    lip = 12;            // front lip that holds the phone
    cable_slot = 14;     // cable exit in the base
    $fn = 32;

    assert(thickness >= 2, "thickness must be at least 2 mm");
    assert(width <= 256 && depth <= 256, "bigger than the A1 bed");
    back_h = depth * tan(angle) / 2;
    echo(str("stand: ", width, " x ", depth, " mm, back ", round(back_h), " mm"));

    difference() {
        union() {
            cube([width, depth, thickness]);                       // base
            translate([0, 0, 0]) cube([width, thickness, lip]);    // front lip
            translate([0, depth * 0.45, 0])
                rotate([90 - angle, 0, 0]) cube([width, thickness, depth * 0.55]);  // back rest
        }
        translate([width / 2 - cable_slot / 2, -1, -1]) cube([cable_slot, depth * 0.35, thickness + 2]);
        translate([0, 0, -50]) cube([width, depth * 2, 50]);       // flat bottom
    }
    ''')


@pytest.fixture
def real_openscad():
    if not shutil.which("openscad"):
        if REQUIRE_REAL:
            pytest.fail("HOME3D_REQUIRE_OPENSCAD=1 but openscad is not installed")
        pytest.skip("openscad is not installed")
    design._version_cache.clear()
    return design.openscad_status()


def _check_real(res, size, tol=1.0, previews=None):
    assert res.ok, (res.error, res.warnings)
    assert res.simple is True and res.bodies == 1 and res.fits_build_volume is True
    for got, want in zip(res.size_mm, size):
        assert abs(got - want) <= tol, (res.size_mm, size)
    assert res.volume_cm3 > 0 and res.est_grams_max > 0 and res.triangles > 12
    if previews:
        assert len(res.previews) == len(res.views) >= 1 and all(Path(p).stat().st_size > 1000 for p in res.previews)
        assert all(Path(p).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for p in res.previews)


@pytest.mark.parametrize("template, params, size", [
    ("name_tag", {"text": "Mum", "width": 70}, (70, 25, 4.2)),
    ("label_box", {"text": "Lego", "width": 50, "depth": 40, "height": 30}, (50, 40.8, 30)),
])
def test_real_openscad_templates(real_openscad, template, params, size):
    src = (customize.TEMPLATE_DIR / customize.TEMPLATES[template]["file"]).read_text(encoding="utf-8")
    res = design.render(template, src, params=params, views=["iso"])
    _check_real(res, size, previews=real_openscad["previews"])
    assert res.openscad_version == real_openscad["version"]


def test_real_openscad_sample_design_and_tweak(real_openscad):
    res = design.render("phone stand", SAMPLE)
    assert res.echo and res.echo[0].startswith('stand: 70 x 80 mm')  # one string: its quotes are dropped
    _check_real(res, (70, 80, res.size_mm[2]), previews=real_openscad["previews"])
    assert res.min_z_mm == 0.0 and 20 < res.size_mm[2] < 80
    wider = design.render("phone stand", from_version=1, params={"width": 90}, views=[])
    assert wider.ok and wider.version == 2 and abs(wider.size_mm[0] - 90) < 0.01
    assert wider.volume_cm3 > res.volume_cm3


def test_real_openscad_errors_and_asserts(real_openscad):
    res = design.render("broken", "w = 4;\ncube([w, w, w]\nsphere(2);\n", views=[])
    assert res.ok is False and res.code == "render_failed" and res.error_line == 3 and "broken_v1.scad" in res.error
    res = design.render("broken", SAMPLE, params={"thickness": 1}, views=[])
    assert res.ok is False and res.code == "assert_failed" and "at least 2 mm" in res.error and res.error_line
    res = design.render("broken", "square(10);", views=[])
    assert res.ok is False and "2D" in res.error


def test_real_openscad_touching_parts_are_not_simple(real_openscad):
    res = design.render("touch", "cube(10); translate([10, 10, 0]) cube(10);", views=[])
    assert res.ok and res.simple is False and "Simple: no" in " ".join(res.warnings)
    res = design.render("apart", "cube(10); translate([15, 0, 0]) cube(5);", views=[])
    assert res.ok and res.simple is True and res.bodies == 2


SKILL_TEMPLATES = sorted((ROOT / "skills" / "parametric-design" / "templates").glob("*.scad"))


@pytest.mark.parametrize("path", SKILL_TEMPLATES, ids=[p.name for p in SKILL_TEMPLATES])
def test_real_openscad_renders_the_skill_templates(real_openscad, path):
    src = path.read_text(encoding="utf-8")
    assert design.check_source(src) == []
    res = design.render(path.stem, src, views=["iso"])
    assert res.ok, (res.error, res.error_line, res.warnings)
    assert res.simple is not False and res.fits_build_volume and res.triangles > 12
    if real_openscad["previews"]:
        assert res.previews


def _sentinels(root: Path) -> dict:
    """Files OUTSIDE any design folder, with sizes no design would have: an STL 31 x 41 x 59, a DXF 27 x 18, a PNG
    and a .scad that defines a variable."""
    import zlib
    root.mkdir(parents=True, exist_ok=True)
    stl = root / "secret.stl"
    _binary_boxes(stl, [(0, 0, 0, 31, 41, 59)])
    lines = []
    for (x0, y0), (x1, y1) in [((0, 0), (27, 0)), ((27, 0), (27, 18)), ((27, 18), (0, 18)), ((0, 18), (0, 0))]:
        lines += ["0", "LINE", "8", "0", "10", str(x0), "20", str(y0), "11", str(x1), "21", str(y1)]
    dxf = root / "secret.dxf"
    dxf.write_text("\n".join(["0", "SECTION", "2", "ENTITIES", *lines, "0", "ENDSEC", "0", "EOF"]) + "\n")
    png = root / "secret.png"
    raw = b"".join(b"\x00" + bytes([(x * 37 + y * 11) % 256 for x in range(16)]) for y in range(16))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 0, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    scad = root / "secret.scad"
    scad.write_text("secret_value = 31415;\ncube([31, 41, 59]);\n")
    return {"stl": stl, "dxf": dxf, "png": png, "scad": scad}


def test_real_openscad_never_reads_files_outside_the_design_folder(real_openscad, tmp_path):
    """The round-4 security probes against the real binary: each is refused before or after the render, and no
    result ever has a sentinel's size or echoes its variable."""
    s = _sentinels(tmp_path / "outside")
    probes = [
        f'linear_extrude("{s["dxf"]}", height = 7);',
        f'linear_extrude(height = 7, "{s["dxf"]}");',
        f'rotate_extrude("{s["dxf"]}");',
        f'dxf_linear_extrude("{s["dxf"]}", height = 3);',
        f'import("part.stl" == "" ? "part.stl" : "{s["stl"]}");',
        f'import(filename = "{s["stl"]}");',
        f'scale([1, 1, 0.1]) surface(file = "relief.png" != "" ? "{s["png"]}" : "relief.png", center = true);',
        f'include <x/*.scad>\ninclude <{s["scad"]}>\n// */\necho(secret_value);',
        f'use <q".scad>\nimport("{s["stl"]}");\necho("x");',
        f'x = 3include <q".scad>; import("{s["stl"]}"); y = ";',
    ]
    for i, src in enumerate(probes):
        try:
            res = design.render(f"probe-{i}", src, views=[])
        except design.DesignError as e:
            assert e.code == "refused", (src, e.code, str(e))
            continue
        assert res.ok is False and res.code == "refused", (src, res.size_mm, res.error)
    # a file name that arrives only through a -D param: no static check can see it, the dependency list does
    res = design.render("dparam", 'outline = "logo.dxf";\nlinear_extrude(outline, height = 4);',
                        params={"outline": str(s["dxf"])}, views=["iso"])
    assert res.ok is False and res.code == "refused" and str(s["dxf"]) in res.error
    assert res.size_mm is None and res.previews == [] and res.echo == []
    stored = Path(res.scad_path).read_text()
    assert str(s["dxf"]) not in stored  # the path was never in the source
    again = design.render("dparam", from_version=1, views=[])  # from_version keeps the param: still refused
    assert again.ok is False and again.code == "refused"
    assert not list((design.designs_dir()).rglob("*.stl"))


def test_real_openscad_files_inside_the_folder_still_work(real_openscad, tmp_path):
    folder = design.designs_dir() / "with-files"
    folder.mkdir(parents=True)
    _binary_boxes(folder / "part.stl", [(0, 0, 0, 12, 8, 4)])
    (folder / "lib").mkdir()
    (folder / "lib" / "sizes.scad").write_text("w = 30;\n")
    res = design.render("with files", 'include <lib/sizes.scad>\nimport("part.stl");\n'
                                      'translate([20, 0, 0]) cube([w, 5, 5]);', views=[])
    assert res.ok, res.error
    assert res.size_mm == [50.0, 8.0, 5.0] and res.bodies == 2


def test_real_openscad_a_giant_stl_hits_the_file_size_limit(real_openscad, monkeypatch):
    monkeypatch.setattr(design, "MAX_STL_BYTES", 200_000)
    res = design.render("giant", "sphere(20, $fn = 200);", views=[])
    assert res.ok is False and res.code == "too_big" and "$fn" in res.error and res.stl_path == ""


def test_real_openscad_typos_are_suspect_and_binary_stl(real_openscad):
    res = design.render("typo", "wall = 2;\ncube([wal, 5, 5]);\ntranslate([10, 0, 0]) cube(3);", views=[])
    assert res.ok and res.size_mm[1] == 3.0  # the 5 mm cube never came out, yet the render is "ok"
    assert any("Ignoring unknown variable 'wal'" in w for w in res.suspect)
    assert customize._stl_is_binary(Path(res.stl_path).read_bytes())


def test_real_openscad_an_inside_out_polyhedron_is_flagged(real_openscad):
    pts = "[[0,0,0],[10,0,0],[10,10,0],[0,10,0],[0,0,10],[10,0,10],[10,10,10],[0,10,10]]"
    faces = [[0, 1, 2, 3], [4, 5, 1, 0], [7, 6, 5, 4], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3]]
    good = design.render("poly", f"polyhedron({pts}, {faces});", views=[])
    bad = design.render("poly", f"polyhedron({pts}, {[f[::-1] for f in faces]});", views=[])
    assert good.ok and good.inverted is False and good.volume_cm3 == 1.0
    assert bad.ok and bad.inverted is True and bad.volume_cm3 == 1.0
    assert "inside out" in " ".join(bad.warnings)


def test_real_openscad_plan_and_bottom_views(real_openscad):
    if not real_openscad["previews"]:
        pytest.skip("no previews here (xvfb-run missing)")
    res = design.render("views", "difference() { cube([30, 20, 6]); translate([5, 5, 3]) cube([8, 8, 4]); }",
                        views=["plan", "bottom"])
    assert res.ok and res.views == ["plan", "bottom"]
    assert all(Path(p).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and Path(p).stat().st_size > 1000
               for p in res.previews)


def _snippets(rel: str) -> list[str]:
    md = (ROOT / "skills" / "parametric-design" / "references" / rel).read_text(encoding="utf-8")
    return re.findall(r"```scad\n(.*?)```", md, re.S)


def test_real_openscad_renders_the_skill_snippets(real_openscad):
    """The reference snippets the agent copies: the sloped-face label, the two-part box, the sweep (also in a
    boolean, which needs triangle faces) and the glue-on name strip with Turkish letters on one baseline."""
    syntax = _snippets("openscad-syntax.md")
    wedge = next(b for b in syntax if "lean = atan2" in b)
    res = design.render("snip-wedge", wedge, views=[])
    assert res.ok and res.simple is True and res.bodies == 1 and not res.suspect, (res.error, res.warnings)
    box = next(b for b in syntax if 'part = "all"' in b)
    res = design.render("snip-box", box, views=[])
    assert res.ok and res.bodies == 2 and not res.suspect
    sweep = next(b for b in syntax if "module sweep" in b)
    assert "each [[a, b, c], [a, c, d]]" in sweep  # triangle faces
    res = design.render("snip-sweep", sweep, views=[])
    assert res.ok and res.inverted is False and res.bodies == 1 and res.simple is None  # lone polyhedron: no CGAL
    cut = sweep + "\ntranslate([40, -20, -1]) cube([10, 40, 2]);\n"
    cut = cut.replace("sweep([for", "difference() { sweep([for", 1).replace(
        "\ntranslate([40, -20, -1]) cube([10, 40, 2]);", "\ntranslate([40, -20, -1]) cube([10, 40, 2]); }")
    res = design.render("snip-sweep", cut, views=[])
    assert res.ok and res.simple is True, (res.error, res.warnings)
    strip = _snippets("curved-text.md")[0].replace('name    = "SAM";', 'name    = "ŞÜKİ";')
    res = design.render("snip-strip", strip, views=[], timeout_s=300)
    assert res.ok and res.simple is True and res.bodies == 1, (res.error, res.warnings)
    assert abs(res.size_mm[2] - 13.0) < 0.01  # letters, dots and cedillas all stay on the 13 mm band
