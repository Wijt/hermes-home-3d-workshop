"""BambuddyBackend against a fake ``urlopen`` fed with recorded-shape (anonymised) Bambuddy JSON."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from dataclasses import dataclass, field

import pytest

import home3d_ws.home3d.backends.bambuddy as bb
from home3d_ws.home3d.backends.base import BackendError, SliceOptions

BASE = "http://192.168.1.50:8000"


# ---- fake HTTP -------------------------------------------------------------------------------------
@dataclass
class Call:
    method: str
    path: str
    query: dict
    body: bytes | None
    headers: dict
    timeout: float

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class FakeResponse:
    def __init__(self, body: bytes, headers: dict | None = None):
        self._body = body
        self.headers = headers or {}
        self.status = 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@dataclass
class FakeHTTP:
    routes: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)

    def add(self, method: str, path: str, body=None, *, status: int = 200, raw: bytes | None = None,
            headers: dict | None = None, exc: Exception | None = None):
        """Register a response; several for one route are served in order (the last one repeats)."""
        self.routes.setdefault((method, path), []).append((body, status, raw, headers, exc))
        return self

    def __call__(self, req, timeout=None):
        parts = urllib.parse.urlsplit(req.full_url)
        assert parts.path.startswith("/api/v1"), parts.path
        path = parts.path[len("/api/v1"):]
        hdrs = {k.lower(): v for k, v in req.header_items()}
        self.calls.append(Call(req.get_method(), path, dict(urllib.parse.parse_qsl(parts.query)), req.data, hdrs,
                               timeout))
        queue = self.routes.get((req.get_method(), path))
        if not queue:
            raise AssertionError(f"unexpected request {req.get_method()} {path}")
        body, status, raw, headers, exc = queue.pop(0) if len(queue) > 1 else queue[0]
        if exc is not None:
            raise exc
        payload = raw if raw is not None else (b"" if body is None else json.dumps(body).encode("utf-8"))
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "error", {}, io.BytesIO(payload))
        return FakeResponse(payload, headers)

    def paths(self, method: str | None = None) -> list[str]:
        return [f"{c.method} {c.path}" for c in self.calls if method in (None, c.method)]


@pytest.fixture
def http(monkeypatch):
    fake = FakeHTTP()
    monkeypatch.setattr(bb, "_urlopen", fake)
    return fake


@pytest.fixture
def backend():
    b = bb.BambuddyBackend(BASE, printer_id=1)
    b.sleeps = []
    b._sleep = b.sleeps.append
    return b


# ---- recorded-shape fixtures (anonymised) -----------------------------------------------------------
def tray(i, color, ttype="PLA", remain=100, brand=""):
    return {"id": i, "tray_color": color, "tray_type": ttype, "tray_sub_brands": brand, "tray_id_name": "",
            "tray_info_idx": "GFL03", "remain": remain, "k": 0.02, "state": 3, "exists": True}


STATUS_RUNNING = {
    "id": 1, "name": "Workshop A1", "connected": True, "state": "RUNNING", "current_print": "",
    "subtask_name": "rose_box", "gcode_file": "", "progress": 42.0, "remaining_time": 37,
    "layer_num": 31, "total_layers": 75,
    "temperatures": {"bed": 64.9, "bed_target": 65.0, "nozzle": 219.6, "nozzle_target": 220.0},
    "hms_errors": [
        {"code": "0x20001", "attr": 50335744, "module": 3, "severity": 3, "actions": [], "job_id": "1",
         "full_code": "0300100000020001",
         "description": "The resonance frequency of the X axis is low. The timing belt may be loose."},
        {"code": "0x20002", "attr": 117448704, "module": 7, "severity": 2, "actions": [], "job_id": "1",
         "full_code": "0700200000020001", "description": "AMS A Slot 1 filament has run out."},
    ],
    "ams": [{"id": 0, "humidity": 0, "tray": [tray(0, "FFFFFFFF"), tray(1, "C52C18FF", brand="PLA Basic"),
                                               tray(2, "000000FF", remain=-1), tray(3, "00000000", ttype="")]}],
    "vt_tray": [{"id": 254, "tray_color": "00000000", "tray_type": "", "remain": 0}],
    "chamber_light": False,
}


# ---- status -----------------------------------------------------------------------------------------
def test_status_mapping(http, backend):
    http.add("GET", "/printers/1/status", STATUS_RUNNING)
    st = backend.status()
    assert http.calls[0].timeout == 20.0
    assert (st.state, st.connected, st.job_name, st.progress) == ("RUNNING", True, "rose_box", 42.0)
    assert (st.remaining_min, st.layer, st.total_layers) == (37, 31, 75)
    assert (st.bed_temp, st.bed_target, st.nozzle_temp) == (64.9, 65.0, 219.6)
    assert st.printer_name == "Workshop A1" and st.is_active
    codes = [h.code for h in st.hms]
    assert codes == ["0300-1000-0002-0001", "0700-2000-0002-0001"]
    assert st.hms[0].ignorable and not st.hms[1].ignorable
    assert [h.code for h in st.blocking_hms] == ["0700-2000-0002-0001"]
    assert st.hms[1].severity == "serious" and "run out" in st.hms[1].message
    assert st.hms[1].wiki_url.endswith("/hmscode/0700_2000_0002_0001")
    colors = [(t.slot, t.material, t.color, t.remain_pct, t.loaded) for t in st.trays]
    assert colors == [(0, "PLA", "#FFFFFF", 100, True), (1, "PLA", "#C52C18", 100, True),
                      (2, "PLA", "#000000", None, True), (3, "", "", 100, False)]
    assert st.trays[1].name == "PLA Basic"


def test_status_offline_when_not_connected(http, backend):
    http.add("GET", "/printers/1/status", dict(STATUS_RUNNING, connected=False))
    st = backend.status()
    assert st.state == "OFFLINE" and st.connected is False and not st.is_active


@pytest.mark.parametrize("raw,expected", [(None, "UNKNOWN"), ("", "UNKNOWN"), ("FINISH", "FINISH"),
                                          ("failed", "FAILED"), ("SLICING", "PREPARE"), ("idle", "IDLE"),
                                          ("SOMETHING_NEW", "UNKNOWN"), (7, "UNKNOWN")])
def test_status_state_normalisation(http, backend, raw, expected):
    http.add("GET", "/printers/1/status", dict(STATUS_RUNNING, state=raw, hms_errors=[], ams=[]))
    assert backend.status().state == expected


def test_status_missing_state_is_never_idle_and_blocks_a_start():
    from home3d_ws.home3d.gates import clear_plate_gate, start_gate
    from home3d_ws.home3d.backends.base import PlateCheck, QueueItem

    st = bb.parse_status({"connected": True, "temperatures": {"bed": 24.0}})
    assert st.state == "UNKNOWN" and st.connected and not st.is_active
    g = start_gate(st, [QueueItem(id=1, status="pending")], 1, plate=PlateCheck(is_empty=True, light_ok=True),
                   in_cron=False, own_item_ids={1})
    assert not g.ok and "state_unknown" in g.codes
    c = clear_plate_gate(st, PlateCheck(is_empty=True, light_ok=True), in_cron=False, cool_temp_c=30.0,
                         auto_start_pending=[])
    assert not c.ok and "state_unknown" in c.codes


@pytest.mark.parametrize("payload", [{}, {"state": "IDLE"}, {"state": "IDLE", "connected": None},
                                     {"state": "IDLE", "connected": "true"}, {"state": "IDLE", "connected": 1}])
def test_status_connected_must_be_literally_true(payload):
    st = bb.parse_status(payload)
    assert st.connected is False and st.state == "OFFLINE"


def test_status_survives_odd_shapes():
    st = bb.parse_status({"connected": True, "state": "IDLE", "temperatures": [], "ams": [None, "x", {"tray": "y"}],
                          "vt_tray": [None], "hms_errors": None})
    assert st.state == "IDLE" and st.bed_temp is None and st.trays == [] and st.hms == []


def test_status_hms_strings_ints_and_junk_are_never_dropped():
    st = bb.parse_status({"connected": True, "state": "PAUSE", "hms_errors": [
        "0700_2000_0002_0001", 0x0700200000020001, "HMS_0300_1000_0002_0001", "0500C010", None, "",
        ["weird"], {"severity": 2}, True]})
    codes = [h.code for h in st.hms]
    assert codes == ["0700-2000-0002-0001", "0700-2000-0002-0001", "0300-1000-0002-0001", "0500-C010",
                     "unknown", "unknown", "unknown"]
    assert st.hms[0].wiki_url.endswith("/hmscode/0700_2000_0002_0001") and st.hms[3].wiki_url == ""
    assert st.hms[2].ignorable  # the X-belt notice stays harmless in any spelling
    assert [h.code for h in st.blocking_hms] == ["0700-2000-0002-0001", "0700-2000-0002-0001", "0500-C010",
                                                 "unknown", "unknown", "unknown"]
    single = bb.parse_status({"connected": True, "state": "PAUSE", "hms_errors": "0700-2000-0002-0001"})
    assert [h.code for h in single.blocking_hms] == ["0700-2000-0002-0001"]
    one_dict = bb.parse_status({"connected": True, "state": "PAUSE",
                                "hms_errors": {"full_code": "0700200000020001", "severity": 2}})
    assert one_dict.hms[0].code == "0700-2000-0002-0001" and one_dict.hms[0].severity == "serious"


def test_status_chamber_light_and_plate_clear_flags():
    st = bb.parse_status(dict(STATUS_RUNNING, chamber_light=True, awaiting_plate_clear=False))
    assert st.chamber_light is True and st.awaiting_plate_clear is False
    st = bb.parse_status({k: v for k, v in STATUS_RUNNING.items() if k != "chamber_light"})
    assert st.chamber_light is None and st.awaiting_plate_clear is None
    assert bb.parse_status(dict(STATUS_RUNNING, chamber_light="on")).chamber_light is None


def test_short_print_error_code_is_kept(http, backend):
    err = {"code": "0xc010", "attr": 1, "module": 5, "severity": 3, "full_code": "0500C010",
           "description": "USB flash drive read-write exception."}
    http.add("GET", "/printers/1/status", dict(STATUS_RUNNING, hms_errors=[err]))
    h = backend.status().hms[0]
    assert h.code == "0500-C010" and h.wiki_url == "" and not h.ignorable


# ---- queue ------------------------------------------------------------------------------------------
def qitem(i, status, pos, *, lib=None, lib_name=None, arch_name=None, manual=True):
    return {"id": i, "printer_id": 1, "status": status, "position": pos, "library_file_id": lib,
            "library_file_name": lib_name, "archive_id": None if lib else 9, "archive_name": arch_name,
            "manual_start": manual, "print_time_seconds": 798, "scheduled_time": None,
            "created_at": "2026-11-04T14:33:11Z", "bed_levelling": "off", "flow_cali": "off",
            "vibration_cali": False}


def test_queue_filters_done_items(http, backend):
    http.add("GET", "/queue/", [
        qitem(1, "completed", 1, arch_name="Cable winder"),
        qitem(2, "cancelled", 1, arch_name="Cable winder"),
        qitem(7, "pending", 5, lib=282, lib_name="tag_white.gcode.3mf"),
        qitem(3, "failed", 1, lib=10, lib_name="x.gcode.3mf"),
        qitem(5, "pending", 1, lib=258, lib_name="soap_dish.gcode.3mf"),
        qitem(4, "skipped", 2, lib=11, lib_name="y.gcode.3mf"),
        qitem(6, "printing", 3, arch_name="Rose box", manual=False),
    ])
    items = backend.queue()
    assert http.calls[0].query == {"printer_id": "1"}
    assert [(q.id, q.status) for q in items] == [(6, "printing"), (5, "pending"), (7, "pending")]
    assert items[1].name == "soap_dish.gcode.3mf" and items[0].name == "Rose box"
    assert items[1].library_file_id == 258 and items[1].manual_start and items[1].is_pending
    assert items[1].print_time_s == 798 and items[1].position == 1
    every = backend.queue(include_done=True)
    assert len(every) == 7 and {q.id for q in every[3:]} == {1, 2, 3, 4}


# ---- plate check ------------------------------------------------------------------------------------
def plate(is_empty, diff, **kw):
    return dict({"is_empty": is_empty, "confidence": 1.0, "difference_percent": diff,
                 "message": f"[built-in] diff {diff}%", "needs_calibration": False, "light_warning": False}, **kw)


@pytest.mark.parametrize("resp,expected", [
    (plate(False, 20.03), None),  # known false-positive band on an empty plate
    (plate(False, 25.9), None),
    (plate(False, 29.5), False),
    (plate(True, 0.25), True),
    (plate(False, 35.0, needs_calibration=True), None),
    (plate(None, None), None),
    (plate("true", 0.25), None),  # only a real boolean counts
    (plate(True, 0.0, failure_reason="no_camera_frame"), None),  # Bambuddy says "empty" when it could not look
])
def test_check_plate_mapping(http, backend, resp, expected):
    http.add("GET", "/printers/1/camera/check-plate", resp)
    pc = backend.check_plate()
    assert pc.is_empty is expected
    assert pc.difference_pct == resp["difference_percent"]
    assert pc.light_ok is True
    if resp.get("difference_percent") == 20.03:
        assert pc.message.startswith("uncertain")
    if resp.get("failure_reason"):
        assert "could not run (no_camera_frame)" in pc.message
    assert http.paths("POST") == []  # light already on: no light toggling


def status_light(on):
    return dict(STATUS_RUNNING, state="FINISH", chamber_light=on)


def test_parse_plate_check_light_warning_is_never_empty():
    pc = bb.parse_plate_check(plate(True, 0.0, light_warning=True))  # the live "empty, 0 %, light off" answer
    assert pc.is_empty is None and pc.light_ok is False and "chamber light was off" in pc.message
    assert bb.parse_plate_check(plate(False, 60.0, light_warning=True)).is_empty is None


def test_check_plate_rechecks_lit_and_turns_light_off(http, backend):
    http.add("GET", "/printers/1/camera/check-plate", plate(False, 40.0, light_warning=True))
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.5))
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    pc = backend.check_plate()
    assert pc.is_empty is True and pc.light_ok is True
    assert http.paths() == ["GET /printers/1/camera/check-plate", "GET /printers/1/status",
                            "POST /printers/1/chamber-light", "GET /printers/1/camera/check-plate",
                            "POST /printers/1/chamber-light"]
    lights = [c.query["on"] for c in http.calls if c.path.endswith("chamber-light")]
    assert lights == ["true", "false"]
    assert backend.sleeps == [backend.light_wait_s]


def test_check_plate_lit_recheck_failure_is_uncertain_and_turns_light_off(http, backend):
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.0, light_warning=True))
    http.add("GET", "/printers/1/camera/check-plate", {"detail": "camera busy"}, status=503)
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    pc = backend.check_plate()
    assert pc.is_empty is None and pc.light_ok is False
    assert "lit re-check failed" in pc.message and "chamber light was off" in pc.message
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]


def test_check_plate_light_on_failure_is_uncertain(http, backend):
    """The e2e finding: the light cannot be switched on -> the unlit "empty" must not survive."""
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.0, light_warning=True))
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"detail": "printer offline"}, status=500)
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    pc = backend.check_plate()
    assert pc.is_empty is None and pc.light_ok is False and "lit re-check failed" in pc.message
    assert http.paths("GET").count("GET /printers/1/camera/check-plate") == 1  # no second, unlit look
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]


def test_check_plate_light_that_never_comes_on_is_uncertain(http, backend):
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.0, light_warning=True))
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    pc = backend.check_plate()  # the re-check still reports light_warning
    assert pc.is_empty is None and pc.light_ok is False
    assert "did not come on" in pc.message


def test_check_plate_never_switches_off_a_light_that_is_on(http, backend):
    # check-plate saw the light off, but the status says it is on (a person switched it on / report lag)
    http.add("GET", "/printers/1/camera/check-plate", plate(False, 40.0, light_warning=True))
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.5))
    http.add("GET", "/printers/1/status", status_light(True))
    pc = backend.check_plate()
    assert pc.is_empty is True and pc.light_ok is True
    assert http.paths("POST") == [] and backend.sleeps == [backend.light_wait_s]


def test_check_plate_light_left_on_is_flagged(http, backend):
    http.add("GET", "/printers/1/camera/check-plate", plate(False, 40.0, light_warning=True))
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.5))
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("POST", "/printers/1/chamber-light", {"detail": "mqtt down"}, status=500)
    pc = backend.check_plate()
    assert pc.is_empty is True  # the lit result is kept
    assert "light_left_on" in pc.message and "mqtt down" in pc.message
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false", "false"]


def test_check_plate_with_unknown_light_state_does_not_touch_it(http, backend):
    """Fix round 2: a light whose state cannot be read is never switched (it may be on for a print, and the
    "off" afterwards would switch it off): the unlit answer stays uncertain."""
    status = dict(STATUS_RUNNING, state="FINISH")
    status.pop("chamber_light", None)
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.0, light_warning=True))
    http.add("GET", "/printers/1/status", status)
    pc = backend.check_plate()
    assert pc.is_empty is None and pc.light_ok is False and not pc.uncertain_band
    assert "light state unknown" in pc.message
    assert http.paths("POST") == [] and backend.sleeps == []


def test_only_the_false_positive_band_is_marked_overrulable():
    assert bb.parse_plate_check(plate(False, 19.9)).uncertain_band is True
    for resp in (plate(False, 30.0), plate(True, 0.5), plate(False, 19.9, light_warning=True),
                 plate(False, 19.9, needs_calibration=True), plate(None, None),
                 plate(False, 19.9, failure_reason="no_camera_frame")):
        assert bb.parse_plate_check(resp).uncertain_band is False, resp


def test_check_plate_unlit_mode_does_not_touch_the_light(http, backend):
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.0, light_warning=True))
    pc = backend.check_plate(lit=False)
    assert pc.is_empty is None and pc.light_ok is False and http.paths() == ["GET /printers/1/camera/check-plate"]


# ---- snapshot ---------------------------------------------------------------------------------------
def _jpeg_bytes() -> bytes:
    try:
        from PIL import Image
    except Exception:  # pragma: no cover - Pillow missing
        return b"\xff\xd8\xff\xdb" + b"\x00" * 64 + b"\xff\xd9"
    buf = io.BytesIO()
    Image.new("RGB", (1536, 1080), (40, 40, 40)).save(buf, "JPEG")
    return buf.getvalue()


def test_snapshot_lit_reencodes_and_switches_light_off(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    snap = backend.snapshot(tmp_path / "media")
    assert http.paths() == ["GET /printers/1/status", "POST /printers/1/chamber-light",
                            "GET /printers/1/camera/snapshot", "POST /printers/1/chamber-light"]
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]
    assert backend.sleeps == [backend.light_wait_s]
    data = snap.path.read_bytes()
    assert snap.lit and snap.path.suffix == ".jpg" and data[:2] == b"\xff\xd8" and b"JFIF" in data[:20]
    try:
        from PIL import Image
    except Exception:  # pragma: no cover
        return
    assert max(Image.open(snap.path).size) <= 1280


def test_snapshot_failure_still_turns_light_off(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", {"detail": "Camera stream unavailable"}, status=503)
    with pytest.raises(BackendError) as ei:
        backend.snapshot(tmp_path)
    assert "GET /printers/1/camera/snapshot: 503 Camera stream unavailable" in str(ei.value)
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]


def test_snapshot_light_on_failure_still_shoots_and_turns_off(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"detail": "printer offline"}, status=500)
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    snap = backend.snapshot(tmp_path)
    assert snap.lit is False and "light on failed" in snap.note
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]
    assert backend.sleeps == []


def test_snapshot_unlit_does_not_touch_light(http, backend, tmp_path):
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    snap = backend.snapshot(tmp_path, lit=False)
    assert http.paths("POST") == [] and snap.lit is False
    assert http.paths() == ["GET /printers/1/camera/snapshot"]


def test_snapshot_leaves_a_light_that_is_on_alone(http, backend, tmp_path):
    """Mid-print photos must not switch off the light the A1's AI failure detection relies on."""
    http.add("GET", "/printers/1/status", dict(STATUS_RUNNING, chamber_light=True))
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    snap = backend.snapshot(tmp_path)
    assert snap.lit is True and http.paths("POST") == [] and backend.sleeps == []


