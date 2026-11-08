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
        return [q for q in self.items if include_done or q.status.lower() in ("pending", "printing")]

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
    assert all("/home3d approve clear" in r["owner_text"] for r in out)
    assert "/home3d approve start 10" in out[1]["owner_text"]
    rig.store.confirm_plate("Vazo", "Sam")  # the owner looked and confirmed: the next notice does not ask again
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
    assert all("/home3d approve clear" in r["owner_text"] for r in out)


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
    assert all("/home3d approve clear" in r["owner_text"] for r in out)
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
