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
from home3d_ws.home3d.hooks import approval_target, hms_ack_detail
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
        return [q for q in self.items if include_done or q.status.lower() in ("pending", "printing")]

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


GATED = {"home3d_start": "start", "home3d_clear_plate": "clear_plate", "home3d_stop": "resume"}


def approve(rt, name, args, session):
    """What the pre_tool_call hook does for an owner session whose gate passed: one single-use pass."""
    qid = args.get("queue_item_id")
    target = approval_target(GATED[name], int(qid) if qid is not None else None, bool(args.get("allow_jump")))
    detail = ""
    if GATED[name] == "resume" and args.get("ack_hms"):  # the hook records the printer errors the owner was shown
        detail = hms_ack_detail([h.code for h in rt.backend.status().blocking_hms])
    rt.store.issue_pass(name, target, session, detail=detail)


def later(rt):
    """More than 90 s pass: the runtime's shared "plate is empty" answer is no longer reused."""
    rt.forget_plate_check()


def gated(rt, name, args, session="s-owner"):
    """An approved call: pass issued for exactly this call, then the handler."""
    approve(rt, name, args, session)
    return call(rt, name, args, session)


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


def test_status_and_list_call_only_active_jobs_ours(rt, be):
    _, q = queued(rt)
    rt.store.upsert_job(q["queue_item_id"], state="cancelled")  # e.g. an id an old workshop job once had
    entry = call(rt, "home3d_status")["queue"][0]
    assert entry["ours"] is False and "requester" not in entry
    assert call(rt, "home3d_queue", {"action": "list"})["items"][0]["ours"] is False


def test_tools_use_public_store_api_only():
    src = Path(tools_mod.__file__).read_text(encoding="utf-8")
    assert "_rows(" not in src and "_exec(" not in src


def test_status_offline(rt, be, monkeypatch):
    monkeypatch.setattr(be, "status", lambda: (_ for _ in ()).throw(BackendError("timed out")))
    out = call(rt, "home3d_status")
    assert out["ok"] and out["printer"] == {"state": "OFFLINE", "connected": False, "error": "timed out"}


def test_camera(rt, be):
    out = call(rt, "home3d_camera", {"check_plate": True})
    assert out["ok"] and Path(out["path"]).is_file() and Path(out["path"]).parent == rt.media_dir.resolve()
    assert out["media_line"] == f"MEDIA:{out['path']}" and out["plate"]["is_empty"] is True
    assert "light_ok" in out["plate"] and "opinion" in out["plate"]["note"]
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


def test_import_needs_the_requesters_own_words_for_a_new_request(rt, be):
    """Fix round 2 (e2e F4): family texts name the print by request_text, so a new request never falls back to the
    English MakerWorld title."""
    out = call(rt, "home3d_import", {"model_id": 77})
    assert out["ok"] is False and "request_text" in out["error"] and "çiçek kutusu" in out["error"]
    assert be.called("import") == []
    ok = call(rt, "home3d_import", {"model_id": 77, "request_text": "çiçek kutusu"})
    assert rt.store.get_request(ok["request_id"])["text"] == "çiçek kutusu"


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
    req = call(rt, "home3d_import", {"model_id": 5, "request_text": "vase"})
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
    req = call(rt, "home3d_import", {"model_id": 5, "request_text": "vase"})
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
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] and out["requester"] == "Mum" and out["eject_planned"] is True
    assert be.called("start") == [("start", q["queue_item_id"])] and be.called("check_plate")
    job = rt.store.get_job(q["queue_item_id"])
    assert job["state"] == "printing" and job["started_ts"]
    assert rt.store.request_for_queue_item(q["queue_item_id"]) is None  # no request (sliced directly)
    assert not rt.store.peek_pass("home3d_start", str(q["queue_item_id"]), "s-owner")  # used up


