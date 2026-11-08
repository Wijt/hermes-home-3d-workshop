"""tools.py: every home3d_* handler against a minimal in-memory backend (no simulator, no Hermes)."""

from __future__ import annotations

import json
import re
import struct
import time
from pathlib import Path

import pytest

from home3d_ws.home3d import tools as tools_mod
from home3d_ws.home3d.backends.base import (FAILED, FINISH, IDLE, PAUSE, RUNNING, Backend, BackendError, HMSError,
                                            LibraryFile, ModelCard, ModelInstance, PlateCheck, PrinterStatus,
                                            QueueItem, Snapshot, SliceResult, Tray)
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store

ROOT = Path(__file__).resolve().parents[1]
AUTO, STD = "auto-9", "std-10"
MUM, DAD, OWNER = "mum-id@s.whatsapp.net", "dad-id@s.whatsapp.net", "owner-id@s.whatsapp.net"


# ---- fake backend ---------------------------------------------------------------------------------
def make_gcode(w, d, h, *, eject=False, material="PLA", nozzle=220, bed=65, slots=1, used=1):
    zs = [round(0.2 * (i + 1), 2) for i in range(max(1, int(round(h / 0.2))))]
    cx = cy = 128.0
    out = ["; HEADER_BLOCK_START", "; model printing time: 1h 25m; total estimated time: 1h 30m 0s",
           "; total filament weight [g] : 25.5", f"; max_z_height: {zs[-1]:.2f}", f"; filament: {used}",
           "; HEADER_BLOCK_END", "; CONFIG_BLOCK_START", "; filament_type = " + ";".join([material] * slots),
           f"; nozzle_temperature = {nozzle}", "; curr_bed_type = Textured PEI Plate",
           f"; textured_plate_temp = {bed}", "; printer_model = Bambu Lab A1", "; enable_prime_tower = 0",
           "; CONFIG_BLOCK_END", "; EXECUTABLE_BLOCK_START", f"M140 S{bed}", f"M104 S{nozzle}", "G90", "M83"]
    for z in zs:
        out += [f"; Z_HEIGHT: {z}", f"G1 Z{z} F720", f"G1 X{cx - w / 2} Y{cy - d / 2} F9000",
                f"G1 X{cx + w / 2} Y{cy - d / 2} E1", f"G1 X{cx + w / 2} Y{cy + d / 2} E1",
                f"G1 X{cx - w / 2} Y{cy + d / 2} E1", f"G1 X{cx - w / 2} Y{cy - d / 2} E1"]
    if eject:
        out += ["; ===== HOME3D AUTO-EJECT v1 =====", "G1 Z2.5 F600", "G1 Y250 F3000"]
    out.append("; EXECUTABLE_BLOCK_END")
    return "\n".join(out) + "\n"


