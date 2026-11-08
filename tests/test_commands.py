"""commands.py (/home3d) and cli.py (hermes home3d): owner-only approvals, info subcommands, demo (no Hermes)."""

from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path

import pytest

from home3d_ws.home3d import cli, commands
from home3d_ws.home3d.backends.base import SliceOptions
from home3d_ws.home3d.backends.simulator import SimulatorBackend
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store

ROOT = Path(__file__).resolve().parents[1]
OWNER, MUM = "owner-id@s.whatsapp.net", "mum-id@s.whatsapp.net"


class Source:  # the bits of gateway.session.SessionSource that /home3d reads
    def __init__(self, user_id=None, chat_id="<group>@g.us", platform="whatsapp"):
        self.user_id, self.chat_id, self.platform = user_id, chat_id, platform


def settings(**over) -> Settings:
    base = dict(backend="simulator", language="en", owner_name="Owner", owner_ids=[OWNER],
                household=[{"id": MUM, "name": "Mum", "address_as": "Mum dear"}])
    base.update(over)
    return Settings(**base)


class Rig:
    def __init__(self, **over):
        self.be = SimulatorBackend()
        self.store = Store()
        self.rt = Runtime(None, settings=settings(**over), store=self.store, backend=self.be)
        self.cmd = commands.make_command(self.rt)

    def queue_job(self) -> int:
        sliced = self.be.slice(1, SliceOptions(printer_preset="sim-autoeject"))
        item = self.be.queue_add(sliced.library_file_id, manual_start=True)
        self.store.upsert_job(item.id, name=item.name, requester="Mum", sliced_file_id=sliced.library_file_id,
                              eject_planned=1)
        return item.id

    def __call__(self, text, user=None, **kw):
        source = kw.pop("source", Source(user) if user else None)
        return self.cmd(text, source=source, session_id=kw.get("session_id", "s1"), platform="whatsapp")


@pytest.fixture
def rig():
    return Rig()


def test_signature_matches_hermes_dispatch():
    """plugin_command_dispatch passes source/session_id/session_key/platform to the names a handler declares."""
    params = inspect.signature(commands.make_command(Rig().rt)).parameters
    assert list(params)[0] == "raw_args"
    assert {"source", "session_id", "platform"} <= set(params) and "session_key" not in params


def test_owner_approves_and_starts_now(rig):
    qid = rig.queue_job()
    reply = rig(f"approve start {qid}", OWNER)
    assert reply.startswith("▶️") and f"#{qid}" in reply and "Mum" in reply
    assert rig.be.status().state in ("PREPARE", "RUNNING")
    assert rig.store.peek_approval("start", str(qid)) is None  # used by this start
    assert rig.store.events(kind="approval_granted")


def test_non_owner_and_chat_id_cannot_approve(rig):
    qid = rig.queue_job()
    for source in (Source(MUM), Source("stranger@s.whatsapp.net"), Source(None, chat_id=OWNER),
                   {"user_id": "", "chat_id": OWNER}):
        reply = rig(f"approve start {qid}", source=source)
        assert "Only the owner" in reply
    assert rig.store.peek_approval("start", str(qid)) is None
    assert rig.be.status().state == "IDLE"


def test_local_session_is_the_owner(rig):
    qid = rig.queue_job()
    assert rig(f"approve start #{qid}").startswith("▶️")


def test_blocked_start_leaves_a_15_minute_approval(rig):
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.start(q1)  # printer busy: the gate refuses q2 for now
    reply = rig(f"approve start {q2}", OWNER)
    assert "15 min" in reply and "busy" in reply
    assert rig.store.peek_approval("start", str(q2)) is not None
    reply = rig(f"approve start {q2} jump", OWNER)
    assert rig.store.peek_approval("start", f"{q2}+jump") is not None


def test_approve_clear_and_resume(rig):
    assert rig("approve clear", OWNER).startswith("✅")
    assert rig.store.peek_approval("clear_plate", "") is None
    reply = rig("approve resume", OWNER)
    assert "not paused" in reply and rig.store.peek_approval("resume", "") is not None


def test_usage_and_unknown(rig):
    assert "approve start" in rig("")
    assert "approve start" in rig("help")
    assert "Usage" in rig("approve", OWNER)
    assert "Usage" in rig("approve start abc", OWNER)
    assert "Unknown subcommand 'frobnicate'" in rig("frobnicate")