@pytest.mark.parametrize("name,args", [("home3d_start", {"queue_item_id": 0}),
                                       ("home3d_clear_plate", {"action": "confirm"}),
                                       ("home3d_stop", {"action": "resume", "reason": "x"})])
def test_gated_handlers_refuse_without_a_pass(rt, be, name, args):
    """ctx.dispatch_tool skips pre_tool_call: a direct handler call (any session, even the owner's) does nothing."""
    if name == "home3d_start":
        _, q = queued(rt)
        args = {"queue_item_id": q["queue_item_id"]}
    if name == "home3d_stop":
        be.state.state, be.state.job_name = PAUSE, "vase"
    be.state.bed_temp = 24.0
    before = list(be.calls)
    for session in ("s-owner", "s-mum", None):
        raw = tools(rt)[name](dict(args), **({"session_id": session} if session else {}))
        out = json.loads(raw)
        assert out["ok"] is False and out["blocked"] and "no approval pass found" in out["error"], out
        assert out["codes"] == ["no_pass"]
    assert be.calls == before  # not even a status read or a camera check
    for kind in ("start", "resume", "mark_plate_cleared"):
        assert not be.called(kind)


def test_a_pass_is_bound_to_session_target_and_single_use(rt, be):
    _, q = queued(rt)
    qid = q["queue_item_id"]
    approve(rt, "home3d_start", {"queue_item_id": qid}, "s-owner")
    assert call(rt, "home3d_start", {"queue_item_id": qid}, "s-mum")["codes"] == ["no_pass"]  # other session
    assert call(rt, "home3d_start", {"queue_item_id": qid, "allow_jump": True},
                "s-owner")["codes"] == ["no_pass"]  # a jump needs its own pass
    approve(rt, "home3d_start", {"queue_item_id": qid}, "s-owner")
    be.state.state = RUNNING  # gate refuses: the pass is still used up
    assert "busy" in call(rt, "home3d_start", {"queue_item_id": qid}, "s-owner")["codes"]
    be.state.state = IDLE
    assert call(rt, "home3d_start", {"queue_item_id": qid}, "s-owner")["codes"] == ["no_pass"]
    assert not be.called("start")
    tr = Runtime(settings=settings(language="tr"), store=rt.store, backend=be)
    assert call(tr, "home3d_start", {"queue_item_id": qid}, "s-owner")["message"].startswith("Bu işlem")


def test_store_failure_authorises_nothing(rt, be, monkeypatch):
    _, q = queued(rt)
    approve(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]}, "s-owner")
    for name in ("consume_pass", "take_pass"):
        monkeypatch.setattr(rt.store, name, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db locked")))
    out = call(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]}, "s-owner")
    assert out["blocked"] and not be.called("start")


def test_start_blocked_by_plate_and_state(rt, be):
    _, q = queued(rt)
    args = {"queue_item_id": q["queue_item_id"]}
    be.plate = PlateCheck(is_empty=None, difference_pct=22.0, message="uncertain")
    out = gated(rt, "home3d_start", args)
    assert out["ok"] is False and out["blocked"] and "plate_uncertain" in out["codes"]
    be.plate, be.state.state = PlateCheck(is_empty=True), RUNNING
    assert "busy" in gated(rt, "home3d_start", args)["codes"]
    be.state.state = IDLE
    be.state.hms = [HMSError(code="0700-2000-0002-0001", message="filament runout")]
    assert "hms" in gated(rt, "home3d_start", args)["codes"]
    be.state.hms = []
    later(rt)
    be.plate = PlateCheck(is_empty=True, difference_pct=1.0, light_ok=False, message="light warning")
    assert "plate_dark" in gated(rt, "home3d_start", args)["codes"]
    assert not be.called("start")