def stl_bytes(w, d, h):
    verts = [(x, y, z) for z in (0.0, h) for y in (0.0, d) for x in (0.0, w)]
    tris = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4),
            (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
    out = bytearray(b"fake".ljust(80, b" ")) + struct.pack("<I", len(tris))
    for a, b, c in tris:
        out += struct.pack("<12fH", 0, 0, 1, *verts[a], *verts[b], *verts[c], 0)
    return bytes(out)


class FakeBackend(Backend):
    name = "fake"

    def __init__(self):
        self.state = PrinterStatus(state=IDLE, bed_temp=24.0, nozzle_temp=25.0, trays=[
            Tray(slot=0, material="PLA", color="#FFFFFF"), Tray(slot=1, material="PLA", color="#D01010"),
            Tray(slot=2, material="PETG", color="#1040E0"), Tray(slot=3, material="", color="", loaded=False)])
        self.plate = PlateCheck(is_empty=True, difference_pct=2.0, confidence=0.9, message="empty")
        self.items: list[QueueItem] = []
        self.library: dict[int, dict] = {1: {"name": "vase.stl", "dims": (40, 40, 20)},
                                         2: {"name": "pen_holder_tall.stl", "dims": (10, 10, 60)},
                                         3: {"name": "box_lid.stl", "dims": (50, 50, 5)},
                                         4: {"name": "big_panel.stl", "dims": (200, 100, 10)}}
        self.calls: list[tuple] = []
        self.next_id = 100
        self.preset_material = {"11": "PLA", "12": "PETG"}

    def _id(self):
        self.next_id += 1
        return self.next_id

    # read
    def status(self):
        return self.state

    def queue(self, include_done=False):
        return [q for q in self.items if include_done or q.status in ("pending", "printing")]

    def snapshot(self, out_dir, lit=True):
        self.calls.append(("snapshot",))
        p = Path(out_dir) / f"snap-{len(self.calls)}.jpg"
        p.write_bytes(b"\xff\xd8fakejpeg")
        return Snapshot(path=p, lit=lit, note="fake")

    def check_plate(self):
        self.calls.append(("check_plate",))
        return self.plate

    def resolve_model(self, url_or_id):
        if "bad" in url_or_id:
            raise BackendError("POST /makerworld/resolve: 404 not found")
        mid = int(re.search(r"(\d+)", url_or_id).group(1))
        return ModelCard(model_id=mid, title=f"Model {mid}", url=f"https://makerworld.com/en/models/{mid}",
                         cover_url=f"https://example.invalid/{mid}.jpg", license="CC BY", likes=10,
                         summary="<p>" + "x" * 500,
                         instances=[ModelInstance(profile_id=mid * 10 + 2, printer_models=["A1 mini"]),
                                    ModelInstance(profile_id=mid * 10 + 1, printer_models=["Bambu Lab A1", "P1S"],
                                                  print_time_min=42, weight_g=12.5)])

    def library_gcode(self, library_file_id, max_bytes=8_000_000):
        e = self.library[library_file_id]
        if "gcode" not in e:
            raise BackendError("not sliced")
        return e["gcode"]

    def preview_url(self, library_file_id):
        return f"http://192.168.1.50:8000/gcode-viewer?library_file={library_file_id}&plate=1"

    # library writes
    def import_model(self, model_id, profile_id=None):
        self.calls.append(("import", model_id, profile_id))
        lid = self._id()
        self.library[lid] = {"name": f"model_{model_id}.3mf", "dims": (40, 40, 20)}
        return LibraryFile(id=lid, name=self.library[lid]["name"], kind="3mf")

    def upload_file(self, path):
        from home3d_ws.home3d.customize import model_bbox

        lid = self._id()
        self.library[lid] = {"name": Path(path).name, "dims": model_bbox(path), "data": Path(path).read_bytes()}
        self.calls.append(("upload", Path(path).name))
        return LibraryFile(id=lid, name=Path(path).name, kind="stl")

    def download_file(self, library_file_id, out_dir):
        e = self.library[library_file_id]
        p = Path(out_dir) / e["name"]
        p.write_bytes(e.get("data") or stl_bytes(*e["dims"]))
        return p

    def slice(self, library_file_id, options, timeout_s=900):
        self.calls.append(("slice", library_file_id, options.printer_preset, options.process_preset,
                           tuple(options.filament_presets), tuple(options.filament_colours)))
        src = self.library[library_file_id]
        material = self.preset_material.get(options.filament_presets[0], "PLA")
        text = make_gcode(*src["dims"], eject=options.printer_preset == AUTO, material=material,
                          nozzle=245 if material == "PETG" else 220, bed=70 if material == "PETG" else 65,
                          **src.get("slots", {}))
        lid = self._id()
        name = src["name"].rsplit(".", 1)[0] + ".gcode.3mf"
        self.library[lid] = {"name": name, "dims": src["dims"], "gcode": text}
        return SliceResult(library_file_id=lid, name=name, print_time_s=5400, filament_g=25.5,
                           filament_types=[material], gcode_text=text)

    # queue / printer
    def queue_add(self, library_file_id, *, ams_mapping=None, plate_id=None, manual_start=True):
        self.calls.append(("queue_add", library_file_id, ams_mapping, manual_start))
        item = QueueItem(id=self._id(), status="pending", name=self.library[library_file_id]["name"],
                         position=len(self.items) + 1, library_file_id=library_file_id, manual_start=manual_start)
        self.items.append(item)
        return item

    def queue_remove(self, queue_item_id):
        self.calls.append(("queue_remove", queue_item_id))
        self.items = [q for q in self.items if q.id != queue_item_id]

    def start(self, queue_item_id):
        self.calls.append(("start", queue_item_id))
        item = next(q for q in self.items if q.id == queue_item_id)
        item.status = "printing"
        self.state.state, self.state.job_name = RUNNING, item.name.replace(".gcode.3mf", "")
        return item

    def stop(self):
        self.calls.append(("stop",))
        self.state.state = FAILED

    def pause(self):
        self.calls.append(("pause",))
        self.state.state = PAUSE

    def resume(self):
        self.calls.append(("resume",))
        self.state.state = RUNNING

    def mark_plate_cleared(self):
        self.calls.append(("mark_plate_cleared",))

    def called(self, kind):
        return [c for c in self.calls if c[0] == kind]


class CronCtx:
    def current_cron_execution(self):
        return {"job": "x"}


def settings(**over):
    base = dict(backend="simulator", persona_name="Mıstık", language="en", owner_name="Owner",
                owner_ids=[OWNER], household=[{"id": MUM, "name": "Mum", "address_as": "Mum dear"},
                                              {"id": DAD, "name": "Dad"}],
                autoeject_printer_preset=AUTO, standard_printer_preset=STD,
                filament_presets={"PLA": "11", "PETG": "12"}, eject_cool_temp_c=30.0)
    base.update(over)
    return Settings(**base)


@pytest.fixture
def be():
    return FakeBackend()


@pytest.fixture
def rt(be, tmp_path):
    store = Store(tmp_path / "w.db")
    store.remember_sender("s-mum", MUM, "whatsapp")
    store.remember_sender("s-dad", DAD, "whatsapp")
    store.remember_sender("s-owner", OWNER, "whatsapp")
    return Runtime(settings=settings(), store=store, backend=be)


def tools(rt):
    return {name: handler for name, _, handler in tools_mod.build_tools(rt)}


def call(rt, name, args=None, session="s-mum"):
    raw = tools(rt)[name](args or {}, session_id=session, task_id="t1")
    assert isinstance(raw, str)
    return json.loads(raw)


def sliced(rt, fid=1, **args):
    return call(rt, "home3d_slice", {"library_file_id": fid, **args})


def queued(rt, fid=1, **args):
    s = sliced(rt, fid)
    return s, call(rt, "home3d_queue", {"action": "add", "sliced_file_id": s["sliced_file_id"], **args})


# ---- registration ---------------------------------------------------------------------------------
def test_build_tools_matches_manifest_and_descriptions(rt):
    built = tools_mod.build_tools(rt)
    names = [n for n, _, _ in built]
    manifest = re.findall(r"^  - (home3d_\w+)$", (ROOT / "plugin.yaml").read_text(), re.M)
    assert names == manifest
    for name, schema, handler in built:
        assert schema["name"] == name and schema["parameters"]["type"] == "object"
        first = schema["description"].split(". ")[0].rstrip(".")
        assert len(first) + 1 <= 60, (name, first)
        assert set(schema["parameters"].get("required", [])) <= set(schema["parameters"]["properties"])
        assert handler.__name__ == name


@pytest.mark.parametrize("bad", [None, {}, {"action": "explode"}, {"library_file_id": "abc"},
                                 {"queue_item_id": 1.5}, {"urls": 5}])
def test_handlers_never_raise(rt, bad):
    for name, _, handler in tools_mod.build_tools(rt):
        out = json.loads(handler(bad))
        assert "ok" in out, name
        if out["ok"] is False:
            assert out["error"], name


def test_backend_errors_become_envelopes(rt, be, monkeypatch):
    def boom(*a, **k):
        raise BackendError("GET /printers/1/status: 500 down")

    monkeypatch.setattr(be, "snapshot", boom)
    out = call(rt, "home3d_camera")
    assert out == {"ok": False, "error": "GET /printers/1/status: 500 down", "backend_error": True}


# ---- status / camera / find -----------------------------------------------------------------------
def test_status(rt, be):
    queued(rt)
    out = call(rt, "home3d_status")
    assert out["ok"] and out["backend"] == "fake" and out["printer"]["state"] == IDLE
    assert out["queue"][0]["ours"] and out["queue"][0]["requester"] == "Mum"
    assert out["jobs"][0]["requester"] == "Mum" and out["speaking"] == "Mum"
    assert out["watcher"]["fresh"] is False and "hint" in out["watcher"]
    rt.store.kv_set("watcher", {"state": IDLE, "plate_state": {"phase": "clear", "job_name": "vase"}})
    out = call(rt, "home3d_status")
    assert out["watcher"]["fresh"] is True and out["plate"]["phase"] == "clear"
    rt.store.kv_set("watcher", {"state": IDLE, "updated": time.time() - 3600})
    rt.store.kv_set("watcher_error", "GET /printers/1/status: timed out")
    out = call(rt, "home3d_status")
    assert out["watcher"]["fresh"] is False and "timed out" in out["watcher"]["error"]


def test_status_offline(rt, be, monkeypatch):
    monkeypatch.setattr(be, "status", lambda: (_ for _ in ()).throw(BackendError("timed out")))
    out = call(rt, "home3d_status")
    assert out["ok"] and out["printer"] == {"state": "OFFLINE", "connected": False, "error": "timed out"}


def test_camera(rt, be):
    out = call(rt, "home3d_camera", {"check_plate": True})
    assert out["ok"] and Path(out["path"]).is_file() and Path(out["path"]).parent == rt.media_dir.resolve()
    assert out["media_line"] == f"MEDIA:{out['path']}" and out["plate"]["is_empty"] is True
    assert not call(rt, "home3d_camera").get("plate")


def test_find_models(rt):
    urls = [f"https://makerworld.com/en/models/{i}#profileId-9" for i in range(1, 8)]
    out = call(rt, "home3d_find_models", {"urls": urls[:5] + ["bad-link"] + urls[5:]})
    assert out["ok"] and len(out["cards"]) == 5 and out["errors"][0]["input"] == "bad-link"
    assert out["skipped"] == urls[5:] and "site:makerworld.com" in out["hint"]
    card = out["cards"][0]
    assert [p["profile_id"] for p in card["a1_profiles"]] == [11] and card["other_profiles"] == 1
    assert len(card["summary"]) <= 240
    empty = call(rt, "home3d_find_models", {"urls": []})
    assert empty["ok"] is False and "site:makerworld.com" in empty["hint"]
    assert call(rt, "home3d_find_models", {"urls": "123, 456"})["cards"][1]["model_id"] == 456


# ---- import / customise ---------------------------------------------------------------------------
def test_import_records_request(rt, be):
    out = call(rt, "home3d_import", {"model_id": "https://makerworld.com/en/models/77", "request_text": "a vase",
                                     "channel": "voice"})
    assert out["ok"] and out["profile_id"] == 771 and be.called("import") == [("import", 77, 771)]
    req = rt.store.get_request(out["request_id"])
    assert req["requester"] == "Mum" and req["sender_id"] == MUM and req["channel"] == "voice"
    assert req["library_file_id"] == out["library_file_id"] and req["model_ref"].endswith("/models/77")
    again = call(rt, "home3d_import", {"model_id": 78, "profile_id": 782, "request_id": out["request_id"]})
    assert again["request_id"] == out["request_id"] and be.called("import")[-1] == ("import", 78, 782)
    assert call(rt, "home3d_import", {})["ok"] is False


def test_customize_scale(rt, be):
    out = call(rt, "home3d_customize", {"library_file_id": 1, "scale": "150%"})
    assert out["ok"] and out["factor"] == 1.5 and out["size_mm"] == pytest.approx([60, 60, 30], abs=1e-3)
    assert be.library[out["library_file_id"]]["name"] == "vase_150pct.stl"
    out = call(rt, "home3d_customize", {"library_file_id": 1, "target_size_mm": 100})
    assert out["size_mm"] == pytest.approx([100, 100, 50], abs=1e-3)
    assert not list(rt.work_dir.iterdir())  # temp files cleaned up


def test_customize_guards(rt, be):
    lid = call(rt, "home3d_customize", {"library_file_id": 3, "scale": 2})
    assert lid["ok"] is False and lid["needs_confirmation"] and "lid" in lid["error"]
    assert call(rt, "home3d_customize", {"library_file_id": 3, "scale": 2, "confirm_mechanism": True})["ok"]
    big = call(rt, "home3d_customize", {"library_file_id": 4, "scale": 2})
    assert big["ok"] is False and "does not fit" in big["error"]
    assert call(rt, "home3d_customize", {"library_file_id": 1})["ok"] is False
    assert call(rt, "home3d_customize", {"library_file_id": 1, "scale": 50})["ok"] is False


def test_customize_template_without_openscad(rt, monkeypatch):
    monkeypatch.setattr(tools_mod.customize.shutil, "which", lambda n: None)
    out = call(rt, "home3d_customize", {"template": "name_tag", "params": {"text": "Sam"}})
    assert out["ok"] is False and "OpenSCAD is not installed" in out["error"]
    assert call(rt, "home3d_customize", {"template": "rocket"})["ok"] is False


# ---- slice ----------------------------------------------------------------------------------------
def test_slice_auto_eject_eligible(rt, be):
    req = call(rt, "home3d_import", {"model_id": 5})
    out = sliced(rt, req["library_file_id"], colour="kırmızı")
    assert out["ok"] and out["eject"]["planned"] is True and out["eject"]["push_z"] == 2.5
    assert out["presets"] == {"printer": AUTO, "process": "0.20mm Standard @BBL A1", "filament": "11"}
    assert out["print_time_min"] == 90 and out["grams"] == 25.5 and out["max_z_mm"] == 20.0
    assert out["preview_url"].endswith(f"library_file={out['sliced_file_id']}&plate=1")
    assert out["suggested_ams_slot"] == 1 and out["colour"] == "#D32F2F"
    assert len(be.called("slice")) == 1 and out["discarded_sliced_file_id"] is None
    assert rt.store.get_request(req["request_id"])["sliced_file_id"] == out["sliced_file_id"]
    assert out["request_id"] == req["request_id"]


def test_slice_auto_not_eligible_reslices_standard(rt, be):
    out = sliced(rt, 2, quality="fine")
    assert out["ok"] and out["eject"]["planned"] is False and out["eject"]["reasons"]
    assert any("footprint" in r for r in out["eject"]["reasons"])
    assert [c[2] for c in be.called("slice")] == [AUTO, STD]
    assert out["presets"]["printer"] == STD and out["presets"]["process"] == "0.16mm High Quality @BBL A1"
    assert out["discarded_sliced_file_id"] is not None and out["discarded_sliced_file_id"] != out["sliced_file_id"]
    assert rt.store.kv_get(f"slice:{out['sliced_file_id']}")["eject_planned"] is False


def test_slice_petg_never_ejected(rt, be):
    out = sliced(rt, 1, material="petg", colour="blue")
    assert out["eject"]["planned"] is False and any("PETG" in r for r in out["eject"]["reasons"])
    assert out["presets"]["filament"] == "12" and out["suggested_ams_slot"] == 2
    assert [c[2] for c in be.called("slice")] == [STD]  # no wasted auto-eject slice


def test_slice_eject_off_and_forced(rt, be):
    off = sliced(rt, 1, eject="off")
    assert off["eject"]["planned"] is False and off["eject"]["reasons"] == ["eject=off"]
    assert [c[2] for c in be.called("slice")] == [STD]
    forced = sliced(rt, 2, eject="on")
    assert forced["eject"]["planned"] is True and any("forced" in w for w in forced["warnings"])
    assert call(rt, "home3d_slice", {"library_file_id": 1, "eject": "maybe"})["ok"] is False
    assert call(rt, "home3d_slice", {"library_file_id": 1, "quality": "ultra"})["ok"] is False


def test_slice_without_autoeject_preset_and_fallbacks(be, tmp_path):
    rt = Runtime(settings=settings(autoeject_printer_preset="", standard_printer_preset="",
                                   filament_presets={}, process_presets={"draft": "my draft"}),
                 store=Store(tmp_path / "x.db"), backend=be)
    out = sliced(rt, 1, quality="draft", colour="#00ff00")
    assert out["eject"]["planned"] is False and out["eject"]["reasons"] == ["no auto-eject printer preset configured"]
    assert out["presets"] == {"printer": tools_mod.DEFAULT_PRINTER_PRESET, "process": "my draft",
                              "filament": "Bambu PLA Basic @BBL A1"}
    assert out["suggested_ams_slot"] is None and any("close to #00FF00" in w for w in out["warnings"])
    assert be.called("slice")[0][5] == ("#00FF00",)


# ---- queue ----------------------------------------------------------------------------------------
def test_queue_add_records_job(rt, be):
    req = call(rt, "home3d_import", {"model_id": 5})
    s = sliced(rt, req["library_file_id"])
    out = call(rt, "home3d_queue", {"action": "add", "sliced_file_id": s["sliced_file_id"], "ams_slot": 1})
    assert out["ok"] and out["manual_start"] is True and out["ams_mapping"] == [1] and out["eject_planned"]
    assert be.called("queue_add") == [("queue_add", s["sliced_file_id"], [1], True)]
    job = rt.store.get_job(out["queue_item_id"])
    assert job["requester"] == "Mum" and job["eject_planned"] == 1 and job["max_z_mm"] == 20.0
    assert job["request_id"] == req["request_id"] and job["state"] == "queued"
    r = rt.store.get_request(req["request_id"])
    assert r["status"] == "queued" and r["queue_item_id"] == out["queue_item_id"]
    listed = call(rt, "home3d_queue", {"action": "list"})
    assert listed["items"][0]["ours"] and listed["items"][0]["eject_planned"] is True


def test_queue_add_mapping_and_tray_warnings(rt, be):
    be.library[9] = {"name": "multi.3mf", "dims": (40, 40, 20), "slots": {"slots": 3, "used": 2}}
    s = sliced(rt, 9)
    out = call(rt, "home3d_queue", {"action": "add", "sliced_file_id": s["sliced_file_id"], "ams_slot": 2})
    assert out["ams_mapping"] == [-1, 2, -1] and any("PETG" in w for w in out["warnings"])
    _, auto = queued(rt, 1)  # no ams_slot: the suggested one
    assert auto["ams_mapping"] == [0] and any("suggested" in w for w in auto["warnings"])
    assert call(rt, "home3d_queue", {"action": "add"})["ok"] is False


def test_queue_add_foreign_sliced_file_reads_gcode(rt, be):
    be.library[50] = {"name": "foreign.gcode.3mf", "dims": (40, 40, 20), "gcode": make_gcode(40, 40, 20, eject=True)}
    out = call(rt, "home3d_queue", {"action": "add", "sliced_file_id": 50, "ams_slot": 0}, session="s-dad")
    assert out["eject_planned"] is True and out["requester"] == "Dad"
    assert rt.store.get_job(out["queue_item_id"])["max_z_mm"] == 20.0


def test_queue_remove_permissions(rt, be):
    _, q = queued(rt)
    qid = q["queue_item_id"]
    no = call(rt, "home3d_queue", {"action": "remove", "queue_item_id": qid}, session="s-dad")
    assert no["ok"] is False and not be.called("queue_remove")
    ok = call(rt, "home3d_queue", {"action": "remove", "queue_item_id": qid}, session="s-mum")
    assert ok["ok"] and be.called("queue_remove") == [("queue_remove", qid)]
    assert rt.store.get_job(qid)["state"] == "cancelled"
    _, q2 = queued(rt)
    assert call(rt, "home3d_queue", {"action": "remove", "queue_item_id": q2["queue_item_id"]},
                session="s-owner")["ok"]
    assert call(rt, "home3d_queue", {"action": "remove", "queue_item_id": 999})["ok"] is False


# ---- start ----------------------------------------------------------------------------------------
def test_start_ok(rt, be):
    _, q = queued(rt)
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]}, session="s-owner")
    assert out["ok"] and out["requester"] == "Mum" and out["eject_planned"] is True
    assert be.called("start") == [("start", q["queue_item_id"])] and be.called("check_plate")
    job = rt.store.get_job(q["queue_item_id"])
    assert job["state"] == "printing" and job["started_ts"]
    assert rt.store.request_for_queue_item(q["queue_item_id"]) is None  # no request (sliced directly)


