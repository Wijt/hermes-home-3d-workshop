"""customize.py: STL (ASCII/binary) and 3MF bounding boxes + scaling, templates (no OpenSCAD needed)."""

from __future__ import annotations

import math
import os
import stat
import struct
import zipfile

import pytest

from home3d_ws.home3d import customize
from home3d_ws.home3d.customize import CustomizeError, model_bbox, model_bounds, scale_model

CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"


def box(x0, y0, z0, w, d, h):
    verts = [(x, y, z) for z in (z0, z0 + h) for y in (y0, y0 + d) for x in (x0, x0 + w)]
    tris = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4),
            (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
    return verts, tris


def write_ascii_stl(path, verts, tris, header="solid part"):
    lines = [header]
    for a, b, c in tris:
        lines += ["  facet normal 0 0 1", "    outer loop"]
        lines += [f"      vertex {x:.6g} {y:.6g} {z:.6g}" for x, y, z in (verts[a], verts[b], verts[c])]
        lines += ["    endloop", "  endfacet"]
    lines.append("endsolid part")
    path.write_text("\n".join(lines) + "\n")
    return path


def write_binary_stl(path, verts, tris, header=b"binary stl"):
    out = bytearray(header.ljust(80, b" "))
    out += struct.pack("<I", len(tris))
    for a, b, c in tris:
        out += struct.pack("<12fH", 0, 0, 1, *verts[a], *verts[b], *verts[c], 0)
    path.write_bytes(bytes(out))
    return path


def mesh_xml(obj_id, verts, tris):
    vx = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in verts)
    tx = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    return (f'<object id="{obj_id}" type="model"><mesh><vertices>{vx}</vertices>'
            f'<triangles>{tx}</triangles></mesh></object>')


RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>\n')


def write_3mf(path, resources, build_items, extra=None, settings='<config><object id="1"/></config>'):
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{CORE}" xmlns:p="{PROD}">'
             f'<metadata name="Application">test</metadata><resources>{resources}</resources>'
             f'<build>{build_items}</build></model>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", settings)
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return path


def approx(seq, expected, tol=1e-3):
    return all(math.isclose(a, b, abs_tol=tol) for a, b in zip(seq, expected))


# ---- STL ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("writer", [write_ascii_stl, write_binary_stl])
def test_stl_bbox_and_scale_about_bottom_centre(tmp_path, writer):
    src = writer(tmp_path / "part.stl", *box(10, 20, 0, 40, 30, 12))
    assert approx(model_bbox(src), (40, 30, 12))
    out = scale_model(src, 1.5, tmp_path / "out" / "part_150.stl")
    assert approx(model_bbox(out), (60, 45, 18))
    (x0, y0, z0), (x1, y1, z1) = model_bounds(out)
    assert approx(((x0 + x1) / 2, (y0 + y1) / 2, z0), (30, 35, 0))  # same centre, still on the bed
    assert (writer is write_binary_stl) == customize._stl_is_binary(out.read_bytes())


def test_binary_stl_whose_header_starts_with_solid(tmp_path):
    src = write_binary_stl(tmp_path / "tricky.stl", *box(0, 0, 0, 10, 10, 10), header=b"solid exported by CAD")
    assert approx(model_bbox(src), (10, 10, 10))
    assert approx(model_bbox(scale_model(src, 0.5, tmp_path / "half.stl")), (5, 5, 5))


def test_ascii_stl_keeps_text_layout(tmp_path):
    src = write_ascii_stl(tmp_path / "a.stl", *box(0, 0, 0, 10, 10, 10))
    out = scale_model(src, 2, tmp_path / "b.stl")
    text = out.read_text()
    assert text.startswith("solid part") and text.count("vertex") == 36 and "facet normal 0 0 1" in text


# ---- 3MF ------------------------------------------------------------------------------------------
def test_3mf_item_without_transform_gets_one(tmp_path):
    src = write_3mf(tmp_path / "m.3mf", mesh_xml(1, *box(0, 0, 0, 20, 10, 5)), '<item objectid="1"/>')
    assert approx(model_bbox(src), (20, 10, 5))
    out = scale_model(src, 2, tmp_path / "m2.3mf")
    assert approx(model_bbox(out), (40, 20, 10))
    with zipfile.ZipFile(out) as z:
        xml = z.read("3D/3dmodel.model").decode()
    assert 'transform="2 0 0 0 2 0 0 0 2 -10 -5 0"' in xml  # scaled about the bottom-centre (10, 5, 0)
    (x0, y0, z0), (x1, y1, _) = model_bounds(out)
    assert approx((x0, y0, z0, x1, y1), (-10, -5, 0, 30, 15))


