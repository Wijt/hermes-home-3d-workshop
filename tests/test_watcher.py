"""watcher.py: zero-token pass over a fake backend (real eject/messages/notify/upgrades modules)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

from home3d_ws.home3d import notify, watcher
from home3d_ws.home3d.backends.base import (FAILED, FINISH, IDLE, OFFLINE, PAUSE, RUNNING, Backend, BackendError,
                                            HMSError, PlateCheck, PrinterStatus, QueueItem, Snapshot)
from home3d_ws.home3d.config import Settings, write_snapshot
from home3d_ws.home3d.store import Store

ROOT = Path(__file__).resolve().parents[1]
MIN = 60.0
T0 = 1_700_000_000.0
EMPTY = PlateCheck(is_empty=True, difference_pct=1.8, confidence=0.95, message="empty")
OCCUPIED = PlateCheck(is_empty=False, difference_pct=41.0, confidence=0.9, message="objects")
RUNOUT = HMSError(code="0700-2000-0002-0001", severity="common",
                  message="AMS A Slot 1 filament has run out. Please insert a new filament.",
                  wiki_url="https://wiki.bambulab.com/en/a1/troubleshooting/hmscode/0700_2000_0002_0001")


class FakeBackend(Backend):
    name = "fake"

    def __init__(self):
        self.st = PrinterStatus(state=IDLE, bed_temp=25.0)
        self.items: list[QueueItem] = []
        self.plate = EMPTY
        self.error: Optional[str] = None
        self.snaps = self.checks = 0

    def status(self):
        if self.error:
            raise BackendError(self.error)
        return self.st

    def queue(self, include_done=False):
        return [q for q in self.items if include_done or q.status in ("pending", "printing")]

    def snapshot(self, out_dir, lit=True):
        self.snaps += 1
        p = Path(out_dir) / f"snap-{self.snaps}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\xff\xd8\xff\xe0fake")
        return Snapshot(path=p, lit=lit, note="fake")

    def check_plate(self):
        self.checks += 1
        return self.plate

    def resolve_model(self, url_or_id):
        raise NotImplementedError

    def library_gcode(self, library_file_id, max_bytes=8_000_000):
        raise NotImplementedError

    def import_model(self, model_id, profile_id=None):
        raise NotImplementedError

    def upload_file(self, path):
        raise NotImplementedError

    def download_file(self, library_file_id, out_dir):
        raise NotImplementedError

    def slice(self, library_file_id, options, timeout_s=900):
        raise NotImplementedError

    def queue_add(self, library_file_id, *, ams_mapping=None, plate_id=None, manual_start=True):
        raise AssertionError("the watcher must never queue")

    def queue_remove(self, queue_item_id):
        raise AssertionError("the watcher must never touch the queue")

    def start(self, queue_item_id):
        raise AssertionError("the watcher must never start a job")

    def stop(self):
        raise AssertionError("the watcher must never stop")

    def pause(self):
        raise AssertionError("the watcher must never pause")

    def resume(self):
        raise AssertionError("the watcher must never resume")

    def mark_plate_cleared(self):
        raise AssertionError("the watcher must never mark the plate clear")


def settings(**kw) -> Settings:
    base = dict(language="tr", owner_name="Sam", owner_ids=["owner-1"], persona_name="Mıstık",
                household=[{"id": "fam-1", "name": "Mum", "address_as": "Anneciğim"},
                           {"id": "fam-2", "name": "Dad"}],
                eject_cool_temp_c=30.0)
    base.update(kw)
    return Settings(**base)


class Rig:
    def __init__(self, **kw):
        self.s = settings(**kw)
        self.b = FakeBackend()
        self.store = Store()
        self.t = T0

    def run(self, minutes: float = 0, **kw) -> list[dict]:
        self.t += minutes * MIN
        return watcher.run_once(self.s, self.b, self.store, now=self.t, **kw)

    def status(self, state, **kw):
        self.b.st = PrinterStatus(state=state, **kw)

    @property
    def kv(self) -> dict:
        return self.store.kv_get(watcher.KV_KEY)


def kinds(results):
    return [r["kind"] for r in results]


@pytest.fixture
def rig():
    r = Rig()
    r.run()  # first pass on an idle printer: baseline only
    return r


def test_first_pass_on_idle_printer_is_silent(rig):
    assert rig.kv["initialized"] and rig.kv["state"] == IDLE
    assert notify.read_outbox() == []


def test_auto_eject_job_full_loop(rig):
    rig.store.upsert_job(7, name="Gül kutusu.gcode.3mf", requester="Mum", eject_planned=1, state="queued")
    rig.status(RUNNING, job_name="Gül kutusu", progress=50, layer=50, total_layers=100, bed_temp=65)
    assert rig.run(2) == []
    assert rig.store.get_job(7)["state"] == "printing"

    rig.status(RUNNING, job_name="Gül kutusu", progress=99, layer=99, total_layers=100, bed_temp=65)
    assert rig.run(30) == [] and rig.b.snaps == 1  # "done" photo before the push
    part_photo = rig.kv["photo_path"]

    rig.status(FINISH, job_name="Gül kutusu", progress=100, layer=100, total_layers=100, bed_temp=60)
    (fin,) = rig.run(2)
    assert fin["kind"] == "finished" and fin["family_text"] == ""  # family waits for the eject outcome
    assert "Otomatik düşürme bekleniyor" in fin["owner_text"] and "#7" in fin["owner_text"]
    assert fin["owner_media"] == part_photo
    assert rig.store.get_job(7)["state"] == "finished"

    rig.status(FINISH, job_name="Gül kutusu", progress=100, bed_temp=28)
    rig.b.plate = OCCUPIED  # the push has not happened yet: an early miss does not count
    assert rig.run(10) == []
    rig.b.plate = EMPTY
    (done,) = rig.run(15)
    assert done["kind"] == "finished_ejected"
    assert done["family_text"] == '✅ Anneciğim, "Gül kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin.'
    assert done["family_media"] == part_photo and done["owner_media"] not in ("", part_photo)
    assert rig.store.get_job(7)["state"] == "cleared"

    box = notify.read_outbox()
    audiences = [(r["audience"], r["dry_run"]) for r in box]
    assert audiences == [("owner", True), ("owner", True), ("family", True)]
    assert box[-1]["media"] == part_photo
    assert rig.store.human_needed() == []

    # a manual job is waiting: tell the owner once, never start it
    rig.b.items = [QueueItem(id=8, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    (ready,) = rig.run(2)
    assert ready["kind"] == "ready_next" and "/home3d approve start 8" in ready["owner_text"]
    assert ready["family_text"] == ""
    assert rig.run(2) == []


def test_finish_without_eject_tells_family_and_logs_moment_until_upgrade(rig):
    for i in range(3):
        name = f"Parça {i}"
        rig.store.upsert_job(20 + i, name=name, requester="Dad", eject_planned=0)
        rig.status(RUNNING, job_name=name, progress=40, layer=4, total_layers=10, bed_temp=60)
        rig.run(5)
        rig.status(FINISH, job_name=name, progress=100, layer=10, total_layers=10, bed_temp=50)
        results = rig.run(30)
        assert kinds(results)[0] == "finished"
        assert results[0]["family_text"] == f'✅ Dad, "{name}" bitti, yazıcıda seni bekliyor.'
        assert "/home3d approve clear" in results[0]["owner_text"]
        assert results[0]["family_media"]  # photo of the finished part for the family
        rig.status(IDLE, bed_temp=25)  # someone took it off and the printer went idle
        assert kinds(rig.run(5)) == ["plate_clear"]  # short owner note: the plate is free again
    assert len(rig.store.human_needed("remove_part")) == 3
    assert kinds(results) == ["finished", "upgrade_proposed"]
    up = results[1]
    assert "makerworld.com/en/models/2335000" in up["owner_text"] and up["family_text"] == ""
    assert rig.store.upgrade_for_kind("remove_part")["status"] == "proposed"
    # one merged owner message for the finishing pass
    owner_msgs = [r for r in notify.read_outbox() if r["audience"] == "owner"]
    assert "💡" in owner_msgs[-2]["text"] and owner_msgs[-2]["text"].startswith("✅ Bitti")


def test_failed_print_resolves_requester_from_request(rig):
    rid = rig.store.add_request(requester="Mum", text="bir vazo")
    rig.store.upsert_job(9, request_id=rid, name="Vazo")
    rig.status(RUNNING, job_name="Vazo", progress=30, layer=12, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.status(FAILED, job_name="Vazo", progress=40, layer=16, total_layers=40, bed_temp=55)
    (r,) = rig.run(2)
    assert r["kind"] == "failed"
    assert r["family_text"] == '⚠️ Anneciğim, yazıcı durdu, "Vazo" yarıda kaldı (%40). Sam\'a haber verdim.'
    assert "katman 16/40" in r["owner_text"] and r["owner_media"]
    assert rig.store.get_job(9)["state"] == "failed"
    assert rig.store.get_request(rid)["status"] == "failed"
    assert [m["kind"] for m in rig.store.human_needed()] == ["failure_check"]
    assert rig.run(2) == []


def test_filament_runout_pause_once_and_new_hms_owner_only(rig):
    rig.store.upsert_job(11, name="Saksı", requester="Mum", eject_planned=1)
    rig.status(RUNNING, job_name="Saksı", progress=20, layer=6, total_layers=30, bed_temp=60)
    rig.run(2)
    rig.status(PAUSE, job_name="Saksı", progress=30, layer=9, total_layers=30, bed_temp=60, hms=[RUNOUT])
    (p,) = rig.run(2)
    assert p["kind"] == "paused"
    assert "filament bitti" in p["family_text"] and "0700" not in p["family_text"]
    assert "0700-2000-0002-0001" in p["owner_text"] and "wiki.bambulab.com" in p["owner_text"]
    assert [m["kind"] for m in rig.store.human_needed()] == ["filament_swap"]
    assert rig.run(2) == []  # still paused: no repeat

    rig.status(RUNNING, job_name="Saksı", progress=35, layer=10, total_layers=30, bed_temp=60)
    assert rig.run(2) == []
    nozzle = HMSError(code="0300-0D00-0001-0003", message="nozzle clog suspected")
    rig.status(RUNNING, job_name="Saksı", progress=40, layer=12, total_layers=30, bed_temp=60, hms=[nozzle])
    (h,) = rig.run(2)
    assert h["kind"] == "hms" and h["family_text"] == "" and "0300-0D00-0001-0003" in h["owner_text"]
    assert rig.run(2) == []


def test_harmless_hms_is_ignored(rig):
    harmless = HMSError(code="0300-1000-0002-0001", message="X-belt resonance notice")
    rig.status(RUNNING, job_name="Kutu", progress=10, layer=1, total_layers=10, bed_temp=60, hms=[harmless])
    assert rig.run(2) == []


def test_offline_notifies_owner_once_after_ten_minutes(rig):
    rig.b.error = "GET /printers/1/status: timed out"
    assert rig.run(1) == []
    assert rig.run(5) == []
    (o,) = rig.run(6)
    assert o["kind"] == "offline" and o["family_text"] == "" and "ulaşılamıyor" in o["owner_text"]
    assert rig.run(30) == []
    rig.b.error = None
    assert rig.run(2) == []
    assert rig.kv["offline_since"] is None and rig.kv["online"] is True
    rig.status(OFFLINE, connected=False)  # backend reports offline without raising
    rig.run(1)
    assert rig.run(11)[0]["kind"] == "offline"


def test_first_pass_on_a_failed_printer_is_quiet_until_plate_clears():
    rig = Rig()
    rig.b.plate = OCCUPIED
    rig.status(FAILED, job_name="eski iş", progress=0, layer=75, total_layers=75, bed_temp=24)
    assert rig.run() == []
    assert rig.kv["plate_state"]["phase"] == "needs_human"
    assert rig.store.human_needed() == [] and notify.read_outbox() == []
    rig.b.plate = EMPTY
    assert rig.run(5) == []  # re-checks only every 15 min
    (c,) = rig.run(11)
    assert c["kind"] == "plate_clear" and c["family_text"] == "" and "Tabla boş" in c["owner_text"]


def test_eject_miss_asks_a_person_and_logs_remove_part(rig):
    rig.store.upsert_job(30, name="Tabak", requester="Mum", eject_planned=1)
    rig.status(RUNNING, job_name="Tabak", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.b.plate = OCCUPIED
    rig.status(FINISH, job_name="Tabak", progress=100, layer=10, total_layers=10, bed_temp=26)
    assert kinds(rig.run(2)) == ["finished"]
    out = []
    for _ in range(8):
        out += rig.run(5)
    assert kinds(out) == ["plate_not_clear"]
    assert "tablada kaldı" in out[0]["family_text"] and "Anneciğim" in out[0]["family_text"]
    assert "parça hâlâ tablada" in out[0]["owner_text"]
    assert [m["kind"] for m in rig.store.human_needed()] == ["remove_part"]
    # the person takes it off: plate clear, short owner note only
    rig.b.plate = EMPTY
    later = rig.run(16)
    assert kinds(later) == ["plate_clear"] and later[0]["family_text"] == ""


def test_owner_or_unknown_requester_gets_no_family_message(rig):
    rig.store.upsert_job(40, name="Braket", requester="Sam", eject_planned=0)
    for name in ("Braket", "Yabancı iş"):
        rig.status(RUNNING, job_name=name, progress=50, layer=5, total_layers=10, bed_temp=60)
        rig.run(2)
        rig.status(FINISH, job_name=name, progress=100, layer=10, total_layers=10, bed_temp=40)
        (r,) = rig.run(2)
        assert r["kind"] == "finished" and r["family_text"] == ""
        rig.status(IDLE, bed_temp=25)
        rig.run(1)


def test_deliver_false_is_a_dry_run(rig, monkeypatch):
    calls = []
    monkeypatch.setattr(notify, "_attempt", lambda cmd: calls.append(cmd) or (True, ""))
    rig.s.owner_target = "whatsapp:<owner-group>@g.us"
    rig.status(PAUSE, job_name="X", progress=5, layer=1, total_layers=10)
    (r,) = rig.run(1, deliver=False)
    assert calls == [] and r["deliveries"][0]["dry_run"] is True


def test_concurrent_pass_is_skipped(rig, data_dir):
    import fcntl

    with open(Path(data_dir) / watcher.LOCK_FILE, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        rig.status(PAUSE, job_name="X", progress=5)
        assert rig.run(1) == []
    assert kinds(rig.run(1)) == ["paused"]


# ---- main() / cron script -------------------------------------------------------------------------
FAKE_HERMES = 'import json\nprint(json.dumps({"success": True}))\n'


def _fake_hermes(tmp_path, monkeypatch) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    exe = bindir / "hermes"
    exe.write_text(f"#!{sys.executable}\n{FAKE_HERMES}", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.delenv(notify.DRY_RUN_ENV, raising=False)


def _paused_backend(monkeypatch) -> FakeBackend:
    b = FakeBackend()
    b.st = PrinterStatus(state=PAUSE, job_name="Vazo", progress=30, layer=3, total_layers=10, hms=[RUNOUT])
    monkeypatch.setattr(watcher, "make_backend", lambda s: b)
    return b


def test_main_is_silent_when_owner_target_is_set(tmp_path, monkeypatch, capsys):
    _fake_hermes(tmp_path, monkeypatch)
    write_snapshot(settings(owner_target="whatsapp:<owner-group>@g.us"))
    _paused_backend(monkeypatch)
    assert watcher.main([]) == 0
    assert capsys.readouterr().out == ""
    (rec,) = notify.read_outbox()
    assert rec["ok"] is True and rec["dry_run"] is False and rec["audience"] == "owner"


def test_main_prints_owner_text_for_cron_delivery_without_target(monkeypatch, capsys):
    write_snapshot(settings(owner_target=""))
    _paused_backend(monkeypatch)
    assert watcher.main([]) == 0
    out = capsys.readouterr().out
    assert "Duraklatıldı" in out and "MEDIA:" in out


def test_main_exits_zero_and_reports_setup_errors_once(monkeypatch, capsys):
    write_snapshot(settings(backend="bambuddy", bambuddy_url=""))
    assert watcher.main([]) == 0
    assert "bambuddy_url" in capsys.readouterr().out
    assert watcher.main([]) == 0
    assert capsys.readouterr().out == ""  # same error: not repeated
    assert (Path(os.environ["HOME3D_DATA_DIR"]) / watcher.LOG_FILE).exists()


def _run_script(script: Path, env_extra: Optional[dict] = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True, env=env, timeout=60,
                          cwd=str(script.parent))


def test_cron_script_template_copied_anywhere(tmp_path, monkeypatch):
    _fake_hermes(tmp_path, monkeypatch)
    write_snapshot(settings(owner_target="whatsapp:<owner-group>@g.us", backend="simulator"))
    template = (ROOT / "scripts" / "home3d_watch.py").read_text(encoding="utf-8")
    assert template.count("__PLUGIN_DIR__") == 1
    home = tmp_path / "hermes-home" / "scripts"
    home.mkdir(parents=True)
    script = home / "home3d_watch.py"
    script.write_text(template.replace("__PLUGIN_DIR__", str(ROOT)), encoding="utf-8")
    proc = _run_script(script)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def test_cron_script_runs_in_place_and_fails_loudly_on_a_bad_plugin_dir(tmp_path):
    write_snapshot(settings(owner_target="whatsapp:<owner-group>@g.us"))
    proc = _run_script(ROOT / "scripts" / "home3d_watch.py", {"HOME3D_DRY_RUN": "1"})
    assert proc.returncode == 0 and proc.stdout == "", proc.stderr
    proc = _run_script(ROOT / "scripts" / "home3d_watch.py", {"HOME3D_PLUGIN_DIR": str(tmp_path / "nope")})
    assert proc.returncode == 1 and "cannot load the plugin" in proc.stderr