def test_start_blocked_by_plate_and_state(rt, be):
    _, q = queued(rt)
    be.plate = PlateCheck(is_empty=None, difference_pct=22.0, message="uncertain")
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] is False and out["blocked"] and "plate_uncertain" in out["codes"]
    be.plate, be.state.state = PlateCheck(is_empty=True), RUNNING
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert "busy" in out["codes"]
    be.state.state = IDLE
    be.state.hms = [HMSError(code="0700-2000-0002-0001", message="filament runout")]
    assert "hms" in call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})["codes"]
    assert not be.called("start")


def test_start_never_jumps_someone_elses_job(rt, be):
    family = be.queue_add(1)  # queued outside the workshop, ahead of ours
    _, q = queued(rt)
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] is False and "jump" in out["codes"] and not be.called("start")
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"], "allow_jump": True})
    assert out["ok"] and any(str(family.id) in w for w in out["warnings"])


def test_start_blocked_in_cron(be, tmp_path):
    rt = Runtime(CronCtx(), settings=settings(), store=Store(tmp_path / "c.db"), backend=be)
    _, q = queued(rt)
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] is False and "in_cron" in out["codes"] and not be.called("start")


def test_start_message_in_household_language(be, tmp_path):
    rt = Runtime(settings=settings(language="tr"), store=Store(tmp_path / "t.db"), backend=be)
    be.plate = PlateCheck(is_empty=False, difference_pct=60.0)
    _, q = queued(rt)
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["message"].startswith("Başlatamam") and out["error"].startswith("Cannot start")