def test_3mf_existing_transform_multiplied_and_entries_preserved(tmp_path):
    # Bambu-style: mesh centred on the origin, item translated to the plate centre
    res = mesh_xml(1, *box(-10, -10, -5, 20, 20, 10))
    src = write_3mf(tmp_path / "bambu.3mf", res, '<item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 5" '
                                                   'printable="1"/>', extra={"Metadata/plate_1.png": b"\x89PNGxx"})
    assert approx(model_bbox(src), (20, 20, 10))
    out = scale_model(src, 0.5, tmp_path / "small.3mf")
    (x0, y0, z0), (x1, y1, z1) = model_bounds(out)
    assert approx((x0, x1, y0, y1, z0, z1), (123, 133, 123, 133, 0, 5))
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        assert a.namelist() == b.namelist()
        for n in a.namelist():
            if n != "3D/3dmodel.model":
                assert a.read(n) == b.read(n)
        xml = b.read("3D/3dmodel.model").decode()
    assert 'printable="1"' in xml and '<metadata name="Application">test</metadata>' in xml
    assert 'transform="0.5 0 0 0 0.5 0 0 0 0.5 128 128 2.5"' in xml


def test_3mf_components_in_other_part_with_rotation(tmp_path):
    # object 2 (root) -> component object 1 in /3D/Objects/part.model, rotated 90 deg about Z
    part = (f'<?xml version="1.0"?><model unit="millimeter" xmlns="{CORE}"><resources>'
            + mesh_xml(1, *box(0, 0, 0, 30, 10, 4)) + "</resources><build/></model>")
    res = (f'<object id="2" type="model"><components><component p:path="/3D/Objects/part.model" objectid="1" '
           f'transform="0 1 0 -1 0 0 0 0 1 0 0 0"/></components></object>')
    src = write_3mf(tmp_path / "comp.3mf", res, '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 100 100 0"/>',
                    extra={"3D/Objects/part.model": part})
    assert approx(model_bbox(src), (10, 30, 4))  # rotated: x/y swapped
    out = scale_model(src, 2, tmp_path / "comp2.3mf")
    assert approx(model_bbox(out), (20, 60, 8))
    assert approx(model_bounds(out)[0][2:], (0,))


def test_3mf_multiple_items_keep_layout(tmp_path):
    res = mesh_xml(1, *box(0, 0, 0, 10, 10, 10))
    items = ('<item objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
             '<item objectid="1" transform="1 0 0 0 1 0 0 0 1 20 0 0"/>')
    src = write_3mf(tmp_path / "two.3mf", res, items)
    assert approx(model_bbox(src), (30, 10, 10))
    out = scale_model(src, 2, tmp_path / "two2.3mf")
    assert approx(model_bbox(out), (60, 20, 20))  # gap scales too: no overlap


def test_3mf_rotated_45_degrees_reads_vertices(tmp_path):
    c = math.sqrt(0.5)
    res = mesh_xml(1, *box(-5, -5, 0, 10, 10, 10))
    src = write_3mf(tmp_path / "rot.3mf", res, f'<item objectid="1" transform="{c} {c} 0 {-c} {c} 0 0 0 1 50 50 0"/>')
    diag = 10 * math.sqrt(2)
    assert approx(model_bbox(src), (diag, diag, 10))  # exact, not the inflated corner box
    assert approx(model_bbox(scale_model(src, 2, tmp_path / "rot2.3mf")), (2 * diag, 2 * diag, 20))


def test_3mf_multi_plate_project_scales_each_plate_in_place(tmp_path):
    res = mesh_xml(1, *box(-10, -10, 0, 20, 20, 10)) + mesh_xml(2, *box(-30, -5, 0, 60, 10, 4))
    items = ('<item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0"/>'
             '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 435 128 0"/>')  # plate 2 sits right of plate 1
    cfg = ('<?xml version="1.0"?><config><object id="1"/><object id="2"/>'
           '<plate><metadata key="plater_id" value="1"/><model_instance><metadata key="object_id" value="1"/>'
           '<metadata key="instance_id" value="0"/></model_instance></plate>'
           '<plate><metadata key="plater_id" value="2"/><model_instance><metadata key="object_id" value="2"/>'
           '<metadata key="instance_id" value="0"/></model_instance></plate></config>')
    src2 = write_3mf(tmp_path / "plates.3mf", res, items, settings=cfg)
    assert approx(model_bbox(src2), (60, 20, 10))  # largest plate per axis, not the 337 mm union
    out = scale_model(src2, 2, tmp_path / "plates_x2.3mf")
    with zipfile.ZipFile(out) as z:
        xml = z.read("3D/3dmodel.model").decode()
    assert 'transform="2 0 0 0 2 0 0 0 2 128 128 0"' in xml and 'transform="2 0 0 0 2 0 0 0 2 435 128 0"' in xml


def test_3mf_errors(tmp_path):
    bad = tmp_path / "bad.3mf"
    bad.write_bytes(b"not a zip")
    with pytest.raises(CustomizeError):
        model_bbox(bad)
    empty = write_3mf(tmp_path / "empty.3mf", mesh_xml(1, *box(0, 0, 0, 1, 1, 1)), "")
    with pytest.raises(CustomizeError, match="no build items"):
        model_bbox(empty)