def test_start_after_a_failed_print_needs_the_owners_plate_confirmation(rt, be):
    _, q = queued(rt)
    args = {"queue_item_id": q["queue_item_id"]}
    be.state.state, be.state.job_name, be.state.bed_temp = FAILED, "old_part", 26.0
    out = gated(rt, "home3d_start", args)  # the camera thinks the plate is empty: not enough after a failure
    assert out["ok"] is False and "after_failure" in out["codes"] and not be.called("start")
    clear = gated(rt, "home3d_clear_plate", {"action": "confirm"})
    assert clear["ok"] and clear["cleared"] and clear["confirmed_for"] == "old_part"
    assert rt.store.plate_confirmed("old_part") and not rt.store.plate_confirmed("other_part")
    out = gated(rt, "home3d_start", args)
    assert out["ok"] and be.called("start")


def test_start_handler_remembers_a_failure_the_printer_forgot(rt, be):
    """safety 6 / e2e NEW-2 at the handler: IDLE after a power cycle, empty job name, camera "empty"."""
    _, q = queued(rt)
    args = {"queue_item_id": q["queue_item_id"]}
    be.state.state, be.state.job_name = IDLE, ""
    rt.store.record_failure("clip", "watcher")
    out = gated(rt, "home3d_start", args)
    assert out["ok"] is False and "after_failure" in out["codes"] and not be.called("start")
    clear = gated(rt, "home3d_clear_plate", {"action": "confirm"})
    assert clear["ok"] and rt.store.unconfirmed_failure() is None
    assert clear["next_job"]["id"] == q["queue_item_id"]  # the owner is told what to start next
    assert gated(rt, "home3d_start", args)["ok"] and be.called("start")


def test_band_reading_after_a_failure_can_be_confirmed_by_the_owner(rt, be):
    """e2e NEW-1 at the handlers: check says can_confirm, confirm records it, and the start then passes."""
    _, q = queued(rt)
    args = {"queue_item_id": q["queue_item_id"]}
    be.state.state, be.state.job_name, be.state.bed_temp = FAILED, "old_part", 26.0
    be.plate = PlateCheck(is_empty=None, difference_pct=19.9, message="uncertain: band", light_ok=True,
                          uncertain_band=True)
    chk = call(rt, "home3d_clear_plate", {"action": "check"})
    assert chk["can_confirm"] is True and chk["plate"]["uncertain_band"] is True
    assert any("confirm the plate is clear yourself" in w for w in chk["warnings"])
    assert "after_failure" in gated(rt, "home3d_start", args)["codes"]
    assert gated(rt, "home3d_clear_plate", {"action": "confirm"})["cleared"]
    out = gated(rt, "home3d_start", args)
    assert out["ok"] and any("owner confirmed" in w for w in out["warnings"])


def test_start_handler_skips_the_camera_when_the_printer_blocks(rt, be):
    _, q = queued(rt)
    be.state.state = RUNNING
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["codes"] == ["busy"] and not be.called("check_plate")


def test_start_handler_reports_a_light_left_on(rt, be):
    _, q = queued(rt)
    be.plate = PlateCheck(is_empty=True, difference_pct=1.0, light_ok=True,
                          message="empty (light_left_on: the chamber light could not be switched off again)")
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] and any("light_left_on" in w for w in out["warnings"])


def test_start_after_finish_warns_camera_only(rt, be):
    _, q = queued(rt)
    be.state.state, be.state.job_name = FINISH, "old_part"
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] and any("only the camera" in w for w in out["warnings"])


def test_start_shares_the_hooks_plate_check(rt, be):
    _, q = queued(rt)
    rt.plate_check()  # what pre_tool_call did a moment ago
    gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert len(be.called("check_plate")) == 1


def test_start_never_jumps_someone_elses_job(rt, be):
    family = be.queue_add(1)  # queued outside the workshop, ahead of ours
    _, q = queued(rt)
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] is False and "jump" in out["codes"] and not be.called("start")
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"], "allow_jump": True})
    assert out["ok"] and any(str(family.id) in w for w in out["warnings"])