# ---- stop / pause / resume ------------------------------------------------------------------------
def test_stop_logs_who_and_reason(rt, be):
    _, q = queued(rt)
    call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]}, session="s-owner")
    out = call(rt, "home3d_stop", {"action": "stop", "reason": "spaghetti"}, session="s-dad")
    assert out["ok"] and out["by"] == "Dad" and be.called("stop")
    ev = rt.store.events(kind="stop_request")[0]
    assert json.loads(ev["payload"])["who"] == "Dad" and json.loads(ev["payload"])["reason"] == "spaghetti"
    job = rt.store.get_job(q["queue_item_id"])
    assert job["state"] == "cancelled" and "Dad" in job["outcome"]
    idle = call(rt, "home3d_stop", {"action": "stop", "reason": "again"})
    assert idle["ok"] is False and len(be.called("stop")) == 1


def test_stop_without_status_still_stops(rt, be, monkeypatch):
    monkeypatch.setattr(be, "status", lambda: (_ for _ in ()).throw(BackendError("timeout")))
    out = call(rt, "home3d_stop", {"action": "stop", "reason": "smoke"})
    assert out["ok"] and be.called("stop")
    assert call(rt, "home3d_stop", {"action": "pause", "reason": "x"})["ok"] is False


def test_pause_resume(rt, be, tmp_path):
    be.state.state, be.state.job_name = RUNNING, "vase"
    assert call(rt, "home3d_stop", {"action": "pause", "reason": "filament"})["ok"] and be.called("pause")
    cron = Runtime(CronCtx(), settings=settings(), store=rt.store, backend=be)
    assert call(cron, "home3d_stop", {"action": "resume", "reason": "ok"})["ok"] is False
    out = call(rt, "home3d_stop", {"action": "resume", "reason": "swapped"}, session="s-owner")
    assert out["ok"] and be.called("resume")
    assert call(rt, "home3d_stop", {"action": "resume", "reason": "x"})["ok"] is False  # not paused


