"""SimulatorBackend: time model, scenarios, plate logic, queue, persistence, synthetic G-code and PNG."""

from __future__ import annotations

import re
import struct
import zipfile
import zlib

import pytest

import home3d_ws.home3d.backends.simulator as sim_mod
from home3d_ws.home3d.backends.base import (FAILED, FINISH, IDLE, OFFLINE, PAUSE, PREPARE, RUNNING, BackendError,
                                            SliceOptions)
from home3d_ws.home3d.backends.simulator import SimulatorBackend

AUTO = SliceOptions(printer_preset="sim-autoeject", process_preset="0.20mm Standard @BBL A1")
STD = SliceOptions(printer_preset="std-a1", process_preset="0.20mm Standard @BBL A1")


@pytest.fixture
def sim():
    return SimulatorBackend()


def _queued(sim, opts=AUTO, library_file_id=1):
    res = sim.slice(library_file_id, opts)
    return res, sim.queue_add(res.library_file_id)


def _run_to_finish(sim, res):
    return sim.advance(2 + res.print_time_s / 60 + 0.01)


def _first_layer_bbox(text):
    z, pts = None, []
    for line in text.splitlines():
        m = re.match(r"G1 .*Z([\d.]+)", line)
        if m and "X" not in line:
            z = float(m.group(1))
        if line.startswith("G1 ") and " E" in line and z is not None:
            if pts and z != pts[0][2]:
                break
            x, y, e = (float(re.search(k + r"(-?[\d.]+)", line).group(1)) for k in ("X", "Y", "E"))
            if e > 0:
                pts.append((x, y, z))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys), pts[0][2]


# ---- library / models ----------------------------------------------------------------------------
def test_seeded_library_and_resolve(sim):
    card = sim.resolve_model("https://makerworld.com/en/models/1440000-gift-box#profileId-77")
    assert card.title == "Gift box"  # the title comes from the link's slug (R2-9)
    assert "80 x 80 x 45 mm" in card.summary  # sized like the catalogue's box
    assert card.license in {"Standard Digital File License", "CC BY"}
    assert len(card.instances) == 2
    assert any("A1" in i.printer_models for i in card.instances)
    assert card.already_imported_library_ids == [1]
    again = sim.resolve_model("1440000")
    assert again.to_dict() == card.to_dict()  # deterministic
    assert sim.resolve_model("1440001").already_imported_library_ids == [2]
    with pytest.raises(BackendError):
        sim.resolve_model("https://example.com/no-model")


def test_import_validates_profile(sim):
    f = sim.import_model(1440003)
    assert f.name == "Name tag keychain.3mf" and not f.sliced
    assert sim.import_model(1440003, profile_id=14400032).id == f.id + 1
    with pytest.raises(BackendError):
        sim.import_model(1440003, profile_id=999)  # an instance id from a URL fragment
    assert f.id in sim.resolve_model("1440003").already_imported_library_ids


# ---- slicing / G-code ----------------------------------------------------------------------------
def test_slice_gcode_header_layers_footprint(sim):
    res = sim.slice(1, AUTO)
    text = sim.library_gcode(res.library_file_id)
    assert text == res.gcode_text
    assert "; HEADER_BLOCK_START" in text and "; HEADER_BLOCK_END" in text
    assert re.search(r"^; model printing time: .+; total estimated time: \d+h \d+m \d+s$", text, re.M)
    assert f"; total filament weight [g] : {res.filament_g:.2f}" in text
    assert "; filament_type = PLA" in text and "; printer_model = Bambu Lab A1" in text
    assert "; max_z_height: 45.00" in text
    assert "; enable_prime_tower = 0" in text
    for cmd in ("M140 S65", "M190 S65", "M104 S220", "M109 S220"):
        assert re.search(rf"^{cmd}\b", text, re.M), cmd
    zs = [float(z) for z in re.findall(r"^; Z_HEIGHT: ([\d.]+)", text, re.M)]
    assert len(zs) == text.count(";LAYER_CHANGE") == int(re.search(r"total layer number: (\d+)", text).group(1))
    assert zs[0] == 0.2 and max(zs) == 45.0 and zs == sorted(zs)
    xmin, xmax, ymin, ymax, z = _first_layer_bbox(text)
    assert z == 0.2 and (xmax - xmin, ymax - ymin) == (80.0, 80.0)
    assert "; HOME3D AUTO-EJECT" in text
    assert res.filament_types == ["PLA"] and res.name == "Flower gift box.gcode.3mf"