def test_refuses_sliced_and_unknown_files(tmp_path):
    for name in ("plate.gcode.3mf", "plate.gcode"):
        p = tmp_path / name
        p.write_bytes(b"x")
        with pytest.raises(CustomizeError, match="sliced"):
            scale_model(p, 2, tmp_path / "o.3mf")
    obj = tmp_path / "m.obj"
    obj.write_text("v 0 0 0")
    with pytest.raises(CustomizeError, match="only .stl and .3mf"):
        model_bbox(obj)


def test_factor_bounds_and_format(tmp_path):
    src = write_ascii_stl(tmp_path / "a.stl", *box(0, 0, 0, 10, 10, 10))
    for f in (0, -1, 100, float("nan"), "abc"):
        with pytest.raises(CustomizeError):
            scale_model(src, f, tmp_path / "b.stl")
    with pytest.raises(CustomizeError, match="keep the .stl"):
        scale_model(src, 2, tmp_path / "b.3mf")
    assert customize.factor_for_size((10, 20, 5), 100) == 5.0
    assert customize.fits_build_volume((256, 10, 10)) and not customize.fits_build_volume((257, 10, 10))


def test_mechanism_words():
    assert customize.mechanism_words("box_lid.stl") == ["lid"]
    assert "kapak" in customize.mechanism_words("Gül kutusu kapak.3mf")
    assert customize.mechanism_words("solid_block.stl") == []
    assert customize.mechanism_words("Vase.3mf") == []


# ---- templates ------------------------------------------------------------------------------------
def test_templates_exist_and_defaults():
    for name, t in customize.TEMPLATES.items():
        assert (customize.TEMPLATE_DIR / t["file"]).is_file()
        scad = (customize.TEMPLATE_DIR / t["file"]).read_text()
        for p in t["params"]:
            assert f"{p} = " in scad, (name, p)
    vals, ignored = customize.template_values("name_tag", {"text": "Sam", "colour": "red"})
    assert ignored == ["colour"] and vals["text"] == "Sam" and vals["width"] == 80.0
    long_vals, _ = customize.template_values("name_tag", {"text": "Bartholomew-Alexander"})
    assert long_vals["font_size"] < 10  # shrunk to fit the plate
    fixed, _ = customize.template_values("name_tag", {"text": "Bartholomew", "font_size": 12})
    assert fixed["font_size"] == 12
    with pytest.raises(CustomizeError, match="unknown template"):
        customize.template_values("rocket", {})


def test_render_template_without_openscad(monkeypatch, tmp_path):
    monkeypatch.setattr(customize.shutil, "which", lambda name: None)
    assert customize.openscad_available() is False
    with pytest.raises(CustomizeError, match="OpenSCAD is not installed"):
        customize.render_template("name_tag", {"text": "Sam"}, tmp_path / "tag.stl")


def _fake_openscad(tmp_path, monkeypatch, fail=False):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "args.txt"
    exe = bindir / "openscad"
    body = ('#!/bin/sh\nprintf "%s\\n" "$@" > "' + str(log) + '"\n'
            + ('echo "ERROR: Parser error in file" >&2\nexit 1\n' if fail else
               'while [ $# -gt 0 ]; do if [ "$1" = "-o" ]; then shift; OUT="$1"; fi; shift; done\n'
               'printf "solid t\\n facet normal 0 0 1\\n outer loop\\n vertex 0 0 0\\n vertex 80 0 0\\n'
               ' vertex 0 25 4.2\\n endloop\\n endfacet\\nendsolid t\\n" > "$OUT"\n'))
    exe.write_text(body)
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    return log


def test_render_template_with_fake_openscad(tmp_path, monkeypatch):
    log = _fake_openscad(tmp_path, monkeypatch)
    assert customize.openscad_available()
    out = customize.render_template("name_tag", {"text": 'Sa"m\\', "width": "90"}, tmp_path / "o" / "tag")
    assert out.suffix == ".stl" and approx(model_bbox(out), (80, 25, 4.2))
    args = log.read_text().splitlines()
    assert args[0] == "-o" and args[-1].endswith("name_tag.scad")
    assert 'text="Sa\\"m\\\\"' in args and "width=90" in args and "thickness=3" in args


def test_render_template_reports_openscad_errors(tmp_path, monkeypatch):
    _fake_openscad(tmp_path, monkeypatch, fail=True)
    with pytest.raises(CustomizeError, match="Parser error"):
        customize.render_template("label_box", {"text": "Screws"}, tmp_path / "box.stl")


def test_render_template_validates_params(tmp_path, monkeypatch):
    _fake_openscad(tmp_path, monkeypatch)
    with pytest.raises(CustomizeError, match="must be a number"):
        customize.render_template("name_tag", {"width": "wide"}, tmp_path / "t.stl")
    with pytest.raises(CustomizeError, match="outside"):
        customize.render_template("name_tag", {"width": 999}, tmp_path / "t.stl")
    with pytest.raises(CustomizeError, match="must not be empty"):
        customize.render_template("name_tag", {"text": "  "}, tmp_path / "t.stl")