def test_jump_check_ignores_old_workshop_ids(rt, be):
    family = be.queue_add(1)
    rt.store.upsert_job(family.id, name="old", state="cancelled")  # an id an old, cancelled workshop job had
    family.status = "Pending"  # status case does not matter
    _, q = queued(rt)
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert "jump" in out["codes"] and not be.called("start")


def test_start_blocked_in_cron(be, tmp_path):
    rt = Runtime(CronCtx(), settings=settings(), store=Store(tmp_path / "c.db"), backend=be)
    rt.store.remember_sender("s-owner", OWNER, "whatsapp")
    _, q = queued(rt)
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["ok"] is False and "in_cron" in out["codes"] and not be.called("start")


def test_start_message_in_household_language(be, tmp_path):
    rt = Runtime(settings=settings(language="tr"), store=Store(tmp_path / "t.db"), backend=be)
    be.plate = PlateCheck(is_empty=False, difference_pct=60.0)
    _, q = queued(rt)
    out = gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    assert out["message"].startswith("Başlatamam") and out["error"].startswith("Cannot start")


# ---- stop / pause / resume ------------------------------------------------------------------------
def test_stop_logs_who_and_reason(rt, be):
    _, q = queued(rt)
    gated(rt, "home3d_start", {"queue_item_id": q["queue_item_id"]})
    out = call(rt, "home3d_stop", {"action": "stop", "reason": "spaghetti"}, session="s-dad")  # no pass needed
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
    paused = call(rt, "home3d_stop", {"action": "pause", "reason": "filament"})
    assert paused["ok"] and be.called("pause") and "/home3d approve resume" in paused["next"]
    cron = Runtime(CronCtx(), settings=settings(), store=rt.store, backend=be)
    resume = {"action": "resume", "reason": "ok"}
    assert "in_cron" in gated(cron, "home3d_stop", resume)["codes"]
    out = gated(rt, "home3d_stop", {"action": "resume", "reason": "swapped"})
    assert out["ok"] and be.called("resume")
    assert "not_paused" in gated(rt, "home3d_stop", resume)["codes"]  # not paused any more


def test_resume_with_an_active_printer_error_needs_the_owners_ack(rt, be):
    be.state.state, be.state.job_name = PAUSE, "vase"
    be.state.hms = [HMSError(code="0C00-0300-0002-0001", message="first layer defect")]
    out = gated(rt, "home3d_stop", {"action": "resume"})
    assert out["blocked"] and "hms_unacknowledged" in out["codes"] and not be.called("resume")
    # ack_hms from someone who is not the owner does not count (even with a pass)
    out = gated(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, session="s-mum")
    assert "hms_unacknowledged" in out["codes"] and not be.called("resume")
    out = gated(rt, "home3d_stop", {"action": "resume", "ack_hms": True})
    assert out["ok"] and be.called("resume") and any("0C00-0300-0002-0001" in w for w in out["warnings"])
    ev = json.loads(rt.store.events(kind="resume_request")[0]["payload"])
    assert ev["hms_acknowledged"] == ["0C00-0300-0002-0001"]


