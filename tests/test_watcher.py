"""watcher.py: zero-token pass over a fake backend (real eject/messages/notify/upgrades modules)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

from home3d_ws.home3d import notify, watcher
from home3d_ws.home3d.backends.base import (FAILED, FINISH, IDLE, OFFLINE, PAUSE, PREPARE, RUNNING, Backend,
                                            BackendError, HMSError, PlateCheck, PrinterStatus, QueueItem, Snapshot)
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
        self.cycles = 0  # chamber light cycles: one per snapshot, check_plate or snapshot_and_check

    def status(self):
        if self.error:
            raise BackendError(self.error)
        return self.st

    def queue(self, include_done=False):
        return [q for q in self.items if include_done or q.status.lower() in ("pending", "printing")]

    def snapshot(self, out_dir, lit=True):
        self.snaps += 1
        self.cycles += 1
        p = Path(out_dir) / f"snap-{self.snaps}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\xff\xd8\xff\xe0fake")
        return Snapshot(path=p, lit=lit, note="fake")

    def check_plate(self):
        self.checks += 1
        self.cycles += 1
        return self.plate

    def snapshot_and_check(self, out_dir):  # one light cycle, like Bambuddy's
        snap, check = self.snapshot(out_dir), self.check_plate()
        self.cycles -= 1
        return snap, check

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


def owner_message(results) -> str:
    """The one owner message a pass sends (its owner texts merged, as ``deliver_notes`` does)."""
    return "\n\n".join(r["owner_text"] for r in results if r["owner_text"])


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
    rig.status(RUNNING, job_name="Gül kutusu", progress=50, layer=50, total_layers=100, bed_temp=65,
               remaining_min=90)
    (st,) = rig.run(2)  # the person who asked hears one short line; the owner started it and hears nothing
    assert st["kind"] == "started" and st["owner_text"] == ""
    assert st["family_text"] == '🖨️ Anneciğim, "Gül kutusu" basılmaya başladı, yaklaşık 1 saat 30 dakika sürecek.'
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
    assert audiences == [("family", True), ("owner", True), ("owner", True), ("family", True)]
    assert box[-1]["media"] == part_photo
    assert rig.store.human_needed() == []

    # a manual workshop job is waiting: tell the owner once (with a fresh photo), never start it
    rig.store.upsert_job(8, name="Kalemlik.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=8, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    snaps = rig.b.snaps
    (ready,) = rig.run(2)
    assert ready["kind"] == "ready_next" and "/home3d approve start 8" in ready["owner_text"]
    assert "Kameraya göre tabla boş" in ready["owner_text"] and "jump" not in ready["owner_text"]
    assert ready["family_text"] == "" and ready["owner_media"] and rig.b.snaps == snaps + 1
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
    assert r["family_text"] == '⚠️ Anneciğim, yazıcı durdu, "bir vazo" yarıda kaldı (%40). Sam\'a haber verdim.'
    assert "katman 16/40" in r["owner_text"] and '"Vazo" (#9)' in r["owner_text"] and r["owner_media"]
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


def test_light_left_on_is_told_to_the_owner_once(rig):
    rig.b.plate = PlateCheck(is_empty=True, difference_pct=1.8, light_ok=True,
                             message="empty; light_left_on: the chamber light could not be switched off again (500)")
    rig.store.upsert_job(13, name="Vazo", requester="Mum", eject_planned=0, state="queued")
    rig.status(RUNNING, job_name="Vazo", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(FINISH, job_name="Vazo", progress=100, layer=10, total_layers=10, bed_temp=26)
    out = rig.run(16) + rig.run(16)
    light = [r for r in out if r["kind"] == "light_left_on"]
    assert len(light) == 1 and light[0]["family_text"] == "" and "ışığı" in light[0]["owner_text"]
    assert not [r for r in rig.run(16) if r["kind"] == "light_left_on"]  # at most once every LIGHT_ALERT_S


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
    (back,) = rig.run(2)  # the owner was told it is unreachable, so they are told it is back (once)
    assert back["kind"] == "online" and back["family_text"] == "" and "yeniden ulaşılıyor" in back["owner_text"]
    assert "43 dakika" in back["owner_text"] and "boşta" in back["owner_text"]
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
    assert c["kind"] == "plate_clear" and c["family_text"] == "" and "Kameraya göre tabla boş" in c["owner_text"]
    assert "/home3d approve clear" in c["owner_text"]  # after a failure a person must confirm the plate
    assert c["owner_media"] and Path(c["owner_media"]).is_file()


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
    # the profile has the plugin switched on, so the installed copy really runs a watcher pass
    (home.parent / "config.yaml").write_text("plugins:\n  enabled:\n    - home-3d-workshop\n", encoding="utf-8")
    script = home / "home3d_watch.py"
    script.write_text(template.replace("__PLUGIN_DIR__", str(ROOT)), encoding="utf-8")
    proc = _run_script(script)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert (Store().kv_get(watcher.KV_KEY) or {}).get("initialized"), "the installed script ran no watcher pass"


def test_cron_script_runs_in_place_and_fails_loudly_on_a_bad_plugin_dir(tmp_path):
    write_snapshot(settings(owner_target="whatsapp:<owner-group>@g.us"))
    proc = _run_script(ROOT / "scripts" / "home3d_watch.py", {"HOME3D_DRY_RUN": "1"})
    assert proc.returncode == 0 and proc.stdout == "", proc.stderr
    proc = _run_script(ROOT / "scripts" / "home3d_watch.py", {"HOME3D_PLUGIN_DIR": str(tmp_path / "nope")})
    assert proc.returncode == 1 and "cannot load the plugin" in proc.stderr


# ---- fix round 1: whose job, what is next, honest plate wording ------------------------------------
def _finish_and_clear(rig, name="Bardak", qid=50):
    """One workshop print (no auto-eject) runs, finishes and is taken off: the plate phase is "clear"."""
    rig.store.upsert_job(qid, name=name, requester="Dad", eject_planned=0, state="queued")
    rig.status(RUNNING, job_name=name, progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(FINISH, job_name=name, progress=100, layer=10, total_layers=10, bed_temp=26)
    rig.b.plate = OCCUPIED
    rig.run(2)
    rig.b.plate = EMPTY
    out = rig.run(16)
    assert "plate_clear" in kinds(out), out
    return out


def test_ready_next_announces_our_job_not_a_stale_foreign_one_ahead(rig):
    rig.store.upsert_job(12, name="Kalemlik.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=73, status="pending", name="sabun_tabagi_v2.gcode.3mf", manual_start=True,
                             position=1, created_at="2025-11-04T10:00:00Z"),
                   QueueItem(id=12, status="pending", name="Kalemlik.gcode.3mf", manual_start=True, position=2)]
    out = _finish_and_clear(rig)
    ready = next(r for r in out if r["kind"] == "ready_next")
    text = ready["owner_text"]
    assert "/home3d approve start 12 jump" in text and '"sabun tabagi v2" (#73)' in text
    assert "approve start 73" not in text and ready["owner_media"]
    assert "queue_foreign" not in kinds(out)  # the foreign item was named in the same text
    assert rig.run(2) == [] and rig.run(30) == []  # once per item


def test_foreign_jobs_alone_are_announced_once_owner_only(rig):
    rig.b.items = [QueueItem(id=73, status="pending", name="sabun_tabagi_v2.gcode.3mf", manual_start=True,
                             created_at="2025-11-04T10:00:00Z")]
    out = _finish_and_clear(rig)
    (foreign,) = [r for r in out if r["kind"] == "queue_foreign"]
    assert "ready_next" not in kinds(out)
    assert '"sabun tabagi v2" (#73, eklenme 2025-11-04)' in foreign["owner_text"]
    assert "approve start" not in foreign["owner_text"] and foreign["family_text"] == ""
    assert rig.run(5) == []
    # a second foreign item later: announced once too; our own job: ready_next with the jump hint
    rig.b.items.append(QueueItem(id=74, status="Pending", name="kanca.gcode.3mf", manual_start=True))
    assert kinds(rig.run(2)) == ["queue_foreign"]
    rig.store.upsert_job(75, name="Vazo.gcode.3mf", requester="Mum", state="queued")
    rig.b.items.append(QueueItem(id=75, status="pending", name="Vazo.gcode.3mf", manual_start=True))
    (ready,) = rig.run(2)
    assert ready["kind"] == "ready_next" and "/home3d approve start 75 jump" in ready["owner_text"]
    assert "#73" in ready["owner_text"] and "#74" in ready["owner_text"]


def test_old_cancelled_workshop_id_is_not_ours(rig):
    rig.store.upsert_job(73, name="eski", requester="Mum", state="cancelled")
    rig.b.items = [QueueItem(id=73, status="pending", name="sabun_tabagi.gcode.3mf", manual_start=True)]
    out = _finish_and_clear(rig)
    assert "ready_next" not in kinds(out) and "queue_foreign" in kinds(out)


def test_ready_next_after_a_failed_print_asks_for_the_plate_confirmation(rig):
    rig.store.upsert_job(9, name="Vazo", requester="Mum", state="queued")
    rig.status(RUNNING, job_name="Vazo", progress=30, layer=12, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.b.plate = OCCUPIED
    rig.status(FAILED, job_name="Vazo", progress=40, layer=16, total_layers=40, bed_temp=26)
    assert kinds(rig.run(2)) == ["failed"]
    rig.store.upsert_job(10, name="Kalemlik.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=10, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    rig.b.plate = EMPTY
    out = rig.run(16)
    assert kinds(out) == ["plate_clear", "ready_next"]
    assert owner_message(out).count("/home3d approve clear") == 1  # asked once in the one owner message
    assert owner_message(out).count("Kameraya göre tabla boş") == 1
    assert "/home3d approve start 10" in out[1]["owner_text"]
    rig.store.confirm_plate("Vazo", "Sam", status=rig.b.st)  # the owner looked and confirmed (on this failed
    # print): the next notice does not ask again
    rig.store.upsert_job(11, name="Saksı.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=11, status="pending", name="Saksı.gcode.3mf", manual_start=True)]
    (again,) = rig.run(2)
    assert again["kind"] == "ready_next" and "/home3d approve clear" not in again["owner_text"]


def test_idle_plate_check_in_the_dark_is_not_empty(rig):
    rig.store.upsert_job(12, name="Kalemlik.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=12, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    rig.b.plate = PlateCheck(is_empty=True, difference_pct=0.0, light_ok=False, message="light warning")
    assert rig.run(16) == [] and rig.b.checks == 1
    rig.b.plate = EMPTY
    assert kinds(rig.run(16)) == ["ready_next"]


def test_job_attribution_prefers_the_printing_queue_item(rig):
    # an old workshop job and a new one share the name: the queue item that is printing decides
    rig.store.upsert_job(5, name="kutu.gcode.3mf", requester="Mum", state="queued")
    rig.store.upsert_job(6, name="kutu.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=5, status="pending", name="kutu.gcode.3mf"),
                   QueueItem(id=6, status="printing", name="kutu.gcode.3mf")]
    rig.status(RUNNING, job_name="kutu", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    assert rig.store.get_job(6)["state"] == "printing" and rig.store.get_job(5)["state"] == "queued"
    rig.b.items[1].status = "completed"  # the queue moves on: the remembered item still decides
    rig.status(FINISH, job_name="kutu", progress=100, layer=10, total_layers=10, bed_temp=26)
    rig.b.plate = OCCUPIED
    (fin,) = [r for r in rig.run(2) if r["kind"] == "finished"]
    assert "Dad" in fin["family_text"] and rig.store.get_job(6)["state"] == "finished"
    assert rig.store.get_job(5)["state"] == "queued"


def test_a_foreign_print_is_nobodys_even_with_a_matching_old_name(rig):
    rig.store.upsert_job(5, name="kutu.gcode.3mf", requester="Mum", state="queued")
    mums = QueueItem(id=5, status="pending", name="kutu.gcode.3mf")  # Mum's job, still waiting in the queue
    rig.b.items = [QueueItem(id=99, status="printing", name="kutu.gcode.3mf"), mums]  # 99: queued in Bambuddy
    rig.status(RUNNING, job_name="kutu", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(FAILED, job_name="kutu", progress=60, layer=6, total_layers=10, bed_temp=50)
    (r,) = rig.run(2)
    assert r["kind"] == "failed" and r["family_text"] == "" and rig.store.get_job(5)["state"] == "queued"
    # a print started outside the queue: only an exact name counts ("kutu" is not "kutuphane_rafi")
    rig.b.items = [mums]
    rig.status(RUNNING, job_name="kutuphane_rafi", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(FINISH, job_name="kutuphane_rafi", progress=100, layer=10, total_layers=10, bed_temp=50)
    (fin,) = [x for x in rig.run(2) if x["kind"] == "finished"]
    assert fin["family_text"] == "" and rig.store.get_job(5)["state"] == "queued"


def test_family_texts_use_the_request_words_owner_texts_the_file(rig):
    rid = rig.store.add_request(requester="Mum", text="  çiçekler için küçük ama çok şık bir hediye kutusu lütfen ")
    rig.store.upsert_job(14, request_id=rid, name="ROSE_BOX_v3_final.gcode.3mf", requester="Mum",
                         eject_planned=0, state="queued")
    rig.status(RUNNING, job_name="ROSE_BOX_v3_final", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(PAUSE, job_name="ROSE_BOX_v3_final", progress=60, layer=6, total_layers=10, bed_temp=60,
               hms=[RUNOUT])
    (p,) = rig.run(2)
    assert "ROSE" not in p["family_text"] and "çiçekler için küçük ama çok şık bir…" in p["family_text"]
    assert '"ROSE BOX v3 final" (#14)' in p["owner_text"]
    assert "/home3d approve resume" in p["owner_text"] and "resume ack" in p["owner_text"]
    assert "home3d_stop" not in p["owner_text"]


# ---- fix round 2 ----------------------------------------------------------------------------------------
def test_a_print_that_ends_in_idle_needs_the_owners_confirmation(rig):
    """safety 6: RUNNING -> IDLE (cancel, power loss) raises "failed"; the camera then says empty. The plate
    notice and "next job ready" must ask for /home3d approve clear first, and the failure is recorded for the
    start gate (``Store.unconfirmed_failure``)."""
    rig.store.upsert_job(9, name="Vazo", requester="Mum", state="queued")
    rig.status(RUNNING, job_name="Vazo", progress=30, layer=12, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.b.plate = OCCUPIED
    rig.status(IDLE, job_name="", bed_temp=26)
    assert kinds(rig.run(2)) == ["failed"]
    assert rig.store.unconfirmed_failure()["job_name"] == "Vazo"
    rig.store.upsert_job(10, name="Kalemlik.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=10, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    rig.b.plate = EMPTY
    out = rig.run(16)
    assert kinds(out) == ["plate_clear", "ready_next"]
    assert owner_message(out).count("/home3d approve clear") == 1


def test_a_power_cycle_after_a_failure_does_not_forget_it(rig):
    """e2e NEW-2: FAILED -> OFFLINE -> IDLE with an "empty" camera reading."""
    rig.store.upsert_job(6, name="clip", requester="Mum", state="printing")
    rig.status(RUNNING, job_name="clip", progress=30, layer=3, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.b.plate = OCCUPIED
    rig.status(FAILED, job_name="clip", progress=31, layer=3, total_layers=40, bed_temp=50)
    assert kinds(rig.run(2)) == ["failed"]
    rig.status(OFFLINE, connected=False)
    rig.run(2)
    rig.store.upsert_job(7, name="seven", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=7, status="pending", name="seven", manual_start=True)]
    rig.b.plate = EMPTY
    rig.status(IDLE, job_name="", bed_temp=24)
    out = rig.run(16)
    assert "ready_next" in kinds(out)
    assert "/home3d approve clear" in owner_message(out)
    assert rig.store.unconfirmed_failure() is not None
    rig.store.confirm_plate("", "Sam")
    assert rig.store.unconfirmed_failure() is None


def test_a_new_print_settles_an_old_failure(rig):
    rig.store.record_failure("old", "watcher")
    rig.status(RUNNING, job_name="started at the printer", progress=1, layer=1, total_layers=40, bed_temp=60)
    rig.run(2)
    assert rig.store.unconfirmed_failure() is None


def test_first_pass_on_a_failed_printer_records_the_failure():
    rig = Rig()
    rig.b.plate = OCCUPIED
    rig.status(FAILED, job_name="eski iş", progress=0, layer=75, total_layers=75, bed_temp=24)
    rig.run()
    assert rig.store.unconfirmed_failure()["job_name"] == "eski iş"


def test_jobs_removed_or_cancelled_in_the_printer_manager_stop_being_ours(rig):
    """safety 7: a store job left "queued" after its item was removed in the Bambuddy UI counted as ours
    forever (a reused queue id would then pass the jump check)."""
    rig.store.upsert_job(5, name="kutu", requester="Mum", state="queued", request_id=None)
    rid = rig.store.add_request(requester="Mum", text="kutu")
    rig.store.upsert_job(6, name="vazo", requester="Mum", state="queued", request_id=rid)
    rig.store.upsert_job(8, name="klips", requester="Mum", state="queued")
    rig.store.upsert_job(9, name="tabak", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=8, status="pending", name="klips", manual_start=True),
                   QueueItem(id=6, status="cancelled", name="vazo"), QueueItem(id=9, status="completed", name="tabak")]
    rig.run(2)
    assert rig.store.get_job(6)["state"] == "cancelled"  # cancelled there: at once
    assert rig.store.get_job(9)["state"] == "finished"  # printed while nobody watched
    assert rig.store.get_request(rid)["status"] == "cancelled"
    assert rig.store.get_job(5)["state"] == "queued"  # missing once: maybe an odd read
    rig.run(2)
    assert rig.store.get_job(5)["state"] == "cancelled" and "removed" in rig.store.get_job(5)["outcome"]
    assert rig.store.get_job(8)["state"] == "queued" and rig.store.active_job_ids() == {8}


def test_a_flaky_queue_read_cancels_nothing(rig):
    rig.store.upsert_job(5, name="kutu", requester="Mum", state="queued")
    rig.b.items = []
    rig.run(2)
    rig.b.items = [QueueItem(id=5, status="pending", name="kutu", manual_start=True)]
    rig.run(2)
    rig.b.items = []
    rig.run(2)
    assert rig.store.get_job(5)["state"] == "queued"


def test_a_light_left_on_by_the_hook_reaches_the_owner(rig):
    rig.store.kv_set("light_left_on:pending", {"ts": T0, "note": "light_left_on: could not switch off (500)"})
    (r,) = rig.run(2)
    assert r["kind"] == "light_left_on" and r["family_text"] == "" and rig.store.kv_get("light_left_on:pending") is None


def test_owner_confirmation_settles_a_camera_doubt_and_announces_the_next_job(rig):
    """After /home3d approve clear (an owner overruling the 18-25 % false-positive band), the watcher moves
    the plate to clear without another camera check, so 'next job ready' is sent."""
    rig.store.upsert_job(30, name="Kart.gcode.3mf", requester="Mum", eject_planned=0, state="queued")
    rig.status(RUNNING, job_name="Kart", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(5)
    rig.b.plate = PlateCheck(is_empty=None, difference_pct=20.5, light_ok=True, uncertain_band=True,
                             message="uncertain: false-positive band")
    rig.status(FINISH, job_name="Kart", progress=100, layer=10, total_layers=10, bed_temp=25)
    assert "finished" in kinds(rig.run(30))
    assert rig.kv["plate_state"]["phase"] == "needs_human"
    rig.store.upsert_job(31, name="Saksı.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=31, status="pending", name="Saksı.gcode.3mf", manual_start=True)]
    assert "ready_next" not in kinds(rig.run(2))  # still a doubt: nothing announced
    rig.store.confirm_plate("Kart", "Sam")
    checks = rig.b.checks
    out = rig.run(2)
    assert rig.kv["plate_state"]["phase"] == "clear" and rig.b.checks == checks
    assert kinds(out) == ["ready_next"] and "/home3d approve start 31" in out[0]["owner_text"]


# ---- fix round 2 (R2-2/3/4/7): whose job, the real eject order, light discipline, approval requests -----
LIVE_DISPATCH_ERROR = ("The printer rejected the print command: MQTT command verification failed "
                       "(HMS 0500-0500-0001-0007).")
UNSURE = PlateCheck(is_empty=None, difference_pct=21.0, light_ok=True, uncertain_band=True,
                    message="uncertain: false-positive band")


def en_rig(**kw) -> Rig:
    r = Rig(language="en", **kw)
    r.run()  # baseline pass on an idle printer
    return r


def test_a_start_that_never_happened_is_told_to_the_owner_and_closed(rig):
    """hw/F2, live item #6 shape: the owner approved, home3d_start stored "printing", then Bambuddy failed the
    dispatch (status failed, started_at None, error_message). Before: six hours of silence, job "printing"."""
    rid = rig.store.add_request(requester="Mum", text="a hook for the towel")
    rig.store.upsert_job(200, request_id=rid, name="towel_hook.gcode.3mf", requester="Mum", eject_planned=1,
                         state="printing", started_ts=T0)
    rig.store.update_request(rid, status="printing")
    rig.b.items = [QueueItem(id=73, status="pending", name="sabunluk.gcode.3mf", manual_start=True, position=1),
                   QueueItem(id=200, status="failed", name="towel_hook.gcode.3mf", manual_start=False, position=2,
                             error_message=LIVE_DISPATCH_ERROR)]
    out = rig.run(2)
    (sf,) = [r for r in out if r["kind"] == "start_failed"]
    assert sf["family_text"] == "" and "Başlatma gerçekleşmedi" in sf["owner_text"]
    assert '"towel hook" (#200)' in sf["owner_text"] and "MQTT command verification failed" in sf["owner_text"]
    assert rig.store.get_job(200)["state"] == "start_failed" and "MQTT" in rig.store.get_job(200)["outcome"]
    assert rig.store.get_request(rid)["status"] == "start_failed"
    assert rig.store.active_job_ids() == set()
    later = [r["kind"] for _ in range(5) for r in rig.run(30)]
    assert "start_failed" not in later


def test_an_archive_reprint_is_not_credited_to_an_old_workshop_job(rig):
    """hw/F3: a reprint from Bambuddy's archive is named by the archive title, the printer reports the file stem.
    The printing queue item decides by id: not ours, no family "done" for Mum, her old job stays closed."""
    rid = rig.store.add_request(requester="Mum", text="a card wallet for my bus pass")
    rig.store.upsert_job(200, request_id=rid, name="card_wallet_a1.gcode.3mf", requester="Mum", eject_planned=0,
                         state="cleared", outcome="removed")
    rig.store.update_request(rid, status="done")
    rig.b.items = [QueueItem(id=205, status="printing", name="Minimal Card Wallet (MakerWorld)", manual_start=False)]
    rig.status(RUNNING, job_name="card_wallet_a1", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    assert rig.store.get_job(200)["state"] == "cleared" and rig.store.get_request(rid)["status"] == "done"
    rig.status(RUNNING, job_name="card_wallet_a1", progress=99, layer=10, total_layers=10, bed_temp=60)
    rig.run(10)
    assert rig.b.snaps == 0  # no near-end photo for a print the workshop did not queue (light discipline)
    rig.b.items[0].status = "completed"
    rig.b.plate = OCCUPIED
    rig.status(FINISH, job_name="card_wallet_a1", progress=100, layer=10, total_layers=10, bed_temp=40)
    (fin,) = [r for r in rig.run(2) if r["kind"] == "finished"]
    assert fin["family_text"] == "" and "Mum" not in fin["owner_text"]
    assert rig.store.get_job(200)["state"] == "cleared"
    # the same file again from the printer's screen (no queue item at all): an old job is never this print
    rig.b.items = []
    rig.status(IDLE, bed_temp=25)
    rig.run(2)
    rig.status(RUNNING, job_name="card_wallet_a1", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.run(2)
    assert rig.store.get_job(200)["state"] == "cleared" and rig.store.get_request(rid)["status"] == "done"


def test_a_finish_hidden_by_the_next_auto_start_job_is_still_reported():
    """hw/F2, s5 shape: our auto-eject print runs RUNNING through its end G-code; Bambuddy dispatches a family
    auto-start item right after FINISH, so the next pass already sees PREPARE. The queue says ours completed."""
    rig = en_rig()
    rid = rig.store.add_request(requester="Mum", text="a hook for the towel")
    rig.store.upsert_job(200, request_id=rid, name="towel_hook.gcode.3mf", requester="Mum", eject_planned=1,
                         state="printing", started_ts=T0)
    ours = QueueItem(id=200, status="printing", name="towel_hook.gcode.3mf", position=1)
    fam = QueueItem(id=210, status="pending", name="kalemlik.gcode.3mf", manual_start=False, position=2)
    rig.b.items = [ours, fam]
    for pct in (90, 98, 100, 100, 100, 100):
        rig.status(RUNNING, job_name="towel_hook", progress=pct, layer=round(pct / 2), total_layers=50, bed_temp=60)
        assert all(r["kind"] == "started" and not r["owner_text"] for r in rig.run(2))
    photo = rig.kv["photo_path"]
    assert rig.b.snaps == 1  # one "done" photo of our part, before the push
    ours.status, fam.status = "completed", "printing"
    rig.status(PREPARE, job_name="kalemlik", progress=0, layer=0, total_layers=120, bed_temp=45)
    (fin,) = rig.run(2)
    assert fin["kind"] == "finished"
    assert fin["family_text"] == '✅ Anneciğim, "a hook for the towel" is done.' and fin["family_media"] == photo
    assert "I missed its end" in fin["owner_text"] and '"towel hook" (#200)' in fin["owner_text"]
    assert rig.store.get_job(200)["state"] == "finished" and rig.store.get_request(rid)["status"] == "done"
    assert rig.store.active_job_ids() == set()
    # the family job is nobody's: its finish says nothing to the family group
    rig.status(RUNNING, job_name="kalemlik", progress=60, layer=70, total_layers=120, bed_temp=60)
    rig.run(30)
    fam.status = "completed"
    rig.status(FINISH, job_name="kalemlik", progress=100, layer=120, total_layers=120, bed_temp=40)
    assert all(r["family_text"] == "" for r in rig.run(30))


def test_a_print_completed_while_nobody_watched_leaves_the_plate_to_the_camera():
    rig = en_rig()
    rig.store.upsert_job(201, name="vase.gcode.3mf", requester="Dad", state="printing", started_ts=T0)
    rig.b.items = [QueueItem(id=201, status="completed", name="vase.gcode.3mf", started_at="2026-11-08T08:00:00Z")]
    rig.b.plate = OCCUPIED
    (fin,) = [r for r in rig.run(2) if r["kind"] == "finished"]
    assert "printer is idle again" in fin["owner_text"] and fin["family_text"] == '✅ Dad, "vase" is done.'
    assert rig.kv["plate_state"]["phase"] == "needs_human"  # no "next job ready" before the camera saw it
    rig.b.plate = EMPTY
    assert "plate_clear" in [r["kind"] for r in rig.run(2)]


def test_real_order_push_before_finish_one_message_one_light_cycle():
    """hw/F6: with preset 9 the A1 cools and pushes inside the end G-code (RUNNING, 100 %) and reports FINISH
    after the push. FINISH is checked at once; one owner message, the family gets the pre-push photo."""
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.run()
    rig.store.upsert_job(7, name="Gift box.gcode.3mf", requester="Mum", eject_planned=1, state="queued")
    rig.status(RUNNING, job_name="Gift box", progress=50, layer=50, total_layers=100, bed_temp=65)
    rig.run(2)
    rig.status(RUNNING, job_name="Gift box", progress=100, layer=100, total_layers=100, bed_temp=60)
    assert rig.run(2) == [] and rig.b.snaps == 1
    part = rig.kv["photo_path"]
    rig.status(RUNNING, job_name="Gift box", progress=100, layer=100, total_layers=100, bed_temp=35)
    assert rig.run(10) == [] and rig.b.snaps == 1 and rig.b.checks == 0  # cool-down + push: nothing to do yet
    cycles = rig.b.cycles
    rig.status(FINISH, job_name="Gift box", progress=100, layer=100, total_layers=100, bed_temp=28)
    out = rig.run(5)
    assert [r["kind"] for r in out] == ["finished", "finished_ejected"]
    fin, ej = out
    assert fin["family_text"] == "" and "pending" not in fin["owner_text"] and "checking" not in fin["owner_text"]
    assert ej["family_text"] == ('✅ Anneciğim, "Gift box" is done. It dropped off by itself, you can take it '
                                 'from the box.')
    assert ej["family_media"] == part and ej["owner_media"] not in ("", part)
    assert rig.b.cycles == cycles + 1  # the plate check and the photo share one light cycle
    box = notify.read_outbox()[1:]  # after the "started" line to the family
    assert [r["audience"] for r in box] == ["owner", "family"]  # one merged owner message
    assert box[0]["text"].startswith("✅ Finished:") and "camera thinks the plate is empty" in box[0]["text"]
    assert box[0]["media"] == ej["owner_media"]
    assert rig.store.get_job(7)["state"] == "cleared" and rig.store.get_job(7)["outcome"] == "ejected"


def test_real_order_eject_miss_after_finish_is_told_within_minutes():
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.run()
    rig.store.upsert_job(8, name="Clip.gcode.3mf", requester="Mum", eject_planned=1, state="queued")
    rig.status(RUNNING, job_name="Clip", progress=100, layer=20, total_layers=20, bed_temp=40)
    rig.run(2)
    rig.b.plate = OCCUPIED
    rig.status(FINISH, job_name="Clip", progress=100, layer=20, total_layers=20, bed_temp=28)
    (fin,) = rig.run(2)
    assert fin["kind"] == "finished" and fin["family_text"] == ""
    assert "Pushed off at the end of the print; checking the camera." in fin["owner_text"]
    assert fin["owner_media"] and fin["owner_media"] != rig.kv["photo_path"]  # what the camera sees now
    checks = rig.b.checks
    assert rig.run(2) == [] and rig.b.checks == checks  # the one re-check waits ~3 min
    (miss,) = rig.run(2)
    assert miss["kind"] == "plate_not_clear" and "stayed on the plate" in miss["family_text"]
    assert "part still on the plate after 2 checks" in miss["owner_text"]
    assert [m["kind"] for m in rig.store.human_needed()] == ["remove_part"]


def _check_minutes(rig, hours: float, step: float = 2.0) -> list[float]:
    """Run passes for ``hours``; the minutes (from now) at which a plate check ran."""
    out, t = [], 0.0
    while t < hours * 60:
        before = rig.b.checks
        rig.run(step)
        t += step
        if rig.b.checks > before:
            out.append(t)
    return out


def test_needs_human_rechecks_back_off_and_stop_after_six():
    """hw/F7, s4 shape: a finished plate the camera stays unsure about (18-25 % band) was re-checked every 15 min
    all night (31 light cycles in 8 h)."""
    rig = en_rig()
    rig.status(RUNNING, job_name="family thing", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.b.plate = UNSURE
    rig.status(FINISH, job_name="family thing", progress=100, layer=10, total_layers=10, bed_temp=25)
    rig.run(2)
    assert rig.kv["plate_state"]["phase"] == "needs_human"
    minutes = _check_minutes(rig, 12)
    assert len(minutes) == watcher.MAX_RECHECKS == 6
    gaps = [b - a for a, b in zip(minutes, minutes[1:])]
    assert [round(g / 2) * 2 for g in gaps] == [16, 30, 60, 120, 120]
    # a new job at the head of the queue starts over (the owner wants to know whether it can start)
    rig.b.items = [QueueItem(id=31, status="pending", name="Saksı.gcode.3mf", manual_start=True)]
    assert _check_minutes(rig, 1) == [2.0, 18.0, 48.0]  # the same backed-off sequence, from the start


def test_idle_unsure_plate_checks_back_off_too():
    """cat/F5: idle printer, a manual job waiting, the empty plate reads in the unsure band."""
    rig = en_rig()
    rig.store.upsert_job(12, name="Kalemlik.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=12, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    rig.b.plate = UNSURE
    minutes = _check_minutes(rig, 12)
    assert len(minutes) == 6 and rig.b.cycles == 6  # one light cycle per check, nothing else
    rig.b.plate = EMPTY
    assert _check_minutes(rig, 2) == []  # capped until something changes
    rig.status(IDLE, bed_temp=24, job_name="")
    rig.store.upsert_job(13, name="Vazo.gcode.3mf", requester="Dad", state="queued")
    rig.b.items.insert(0, QueueItem(id=13, status="pending", name="Vazo.gcode.3mf", manual_start=True))
    out = rig.run(16)
    assert "ready_next" in [r["kind"] for r in out]


def test_an_approval_request_reaches_the_owner_once():
    """cat/F2: the hook refused Mum's start and recorded a request; the watcher tells the owner once."""
    rig = en_rig()
    rid = rig.store.add_request(requester="Mum", text="a hook for the towel")
    rig.store.upsert_job(7, request_id=rid, name="towel_hook.gcode.3mf", requester="Mum", sliced_file_id=33,
                         state="queued")
    rig.store.kv_set("slice:33", {"grams": 35.2, "print_time_min": 80})
    rig.b.items = [QueueItem(id=5, status="printing", name="dads_job.gcode.3mf", manual_start=True),
                   QueueItem(id=7, status="pending", name="towel_hook.gcode.3mf", manual_start=True,
                             print_time_s=4800)]
    rig.status(RUNNING, job_name="dads_job", progress=10, layer=1, total_layers=10, bed_temp=60)
    req = rig.store.add_approval_request("start", 7, "Mum", "s-mum")
    assert req is not None
    out = rig.run(2)
    (a,) = [r for r in out if r["kind"] == "approval_request"]
    assert a["owner_text"] == ('🙋 Mum asks to start #7 "towel hook" (1 h 20 min, 35 g).\n'
                               'To start it: /home3d approve start 7')
    assert a["family_text"] == "" and "will start" not in a["owner_text"]
    assert rig.store.pending_approval_requests() == []
    assert not [r for r in rig.run(2) + rig.run(30) if r["kind"] == "approval_request"]
    # a request for an item that is no longer waiting is dropped without a word
    rig.store.add_approval_request("start", 99, "Dad", "s-dad")
    assert not [r for r in rig.run(2) if r["kind"] == "approval_request"]
    assert rig.store.pending_approval_requests() == []
    # resume and clear requests carry their own command
    rig.status(PAUSE, job_name="dads_job", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.store.add_approval_request("resume", None, "Dad", "s-dad")
    (r,) = [x for x in rig.run(2) if x["kind"] == "approval_request"]
    assert r["owner_text"].startswith("🙋 Dad asks to resume") and "/home3d approve resume" in r["owner_text"]
    rig.status(RUNNING, job_name="dads_job", progress=12, layer=2, total_layers=10, bed_temp=60)
    rig.store.add_approval_request("clear_plate", None, "Mum", "s-mum")
    (c,) = [x for x in rig.run(2) if x["kind"] == "approval_request"]
    assert "/home3d approve clear" in c["owner_text"] and "Look at the plate" in c["owner_text"]


def test_an_approval_request_and_ready_next_for_the_same_job_are_one_message():
    rig = en_rig()
    rig.store.upsert_job(7, name="towel_hook.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=7, status="pending", name="towel_hook.gcode.3mf", manual_start=True)]
    rig.store.add_approval_request("start", 7, "Mum", "s-mum")
    out = rig.run(16)
    assert [r["kind"] for r in out] == ["ready_next"]
    assert "🙋 Mum asked to start it." in out[0]["owner_text"] and "/home3d approve start 7" in out[0]["owner_text"]
    assert rig.store.pending_approval_requests() == []


def test_a_watcher_without_the_approval_store_api_still_runs(monkeypatch):
    rig = en_rig()
    monkeypatch.setattr(Store, "pending_approval_requests", property(lambda self: None), raising=False)
    rig.status(PAUSE, job_name="X", progress=5)
    assert [r["kind"] for r in rig.run(2)] == ["paused"]


def test_the_same_file_started_again_by_the_printer_manager_is_a_new_print():
    """Our clip finishes and the family's auto-start copy of the same file starts before the next pass: the printing
    queue item changed, so it is a new print (ours is reported, the copy is nobody's)."""
    rig = en_rig()
    rig.store.upsert_job(200, name="clip.gcode.3mf", requester="Mum", eject_planned=0, state="printing")
    ours = QueueItem(id=200, status="printing", name="clip.gcode.3mf")
    copy = QueueItem(id=210, status="pending", name="clip.gcode.3mf", manual_start=False)
    rig.b.items = [ours, copy]
    rig.status(RUNNING, job_name="clip", progress=60, layer=6, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(RUNNING, job_name="clip", progress=100, layer=10, total_layers=10, bed_temp=60)
    rig.run(2)
    photo = rig.kv["photo_path"]
    ours.status, copy.status = "completed", "printing"
    rig.status(RUNNING, job_name="clip", progress=3, layer=1, total_layers=10, bed_temp=60)
    (fin,) = rig.run(2)
    assert fin["kind"] == "finished" and "Anneciğim" in fin["family_text"] and fin["family_media"] == photo
    assert rig.store.get_job(200)["state"] == "finished" and rig.store.get_job(210) is None
    copy.status = "completed"
    rig.status(FINISH, job_name="clip", progress=100, layer=10, total_layers=10, bed_temp=40)
    assert all(r["family_text"] == "" for r in rig.run(2))


def test_a_printing_job_cancelled_in_the_printer_manager_is_closed_quietly():
    rig = en_rig()
    rid = rig.store.add_request(requester="Mum", text="a vase")
    rig.store.upsert_job(202, request_id=rid, name="vase.gcode.3mf", requester="Mum", state="printing")
    rig.b.items = [QueueItem(id=202, status="cancelled", name="vase.gcode.3mf")]
    assert rig.run(2) == []
    assert rig.store.get_job(202)["state"] == "cancelled" and rig.store.get_request(rid)["status"] == "cancelled"
    # while the printer still shows our job, the plate state machine (not the queue) decides
    rig.store.upsert_job(203, name="cup.gcode.3mf", requester="Dad", state="printing")
    rig.b.items = [QueueItem(id=203, status="printing", name="cup.gcode.3mf")]
    rig.status(RUNNING, job_name="cup", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.b.items[0].status = "completed"
    rig.status(RUNNING, job_name="cup", progress=100, layer=10, total_layers=10, bed_temp=60)
    assert rig.run(2) == [] and rig.store.get_job(203)["state"] == "printing"


# ---- closer (round 2 review): attribution edge cases and a printer switch ----------------------------------------
def test_a_print_from_elsewhere_is_not_a_workshop_job_that_still_waits_in_the_queue():
    """Mum's #5 "kutu" is visibly PENDING; a "kutu" print starts outside the queue (printer screen, phone app,
    Bambuddy's archive reprint). It cannot be #5: no family "done" while her job still waits."""
    rig = en_rig()
    rig.store.upsert_job(5, name="kutu.gcode.3mf", requester="Mum", state="queued", eject_planned=0)
    mums = QueueItem(id=5, status="pending", name="kutu.gcode.3mf", manual_start=True)
    rig.b.items = [mums]
    rig.status(RUNNING, job_name="kutu", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    assert rig.store.get_job(5)["state"] == "queued"
    rig.status(FINISH, job_name="kutu", progress=100, layer=10, total_layers=10, bed_temp=40)
    rig.b.plate = OCCUPIED
    fin = [r for r in rig.run(2) if r["kind"] == "finished"]
    assert fin and all(r["family_text"] == "" for r in fin) and all("Mum" not in r["owner_text"] for r in fin)
    assert rig.store.get_job(5)["state"] == "queued" and mums.status == "pending"


def test_one_failed_queue_read_never_credits_a_reprint_to_a_waiting_job_by_name():
    """An archive reprint (#205, archive title) starts while the one queue read of that pass fails; Mum has a copy
    of the same file waiting (#210). The pass decides nothing by name and remembers nothing; the next pass sees
    the printing item #205 (not ours)."""
    rig = en_rig()
    rig.store.upsert_job(210, name="card_wallet_a1.gcode.3mf", requester="Mum", state="queued", eject_planned=0)
    reprint = QueueItem(id=205, status="printing", name="Minimal Card Wallet (MakerWorld)", manual_start=False)
    rig.b.items = [reprint, QueueItem(id=210, status="pending", name="card_wallet_a1.gcode.3mf", manual_start=True)]
    real_queue = rig.b.queue
    rig.b.queue = lambda include_done=False: (_ for _ in ()).throw(BackendError("GET /queue/: timed out"))
    rig.status(RUNNING, job_name="card_wallet_a1", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.run(2)
    assert "job_memo" not in rig.kv or rig.kv["job_memo"].get("name") != "card_wallet_a1"
    rig.b.queue = real_queue
    rig.status(RUNNING, job_name="card_wallet_a1", progress=60, layer=6, total_layers=10, bed_temp=60)
    rig.run(2)
    assert rig.store.get_job(210)["state"] == "queued"
    reprint.status = "completed"
    rig.status(FINISH, job_name="card_wallet_a1", progress=100, layer=10, total_layers=10, bed_temp=40)
    rig.b.plate = OCCUPIED
    fin = [r for r in rig.run(2) if r["kind"] == "finished"]
    assert fin and all(r["family_text"] == "" for r in fin)
    assert rig.store.get_job(210)["state"] == "queued"


def test_a_failed_dispatch_is_told_even_when_the_printer_shows_the_same_file_finished():
    """The printer still shows FINISH "box" (a copy the watcher never saw); Dad's #8 of the same file failed to
    dispatch (failed, no started_at). Not "Dad, box is done": the owner hears the start did not happen."""
    rig = en_rig()
    rig.status(FINISH, job_name="box", progress=100, layer=10, total_layers=10, bed_temp=25)
    rig.store.upsert_job(8, name="box.gcode.3mf", requester="Dad", state="printing", started_ts=rig.t)
    rig.b.items = [QueueItem(id=8, status="failed", name="box.gcode.3mf", error_message="MQTT command verification "
                             "failed", started_at=None)]
    out = [r for _ in range(5) for r in rig.run(2)]
    assert "start_failed" in kinds(out)
    assert all(r["family_text"] == "" for r in out), [r["family_text"] for r in out]
    assert rig.store.get_job(8)["state"] == "start_failed"


def test_a_failed_dispatch_after_a_watched_print_of_the_same_file():
    rig = en_rig()
    rig.store.upsert_job(6, name="box.gcode.3mf", requester="Dad", state="queued", eject_planned=0)
    six = QueueItem(id=6, status="printing", name="box.gcode.3mf", started_at="2026-11-08T08:00:00")
    rig.b.items = [six]
    rig.status(RUNNING, job_name="box", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    six.status = "completed"
    rig.status(FINISH, job_name="box", progress=100, layer=10, total_layers=10, bed_temp=25)
    rig.b.plate = EMPTY
    rig.run(2), rig.run(2)
    rig.store.upsert_job(8, name="box.gcode.3mf", requester="Mum", state="printing", started_ts=rig.t)
    rig.b.items = [six, QueueItem(id=8, status="failed", name="box.gcode.3mf", error_message="MQTT", started_at=None)]
    later = kinds([r for _ in range(3) for r in rig.run(2)])
    assert "start_failed" in later and "finished" not in later


def test_a_printer_switch_starts_the_watcher_state_over():
    """R2-1 follow-up: config.yaml switched from a real printer to the simulator (or another printer). The old
    state (job, plate phase, eject flow) is not about the new printer: the next pass is a first pass, so the new
    camera never 'clears' the old job and nothing is told to the family."""
    rig = en_rig()
    rig.store.upsert_job(7, name="box.gcode.3mf", requester="Mum", state="queued", eject_planned=1)
    seven = QueueItem(id=7, status="printing", name="box.gcode.3mf", started_at="x")
    rig.b.items = [seven]
    for pct in (50, 99):
        rig.status(RUNNING, job_name="box", progress=pct, layer=round(pct / 10), total_layers=10, bed_temp=60)
        rig.run(2)
    seven.status = "completed"
    rig.status(FINISH, job_name="box", progress=100, layer=10, total_layers=10, bed_temp=60)
    rig.b.plate = OCCUPIED
    rig.run(2)
    assert rig.kv["backend_key"] == ["fake", "", ""] and rig.kv.get("job_memo", {}).get("qid") == 7
    other = FakeBackend()
    other.name = "simulator"
    other.plate = EMPTY
    rig.b = other  # another printer: idle, empty plate
    out = rig.run(2) + rig.run(2)
    assert [r for r in out if r["family_text"]] == [] and "plate_clear" not in kinds(out)
    assert rig.kv["backend_key"] == ["simulator", "", ""] and "job_memo" not in rig.kv
    assert rig.store.get_job(7)["state"] not in ("cleared",)


def test_a_watcher_state_from_before_the_printer_key_is_kept():
    rig = en_rig()
    w = dict(rig.kv)
    w.pop("backend_key")
    w["light_alert_ts"] = rig.t
    rig.store.kv_set(watcher.KV_KEY, w)
    rig.run(2)
    assert rig.kv["backend_key"] == ["fake", "", ""] and rig.kv["light_alert_ts"] == rig.t - 2 * MIN


def test_ready_next_says_to_mark_the_plate_clear_first_when_bambuddy_waits_for_it():
    """Bambuddy's "Require plate clear" on (doctor recommends it): after FINISH it reports awaiting_plate_clear and
    blocks every start until the plate is marked clear. The "next job ready" text says so before the start."""
    rig = en_rig()
    rig.store.upsert_job(12, name="Kalemlik.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=12, status="pending", name="Kalemlik.gcode.3mf", manual_start=True)]
    rig.store.upsert_job(50, name="Bardak", requester="Dad", eject_planned=0, state="queued")
    rig.status(RUNNING, job_name="Bardak", progress=50, layer=5, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(FINISH, job_name="Bardak", progress=100, layer=10, total_layers=10, bed_temp=26,
               awaiting_plate_clear=True)
    rig.b.plate = OCCUPIED
    rig.run(2)
    rig.b.plate = EMPTY
    ready = next(r for r in rig.run(16) if r["kind"] == "ready_next")
    text = ready["owner_text"]
    first = "Bambuddy waits for the plate to be marked clear: first /home3d approve clear"
    assert first in text and text.index(first) < text.index("/home3d approve start 12")


# ---- review round 3 ---------------------------------------------------------------------------------------
def _foreign_print(rig: Rig, n: int, plate: PlateCheck) -> list[dict]:
    """A family print queued in the printer manager (no workshop row), sliced with auto-eject: the A1 pushes the part
    at RUNNING 100 % and reports FINISH after it. Returns the results of the FINISH pass."""
    qid = 300 + n
    rig.b.items = [QueueItem(id=qid, status="printing", name="family_hook.gcode.3mf", manual_start=False)]
    rig.status(RUNNING, job_name="family_hook", progress=50, layer=10, total_layers=20, bed_temp=65)
    rig.run(2)
    rig.status(RUNNING, job_name="family_hook", progress=100, layer=20, total_layers=20, bed_temp=35)
    rig.run(20)
    rig.b.items[0].status = "completed"
    rig.b.plate = plate
    rig.status(FINISH, job_name="family_hook", progress=100, layer=20, total_layers=20, bed_temp=28)
    out = rig.run(2)
    rig.b.items = []
    rig.status(IDLE, job_name="", bed_temp=25)
    rig.run(30)
    return out


def test_r3_a_pushed_foreign_print_is_not_told_as_take_it_off_and_logs_no_moment():
    """W1: a print the workshop did not queue gets one look at FINISH (one light cycle with the photo). An empty plate
    is said as such; no "No auto-eject: take the part off", no remove_part moment, no false upgrade proposal."""
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.run()
    for n in range(3):
        cycles = rig.b.cycles
        out = _foreign_print(rig, n, EMPTY)
        (fin,) = [r for r in out if r["kind"] == "finished"]
        assert "Not queued through the workshop; the camera thinks the plate is empty" in fin["owner_text"]
        assert "No auto-eject" not in fin["owner_text"] and fin["family_text"] == ""
        assert "upgrade_proposed" not in kinds(out)
        assert rig.b.cycles - cycles <= 2  # the FINISH look and its photo share one light cycle
    assert rig.store.human_needed(kind="remove_part") == [] and rig.store.upgrades() == []


def test_r3_a_foreign_print_left_on_the_plate_is_a_real_moment():
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.run()
    (fin,) = [r for r in _foreign_print(rig, 0, OCCUPIED) if r["kind"] == "finished"]
    assert "take the part off if it is still there" in fin["owner_text"]
    assert len(rig.store.human_needed(kind="remove_part")) == 1
    band = PlateCheck(is_empty=None, difference_pct=21.0, message="unsure", light_ok=True, uncertain_band=True)
    _foreign_print(rig, 1, band)  # a camera doubt is not evidence that a person had to step in
    assert len(rig.store.human_needed(kind="remove_part")) == 1


def test_r3_an_owner_stop_is_not_reported_as_a_failure():
    """W2: home3d_stop closes the job as cancelled and logs a stop_request; the printer then says FAILED (or IDLE).
    The owner gets a "stopped by" note (no family "I've told the owner"), the stop outcome stays, the failure is still
    recorded for the plate gate, and no failure_check moment / upgrade proposal is counted."""
    for end in (FAILED, IDLE):
        rig = Rig(language="en")
        rig.run()
        rig.store.upsert_job(103, name="towel_hook.gcode.3mf", requester="Mum", state="queued", request_id=None)
        rig.b.items = [QueueItem(id=103, status="printing", name="towel_hook.gcode.3mf")]
        rig.status(RUNNING, job_name="towel_hook", progress=20, layer=5, total_layers=40, bed_temp=60)
        rig.run(2)
        # what tools._h_stop does
        rig.store.add_event("stop_request", "towel_hook", {"who": "Sam", "reason": "wrong colour"})
        rig.store.upsert_job(103, state="cancelled", outcome="stopped by Sam: wrong colour")
        rig.b.items[0].status = "failed"
        rig.status(end, job_name="towel_hook" if end == FAILED else "", progress=20, layer=5, total_layers=40,
                   bed_temp=50)
        out = rig.run(2)
        assert kinds(out) == ["stopped"], out
        assert "Stopped by Sam: wrong colour" in out[0]["owner_text"] and out[0]["family_text"] == ""
        assert "failed" not in out[0]["owner_text"].lower()
        job = rig.store.get_job(103)
        assert job["state"] == "cancelled" and job["outcome"] == "stopped by Sam: wrong colour"
        assert rig.store.unconfirmed_failure() is not None  # a half print may be on the plate: confirm first
        assert rig.store.human_needed(kind="failure_check") == []


def test_r3_a_real_failure_still_tells_the_family():
    rig = Rig(language="en")
    rig.run()
    rig.store.upsert_job(5, name="vase.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=5, status="printing", name="vase.gcode.3mf")]
    rig.status(RUNNING, job_name="vase", progress=20, layer=5, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.store.add_event("stop_request", "other_job", {"who": "Sam"})  # a stop of something else
    rig.status(FAILED, job_name="vase", progress=21, layer=5, total_layers=40, bed_temp=50)
    out = rig.run(2)
    assert kinds(out) == ["failed"] and "the printer stopped" in out[0]["family_text"]
    assert rig.store.get_job(5)["state"] == "failed" and rig.store.human_needed(kind="failure_check")


def test_r3_the_finish_duration_is_the_real_print_time_or_left_out():
    """W3: a print first seen mid-way (watcher set up late) gets no duration; a queue item's started_at is used."""
    rig = Rig(language="en")
    rig.status(RUNNING, job_name="octopus", progress=80, layer=190, total_layers=238, bed_temp=60)
    rig.run()  # the watcher's very first pass: the print started long before
    rig.status(FINISH, job_name="octopus", progress=100, layer=238, total_layers=238, bed_temp=30)
    fin = [r for r in rig.run(140) if r["kind"] == "finished"][0]
    assert " h " not in fin["owner_text"] and "min" not in fin["owner_text"].split("\n")[0]
    # a queue item that started 9 h 18 min before the watcher's first look at it
    rig2 = Rig(language="en")
    rig2.run()
    started = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(T0 + 2 * MIN - 558 * MIN)) + ".5Z"
    rig2.store.upsert_job(102, name="octopus.gcode.3mf", requester="Mum", state="queued")
    rig2.b.items = [QueueItem(id=102, status="printing", name="octopus.gcode.3mf", started_at=started)]
    rig2.status(RUNNING, job_name="octopus", progress=80, layer=190, total_layers=238, bed_temp=60)
    rig2.run(2)
    rig2.status(FINISH, job_name="octopus", progress=100, layer=238, total_layers=238, bed_temp=30)
    fin = [r for r in rig2.run(60) if r["kind"] == "finished"][0]
    assert "10 h 18 min" in fin["owner_text"], fin["owner_text"]


def test_r3_a_print_seen_starting_gets_its_duration_from_the_watcher():
    rig = Rig(language="en")
    rig.run()  # idle
    rig.status(RUNNING, job_name="cup", progress=1, layer=1, total_layers=20, bed_temp=60)
    rig.run(2)
    rig.status(FINISH, job_name="cup", progress=100, layer=20, total_layers=20, bed_temp=30)
    fin = [r for r in rig.run(45) if r["kind"] == "finished"][0]
    assert "45 min" in fin["owner_text"]


def test_r3_next_job_ready_is_told_again_after_another_print_used_the_plate():
    """W4: #104 was announced; a family auto-start print then ran and the plate is empty again: told once more."""
    rig = Rig(language="en")
    rig.run()
    rig.store.upsert_job(104, name="hook.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=104, status="pending", name="hook.gcode.3mf", manual_start=True)]
    assert "ready_next" in kinds(rig.run(16))
    assert "ready_next" not in kinds(rig.run(16))
    fam = QueueItem(id=105, status="printing", name="family.gcode.3mf", manual_start=False)
    rig.b.items = [fam] + rig.b.items
    rig.status(RUNNING, job_name="family", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.run(2)
    fam.status = "completed"
    rig.status(FINISH, job_name="family", progress=100, layer=10, total_layers=10, bed_temp=28)
    seen = kinds(rig.run(30)) + kinds(rig.run(30))
    assert seen.count("ready_next") == 1, seen


def test_r3_a_resume_request_when_nothing_is_paused_says_so():
    rig = Rig(language="en")
    rig.run()
    rig.status(FINISH, job_name="vase", progress=100, layer=10, total_layers=10, bed_temp=28)
    rig.store.add_approval_request("resume", None, "Mum", "s-mum")
    (a,) = [r for r in rig.run(2) if r["kind"] == "approval_request"]
    assert "nothing is paused now (finished)" in a["owner_text"] and "approve resume" not in a["owner_text"]
    assert rig.store.pending_approval_requests() == []


def test_r3_an_approval_request_stays_pending_when_the_owner_text_fails(monkeypatch):
    """R3-ROB-1: a failed owner send leaves the request unannounced (the next pass tries again), so the hook never
    tells the family "the owner already got this"."""
    rig = Rig(language="en", owner_target="whatsapp:<owner-chat>")
    rig.run()
    rig.store.upsert_job(7, name="towel_hook.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=7, status="pending", name="towel_hook.gcode.3mf", manual_start=True)]
    rig.status(RUNNING, job_name="dads_job", progress=10, layer=1, total_layers=10, bed_temp=60)
    rig.store.add_approval_request("start", 7, "Mum", "s-mum")
    sent: list[str] = []

    def fail(settings, target, text, media=None, *, audience="", dry_run=False, **kw):
        sent.append(text)
        return notify.Delivery(target=target, ok=False, error="adapter not connected", audience=audience)

    monkeypatch.setattr(notify, "send", fail)
    assert "approval_request" in kinds(rig.run(2))
    (row,) = rig.store.approval_requests()
    assert row["announced_ts"] is None and len(rig.store.pending_approval_requests()) == 1
    (rec,) = rig.store.outbox(status="pending")  # the message waits in the outbox for its retry
    assert rec["attempts"] == 1 and rec["last_error"] == "adapter not connected"
    assert rig.run(0.5) == [] and len(sent) == 1  # backoff: not retried yet, and not written a second time
    monkeypatch.setattr(notify, "send", lambda s, t, x, m=None, *, audience="", dry_run=False, **kw:
                        notify.Delivery(target=t, ok=True, audience=audience))
    rig.run(2)  # the same record is retried (no second approval message)
    assert rig.store.pending_approval_requests() == []
    assert rig.store.outbox_get(rec["id"])["status"] == "sent" and rig.store.outbox_counts()["sent"] == 1
    assert len(sent) == 1


def test_r3_a_broken_store_reports_the_error_once_not_every_tick(tmp_path, monkeypatch, capsys):
    """R3-ROB-3: workshop.db is not a database: the owner gets one error notice, not one per cron tick; a dry run
    never sends it."""
    _fake_hermes(tmp_path, monkeypatch)
    calls = tmp_path / "calls.log"
    exe = tmp_path / "bin" / "hermes"
    exe.write_text(f"#!{sys.executable}\nimport json, sys\nopen({str(calls)!r}, 'a').write(' '.join(sys.argv[1:]) "
                   "+ '\\n')\nprint(json.dumps({'success': True}))\n", encoding="utf-8")
    write_snapshot(settings(owner_target="whatsapp:<owner-chat>"))
    (Path(os.environ["HOME3D_DATA_DIR"]) / "workshop.db").write_bytes(os.urandom(4096))
    assert watcher.main(["--dry-run"]) == 0
    assert "DatabaseError" in capsys.readouterr().out and not calls.exists()  # dry run: printed, never sent
    for _ in range(3):
        assert watcher.main([]) == 0
    assert len(calls.read_text().splitlines()) == 1


def test_r3_a_workshop_print_that_ended_before_the_first_pass_is_reported():
    """J3-1: the start tool recorded the job as printing; the watcher's very first pass finds FINISH: it is reported
    (not swallowed as an old baseline) and the job does not stay "printing" for good."""
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.store.upsert_job(1, name="coaster.gcode.3mf", requester="Mum", eject_planned=1, state="printing",
                         started_ts=T0)
    rig.b.items = [QueueItem(id=1, status="completed", name="coaster.gcode.3mf")]
    rig.status(FINISH, job_name="coaster", progress=100, layer=12, total_layers=12, bed_temp=28)
    seen = kinds(rig.run())
    assert "finished" in seen, seen
    seen += kinds(rig.run(5))
    assert "finished_ejected" in seen and rig.store.get_job(1)["state"] == "cleared"


def test_r3_an_old_finish_found_on_the_first_pass_stays_quiet():
    rig = Rig(language="en")
    rig.store.upsert_job(1, name="old.gcode.3mf", requester="Mum", state="finished")
    rig.status(FINISH, job_name="old", progress=100, layer=12, total_layers=12, bed_temp=28)
    assert rig.run() == []


def test_r3_one_owner_message_says_the_camera_reading_once():
    """J3-5: finished_ejected and ready_next in the same pass are one owner message: the camera line once."""
    rig = Rig(language="en")
    rig.b.eject_in_gcode = True
    rig.run()
    rig.store.upsert_job(7, name="Gift box.gcode.3mf", requester="Mum", eject_planned=1, state="queued")
    rig.store.upsert_job(8, name="Hook.gcode.3mf", requester="Dad", state="queued")
    rig.b.items = [QueueItem(id=7, status="printing", name="Gift box.gcode.3mf"),
                   QueueItem(id=8, status="pending", name="Hook.gcode.3mf", manual_start=True)]
    rig.status(RUNNING, job_name="Gift box", progress=50, layer=50, total_layers=100, bed_temp=65)
    rig.run(2)
    rig.b.items[0].status = "completed"
    rig.status(FINISH, job_name="Gift box", progress=100, layer=100, total_layers=100, bed_temp=28)
    out = rig.run(5)
    assert kinds(out) == ["finished", "finished_ejected", "ready_next"], kinds(out)
    msg = owner_message(out)
    assert msg.count("camera thinks the plate is empty") == 1 and "/home3d approve start 8" in msg
    (box,) = [r for r in notify.read_outbox() if r["audience"] == "owner" and "approve start 8" in r["text"]]
    assert box["text"].lower().count("the camera thinks the plate is empty") == 1


def test_r3_a_stop_the_stop_tool_could_not_match_still_closes_the_job():
    """W2: only the stop_request event names the print (the stop tool did not find the job by name): the watcher
    closes the job as stopped, so the queue reconcile never reports it as failed later."""
    rig = Rig(language="en")
    rig.run()
    rig.store.upsert_job(103, name="towel_hook.gcode.3mf", requester="Mum", state="queued")
    rig.b.items = [QueueItem(id=103, status="printing", name="towel_hook.gcode.3mf")]
    rig.status(RUNNING, job_name="towel_hook", progress=20, layer=5, total_layers=40, bed_temp=60)
    rig.run(2)
    rig.store.add_event("stop_request", "towel_hook", {"who": "Dad", "reason": "spaghetti"})
    rig.b.items[0].status = "failed"
    rig.b.items[0].started_at = "2023-11-14T22:15:00Z"
    rig.status(IDLE, job_name="", bed_temp=40)
    assert kinds(rig.run(2)) == ["stopped"]
    job = rig.store.get_job(103)
    assert job["state"] == "cancelled" and job["outcome"] == "stopped by Dad: spaghetti"
    later = kinds(rig.run(2)) + kinds(rig.run(20))
    assert "failed" not in later, later


# ---- delivery: outbox records, groups, who is told ---------------------------------------------------------------
def test_dl_without_targets_nothing_counts_as_notified(rig):
    """Audit: with empty targets events were stored owner_notified=1 / family_notified=1 though nothing was sent."""
    rig.store.upsert_job(7, name="Vazo.gcode.3mf", requester="Mum", state="queued")
    rig.status(PAUSE, job_name="Vazo", progress=30, layer=3, total_layers=10)
    out = rig.run(2)
    assert "paused" in kinds(out) and any(r["family_text"] for r in out)
    assert all(e["owner_notified"] == 0 and e["family_notified"] == 0 for e in rig.store.events())
    assert rig.store.outbox_counts()["no_target"] == 2 and rig.store.outbox_counts()["sent"] == 0


def test_dl_a_sent_record_marks_its_events_notified(rig, monkeypatch):
    monkeypatch.setattr(notify, "send", lambda s, t, x, m=None, *, audience="", dry_run=False, **kw:
                        notify.Delivery(target=t, ok=True, dry_run=dry_run, audience=audience,
                                        status=notify.DRY_RUN if dry_run else notify.SENT))
    rig.s.owner_target, rig.s.family_target = "whatsapp:<owner-chat>", "whatsapp:<family-group>"
    rig.store.upsert_job(7, name="Vazo.gcode.3mf", requester="Mum", state="queued")
    rig.status(PAUSE, job_name="Vazo", progress=30, layer=3, total_layers=10)
    rig.run(2)
    ev = next(e for e in rig.store.events() if e["kind"] == "paused")
    assert ev["owner_notified"] == 1 and ev["family_notified"] == 1


def test_dl_an_outsider_requester_is_not_announced_the_owner_is_told():
    """Audit: a job for a requester in no group and not in the household was announced into the family group."""
    rig = Rig(language="en", family_target="whatsapp:<family-group>")
    rig.run()
    rig.store.upsert_job(9, name="clip.gcode.3mf", requester="Alex", state="queued")
    rig.status(RUNNING, job_name="clip", progress=10, layer=1, total_layers=10, bed_temp=60)
    (st,) = rig.run(2)  # the first notice about the job: the owner learns that nobody else is told
    assert st["family_text"] == "" and st["owner_text"].startswith("ℹ️ Alex is in no group")
    rig.status(PAUSE, job_name="clip", progress=30, layer=3, total_layers=10)
    (p,) = rig.run(2)
    assert p["family_text"] == "" and "Paused" in p["owner_text"] and "in no group" not in p["owner_text"]
    assert not [r for r in notify.read_outbox() if r["target"] == "whatsapp:<family-group>"]
    rig.status(RUNNING, job_name="clip", progress=40, layer=4, total_layers=10, bed_temp=60)
    rig.run(2)
    rig.status(PAUSE, job_name="clip", progress=50, layer=5, total_layers=10)
    (p2,) = rig.run(2)
    assert "in no group" not in p2["owner_text"]  # told once per job


def test_dl_a_team_group_hears_neutral_wording_in_its_own_chat():
    lab = {"name": "Lab", "target": "telegram:<lab-group>", "language": "en", "tone": "team", "members": ["u-alex"]}
    rig = Rig(language="tr", family_target="whatsapp:<family-group>", groups=[lab])
    rig.run()
    rid = rig.store.add_request(requester="Alex", text="sensor bracket", platform="telegram", chat_id="<lab-group>",
                                sender_id="u-alex")
    rig.store.upsert_job(9, request_id=rid, name="bracket.gcode.3mf", requester="Alex", state="queued")
    rig.status(RUNNING, job_name="bracket", progress=10, layer=1, total_layers=10, bed_temp=60, remaining_min=30)
    (st,) = rig.run(2)
    assert st["family_text"] == '🖨️ Print started: "sensor bracket" (for Alex), about 30 min.' and st["group"] == "Lab"
    rig.status(PAUSE, job_name="bracket", progress=30, layer=3, total_layers=10)
    (p,) = rig.run(2)
    assert p["family_text"].startswith('⏸️ Print paused: "sensor bracket" (for Alex)')
    assert "Duraklatıldı" in p["owner_text"]  # the owner keeps the technical notice in the household language
    box = notify.read_outbox()
    assert {r["target"] for r in box if r["audience"] == "team"} == {"telegram:<lab-group>"}
    assert not [r for r in box if r["target"] == "whatsapp:<family-group>"]