def test_slice_variants(sim, monkeypatch):
    std = sim.slice(1, STD).gcode_text
    assert "AUTO-EJECT" not in std
    monkeypatch.setenv(sim_mod.AUTOEJECT_ENV, "9")
    assert "; HOME3D AUTO-EJECT" in sim.slice(1, SliceOptions(printer_preset="9")).gcode_text
    assert "; HOME3D AUTO-EJECT" in SimulatorBackend(autoeject_presets=["42"]).slice(
        1, SliceOptions(printer_preset="42")).gcode_text
    petg = sim.slice(2, SliceOptions(printer_preset="A1 mini std", filament_presets=["Generic PETG HF"],
                                     process_preset="0.28mm Extra Draft @BBL A1"))
    t = petg.gcode_text
    assert petg.filament_types == ["PETG"] and "; filament_type = PETG" in t
    assert "; printer_model = Bambu Lab A1 mini" in t and "M140 S70" in t and "; layer_height = 0.28" in t
    with pytest.raises(BackendError):
        sim.slice(petg.library_file_id, STD)  # already sliced
    with pytest.raises(BackendError):
        sim.library_gcode(1)  # raw model has no G-code


def test_material_from_snapshot_preset_ids(sim):
    from home3d_ws.home3d import config

    config.write_snapshot(config.Settings(filament_presets={"PLA": "12", "PETG": "15"},
                                          autoeject_printer_preset="9"))
    res = sim.slice(1, SliceOptions(printer_preset="9", filament_presets=["15"]))
    assert res.filament_types == ["PETG"] and "; HOME3D AUTO-EJECT" in res.gcode_text


def test_gcode_parses_with_gcode_module_if_present(sim):
    gcode = pytest.importorskip("home3d_ws.home3d.gcode")
    info = gcode.inspect_gcode(sim.slice(1, AUTO).gcode_text)
    assert info.has_eject_marker and info.max_z == pytest.approx(45.0)
    assert info.filament_types == ["PLA"] and "A1" in info.printer_model
    assert info.first_layer_bbox == pytest.approx((88.0, 168.0, 88.0, 168.0))


def test_download_and_upload_files(sim, tmp_path):
    raw = sim.download_file(1, tmp_path / "dl")
    assert raw.name == "Flower gift box.3mf"
    with zipfile.ZipFile(raw) as z:
        assert "<vertex" in z.read("3D/3dmodel.model").decode()
    res = sim.slice(1, AUTO)
    sliced = sim.download_file(res.library_file_id, tmp_path / "dl")
    with zipfile.ZipFile(sliced) as z:
        assert "; HOME3D AUTO-EJECT" in z.read("Metadata/plate_1.gcode").decode()
    up = sim.upload_file(sliced)
    assert up.sliced and up.kind == "gcode.3mf"
    assert "; HOME3D AUTO-EJECT" in sim.library_gcode(up.id)
    stl = tmp_path / "part.stl"
    sim_mod.write_box_stl(stl, (30, 20, 10))
    f = sim.upload_file(stl)
    assert f.kind == "stl" and not f.sliced
    assert sim.download_file(f.id, tmp_path / "back").read_bytes() == stl.read_bytes()
    with pytest.raises(BackendError):
        sim.upload_file(tmp_path / "missing.3mf")


