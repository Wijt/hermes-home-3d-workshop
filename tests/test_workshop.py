"""The Workshop screen's overview (``home3d.workshop``) on the simulator, through the same surfaces Hermes uses.

Every state is reached the real way: household turns and tool calls through ``pre_tool_call`` -> handler ->
``post_tool_call``, owner starts with ``/home3d approve``, the zero-token watcher (``deliver=False``: outbox only)
noticing finishes and failures. The overview is then read the way the dashboard reads it.

``HOME3D_WRITE_FIXTURE=1 pytest tests/test_workshop.py -k fixture`` regenerates
``tests/fixtures/workshop_overview.json`` (a real OpenSCAD render when openscad is installed).
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest

from home3d_ws.home3d import checks, design, upgrades, watcher, workshop
from home3d_ws.home3d.backends.simulator import SimulatorBackend, render_plate_png, write_box_stl
from home3d_ws.home3d.commands import make_command
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.hooks import make_hooks
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store
from home3d_ws.home3d.tools import build_tools

OWNER, MUM, ENGINEER = "owner-id@s.whatsapp.net", "mum-id@s.whatsapp.net", "engineer-id@s.whatsapp.net"
FLOWER_BOX, COASTER, CABLE_CLIP = 1440000, 1440007, 1440001
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "workshop_overview.json"
FIXTURE_FILES = FIXTURE.parent / "workshop_files"
TOP_KEYS = {"schema", "generated_ts", "backend", "persona", "simulated", "printer", "now", "camera", "waiting",
            "queue", "done_box", "notices", "filament", "needs_human", "upgrades", "designs", "setup", "watcher",
            "groups", "viewer"}
BRACKET_SCAD = """// wall bracket for a 20 mm rail
width = 40; depth = 30; thick = 4; height = 35;
difference() {
  union() {
    cube([width, depth, thick]);
    cube([width, thick, height]);
  }
  for (x = [10, 30]) translate([x, depth - 10, -1]) cylinder(d = 4.5, h = thick + 2, $fn = 32);
}
"""


class Source:
    def __init__(self, user_id):
        self.user_id, self.chat_id, self.platform = user_id, "<group>@g.us", "whatsapp"


class Shop:
    """One household on the simulated printer, read by the Workshop overview."""

    def __init__(self):
        self.settings = Settings(
            backend="simulator", language="en", persona_name="Mıstık", owner_name="Sam", owner_ids=[OWNER],
            household=[{"id": MUM, "name": "Mum"}, {"id": ENGINEER, "name": "Engineer"}],
            groups=[{"name": "Family", "target": "telegram:<family-group>", "tone": "family", "members": [MUM]},
                    {"name": "R&D", "target": "telegram:<lab-group>", "tone": "team", "members": [ENGINEER]}],
            owner_target="telegram:<owner-chat>", family_target="telegram:<family-group>")
        self.be = SimulatorBackend()
        self.store = Store()
        self.rt = Runtime(None, settings=self.settings, store=self.store, backend=self.be)
        self.tools = {name: handler for name, _schema, handler in build_tools(self.rt)}
        self.hooks = make_hooks(self.rt)
        self.cmd = make_command(self.rt)
        self.kinds: list[str] = []

    def overview(self) -> dict:
        ov = workshop.build_overview(self.rt)
        json.dumps(ov)  # JSON-ready, no custom encoder needed
        return ov

    def turn(self, session: str, sender: str, text: str) -> None:
        self.hooks["pre_llm_call"](session_id=session, user_message=text, platform="whatsapp", sender_id=sender,
                                   is_first_turn=True)

    def call(self, name: str, args: dict, session: str) -> dict:
        d = self.hooks["pre_tool_call"](tool_name=name, args=args, task_id="t", session_id=session)
        if d and d.get("action") == "block":
            self.hooks["post_tool_call"](tool_name=name, args=args, result=json.dumps({"error": d["message"]}),
                                         session_id=session)
            return {"ok": False, "blocked": True, "error": d["message"]}
        raw = self.tools[name](args, session_id=session, task_id="t")
        self.hooks["post_tool_call"](tool_name=name, args=args, result=raw, session_id=session)
        return json.loads(raw)

    def slash(self, text: str) -> str:
        return self.cmd(text, source=Source(OWNER), session_id="s-owner", platform="whatsapp")

    def watch(self) -> list[dict]:
        res = watcher.run_once(self.settings, self.be, self.store, deliver=False)
        self.kinds += [r["kind"] for r in res]
        return res

    def run_until(self, kinds: set[str], step_min: float = 5, max_steps: int = 150) -> None:
        for _ in range(max_steps):
            self.be.advance(step_min)
            self.watch()
            if kinds & set(self.kinds):
                return
        raise AssertionError(f"none of {sorted(kinds)}; saw {self.kinds}")

    # -- the request flows --
    def request(self, session: str, sender: str, model_id: int, text: str, **slice_args) -> int:
        self.turn(session, sender, text)
        imp = self.call("home3d_import", {"model_id": model_id, "request_text": text}, session)
        assert imp["ok"], imp
        sl = self.call("home3d_slice", {"library_file_id": imp["library_file_id"], "material": "PLA",
                                        "request_id": imp["request_id"], **slice_args}, session)
        assert sl["ok"], sl
        q = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl["sliced_file_id"],
                                       "request_id": imp["request_id"]}, session)
        assert q["ok"], q
        return q["queue_item_id"]

    def design_request(self, slug: str, version: int, text: str) -> int:
        self.turn("s-eng", ENGINEER, text)
        up = self.call("home3d_design", {"action": "upload", "name": slug, "version": version,
                                         "request_text": text}, "s-eng")
        assert up["ok"], up
        sl = self.call("home3d_slice", {"library_file_id": up["library_file_id"], "material": "PLA",
                                        "colour": "black", "request_id": up["request_id"]}, "s-eng")
        assert sl["ok"], sl
        q = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl["sliced_file_id"],
                                       "request_id": up["request_id"]}, "s-eng")
        assert q["ok"] and q["requester"] == "Engineer", q
        return q["queue_item_id"]


def fake_design(slug: str, version: int, dims=(40.0, 30.0, 35.0), ok: bool = True) -> None:
    """A design version on disk the way ``design.render`` leaves it (no OpenSCAD needed)."""
    folder = design.designs_dir() / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{slug}_v{version}.scad").write_text(BRACKET_SCAD, encoding="utf-8")
    meta = {"ok": ok, "name": slug, "version": version, "error": "" if ok else "Parser error in line 3",
            "previews": [], "part": "", "created": 0.0}
    if ok:
        write_box_stl(folder / f"{slug}_v{version}.stl", dims)
        png = folder / f"{slug}_v{version}_iso.png"
        png.write_bytes(render_plate_png({"dims": list(dims), "colour": "#4682B4"}))
        meta.update(size_mm=list(dims), volume_cm3=round(dims[0] * dims[1] * dims[2] / 1000, 2), bodies=1,
                    est_grams_max=round(dims[0] * dims[1] * dims[2] / 1000 * 1.24, 1), triangles=12,
                    fits_build_volume=True, simple=True, previews=[str(png.resolve())])
    (folder / f"{slug}_v{version}.json").write_text(json.dumps(meta), encoding="utf-8")


def real_design(slug: str) -> bool:
    """Two real OpenSCAD versions (v1 too thin, v2 thicker), when openscad is installed."""
    if not shutil.which("openscad"):
        return False
    r1 = design.render(slug, BRACKET_SCAD.replace("thick = 4", "thick = 2.4"), views=["iso", "top"], timeout_s=120)
    r2 = design.render(slug, BRACKET_SCAD, views=["iso", "top"], timeout_s=120)
    return bool(r1.ok and r2.ok)


@pytest.fixture
def shop():
    s = Shop()
    s.watch()  # baseline pass
    return s


# ---- states ----------------------------------------------------------------------------------------------------------
def test_fresh_simulator_overview_has_every_section_and_nothing_made_up(shop):
    ov = shop.overview()
    assert TOP_KEYS <= set(ov) and ov["schema"] == workshop.SCHEMA_VERSION
    assert ov["backend"] == "simulator" and ov["simulated"] is True and ov["persona"] == "Mıstık"
    assert ov["printer"]["state"] == "idle" and ov["printer"]["errors"] == []
    assert ov["now"] is None and ov["waiting"] == [] and ov["queue"] == [] and ov["done_box"] == []
    assert ov["needs_human"] == [] and ov["upgrades"] == [] and ov["designs"] == []
    assert ov["notices"] == {"pending": 0, "sent": 0, "failed": 0, "no_target": 0, "dry_run": 0, "recent": []}
    assert [s["slot"] for s in ov["filament"]["slots"]] == [0, 1, 2, 3]
    assert ov["filament"]["slots"][0]["label"] == "Slot 1"
    assert ov["watcher"]["fresh"] is True and ov["watcher"]["model_calls"] == 0
    assert ov["camera"]["available"] is True and ov["camera"]["frame"] is None
    assert ov["groups"] == [{"name": "Family", "tone": "family", "language": "en", "members": 1},
                            {"name": "R&D", "tone": "team", "language": "en", "members": 1}]
    assert "target" not in json.dumps(ov["groups"])
    assert ov["viewer"] == {"is_owner": True, "reason": ""}
    setup = ov["setup"]
    assert setup["checked_ts"] and setup["pending"] is False  # the first overview waited for the run
    ids = {c["id"]: c for c in setup["checks"]}
    assert list(ids) == list(checks.CHECK_IDS)
    assert ids["printer"]["status"] == "ok" and ids["camera"]["status"] == "ok"
    assert all(c["status"] in ("ok", "warn", "missing", "error") for c in ids.values())
    assert ov["problems"] == []


def test_a_designed_part_waiting_for_the_owners_approval(shop):
    fake_design("rail-bracket", 1)
    qid = shop.design_request("rail-bracket", 1, "a bracket for the lab rail")
    blocked = shop.call("home3d_start", {"queue_item_id": qid}, "s-eng")
    assert blocked["blocked"]

    ov = shop.overview()
    assert len(ov["waiting"]) == 1
    w = ov["waiting"][0]
    req = shop.store.approval_requests()[0]
    assert w["id"] == req["id"] and w["source"] == "request" and w["action"] == "start"
    assert w["queue_item_id"] == qid and w["command"] == f"home3d approve start {qid}" and w["alt"] is None
    assert w["asked_by"] == {"name": "Engineer", "group": "R&D"} and w["request_text"] == "a bracket for the lab rail"
    f = w["facts"]
    assert f["print_time_min"] and f["grams"] and f["material"] == "PLA" and f["color"] == "#000000"
    assert f["slot"] == 2 and f["slot_label"] == "Slot 3" and isinstance(f["eject_planned"], bool)
    checks = {c["id"]: c for c in w["checklist"]}
    assert set(checks) == {"printer_free", "no_error", "still_waiting", "plate", "turn", "filament"}
    assert all(c["ok"] for c in checks.values()), checks
    assert "right before the start" in checks["plate"]["detail"]
    assert w["ready"] is True
    assert w["model"]["stl"] == "designs/rail-bracket/rail-bracket_v1.stl"
    assert workshop.resolve_file(shop.rt, w["model"]["stl"]).name == "rail-bracket_v1.stl"
    assert workshop.resolve_file(shop.rt, w["model"]["preview"]).suffix == ".png"

    q = ov["queue"]
    assert [i["id"] for i in q] == [qid] and q[0]["ours"] is True and q[0]["for"]["name"] == "Engineer"
    assert q[0]["model"]["stl"] == w["model"]["stl"]
    d = ov["designs"]
    assert d[0]["slug"] == "rail-bracket" and d[0]["versions"][0]["stl"] == w["model"]["stl"]
    assert d[0]["versions"][0]["facts"]["ok"] is True
    assert ov["notices"]["recent"] == []  # the watcher has not told the owner yet

    shop.watch()  # the watcher tells the owner once (outbox only in this test): still waiting for the click
    ov = shop.overview()
    assert [w["id"] for w in ov["waiting"]] == [req["id"]]
    n = ov["notices"]["recent"][0]
    assert n["to"] == "owner chat" and n["status"] == "dry_run" and n["text"] and "target" not in n


def test_the_owners_own_queued_job_also_waits_and_a_job_ahead_blocks_the_turn(shop):
    shop.be.set_scenario("busy")  # a job queued elsewhere waits ahead
    shop.turn("s-owner", OWNER, "print a cable clip")
    qid = shop.request("s-owner", OWNER, CABLE_CLIP, "cable clip")
    ov = shop.overview()
    assert len(ov["waiting"]) == 1
    w = ov["waiting"][0]
    assert w["id"] is None and w["source"] == "queue" and w["key"] == f"start-{qid}"
    assert w["asked_by"]["name"] == "Sam"
    turn = next(c for c in w["checklist"] if c["id"] == "turn")
    assert turn["ok"] is False and "waiting ahead" in turn["detail"]
    assert w["ready"] is False and w["alt"]["command"] == f"home3d approve start {qid} jump"
    foreign = next(i for i in ov["queue"] if not i["ours"])
    assert foreign["for"] == {"name": "", "group": ""} and foreign["eject_planned"] is None


def test_printing_for_mum_shows_who_progress_and_the_queue(shop):
    qid = shop.request("s-mum", MUM, FLOWER_BOX, "a small box for flowers")
    reply = shop.slash(f"approve start {qid}")
    assert f"#{qid}" in reply, reply
    shop.be.advance(40)
    shop.watch()
    ov = shop.overview()
    p = ov["printer"]
    assert p["state"] == "printing" and p["job_name"] == "Flower gift box"
    assert 0 < p["progress"] < 100 and p["remaining_min"] > 0 and p["layer"] and p["total_layers"]
    assert ov["now"]["queue_item_id"] == qid and ov["now"]["for"] == {"name": "Mum", "group": "Family"}
    assert reply.endswith("[home3d:ok]") and "\"Flower gift box\"" in reply, reply
    assert ov["now"]["eject_planned"] is True and ov["now"]["model"] is None  # a MakerWorld model: no local STL
    assert [(i["id"], i["status"]) for i in ov["queue"]] == [(qid, "printing")]
    assert ov["waiting"] == []


def test_after_a_finish_the_part_is_in_the_done_box_with_its_photo(shop):
    qid = shop.request("s-mum", MUM, COASTER, "a coaster")
    shop.slash(f"approve start {qid}")
    shop.run_until({"finished_ejected"})
    ov = shop.overview()
    assert ov["printer"]["state"] == "finished"
    box = ov["done_box"]
    part = shop.store.done_box()[0]
    assert len(box) == 1 and box[0]["job_id"] == qid and box[0]["id"] == part["id"] and box[0]["outcome"] == "pushed"
    assert box[0]["for"] == {"name": "Mum", "group": "Family"} and box[0]["collected"] is False
    assert ov["generated_ts"] - 3600 < box[0]["finished_ts"] <= ov["generated_ts"] + 1  # wall time, not sim time
    assert box[0]["command"] == f"home3d collected {part['id']}"
    assert box[0]["photo"] and workshop.resolve_file(shop.rt, box[0]["photo"]).is_file()
    assert ov["camera"]["frame"] and ov["camera"]["taken_ts"]
    assert any(n["to"] == "Family" for n in ov["notices"]["recent"])
    assert ov["now"]["queue_item_id"] == qid  # the finished job is still what the printer shows


def test_after_a_failure_the_plate_check_blocks_the_next_start_and_a_human_moment_is_logged(shop):
    shop.be.set_scenario("fail")
    qid = shop.request("s-mum", MUM, COASTER, "a coaster")
    shop.slash(f"approve start {qid}")
    shop.run_until({"failed"})
    shop.be.set_scenario("ok")
    fake_design("rail-bracket", 1)
    qid2 = shop.design_request("rail-bracket", 1, "a bracket")
    shop.call("home3d_start", {"queue_item_id": qid2}, "s-eng")
    ov = shop.overview()
    assert ov["printer"]["state"] == "failed"
    assert all(d["job_id"] != qid for d in ov["done_box"])  # a failed print leaves no part to collect
    assert any(h["kind"] == "failure_check" and h["open"] for h in ov["needs_human"])
    assert ov["needs_human"][0]["open"]  # open moments come first
    w = next(w for w in ov["waiting"] if w["queue_item_id"] == qid2)
    plate = next(c for c in w["checklist"] if c["id"] == "plate")
    assert plate["ok"] is False and "failed" in plate["detail"] and w["ready"] is False


def test_paused_with_a_printer_error_offers_resume_with_ack(shop):
    shop.be.set_scenario("pause_hms")
    qid = shop.request("s-mum", MUM, FLOWER_BOX, "flower box")
    shop.slash(f"approve start {qid}")
    shop.run_until({"paused"})
    shop.turn("s-mum", MUM, "is it stuck?")
    shop.call("home3d_stop", {"action": "resume", "reason": "Mum asks"}, "s-mum")
    ov = shop.overview()
    assert ov["printer"]["state"] == "paused" and ov["printer"]["errors"][0]["code"]
    w = next(w for w in ov["waiting"] if w["action"] == "resume")
    assert w["command"] == "home3d approve resume" and w["alt"]["command"] == "home3d approve resume ack"
    assert next(c for c in w["checklist"] if c["id"] == "no_error")["ok"] is False


def test_offline_printer_is_a_state_not_a_crash(shop):
    shop.be.set_scenario("offline")
    ov = shop.overview()
    assert ov["printer"]["state"] == "offline" and ov["camera"]["available"] is False
    assert ov["filament"]["slots"] == [] and ov["queue"] == []
    assert next(c for c in ov["setup"]["checks"] if c["id"] == "printer")["status"] == "error"


def test_a_backend_that_raises_still_gives_a_screen(shop, monkeypatch):
    from home3d_ws.home3d.backends.base import BackendError

    def down():
        raise BackendError("Bambuddy unreachable (simulated)")

    monkeypatch.setattr(shop.be, "status", down)
    ov = shop.overview()
    assert ov["printer"]["state"] == "offline"
    assert ov["printer"]["errors"] == [{"code": "", "text": "Bambuddy unreachable (simulated)"}]


def test_one_broken_section_is_reported_and_the_rest_still_render(shop, monkeypatch):
    def boom(limit=20):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(design, "list_designs", boom)
    ov = shop.overview()
    assert ov["designs"] == [] and ov["printer"]["state"] == "idle"
    assert any(p.startswith("designs: RuntimeError") for p in ov["problems"])


def test_the_overview_never_takes_a_photo_checks_the_plate_or_writes_to_the_printer(shop, monkeypatch):
    qid = shop.request("s-mum", MUM, COASTER, "a coaster")
    shop.call("home3d_start", {"queue_item_id": qid}, "s-mum")
    for name in ("snapshot", "check_plate", "snapshot_and_check", "start", "stop", "pause", "resume",
                 "mark_plate_cleared", "queue_add", "queue_remove", "slice", "upload_file", "import_model"):
        monkeypatch.setattr(shop.be, name, lambda *a, _n=name, **k: pytest.fail(f"overview called {_n}"))
    monkeypatch.setattr(shop.rt, "plate_check", lambda *a, **k: pytest.fail("overview ran a plate check"))
    ov = shop.overview()
    assert ov["waiting"] and ov["problems"] == []


def test_collected_through_the_command_and_the_groups_setting(shop):
    qid = shop.request("s-mum", MUM, COASTER, "a coaster")
    shop.slash(f"approve start {qid}")
    shop.run_until({"finished_ejected"})
    d = shop.overview()["done_box"][0]
    assert d["collected"] is False and d["job_id"] == qid
    reply = shop.slash(d["command"].removeprefix("home3d "))
    assert reply.endswith("[home3d:ok]") and "coaster" in reply.lower(), reply
    d = shop.overview()["done_box"][0]
    assert d["collected"] is True and d["collected_by"] == "Sam" and d["collected_ts"]
    shop.settings.groups = [{"name": "Lab", "tone": "team", "target": "telegram:<lab>"}]
    assert shop.overview()["groups"] == [{"name": "Lab", "tone": "team", "language": "en", "members": 0}]


def test_notices_show_dry_run_neutrally_and_hide_texts_from_a_non_owner(shop):
    shop.store.outbox_add(audience="family", target="telegram:<family-group>", text="Your coaster is ready",
                          group="Family", status="dry_run", job_name="coaster.gcode.3mf")
    shop.store.outbox_add(audience="owner", target="telegram:<owner-chat>", text="Coaster done", status="pending")
    ov = shop.overview()
    n = ov["notices"]
    assert n["dry_run"] == 1 and n["failed"] == 0 and n["pending"] == 1
    dry = next(r for r in n["recent"] if r["status"] == "dry_run")
    assert dry["to"] == "Family" and dry["text"] == "Your coaster is ready" and dry["job"] == "coaster"
    assert "<family-group>" not in json.dumps(n) and "<owner-chat>" not in json.dumps(n)
    shop.settings.local_is_owner = False
    n = shop.overview()["notices"]
    assert all(r["text"] == "" and r["error"] == "" for r in n["recent"]) and n["dry_run"] == 1
    assert "coaster is ready" not in json.dumps(n).lower()
    assert all(c["detail"] == "" for c in shop.overview()["setup"]["checks"])


def test_setup_checks_are_cached_and_never_hold_up_the_overview(shop, monkeypatch):
    shop.overview()  # first run, cached
    calls = []
    monkeypatch.setattr(checks, "run_checks", lambda *a, **k: calls.append(1) or [])
    shop.overview()
    assert calls == []  # reused
    monkeypatch.setattr(workshop, "SETUP_MAX_AGE_S", 0.0)
    import threading
    gate = threading.Event()

    def slow(*a, **k):
        gate.wait(10)
        return [{"id": "printer", "label": "Printer", "status": "ok", "detail": "", "fix": ""}]

    monkeypatch.setattr(checks, "run_checks", slow)
    ov = shop.overview()  # stale: the old rows come back at once, a run goes on in the background
    assert ov["setup"]["pending"] is True and ov["setup"]["checks"]
    gate.set()


def test_design_versions_list_failed_ones_with_their_error(shop):
    fake_design("phone-stand", 1)
    fake_design("phone-stand", 2, ok=False)
    fake_design("phone-stand", 3, dims=(70.0, 85.0, 60.0))
    ov = shop.overview()
    d = next(x for x in ov["designs"] if x["slug"] == "phone-stand")
    assert [v["version"] for v in d["versions"]] == [1, 2, 3] and d["latest_ok"] == 3
    v2 = d["versions"][1]
    assert v2["stl"] is None and v2["previews"] == [] and v2["facts"]["ok"] is False and "Parser" in v2["note"]
    assert d["versions"][2]["facts"]["size_mm"] == [70.0, 85.0, 60.0]


def test_upgrade_proposal_and_open_moments(shop):
    for _ in range(3):
        upgrades.log_moment(shop.store, "remove_part", "part left on the plate", job_name="coaster", source="watcher")
    upgrades.evaluate(shop.store, shop.settings)
    ov = shop.overview()
    assert ov["upgrades"][0]["status"] == "proposed" and ov["upgrades"][0]["count"] == 3
    assert ov["upgrades"][0]["title"].startswith("Auto-eject") and ov["upgrades"][0]["why"]
    assert ov["needs_human"][0]["text"].startswith("Take a finished part off the plate")


def test_names_read_the_way_people_say_them():
    assert workshop.pretty_name("flower_box_v2.gcode.3mf") == "flower box v2"
    assert workshop.pretty_name("mum-key-tag_v1") == "Mum key tag v1"
    assert workshop.pretty_name("Cable clip") == "Cable clip"
    assert workshop.pretty_name("T-Rex skull") == "T-Rex skull"


def test_an_approval_wait_moment_shows_no_internal_tool_note(shop):
    upgrades.log_moment(shop.store, "approve_start", "home3d_start start:5 waited for the owner's approval",
                        source="gate")
    h = shop.overview()["needs_human"][0]
    assert h["kind"] == "approve_start" and "home3d_" not in h["text"] and ":" not in h["text"]


# ---- file references ---------------------------------------------------------------------------------------------
def test_file_refs_are_confined_to_designs_and_media(shop, data_dir, tmp_path):
    fake_design("rail-bracket", 1)
    good = "designs/rail-bracket/rail-bracket_v1.stl"
    payload = workshop.file_payload(shop.rt, good)
    assert payload["name"] == "rail-bracket_v1.stl" and payload["mime"] == "model/stl"
    assert payload["dataUrl"].startswith("data:model/stl;base64,") and payload["bytes"] > 0

    (data_dir / "secret.png").write_bytes(b"x")
    (data_dir / "media").mkdir(exist_ok=True)
    (data_dir / "media" / "notes.txt").write_text("x")
    (data_dir / "media" / "big.png").write_bytes(b"\0" * (workshop.MAX_IMAGE_BYTES + 1))
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    (data_dir / "media" / "link.png").symlink_to(outside)
    (data_dir / "media" / "db.png").symlink_to(data_dir / "workshop.db")
    cases = {
        "": 400, "../outside.png": 400, "designs/../secret.png": 400, "/etc/passwd": 400,
        str(data_dir / "secret.png"): 400, "designs\\x.stl": 400, "designs/x.stl\x00.png": 400, "~/x.png": 400,
        "designs//x.stl": 400, "secret.png": 403, "workshop.db": 403, "media/notes.txt": 415,
        "designs/rail-bracket/rail-bracket_v1.scad": 415, "designs/rail-bracket/rail-bracket_v1.json": 415,
        "media/nope.png": 404, "media/big.png": 413, "media/link.png": 403, "media/db.png": 403,
    }
    for ref, code in cases.items():
        with pytest.raises(workshop.FileRefError) as err:
            workshop.resolve_file(shop.rt, ref)
        assert err.value.status == code, (ref, err.value.status, str(err.value))


def test_file_ref_only_names_files_it_would_serve(shop, data_dir, tmp_path):
    fake_design("rail-bracket", 1)
    stl = design.designs_dir() / "rail-bracket" / "rail-bracket_v1.stl"
    assert workshop.file_ref(stl) == "designs/rail-bracket/rail-bracket_v1.stl"
    assert workshop.file_ref(data_dir / "workshop.db") is None
    assert workshop.file_ref(tmp_path / "elsewhere.png") is None
    assert workshop.file_ref(None) is None


# ---- the fixture for the front end ---------------------------------------------------------------------------------
def build_showcase(shop: Shop, *, real_render: bool = False) -> dict:
    """Every section with data: two deliveries (one pushed off, one taken off by hand), Mum's flower box printing,
    the Engineer's designed bracket waiting for approval, a human-needed moment and an upgrade proposal."""
    # history: two earlier "took it off by hand" moments, so the third one makes a proposal
    for _ in range(2):
        upgrades.log_moment(shop.store, "remove_part", "part left on the plate", job_name="Pen holder",
                            source="watcher")
    # delivery 1: Mum's coaster, pushed off into the done box
    q1 = shop.request("s-mum", MUM, COASTER, "a coaster for the living room")
    shop.slash(f"approve start {q1}")
    shop.run_until({"finished_ejected"})
    # delivery 2: Sam's cable clip, sliced without auto-eject: someone takes it off the plate by hand
    shop.turn("s-owner", OWNER, "print me a cable clip, no push-off")
    q2 = shop.request("s-owner", OWNER, CABLE_CLIP, "cable clip", eject="off")
    shop.run_until({"ready_next"})
    shop.slash(f"approve start {q2}")
    shop.kinds.clear()
    shop.run_until({"finished"})
    shop.be.human_clears_plate()
    shop.kinds.clear()
    shop.run_until({"plate_clear", "ready_next"})
    shop.slash(f"collected {shop.store.done_box()[-1]['id']}")  # Mum picked up her coaster
    # now: Mum's flower box printing
    q3 = shop.request("s-mum", MUM, FLOWER_BOX, "a small box for flowers")
    shop.watch()
    shop.slash(f"approve start {q3}")
    shop.be.advance(55)
    shop.watch()
    # the Engineer's designed bracket (two versions), queued and asked for
    if not (real_render and real_design("rail-bracket")):
        fake_design("rail-bracket", 1, dims=(40.0, 30.0, 35.0))
        fake_design("rail-bracket", 2, dims=(40.0, 30.0, 35.0))
    q4 = shop.design_request("rail-bracket", 2, "a bracket for the lab rail, 4 mm thick")
    shop.call("home3d_start", {"queue_item_id": q4}, "s-eng")
    shop.be.advance(2)
    shop.watch()
    return shop.overview()