# ---- clear plate ----------------------------------------------------------------------------------
def test_clear_plate_check_and_confirm(rt, be):
    _, q = queued(rt)
    rt.store.upsert_job(q["queue_item_id"], state="finished")
    be.state.state, be.state.bed_temp = FINISH, 55.0
    chk = call(rt, "home3d_clear_plate", {"action": "check"})
    assert chk["ok"] and chk["media_line"].startswith("MEDIA:") and chk["can_confirm"] is False
    hot = call(rt, "home3d_clear_plate", {"action": "confirm"})
    assert hot["ok"] is False and "bed_hot" in hot["codes"] and not be.called("mark_plate_cleared")
    be.state.bed_temp = 26.0
    out = call(rt, "home3d_clear_plate", {"action": "confirm"}, session="s-owner")
    assert out["ok"] and out["cleared"] and be.called("mark_plate_cleared")
    assert rt.store.get_job(q["queue_item_id"])["state"] == "cleared"
    be.plate = PlateCheck(is_empty=False, difference_pct=70.0)
    assert "plate_occupied" in call(rt, "home3d_clear_plate", {"action": "confirm"})["codes"]


# ---- household ------------------------------------------------------------------------------------
def test_household(rt):
    who = call(rt, "home3d_household", {"action": "who"})
    assert who["speaking"] == {"name": "Mum", "role": "family", "address_as": "Mum dear"}
    assert {p["name"] for p in who["people"]} == {"Owner", "Mum", "Dad"}
    assert "id" not in who["people"][0]
    assert call(rt, "home3d_household", {"action": "remember", "text": "likes red"})["person"] == "Mum"
    req = call(rt, "home3d_import", {"model_id": 5, "request_text": "flower pot"})
    hist = call(rt, "home3d_household", {"action": "history"})
    assert hist["person"] == "Mum" and hist["requests"][0]["text"] == "flower pot"
    assert hist["notes"][0]["text"] == "likes red"
    assert call(rt, "home3d_household", {"action": "history", "person": "Dad"}, session="s-dad")["requests"] == []
    note = call(rt, "home3d_household", {"action": "note", "text": "too small", "request_id": req["request_id"]})
    assert note["ok"] and rt.store.get_request(req["request_id"])["outcome"] == "too small"
    assert call(rt, "home3d_household", {"action": "note", "text": "garage is cold"})["count"] == 1
    assert call(rt, "home3d_household", {"action": "remember"})["ok"] is False