# ---- print progression ---------------------------------------------------------------------------
def test_progression_with_advance(sim):
    res, item = _queued(sim, STD)
    sim.start(item.id)
    st = sim.status()
    assert st.state == PREPARE and st.job_name == "Flower gift box" and st.layer == 0
    assert st.bed_temp == 25.0 and st.bed_target == 65.0
    st = sim.advance(1)
    assert st.state == PREPARE and 25.0 < st.bed_temp < 65.0
    st = sim.advance(1 + res.print_time_s / 120)
    assert st.state == RUNNING and st.progress == pytest.approx(50.0, abs=0.2)
    assert st.layer == pytest.approx(st.total_layers / 2, abs=1) and st.bed_temp == 65.0
    assert st.remaining_min == pytest.approx(res.print_time_s / 120, abs=1)
    assert sim.queue()[0].status == "printing"
    st = sim.advance(res.print_time_s / 120 + 0.01)
    assert st.state == FINISH and st.progress == 100.0 and st.layer == st.total_layers
    assert st.bed_temp > 60 and st.bed_target == 0.0
    assert sim.queue() == [] and sim.queue(include_done=True)[0].status == "completed"
    assert sim.advance(20).bed_temp <= 26.0  # cooled to room temperature within ~20 sim-min
    assert sim.recent_archives(1)[0]["status"] == "completed"


def test_plate_after_finish_with_eject_marker(sim):
    """The REAL A1 order (R2-3): the end G-code cools the bed (M400 S900) and pushes the part while the printer
    still reports RUNNING at 100 %; FINISH comes after the push."""
    assert sim.eject_in_gcode is True
    res, item = _queued(sim, AUTO)
    sim.start(item.id)
    assert sim.check_plate().is_empty is True  # PREPARE: nothing printed yet
    sim.advance(3)
    assert sim.check_plate().is_empty is False  # part is being printed
    sim.advance(res.print_time_s / 60 - 1 + 0.01)  # 2 min PREPARE + duration since start: last layer done
    st = sim.status()
    assert st.state == RUNNING and st.progress == 100.0 and st.layer == st.total_layers
    assert st.remaining_min == 15 and st.bed_target == 0.0 and sim.check_plate().is_empty is False
    assert sim.queue()[0].status == "printing"
    st = sim.advance(14)
    assert st.state == RUNNING and st.bed_temp <= 30 and sim.check_plate().is_empty is False  # still cooling
    st = sim.advance(1.1)
    assert st.state == FINISH and st.progress == 100.0  # FINISH only after the push
    pc = sim.check_plate()
    assert pc.is_empty is True and pc.difference_pct < 26
    done = sim.queue(include_done=True)[0]
    assert done.status == "completed" and done.started_at and done.error_message == ""
    assert sim.advance(10).bed_temp <= 26.0  # keeps cooling from where the end G-code left it


def test_plate_after_finish_without_eject_marker(sim):
    res, item = _queued(sim, STD)
    sim.start(item.id)
    _run_to_finish(sim, res)
    sim.advance(120)
    pc = sim.check_plate()
    assert pc.is_empty is False and pc.difference_pct >= 26
    sim.mark_plate_cleared()
    assert sim.check_plate().is_empty is True


def test_eject_miss_keeps_part(sim):
    res, item = _queued(sim, AUTO)
    sim.set_scenario("eject_miss")
    sim.start(item.id)
    _run_to_finish(sim, res)
    sim.advance(60)
    assert sim.status().state == FINISH and sim.check_plate().is_empty is False
    sim.human_clears_plate()
    assert sim.check_plate().is_empty is True


def test_fail_scenario(sim):
    res, item = _queued(sim)
    sim.set_scenario("fail")
    sim.start(item.id)
    st = _run_to_finish(sim, res)
    assert st.state == FAILED and st.progress == 40.0
    assert st.layer == pytest.approx(0.4 * st.total_layers, abs=1)
    assert sim.queue(include_done=True)[0].status == "failed"
    assert sim.check_plate().is_empty is False  # half-printed part stays
    with pytest.raises(BackendError):
        sim.start(item.id)


def test_fail_set_mid_print_fires_at_current_progress(sim):
    res, item = _queued(sim, STD)
    sim.start(item.id)
    sim.advance(2 + res.print_time_s * 0.6 / 60)
    sim.set_scenario("fail")
    st = sim.status()
    assert st.state == FAILED and st.progress == pytest.approx(60.0, abs=0.2)