def test_showcase_fills_every_section(shop):
    ov = build_showcase(shop)
    assert ov["printer"]["state"] == "printing" and ov["now"]["for"]["name"] == "Mum"
    assert [w["asked_by"]["name"] for w in ov["waiting"]] == ["Engineer"] and ov["waiting"][0]["model"]["stl"]
    assert len(ov["done_box"]) == 2
    assert {d["outcome"] for d in ov["done_box"]} == {"pushed", "taken_off"}
    assert any(d["collected"] for d in ov["done_box"])
    assert ov["needs_human"] and ov["upgrades"] and ov["designs"] and ov["notices"]["recent"]
    assert ov["camera"]["frame"] and ov["filament"]["slots"] and ov["groups"]
    assert ov["problems"] == []


def test_fixture_matches_the_contract(shop):
    if os.environ.get("HOME3D_WRITE_FIXTURE") == "1":
        ov = build_showcase(shop, real_render=True)
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(workshop.dumps(ov) + "\n", encoding="utf-8")
        # the files the overview names, at their reference paths, for a front-end mock of GET file?ref=
        shutil.rmtree(FIXTURE_FILES, ignore_errors=True)
        for ref in sorted(set(re.findall(r'"((?:designs|media)/[^"]+)"', FIXTURE.read_text(encoding="utf-8")))):
            dest = FIXTURE_FILES / ref
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(workshop.resolve_file(shop.rt, ref), dest)
    if not FIXTURE.is_file():
        pytest.skip("no fixture yet (HOME3D_WRITE_FIXTURE=1 writes it)")
    ov = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert TOP_KEYS <= set(ov) and ov["schema"] == workshop.SCHEMA_VERSION
    assert ov["printer"]["state"] in ("idle", "printing", "paused", "finished", "failed", "offline")
    for w in ov["waiting"]:
        assert {"id", "action", "queue_item_id", "name", "asked_by", "asked_ts", "facts", "checklist", "command",
                "model"} <= set(w)
        assert w["action"] in ("start", "clear", "resume") and not w["command"].startswith("/")
    for d in ov["done_box"]:
        assert d["outcome"] in ("pushed", "on_plate", "taken_off", "unknown") and d["command"] == f"home3d collected {d['id']}"
    for n in ov["notices"]["recent"]:
        assert n["status"] in ("sent", "pending", "failed", "no_target", "dry_run") and "target" not in n
    for c in ov["setup"]["checks"]:
        assert c["status"] in ("ok", "warn", "missing", "error")
    assert ov["now"] and ov["waiting"] and len(ov["done_box"]) >= 2 and ov["needs_human"] and ov["upgrades"]
    assert ov["designs"][0]["versions"][-1]["stl"]
    for ref in set(re.findall(r'"((?:designs|media)/[^"]+)"', FIXTURE.read_text(encoding="utf-8"))):
        assert (FIXTURE_FILES / ref).is_file(), ref  # every file the fixture names ships beside it