# ---- human-needed / upgrades ----------------------------------------------------------------------
def test_human_needed_to_upgrade_flow(rt):
    pytest.importorskip("home3d_ws.home3d.upgrades")
    for i in range(2):
        out = call(rt, "home3d_human_needed", {"action": "log", "kind": "remove_part", "detail": f"#{i}"})
        assert out["ok"] and out["new_proposals"] == [] and out["who"] == "Mum"
    third = call(rt, "home3d_human_needed", {"action": "log", "kind": "remove_part"}, session="s-dad")
    assert third["count"] == 3 and len(third["new_proposals"]) == 1 and third["who"] == "Dad"
    uid = third["new_proposals"][0]["id"]
    odd = call(rt, "home3d_human_needed", {"action": "log", "kind": "glued fingers"})
    assert odd["kind"] == "other"
    listed = call(rt, "home3d_human_needed", {"action": "list"})
    assert listed["counts_30d"]["remove_part"] == 3 and listed["thresholds"]["remove_part"] == 3
    ups = call(rt, "home3d_upgrades", {"action": "list"})
    assert ups["upgrades"][0]["id"] == uid and ups["upgrades"][0]["status"] == "proposed"
    assert call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": uid}, session="s-mum")["ok"] is False
    assert call(rt, "home3d_upgrades", {"action": "installed", "upgrade_id": uid},
                session="s-owner")["ok"] is False  # not accepted yet
    acc = call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": uid, "note": "do it"}, session="s-owner")
    assert acc["ok"] and acc["status"] == "accepted" and "makerworld" in acc["next"]
    for step in ("printing", "installed"):
        assert call(rt, "home3d_upgrades", {"action": step, "upgrade_id": uid}, session="s-owner")["status"] == step
    assert call(rt, "home3d_upgrades", {"action": "evaluate"})["new_proposals"] == []
    assert call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": 999}, session="s-owner")["ok"] is False