def test_pause_hms_scenario(sim):
    res, item = _queued(sim, STD)
    sim.set_scenario("pause_hms")
    sim.start(item.id)
    st = _run_to_finish(sim, res)
    assert st.state == PAUSE and st.progress == 30.0
    assert [h.code for h in st.blocking_hms] == ["0700-2000-0002-0001"]
    assert st.trays[0].remain_pct == 0 and st.bed_target == 65.0
    assert sim.advance(600).progress == 30.0  # frozen while paused
    sim.resume()
    st = sim.status()
    assert st.state == RUNNING and st.hms == [] and st.trays[0].remain_pct == 100
    st = sim.advance(res.print_time_s * 0.7 / 60 + 0.01)
    assert st.state == FINISH


def test_manual_pause_resume_stop(sim):
    with pytest.raises(BackendError):
        sim.stop()
    with pytest.raises(BackendError):
        sim.resume()
    res, item = _queued(sim)
    sim.start(item.id)
    sim.advance(10)
    sim.pause()
    p = sim.status().progress
    assert sim.advance(30).state == PAUSE and sim.status().progress == p
    sim.resume()
    sim.advance(1)
    assert sim.status().progress > p
    sim.stop()
    st = sim.status()
    assert st.state == FAILED
    assert sim.queue(include_done=True)[0].status == "cancelled"
    assert sim.check_plate().is_empty is False


def test_stop_during_prepare_leaves_plate_empty(sim):
    _, item = _queued(sim)
    sim.start(item.id)
    sim.stop()
    assert sim.status().state == FAILED and sim.check_plate().is_empty is True


def test_offline_scenario(sim):
    _, item = _queued(sim)
    sim.set_scenario("offline")
    st = sim.status()
    assert st.state == OFFLINE and not st.connected
    for call in (lambda: sim.start(item.id), sim.check_plate, sim.stop):
        with pytest.raises(BackendError):
            call()
    sim.set_scenario("ok")
    assert sim.status().state == IDLE


# ---- queue -----------------------------------------------------------------------------------------
def test_queue_ordering_busy_and_remove(sim):
    _, a = _queued(sim)
    _, b = _queued(sim, STD, library_file_id=2)
    assert [q.id for q in sim.queue()] == [a.id, b.id] and [q.position for q in sim.queue()] == [1, 2]
    sim.set_scenario("busy")
    sim.set_scenario("busy")  # idempotent: one family job
    q = sim.queue()
    assert len(q) == 3 and q[0].name == "Phone stand.gcode.3mf" and q[0].manual_start
    assert [x.id for x in q[1:]] == [a.id, b.id]
    _, c = _queued(sim, STD)
    assert sim.queue()[-1].id == c.id
    sim.queue_remove(b.id)
    assert b.id not in [x.id for x in sim.queue()]
    with pytest.raises(BackendError):
        sim.queue_remove(9999)
    sim.start(a.id)
    with pytest.raises(BackendError):
        sim.queue_remove(a.id)  # printing
    with pytest.raises(BackendError):
        sim.queue_add(1)  # raw model, not sliced


def test_start_guards(sim):
    res, a = _queued(sim, STD)
    _, b = _queued(sim, STD)
    with pytest.raises(BackendError):
        sim.start(9999)
    sim.start(a.id)
    with pytest.raises(BackendError):
        sim.start(b.id)  # printer busy
    _run_to_finish(sim, res)
    with pytest.raises(BackendError, match="plate"):
        sim.start(b.id)  # part still on the plate
    sim.human_clears_plate()
    assert sim.start(b.id).status == "printing"


def test_non_manual_item_auto_starts_only_on_clear_plate(sim):
    res, a = _queued(sim, STD)
    sim.start(a.id)
    _run_to_finish(sim, res)
    auto = sim.queue_add(sim.slice(2, STD).library_file_id, manual_start=False)
    assert sim.status().state == FINISH  # plate occupied -> manager waits
    sim.mark_plate_cleared()
    assert sim.status().state == PREPARE
    assert {q.id: q.status for q in sim.queue()}[auto.id] == "printing"