def test_status_whoami_moments_upgrades(rig):
    qid = rig.queue_job()
    text = rig("status")
    assert "IDLE" in text and f"#{qid}" in text and "Mum" in text and "Watcher not running" in text
    who = rig("whoami", OWNER)
    assert "owner: yes" in who and OWNER in who
    who = rig("whoami", "new-person@s.whatsapp.net")
    assert "owner: no" in who and "add this id" in who
    assert "No human-needed moments" in rig("moments")
    for _ in range(3):
        rig.store.add_human_needed("remove_part", "took it off", job_name="Box", who="Mum")
    assert "remove_part 3" in rig("moments")
    up = rig("upgrades")
    assert "💡" in up and "makerworld.com" in up


def test_turkish_replies():
    r = Rig(language="tr")
    assert "Sadece sahibi" in r("approve clear", MUM)
    assert "Kuyruk boş" in r("status")


def test_never_raises_on_garbage(rig):
    for raw in (None, 123, 'approve start "unterminated', "approve start 99999", "APPROVE START 1 jump",
                "status extra args", "\x00\x01"):
        assert isinstance(rig.cmd(raw, source=None), str)
    assert isinstance(rig.cmd("approve clear", source=object()), str)


# ---- CLI -----------------------------------------------------------------------------------------------
def _parse(argv):
    parser = argparse.ArgumentParser(prog="hermes home3d")
    cli.setup_parser(parser)
    return parser.parse_args(argv)


def test_cli_parser_and_dispatch(rig, capsys):
    assert _parse(["setup", "--interval", "5m", "--print-only"]).print_only
    assert _parse(["simulate", "advance", "30", "--watch"]).minutes == 30
    assert _parse(["demo", "--lang", "tr"]).lang == "tr"
    assert cli.handle(_parse([]), rig.rt) == 2
    assert cli.handle(_parse(["simulate", "scenario", "eject_miss"]), rig.rt) == 0
    assert cli.handle(_parse(["simulate", "status"]), rig.rt) == 0
    assert cli.handle(_parse(["status"]), rig.rt) == 0
    assert cli.handle(_parse(["watch", "--once", "--dry-run"]), rig.rt) == 0
    out = capsys.readouterr().out
    assert "scenario: eject_miss" in out and "IDLE" in out
    bambuddy = Runtime(None, settings=settings(backend="bambuddy", bambuddy_url="http://192.168.1.50:8000"))
    assert cli.handle(_parse(["simulate", "status"]), bambuddy) == 2


def test_cli_setup_installs_script_and_prints_cron(tmp_path, monkeypatch, capsys, data_dir):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    rt = Runtime(None, settings=settings(watch_interval="3m"))
    assert cli.handle(_parse(["setup", "--print-only"]), rt) == 0
    script = tmp_path / "hermes" / "scripts" / cli.SCRIPT_NAME
    text = script.read_text(encoding="utf-8")
    assert "__PLUGIN_DIR__" not in text and repr(str(ROOT)) in text and os.access(script, os.X_OK)
    assert (data_dir / "watcher-config.json").is_file()
    out = capsys.readouterr().out
    assert "cron create 'every 3m' --name home3d-watch --no-agent --script home3d_watch.py --deliver local" in out
    assert cli.cron_schedule("0 */2 * * *") == "0 */2 * * *"


def test_cli_doctor_on_the_simulator(rig, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    code = cli.handle(_parse(["doctor"]), rig.rt)
    out = capsys.readouterr().out
    assert "printer" in out and "IDLE" in out and "sim-autoeject" in out
    assert code in (0, 1)  # 1 only while a bundled file (the skill) is missing


def test_demo_runs_the_whole_loop(data_dir):
    lines: list[str] = []
    res = cli.run_demo(lang="en", out=lines.append)
    assert res["ok"], res["missing"]
    assert os.environ["HOME3D_DATA_DIR"] == str(data_dir) and "HOME3D_DRY_RUN" not in os.environ
    assert not Path(res["data_dir"]).exists()  # temporary dir removed
    kinds = res["events"]
    assert kinds.index("finished") < kinds.index("finished_ejected") < kinds.index("ready_next") \
        < kinds.index("plate_not_clear")
    audiences = {(r["audience"], r["dry_run"]) for r in res["outbox"]}
    assert audiences == {("owner", True), ("family", True)}
    text = "\n".join(lines)
    assert "owner approval needed" in text and "/home3d approve start" in text and "remove_part" in text
    assert "upgrade_proposed" in res["milestones"] and "💡" in text and "accept upgrade" in text
    assert "home3d_upgrades accept" not in text  # the owner is told what to say, not a tool name


def test_demo_turkish_keeps_its_data(tmp_path):
    res = cli.run_demo(lang="tr", data_dir=str(tmp_path / "demo"), out=lambda s: None)
    assert res["ok"], res["missing"]
    assert (tmp_path / "demo" / "outbox.jsonl").is_file()
    family = [r["text"] for r in res["outbox"] if r["audience"] == "family"]
    assert family and any("Anneciğim" in t for t in family)