def test_the_hms_ack_covers_only_the_errors_the_owner_was_shown(rt, be):
    """Fix round 2 (safety 2): a new printer error that appears while Hermes' prompt waits is not acknowledged."""
    be.state.state, be.state.job_name = PAUSE, "vase"
    be.state.hms = [HMSError(code="0700-2000-0002-0001", message="filament ran out")]
    approve(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")  # the owner saw the filament code
    be.state.hms.append(HMSError(code="0300-0100-0001-0007", message="heatbed fault"))  # a new fatal error
    out = call(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")
    assert out["blocked"] and "hms_unacknowledged" in out["codes"] and not be.called("resume")
    assert "0300-0100-0001-0007" in out["error"]
    # a pass without any acknowledged codes never acknowledges anything
    be.state.hms = [HMSError(code="0700-2000-0002-0001", message="filament ran out")]
    rt.store.issue_pass("home3d_stop", "", "s-owner")
    out = call(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")
    assert out["blocked"] and "hms_unacknowledged" in out["codes"] and not be.called("resume")
    # the error the owner saw cleared meanwhile: fewer errors than acknowledged is fine
    approve(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")
    be.state.hms = []
    out = call(rt, "home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")
    assert out["ok"] and be.called("resume")


# ---- clear plate ----------------------------------------------------------------------------------
def test_clear_plate_check_and_confirm(rt, be):
    _, q = queued(rt)
    rt.store.upsert_job(q["queue_item_id"], state="finished")
    be.state.state, be.state.job_name, be.state.bed_temp = FINISH, "vase", 55.0
    chk = call(rt, "home3d_clear_plate", {"action": "check"})  # anyone may look, no pass
    assert chk["ok"] and chk["media_line"].startswith("MEDIA:") and chk["can_confirm"] is False
    hot = gated(rt, "home3d_clear_plate", {"action": "confirm"})
    assert hot["ok"] is False and "bed_hot" in hot["codes"] and not be.called("mark_plate_cleared")
    be.state.bed_temp = None
    assert "bed_unknown" in gated(rt, "home3d_clear_plate", {"action": "confirm"})["codes"]
    be.state.bed_temp = 26.0
    out = gated(rt, "home3d_clear_plate", {"action": "confirm"})
    assert out["ok"] and out["cleared"] and be.called("mark_plate_cleared") and out["by"] == "Owner"
    assert rt.store.get_job(q["queue_item_id"])["state"] == "cleared"
    assert rt.store.plate_confirmed("vase")
    later(rt)
    be.plate = PlateCheck(is_empty=False, difference_pct=70.0)
    assert "plate_occupied" in gated(rt, "home3d_clear_plate", {"action": "confirm"})["codes"]


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
    # approve_start is logged but never proposed (owner approval is a safety step): no threshold is shown
    assert "approve_start" not in listed["thresholds"] and listed["never_proposed"] == ["approve_start"]
    waited = call(rt, "home3d_human_needed", {"action": "log", "kind": "approve_start"})
    assert waited["ok"] and waited["proposes"] is False and waited["threshold"] is None
    ups = call(rt, "home3d_upgrades", {"action": "list"})
    assert ups["upgrades"][0]["id"] == uid and ups["upgrades"][0]["status"] == "proposed"
    assert call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": uid}, session="s-mum")["ok"] is False
    assert call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": uid}, session="s-nobody")["ok"] is False
    assert call(rt, "home3d_upgrades", {"action": "installed", "upgrade_id": uid},
                session="s-owner")["ok"] is False  # not accepted yet
    acc = call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": uid, "note": "do it"}, session="s-owner")
    assert acc["ok"] and acc["status"] == "accepted" and "makerworld" in acc["next"]
    for step in ("printing", "installed"):
        assert call(rt, "home3d_upgrades", {"action": step, "upgrade_id": uid}, session="s-owner")["status"] == step
    assert call(rt, "home3d_upgrades", {"action": "evaluate"})["new_proposals"] == []
    assert call(rt, "home3d_upgrades", {"action": "accept", "upgrade_id": 999}, session="s-owner")["ok"] is False


def test_card_marks_native_and_a1_compatible_profiles(pkg):
    from home3d_ws.home3d.backends.base import ModelCard, ModelInstance
    from home3d_ws.home3d import tools as T
    card = ModelCard(model_id=1, title="Card wallet", instances=[
        ModelInstance(profile_id=1001, printer_models=["A1 mini"], compatible_models=["P1S", "A1"]),
        ModelInstance(profile_id=1002, printer_models=["A1"]),
        ModelInstance(profile_id=1003, printer_models=["P1S"], compatible_models=["X1C"])])
    d = T._card(card)
    assert [(p["profile_id"], p["fit"]) for p in d["a1_profiles"]] == [(1002, "native"), (1001, "a1_compatible")]
    assert d["other_profiles"] == 1 and "note" not in d
    only_compat = T._card(ModelCard(model_id=2, title="x", instances=[
        ModelInstance(profile_id=7, printer_models=["A1 mini"], compatible_models=["A1"])]))
    assert only_compat["a1_profiles"][0]["fit"] == "a1_compatible" and "re-slices" in only_compat["note"]
    none = T._card(ModelCard(model_id=3, title="y", instances=[ModelInstance(profile_id=8, printer_models=["A1 mini"])]))
    assert none["a1_profiles"] == [] and "no A1 print profile" in none["note"]


# ---- fix round 2 ------------------------------------------------------------------------------------------------
def test_request_text_is_named_where_the_agent_looks(rt):
    """catalog F7: the schema and the hints never said request_text is needed, so the first import failed."""
    out = call(rt, "home3d_find_models", {"urls": ["1"]})
    assert "request_text" in out["next"] and "home3d_import" in out["next"]
    spec = {name: desc for name, desc, *_ in tools_mod.SPECS}
    assert "request_text" in spec["home3d_import"]


def test_the_simulator_hint_lists_its_built_in_catalog(tmp_path):
    from home3d_ws.home3d.backends import simulator
    from home3d_ws.home3d.backends.simulator import SimulatorBackend

    sim = Runtime(settings=settings(), store=Store(tmp_path / "s.db"), backend=SimulatorBackend())
    hint = call(sim, "home3d_find_models", {"urls": []})["hint"]
    ids = getattr(simulator, "CATALOG_IDS", ())
    assert "site:makerworld.com" in hint
    if ids:
        assert "Simulated printer" in hint and str(ids[0][0]) in hint


def test_status_says_why_the_watcher_is_silent(rt, monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    w = call(rt, "home3d_status")["watcher"]
    assert w["state"] == "not_installed" and "hermes home3d setup" in w["hint"]
    script = tmp_path / "hermes" / "scripts" / "home3d_watch.py"
    script.parent.mkdir(parents=True)
    script.write_text("#", encoding="utf-8")
    w = call(rt, "home3d_status")["watcher"]
    assert w["state"] == "never_ran" and "scheduler is not running" in w["hint"] and "hermes gateway" in w["hint"]
    rt.store.kv_set("watcher", {"state": IDLE, "updated": time.time() - 1800})
    w = call(rt, "home3d_status")["watcher"]
    assert w["state"] == "stale" and "30 min ago" in w["hint"]
    rt.store.kv_set("watcher", {"state": IDLE, "updated": time.time()})
    w = call(rt, "home3d_status")["watcher"]
    assert w["state"] == "ok" and w["fresh"] and "hint" not in w


def test_running_the_action_settles_the_family_request(rt, be):
    """R2-7: a request the owner already acted on is never announced afterwards."""
    _, q = queued(rt)
    qid = q["queue_item_id"]
    rt.store.add_approval_request("start", qid, "Mum", "s-mum")
    rt.store.add_approval_request("start", qid + 1, "Mum", "s-mum")
    rt.store.add_approval_request("clear_plate", None, "Dad", "s-dad")
    rt.store.add_approval_request("resume", None, "Mum", "s-mum")
    assert gated(rt, "home3d_start", {"queue_item_id": qid})["ok"]
    assert [(r["action"], r["queue_item_id"]) for r in rt.store.pending_approval_requests()] == \
        [("start", qid + 1), ("clear_plate", None), ("resume", None)]
    be.state.state, be.state.job_name, be.state.bed_temp = FINISH, "vase", 25.0
    assert gated(rt, "home3d_clear_plate", {"action": "confirm"})["ok"]
    be.state.state = PAUSE
    assert gated(rt, "home3d_stop", {"action": "resume"})["ok"]
    assert [r["queue_item_id"] for r in rt.store.pending_approval_requests()] == [qid + 1]