def test_snapshot_with_unknown_light_state_does_not_touch_it(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", {"detail": "boom"}, status=500)
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    snap = backend.snapshot(tmp_path)
    assert snap.lit is False and http.paths("POST") == [] and "light state unknown" in snap.note
    http.calls.clear()
    http.routes.clear()
    http.add("GET", "/printers/1/status", {k: v for k, v in STATUS_RUNNING.items() if k != "chamber_light"})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    assert backend.snapshot(tmp_path).lit is False and http.paths("POST") == []


def test_snapshot_light_left_on_is_flagged_and_photo_kept(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("POST", "/printers/1/chamber-light", {"success": False, "message": "no ack"})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes())
    snap = backend.snapshot(tmp_path)
    assert snap.path.exists() and snap.lit is True
    assert "light_left_on" in snap.note and "no ack" in snap.note
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false", "false"]


def test_snapshot_without_pillow_adds_jfif_header(http, backend, tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "PIL", None)  # import PIL -> ImportError
    raw = b"\xff\xd8\xff\xdb\x00\x43" + b"\x01" * 80 + b"\xff\xd9"
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=raw)
    snap = backend.snapshot(tmp_path)
    data = snap.path.read_bytes()
    assert data.startswith(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00") and data.endswith(raw[2:])
    assert "Pillow unavailable" in snap.note
    assert bb.ensure_jfif(data) == data  # idempotent


# ---- slicing ----------------------------------------------------------------------------------------
GCODE = ("; HEADER_BLOCK_START\n; total estimated time: 1h 22m 13s\n; max_z_height: 15.00\n; HEADER_BLOCK_END\n"
         "; CONFIG_BLOCK_START\n; filament_type = PLA;PLA;PETG\n; CONFIG_BLOCK_END\nG1 X10 Y10\n"
         "; HOME3D AUTO-EJECT\nM18\n")


def test_slice_request_body_and_polling(http, backend):
    http.add("POST", "/library/files/344/slice", {"job_id": 7, "status": "pending",
                                                  "status_url": "/api/v1/slice-jobs/7"})
    http.add("GET", "/slice-jobs/7", {"job_id": 7, "status": "pending", "progress": None})
    http.add("GET", "/slice-jobs/7", {"job_id": 7, "status": "running",
                                      "progress": {"stage": "Generating G-code", "total_percent": 75}})
    http.add("GET", "/slice-jobs/7", {"job_id": 7, "status": "running", "progress": {"stage": "Exporting"}})
    http.add("GET", "/slice-jobs/7", {"job_id": 7, "status": "running", "progress": {"stage": "Exporting"}})
    http.add("GET", "/slice-jobs/7", {"job_id": 7, "status": "completed", "result": {
        "library_file_id": 345, "name": "pill_box.gcode.3mf", "print_time_seconds": 4933,
        "filament_used_g": 30.94, "used_embedded_settings": False}})
    http.add("GET", "/library/files/345/gcode", raw=GCODE.encode(), headers={"Content-Type": "text/plain"})
    opts = SliceOptions(printer_preset="9", process_preset="0.20mm Standard @BBL A1", filament_presets=["3"],
                        bed_type="Textured PEI Plate", process_overrides={"brim_type": "outer_only",
                                                                          "layer_height": "0.16"})
    res = backend.slice(344, opts)
    body = http.calls[0].json()
    assert http.calls[0].headers["content-type"] == "application/json" and http.calls[0].timeout == 60.0
    assert body["printer_preset"] == {"source": "local", "id": "9"}
    assert body["process_preset"] == {"source": "standard", "id": "0.20mm Standard @BBL A1"}
    assert body["filament_preset"] == {"source": "local", "id": "3"} and "filament_presets" not in body
    assert body["export_3mf"] is True and body["bed_type"] == "Textured PEI Plate" and "plate" not in body
    ov = body["process_overrides"]
    assert ov["wall_generator"] == "arachne" and ov["z_hop"] == "0.4" and ov["z_hop_types"] == "Slope Lift"
    assert ov["enable_prime_tower"] == "0" and ov["brim_type"] == "outer_only" and ov["layer_height"] == "0.16"
    assert backend.sleeps == [2.0, 3.0, 4.5, 5.0, 5.0]
    assert (res.library_file_id, res.name, res.print_time_s, res.filament_g) == (345, "pill_box.gcode.3mf",
                                                                                   4933, 30.94)
    assert res.filament_types == ["PLA", "PETG"] and "HOME3D AUTO-EJECT" in res.gcode_text


def test_slice_multi_filament_and_source_prefix(backend):
    body = backend.slice_request_body(SliceOptions(
        printer_preset="10", process_preset="cloud:GP079", filament_presets=["3", "Bambu PLA Basic @BBL A1"],
        filament_colours=["#FFFFFF", "#C52C18"], plate=2))
    assert body["process_preset"] == {"source": "cloud", "id": "GP079"}
    assert body["filament_presets"] == [{"source": "local", "id": "3"},
                                        {"source": "standard", "id": "Bambu PLA Basic @BBL A1"}]
    assert "filament_preset" not in body and body["plate"] == 2 and body["filament_colours"][1] == "#C52C18"
    with pytest.raises(BackendError):
        backend.slice_request_body(SliceOptions(printer_preset="9", process_preset="x"))


def test_slice_job_failure_raises(http, backend):
    http.add("POST", "/library/files/5/slice", {"job_id": 3, "status": "pending"})
    http.add("GET", "/slice-jobs/3", {"job_id": 3, "status": "failed", "error_status": 400,
                                      "error_detail": "Invalid local preset id for filament: 'X'"})
    with pytest.raises(BackendError, match="slice job 3 failed: 400 Invalid local preset id"):
        backend.slice(5, SliceOptions(printer_preset="9", process_preset="p", filament_presets=["X"]))


def test_slice_timeout(http, backend):
    clock = iter(range(0, 10_000, 4))
    backend._clock = lambda: next(clock)
    http.add("POST", "/library/files/5/slice", {"job_id": 4, "status": "pending"})
    http.add("GET", "/slice-jobs/4", {"job_id": 4, "status": "running", "progress": {"stage": "Slicing"}})
    with pytest.raises(BackendError, match=r"timed out after 20 s \(stage: Slicing\)"):
        backend.slice(5, SliceOptions(printer_preset="9", process_preset="p", filament_presets=["1"]), timeout_s=20)


def test_slice_survives_gcode_fetch_failure(http, backend):
    http.add("POST", "/library/files/5/slice", {"job_id": 8, "status": "pending"})
    http.add("GET", "/slice-jobs/8", {"job_id": 8, "status": "completed", "result": {"library_file_id": 9}})
    http.add("GET", "/library/files/9/gcode", {"detail": "boom"}, status=500)
    res = backend.slice(5, SliceOptions(printer_preset="9", process_preset="p", filament_presets=["1"]))
    assert res.library_file_id == 9 and res.gcode_text == ""


def test_library_gcode_keeps_tail_when_truncated(http, backend):
    text = "; HEADER\n" + "G1 X1 Y1 E0.1\n" * 5000 + "; HOME3D AUTO-EJECT\nM18\n"
    http.add("GET", "/library/files/12/gcode", raw=text.encode())
    out = backend.library_gcode(12, max_bytes=4000)
    assert out.startswith("; HEADER") and "HOME3D AUTO-EJECT" in out and "; HOME3D TRUNCATED" in out
    assert len(out.encode()) < 4200


# ---- queue / printer writes ---------------------------------------------------------------------------
def test_queue_add_sends_calibration_fields_and_manual_start(http, backend):
    http.add("POST", "/queue/", qitem(95, "pending", 6, lib=345, lib_name="pill_box.gcode.3mf"))
    item = backend.queue_add(345, ams_mapping=[1], plate_id=1)
    body = http.calls[0].json()
    assert body == {"library_file_id": 345, "printer_id": 1, "manual_start": True, "bed_levelling": "off",
                    "flow_cali": "off", "vibration_cali": False, "ams_mapping": [1], "plate_id": 1}
    assert (item.id, item.status, item.library_file_id, item.manual_start) == (95, "pending", 345, True)


def test_queue_add_defaults_still_send_calibration(http, backend):
    http.add("POST", "/queue/", qitem(96, "pending", 7, lib=1, lib_name="a.gcode.3mf"))
    backend.queue_add(1)
    body = http.calls[0].json()
    assert body["manual_start"] is True and body["vibration_cali"] is False
    assert body["bed_levelling"] == "off" and body["flow_cali"] == "off" and "ams_mapping" not in body


def test_start_remove_and_printer_commands(http, backend):
    http.add("POST", "/queue/95/start", {"success": True, "message": "Queued for dispatch"})
    http.add("GET", "/queue/95", qitem(95, "pending", 1, lib=345, lib_name="pill_box.gcode.3mf", manual=False))
    http.add("DELETE", "/queue/96", {"message": "deleted"})
    for cmd in ("stop", "pause", "resume"):
        http.add("POST", f"/printers/1/print/{cmd}", {"success": True, "message": f"Print {cmd} command sent"})
    http.add("POST", "/printers/1/clear-plate", {"success": True})
    assert backend.start(95).id == 95
    backend.queue_remove(96)
    backend.stop(), backend.pause(), backend.resume(), backend.mark_plate_cleared()
    assert http.paths() == ["POST /queue/95/start", "GET /queue/95", "DELETE /queue/96",
                            "POST /printers/1/print/stop", "POST /printers/1/print/pause",
                            "POST /printers/1/print/resume", "POST /printers/1/clear-plate"]


def test_start_refusals_are_readable(http, backend):
    http.add("POST", "/queue/95/start", {"detail": {"code": "insufficient_filament", "deficit": [
        {"slot_id": 2, "ams_id": 0, "tray_id": 1, "filament_type": "PLA", "required_grams": 30.94,
         "remaining_grams": 12.0},
        {"slot_id": 3, "ams_id": 255, "tray_id": 0, "filament_type": "PETG", "required_grams": 4.25,
         "remaining_grams": None}]}}, status=409)
    with pytest.raises(BackendError) as ei:
        backend.start(95)
    msg = str(ei.value)
    assert msg.startswith("Bambuddy refused to start queue item 95: not enough filament: ")
    assert "PLA in AMS A slot 2 needs 31 g, 12 g left" in msg
    assert "PETG in external spool needs 4.2 g, amount left unknown" in msg and msg.endswith("(HTTP 409)")
    assert "{" not in msg

    http.add("POST", "/queue/96/start", {"detail": {"code": "unmatched_filament",
                                                    "missing": ["PLA (Red)", "PETG (Black)"]}}, status=409)
    with pytest.raises(BackendError, match=r"queue item 96: no loaded filament matches what the job needs: "
                                           r"PLA \(Red\), PETG \(Black\) \(HTTP 409\)"):
        backend.start(96)

    http.add("POST", "/queue/97/start", {"detail": "Can only start pending items, current status: 'printing'"},
             status=400)
    with pytest.raises(BackendError, match="refused to start queue item 97: Can only start pending items"):
        backend.start(97)

    http.add("POST", "/queue/98/start", {"detail": {"code": "something_new"}}, status=409)
    with pytest.raises(BackendError, match="queue item 98: something new"):
        backend.start(98)

    http.add("POST", "/queue/99/start", {"detail": "boom"}, status=500)  # server errors keep the raw form
    with pytest.raises(BackendError, match=r"^POST /queue/99/start: 500 boom$") as ei:
        backend.start(99)
    assert isinstance(ei.value, bb.BambuddyHTTPError) and ei.value.status == 500


def test_success_false_raises(http, backend):
    http.add("POST", "/printers/1/print/resume", {"success": False, "message": "Printer not paused"})
    with pytest.raises(BackendError, match="print resume: Printer not paused"):
        backend.resume()


# ---- MakerWorld / library --------------------------------------------------------------------------
RESOLVED = {
    "model_id": 1085771, "profile_id": None, "already_imported_library_ids": [52],
    "design": {"id": 1085771, "title": "Rose Printed in a Single Piece", "coverUrl": "https://cdn.example/rose.jpg",
               "designCreator": {"uid": 1, "name": "Maker"}, "license": "Standard Digital File License",
               "likeCount": 746, "downloadCount": 1925, "printCount": 530,
               "summary": "<p>A rose &amp; stem.</p><p>Prints <b>without</b> supports.</p>"},
    "instances": [
        {"id": 1078505, "profileId": "222532353", "title": "0.16mm layer, 3 walls",
         "compatibility": {"devProductName": "P1S"}, "prediction": 7260, "weight": 18.4},
        {"id": 1078600, "profileId": 222532999, "title": "A1 tuned",
         "compatibility": {"devProductName": "A1"},
         "extention": {"modelInfo": {"plates": [{"prediction": 3600, "weight": 10.0},
                                                {"prediction": 1800, "weight": 5.5}]}}},
        {"id": 1078700, "title": "broken, no profile id"},
    ],
}


def test_resolve_model_bare_id(http, backend):
    http.add("POST", "/makerworld/resolve", RESOLVED)
    card = backend.resolve_model("1085771")
    assert http.calls[0].json() == {"url": "https://makerworld.com/en/models/1085771"}
    assert (card.model_id, card.title, card.creator, card.license) == (
        1085771, "Rose Printed in a Single Piece", "Maker", "Standard Digital File License")
    assert (card.likes, card.downloads, card.prints) == (746, 1925, 530)
    assert card.summary == "A rose & stem.\nPrints without supports."
    assert card.already_imported_library_ids == [52] and card.cover_url.endswith("rose.jpg")
    assert [(i.profile_id, i.printer_models, i.print_time_min, i.weight_g, i.plates) for i in card.instances] == [
        (222532353, ["P1S"], 121, 18.4, None), (222532999, ["A1"], 90, 15.5, 2)]


def test_resolve_model_fragment_is_instance_id(http, backend):
    http.add("POST", "/makerworld/resolve", RESOLVED)
    url = "https://makerworld.com/en/models/1085771-rose#profileId-1078600"
    card = backend.resolve_model(url)
    assert http.calls[0].json() == {"url": url}
    assert card.instances[0].profile_id == 222532999 and card.url == url


@pytest.mark.parametrize("given, sent", [
    ("1085771", "https://makerworld.com/en/models/1085771"),
    ("  1085771 ", "https://makerworld.com/en/models/1085771"),
    ("https://makerworld.com/en/models/1085771-rose#profileId-1078600",
     "https://makerworld.com/en/models/1085771-rose#profileId-1078600"),
    ("https://www.makerworld.com/en/models/5?from=search", "https://www.makerworld.com/en/models/5?from=search"),
    ("https://makerworld.com:443/en/models/5", "https://makerworld.com:443/en/models/5"),
    ("HTTPS://MakerWorld.com/en/models/5", "HTTPS://MakerWorld.com/en/models/5"),
    ("makerworld.com/en/models/5", "https://makerworld.com/en/models/5"),
    ("www.makerworld.com/en/models/5", "https://www.makerworld.com/en/models/5"),
])
def test_makerworld_url_accepts_ids_and_makerworld_links(given, sent):
    assert bb.makerworld_url(given) == sent


@pytest.mark.parametrize("given", [
    "http://makerworld.com/en/models/5",  # not https
    "ftp://makerworld.com/en/models/5",
    "file:///etc/passwd",
    "http://169.254.169.254/latest/meta-data/",
    "https://localhost:8000/api/v1/settings",
    "https://example.com/makerworld.com/en/models/5",
    "https://makerworld.com.example.com/en/models/5",
    "https://notmakerworld.com/en/models/5",
    "https://makerworld.com@example.com/en/models/5",
    "https://example.com\\@makerworld.com/en/models/5",
    "https://user:pw@makerworld.com/en/models/5",
    "https://makerworld.com:8443/en/models/5",
    "https://makerworld.com:x/en/models/5",
    "https://makerworld.com/en/models/5\nHost: example.com",
    "https://makerworld.com /en/models/5",
    "makerworld.example.com/en/models/5",
    "www.makerworld.com.cn/zh/models/5",
    "javascript:alert(1)",
    "//makerworld.com/en/models/5",
    "a rose vase",
    "\u0661\u0662\u0663",  # digits, but not ASCII ones
])
def test_makerworld_url_refuses_everything_else(given, http, backend):
    with pytest.raises(BackendError, match="not a MakerWorld link"):
        bb.makerworld_url(given)
    with pytest.raises(BackendError, match="not a MakerWorld link"):
        backend.resolve_model(given)
    assert http.calls == []  # refused here: Bambuddy is never asked to fetch it


def test_makerworld_url_needs_something():
    with pytest.raises(BackendError, match="no MakerWorld link"):
        bb.makerworld_url("  ")


def test_import_model_checks_download_status(http, backend):
    http.add("GET", "/makerworld/status", {"has_cloud_token": False, "can_download": False,
                                           "sign_in_expired": True})
    with pytest.raises(BackendError, match="sign-in expired"):
        backend.import_model(1085771, 222532999)
    assert http.paths("POST") == []


def test_import_model(http, backend):
    http.add("GET", "/makerworld/status", {"has_cloud_token": True, "can_download": True})
    http.add("POST", "/makerworld/import", {"library_file_id": 52, "filename": "Rose 1.3.3mf", "folder_id": 1,
                                            "profile_id": 222532999, "was_existing": False})
    lf = backend.import_model(1085771, 222532999)
    assert http.calls[1].json() == {"model_id": 1085771, "profile_id": 222532999}
    assert (lf.id, lf.name, lf.kind, lf.sliced) == (52, "Rose 1.3.3mf", "3mf", False)


def test_upload_file_multipart(http, backend, tmp_path):
    src = tmp_path / "tag.stl"
    src.write_bytes(b"solid tag\nendsolid tag\n")
    http.add("POST", "/library/files", {"id": 400, "filename": "tag.stl", "file_type": "stl", "file_size": 23,
                                        "thumbnail_path": None})
    lf = backend.upload_file(src)
    call = http.calls[0]
    assert call.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert b'name="file"; filename="tag.stl"' in call.body and b"solid tag\nendsolid tag\n" in call.body
    assert (lf.id, lf.kind, lf.sliced) == (400, "stl", False)


def test_download_file_uses_safe_name(http, backend, tmp_path):
    http.add("GET", "/library/files/345/download", raw=b"PK\x03\x04zip",
             headers={"Content-Disposition": 'attachment; filename="../../evil/pill_box.gcode.3mf"'})
    path = backend.download_file(345, tmp_path / "dl")
    assert path == tmp_path / "dl" / "pill_box.gcode.3mf" and path.read_bytes() == b"PK\x03\x04zip"


def test_download_file_falls_back_to_metadata_name(http, backend, tmp_path):
    http.add("GET", "/library/files/7/download", raw=b"solid")
    http.add("GET", "/library/files/7", {"id": 7, "filename": "box.stl"})
    assert backend.download_file(7, tmp_path).name == "box.stl"


# ---- errors / config ----------------------------------------------------------------------------------
def test_http_error_becomes_backend_error(http, backend):
    http.add("GET", "/printers/1/status", {"detail": "Printer not found"}, status=404)
    with pytest.raises(BackendError) as ei:
        backend.status()
    assert str(ei.value) == "GET /printers/1/status: 404 Printer not found"


def test_validation_error_is_short(http, backend):
    http.add("POST", "/queue/", {"detail": [{"loc": ["body", "plate_id"], "msg": "Input should be an integer"}]},
             status=422)
    with pytest.raises(BackendError, match="POST /queue/: 422 Input should be an integer"):
        backend.queue_add(1)


def test_network_errors_become_backend_error(http, backend):
    http.add("GET", "/printers/1/status", exc=urllib.error.URLError(ConnectionRefusedError(111, "refused")))
    http.add("GET", "/queue/", exc=TimeoutError("timed out"))
    http.add("GET", "/makerworld/status", raw=b"<html>proxy error</html>")
    with pytest.raises(BackendError, match="GET /printers/1/status: "):
        backend.status()
    with pytest.raises(BackendError, match="GET /queue/: timed out"):
        backend.queue()
    with pytest.raises(BackendError, match="invalid JSON"):
        backend.import_model(1)


def test_base_url_api_key_and_preview(http):
    b = bb.BambuddyBackend("192.168.1.50:8000/api/v1/", printer_id=2, api_key="k-123",
                           public_url="https://printer.example.org/")
    assert b.api == "http://192.168.1.50:8000/api/v1"
    assert b.preview_url(345) == "https://printer.example.org/gcode-viewer?library_file=345&plate=1"
    http.add("GET", "/printers/2/status", STATUS_RUNNING)
    b.status()
    assert http.calls[0].headers["x-api-key"] == "k-123"
    plain = bb.BambuddyBackend(BASE)
    assert plain.preview_url(1).startswith(BASE + "/gcode-viewer")
    http.add("GET", "/printers/1/status", STATUS_RUNNING)
    plain.status()
    assert "x-api-key" not in http.calls[1].headers


def test_recent_archives(http, backend):
    http.add("GET", "/archives/", [{"id": 116, "print_name": "pill_box", "filename": "pill_box.gcode.3mf",
                                    "status": "failed", "print_time_seconds": 5141, "actual_time_seconds": None,
                                    "filament_used_grams": 31.11, "photos": ["finish_1.jpg"],
                                    "failure_reason": None, "makerworld_url": None}])
    rows = backend.recent_archives(2)
    assert http.calls[0].query == {"limit": "2", "printer_id": "1"}
    assert rows[0]["name"] == "pill_box" and rows[0]["print_time_s"] == 5141 and rows[0]["photos"] == ["finish_1.jpg"]


def test_preset_helpers(http, backend):
    http.add("GET", "/slicer/presets", {"local": {"printer": [{"id": "9", "name": "A1 - AutoEject"}],
                                                  "process": [], "filament": []},
                                        "standard": {"printer": [], "process": [], "filament": []},
                                        "cloud": {"printer": [{"id": "GM030"}]}})
    http.add("GET", "/local-presets/9", {"id": "9", "setting": {"machine_end_gcode": "M400\n; HOME3D AUTO-EJECT\n"}})
    assert backend.presets()["local"]["printer"] == [{"id": "9", "name": "A1 - AutoEject", "filament_type": None}]
    assert backend.preset_has_eject_marker("9") is True
    assert backend.preset_has_eject_marker("Bambu Lab A1") is None


def test_make_backend_builds_bambuddy(pkg):
    from home3d_ws.home3d.backends import make_backend
    from home3d_ws.home3d.config import load_settings

    s = load_settings(overrides={"backend": "bambuddy", "bambuddy_url": BASE, "printer_id": 3})
    b = make_backend(s)
    assert isinstance(b, bb.BambuddyBackend) and b.printer_id == 3 and b.name == "bambuddy"
    assert b.api_key == ""  # no Hermes secret scope in tests


# Shape of a real Bambuddy 1.3.0 /makerworld/resolve answer (trimmed, values made up): the full design
# carries compatibility + other compatible printers; the flattened top-level list has empty details.
RESOLVED_REAL_SHAPE = {
    "model_id": 4242, "profile_id": None, "already_imported_library_ids": [],
    "design": {"id": 4242, "title": "Card wallet", "designCreator": {"name": "Maker"},
               "instances": [
                   {"id": 11, "profileId": 1001, "title": "0.2mm layer, 3 walls", "prediction": 7727, "weight": 48,
                    "extention": {"modelInfo": {
                        "compatibility": {"devModelName": "N1", "devProductName": "A1 mini", "nozzleDiameter": 0.4},
                        "otherCompatibility": [{"devModelName": "C12", "devProductName": "P1S", "profileId": 5001},
                                               {"devModelName": "N2S", "devProductName": "A1", "profileId": 5002}],
                        "plates": [{"index": 1, "prediction": 7727, "weight": 48}]}}},
                   {"id": 12, "profileId": 1002, "title": "A1 native", "prediction": 3600, "weight": 20,
                    "extention": {"modelInfo": {"compatibility": {"devModelName": "N2S", "devProductName": "A1"},
                                                "otherCompatibility": None, "plates": [{"index": 1}]}}},
                   {"id": 13, "profileId": 1003, "title": "P1S only",
                    "extention": {"modelInfo": {"compatibility": {"devProductName": "P1S"},
                                                "otherCompatibility": [{"devProductName": "X1C"}]}}}]},
    "instances": [{"id": 11, "profileId": 1001, "title": "0.2mm layer, 3 walls",
                   "detail": {"extention": {"modelInfo": {"compatibility": {"devProductName": ""}}}}}],
}


def test_resolve_model_reads_full_design_instances(http, backend):
    http.add("POST", "/makerworld/resolve", RESOLVED_REAL_SHAPE)
    card = backend.resolve_model("4242")
    got = [(i.profile_id, i.printer_models, i.compatible_models, i.print_time_min, i.weight_g, i.plates)
           for i in card.instances]
    assert got == [(1001, ["A1 mini"], ["P1S", "A1"], 129, 48.0, 1),
                   (1002, ["A1"], [], 60, 20.0, 1),
                   (1003, ["P1S"], ["X1C"], None, None, None)]


# ---- one light cycle; never trust a stale "light on" right after we switched it off ----------------------
def test_snapshot_and_check_uses_one_light_cycle(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    http.add("GET", "/printers/1/camera/check-plate", plate(False, 27.2))
    snap, pc = backend.snapshot_and_check(tmp_path)
    assert http.paths() == ["GET /printers/1/status", "POST /printers/1/chamber-light",
                            "GET /printers/1/camera/snapshot", "GET /printers/1/camera/check-plate",
                            "POST /printers/1/chamber-light"]
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]
    assert backend.sleeps == [backend.light_wait_s] and snap.lit and pc.is_empty is False


def test_snapshot_and_check_leaves_a_light_that_is_on(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(True))
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.4))
    snap, pc = backend.snapshot_and_check(tmp_path)
    assert http.paths("POST") == [] and pc.is_empty is True and snap.lit