# ---- persistence / clock ---------------------------------------------------------------------------
def test_cross_instance_persistence(tmp_path):
    path = tmp_path / "shared" / "sim.json"
    a, b = SimulatorBackend(path), SimulatorBackend(path)
    res, item = _queued(a)
    assert [q.id for q in b.queue()] == [item.id]
    a.start(item.id)
    assert b.status().state == PREPARE
    b.advance(5)
    assert a.status().state == RUNNING
    a.set_scenario("fail")
    a.advance(res.print_time_s / 60)
    assert b.status().state == FAILED
    assert path.exists() and SimulatorBackend(path).status().state == FAILED


def test_default_state_in_data_dir(sim, data_dir):
    sim.status()
    assert (data_dir / "simulator.json").exists()


def test_clock_speed_and_reanchor(sim, monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(sim_mod, "_wall", lambda: now[0])
    monkeypatch.setenv("HOME3D_SIM_SPEED", "60")
    sim.reset()
    t0 = sim.now()
    now[0] += 10  # 10 real seconds = 10 sim minutes
    assert sim.now() == pytest.approx(t0 + 600)
    monkeypatch.setenv("HOME3D_SIM_SPEED", "0")
    t1 = sim.now()
    now[0] += 100
    assert sim.now() == pytest.approx(t1) == pytest.approx(t0 + 600)
    sim.advance(5)
    assert sim.now() == pytest.approx(t1 + 300)


def test_reset_and_bad_scenario(sim):
    _, item = _queued(sim)
    sim.start(item.id)
    sim.set_scenario("fail")
    sim.reset()
    assert sim.status().state == IDLE and sim.queue(include_done=True) == []
    assert sim.check_plate().is_empty is True
    with pytest.raises(BackendError):
        sim.set_scenario("explode")
    with pytest.raises(BackendError):
        sim.advance(-1)


# ---- snapshot PNG ----------------------------------------------------------------------------------
def _png_info(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    length, tag = struct.unpack(">I4s", data[8:16])
    assert tag == b"IHDR" and length == 13
    w, h, depth, ctype, _, _, _ = struct.unpack(">IIBBBBB", data[16:29])
    assert zlib.crc32(data[12:29]) & 0xFFFFFFFF == struct.unpack(">I", data[29:33])[0]
    pos, idat = 33, b""
    while pos < len(data):
        n, t = struct.unpack(">I4s", data[pos:pos + 8])
        if t == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    assert len(raw) == h * (1 + w * 3)
    centre = (h // 2) * (1 + w * 3) + 1 + (w // 2) * 3
    return w, h, depth, ctype, tuple(raw[centre:centre + 3])


def test_snapshot_png(sim, tmp_path):
    empty = sim.snapshot(tmp_path / "media")
    assert empty.note == "simulated" and empty.lit and empty.path.suffix == ".png"
    w, h, depth, ctype, px = _png_info(empty.path.read_bytes())
    assert (w, h, depth, ctype) == (320, 240, 8, 2) and max(px) < 80  # dark plate
    res, item = _queued(sim)
    sim.start(item.id)
    _run_to_finish(sim, res)
    full = sim.snapshot(tmp_path / "media")
    assert full.path != empty.path
    assert min(_png_info(full.path.read_bytes())[4]) > 180  # light part in the middle
    dark = sim.snapshot(tmp_path / "media", lit=False)
    assert not dark.lit and max(_png_info(dark.path.read_bytes())[4]) < 80


def test_simulator_mirrors_light_fields(sim):
    st = sim.status()
    assert st.state == IDLE and st.chamber_light is False and st.connected is True
    pc = sim.check_plate()
    assert pc.is_empty is True and pc.light_ok is True  # the simulated check is always lit
    res, item = _queued(sim, STD)
    sim.start(item.id)
    sim.advance(3)
    assert sim.status().chamber_light is False and sim.check_plate().light_ok is True
    sim.set_scenario("offline")
    assert sim.status().chamber_light is None


def test_simulator_queue_items_use_lower_case_statuses_and_is_done(sim):
    res, item = _queued(sim, STD)
    assert item.is_pending and not item.is_done
    sim.start(item.id)
    _run_to_finish(sim, res)
    done = sim.queue(include_done=True)[0]
    assert done.status == "completed" and done.is_done and not done.is_pending


# ---- fix round 2 ----------------------------------------------------------------------------------------
def test_eject_miss_stays_running_through_the_push_then_finish_with_the_part(sim):
    res, item = _queued(sim, AUTO)
    sim.set_scenario("eject_miss")
    sim.start(item.id)
    st = _run_to_finish(sim, res)
    assert st.state == RUNNING and st.progress == 100.0
    st = sim.advance(15.1)
    assert st.state == FINISH and sim.check_plate().is_empty is False  # the push ran but missed


def test_stop_during_the_end_gcode_cool_down(sim):
    res, item = _queued(sim, AUTO)
    sim.start(item.id)
    _run_to_finish(sim, res)
    sim.advance(5)
    sim.stop()
    st = sim.status()
    assert st.state == FAILED and st.bed_temp < 65 and sim.check_plate().is_empty is False


def test_require_plate_clear_off_starts_auto_items_on_a_finished_printer(sim):
    """R2-5: Bambuddy with "Require plate clear" off dispatches an auto-start item on a FINISH printer at once,
    before any camera check, even with a part still on the plate."""
    assert sim.settings() == {"require_plate_clear": True}
    res, a = _queued(sim, STD)
    sim.start(a.id)
    _run_to_finish(sim, res)
    auto = sim.queue_add(sim.slice(2, STD).library_file_id, manual_start=False)
    assert sim.status().state == FINISH  # require_plate_clear on: the manager waits for the clear plate
    sim.set_require_plate_clear(False)
    assert sim.settings() == {"require_plate_clear": False}
    st = sim.status()
    assert st.state == PREPARE and {q.id: q.status for q in sim.queue()}[auto.id] == "printing"
    # the flag lives in the shared state file: another instance (the watcher's) sees it
    assert SimulatorBackend().settings()["require_plate_clear"] is False
    assert SimulatorBackend(require_plate_clear=True).settings()["require_plate_clear"] is True


def test_auto_start_right_after_an_auto_eject_finish(sim):
    """The family's auto-start item starts the moment our pushed-off print reports FINISH: the watcher can miss our
    FINISH entirely (R2-2 reconciles it from the queue)."""
    res, ours = _queued(sim, AUTO)
    sim.start(ours.id)
    fam = sim.queue_add(sim.slice(2, STD).library_file_id, manual_start=False)
    _run_to_finish(sim, res)
    assert sim.status().state == RUNNING
    st = sim.advance(15.1)
    assert st.state == PREPARE and st.job_name == "Cable clip"
    every = {q.id: q for q in sim.queue(include_done=True)}
    assert every[ours.id].status == "completed" and every[fam.id].status == "printing"


def test_dispatch_fail_scenario(sim):
    """Live Bambuddy item #6 shape: the start is accepted, then the item fails without starting."""
    _, item = _queued(sim, STD)
    sim.set_scenario("dispatch_fail")
    assert sim.start(item.id).status == "pending"
    st = sim.advance(1)
    assert st.state == IDLE
    failed = sim.queue(include_done=True)[0]
    assert failed.status == "failed" and failed.started_at is None and "rejected" in failed.error_message
    assert sim.queue() == []


def test_titles_come_from_the_link_slug_and_sizes_from_keywords(sim):
    """judge/F4: a real MakerWorld link gets a title that matches it, and a size that fits the word."""
    card = sim.resolve_model("https://makerworld.com/en/models/1092613-simple-coaster#profileId-1")
    assert card.title == "Simple coaster" and "95 x 95 x 4 mm" in card.summary
    assert card.instances[0].title == "Simple coaster - A1 0.4 nozzle"
    assert sim.import_model(1092613).name == "Simple coaster.3mf"  # import names it like the card
    assert sim.resolve_model("1092613").title == "Simple coaster"  # remembered for the bare id
    odd = sim.resolve_model("https://makerworld.com/en/models/77-articulated-octopus")
    assert odd.title == "Articulated octopus"  # no keyword: the catalogue size of the id
    assert sim.resolve_model("1440006").title == "Pen holder"  # a bare catalogue id
    assert dict(sim_mod.CATALOG_IDS)[1440007] == "Coaster"
    assert sim.resolve_model("https://makerworld.com/en/models/5-plant-pots").summary.endswith("90 x 90 x 80 mm.")