def test_check_plate_right_after_our_light_off_does_a_lit_check(http, backend, tmp_path):
    # live finding (8 Nov 2026): after we switch the light off, the status still says "on" for a few
    # seconds and Bambuddy's check-plate answers from a dark frame without a light_warning.
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    backend.snapshot(tmp_path)
    http.calls.clear()
    http.routes[("GET", "/printers/1/status")] = [(status_light(True), 200, None, None, None)]  # stale "on"
    http.add("GET", "/printers/1/camera/check-plate", plate(True, 0.3))
    pc = backend.check_plate()
    assert http.paths() == ["POST /printers/1/chamber-light", "GET /printers/1/camera/check-plate",
                            "POST /printers/1/chamber-light"]
    assert [c.query["on"] for c in http.calls if c.method == "POST"] == ["true", "false"]
    assert pc.is_empty is True


def test_lit_check_failure_after_our_light_off_is_uncertain(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", status_light(False))
    http.add("POST", "/printers/1/chamber-light", {"success": True})
    http.add("GET", "/printers/1/camera/snapshot", raw=_jpeg_bytes(), headers={"Content-Type": "image/jpeg"})
    backend.snapshot(tmp_path)
    http.add("GET", "/printers/1/camera/check-plate", {"detail": "camera busy"}, status=503)
    pc = backend.check_plate()
    assert pc.is_empty is None and pc.light_ok is False and "lit re-check failed" in pc.message


# ---- fix round 2 ------------------------------------------------------------------------------------------------
def test_a_failed_dispatch_keeps_its_reason_and_no_start_time(http, backend):
    """hw F2: live item #6 (shape): status failed, started_at None, error_message from the printer."""
    http.add("GET", "/queue/", [
        {"id": 6, "status": "failed", "library_file_name": "clip.gcode.3mf", "manual_start": True,
         "started_at": None, "error_message": "The printer rejected the print command: MQTT command verification "
                                              "failed (HMS 0500-0500-0001-0007)"},
        {"id": 7, "status": "completed", "archive_name": "Card wallet", "started_at": "2026-11-07T18:02:11",
         "error_message": None},
        {"id": 8, "status": "pending", "library_file_name": "box.gcode.3mf"}])
    items = {q.id: q for q in backend.queue(include_done=True)}
    assert items[6].started_at is None and items[6].error_message.startswith("The printer rejected the print")
    assert items[7].started_at == "2026-11-07T18:02:11" and items[7].error_message == ""
    assert items[8].started_at is None and items[8].error_message == ""


def test_the_real_printer_pushes_inside_the_end_gcode():
    assert bb.BambuddyBackend.eject_in_gcode is True


def test_settings_reads_require_plate_clear(http, backend):
    http.add("GET", "/settings/", {"require_plate_clear": False, "plate_detection_enabled": False})
    assert backend.settings()["require_plate_clear"] is False
    assert http.paths() == ["GET /settings/"]
    http.routes.clear()
    http.add("GET", "/settings/", ["not", "a", "dict"])
    with pytest.raises(BackendError):
        backend.settings()


def test_with_timeout_caps_every_request_of_a_copy(http, backend, tmp_path):
    http.add("GET", "/printers/1/status", {"connected": True, "state": "IDLE"})
    http.add("GET", "/printers/1/camera/check-plate", {"is_empty": True, "difference_percent": 1.0})
    quick = backend.with_timeout(5)
    assert quick is not backend and backend.timeout_cap is None and quick.timeout_cap == 5
    quick.status()
    quick._get("/printers/1/camera/check-plate", timeout=30.0)  # an explicit long timeout is capped too
    backend.status()
    assert [c.timeout for c in http.calls] == [5, 5, backend.timeout_s]
    assert quick.with_timeout(10).timeout_cap == 5 and quick.with_timeout(2).timeout_cap == 2
