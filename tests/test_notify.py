"""notify.py: delivery through a fake ``hermes`` binary on PATH, retry, dry-run outbox."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from home3d_ws.home3d import notify as N
from home3d_ws.home3d.config import Settings

OWNER = "whatsapp:<owner-group>@g.us"
FAMILY = "whatsapp:<family-group>@g.us"

# Fake hermes: logs argv, fails the first FAIL_FIRST calls, then prints the real --json success payload.
FAKE = """\
import json, os, sys
from pathlib import Path
log = Path(os.environ["FAKE_HERMES_LOG"])
calls = log.read_text().splitlines() if log.exists() else []
with log.open("a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
if len(calls) < int(os.environ.get("FAKE_HERMES_FAIL_FIRST", "0")):
    print(json.dumps({"error": "adapter not connected"}, indent=2))
    sys.exit(1)
print(json.dumps({"success": True, "platform": "whatsapp"}, indent=2))
"""


@pytest.fixture
def hermes(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "hermes"
    exe.write_text(f"#!{sys.executable}\n{FAKE}", encoding="utf-8")
    exe.chmod(0o755)
    log = tmp_path / "hermes-calls.jsonl"
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_HERMES_LOG", str(log))
    monkeypatch.delenv(N.DRY_RUN_ENV, raising=False)
    monkeypatch.setattr(N, "RETRY_DELAY_S", 0)

    def calls() -> list[list[str]]:
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    return calls


def _settings(**kw) -> Settings:
    base = dict(owner_target=OWNER, family_target=FAMILY)
    base.update(kw)
    return Settings(**base)


def test_send_success_uses_hermes_send_json_and_records_outbox(hermes, tmp_path):
    photo = tmp_path / "part.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xe0fake")
    d = N.send(_settings(), OWNER, "✅ Bitti: \"Vazo\"", photo, audience="owner")
    assert d.ok and not d.dry_run and d.error == "" and d.target == OWNER
    (argv,) = hermes()
    assert argv[:5] == ["send", "-t", OWNER, "--json", "--"]
    assert argv[5] == f"✅ Bitti: \"Vazo\"\nMEDIA:{photo.resolve()}"
    (rec,) = N.read_outbox()
    assert rec["audience"] == "owner" and rec["target"] == OWNER and rec["ok"] is True
    assert rec["media"] == str(photo) and rec["text"].startswith("✅")


def test_send_profile_is_passed_before_the_subcommand(hermes):
    assert N.send(_settings(send_profile="default"), OWNER, "hi").ok
    assert hermes()[0][:3] == ["-p", "default", "send"]


def test_text_starting_with_a_dash_is_not_parsed_as_a_flag(hermes):
    assert N.send(_settings(), OWNER, "-- not a flag").ok
    assert hermes()[0][-2:] == ["--", "-- not a flag"]


def test_retries_once_then_succeeds(hermes, monkeypatch):
    monkeypatch.setenv("FAKE_HERMES_FAIL_FIRST", "1")
    d = N.send(_settings(), OWNER, "hello")
    assert d.ok and len(hermes()) == 2


def test_gives_up_after_one_retry_and_reports_the_error(hermes, monkeypatch):
    monkeypatch.setenv("FAKE_HERMES_FAIL_FIRST", "5")
    d = N.send(_settings(), OWNER, "hello", audience="owner")
    assert not d.ok and "adapter not connected" in d.error
    assert len(hermes()) == 2
    assert N.read_outbox()[-1]["ok"] is False


def test_empty_target_is_a_dry_run_outbox_only(hermes):
    d = N.send(_settings(owner_target=""), "", "hello", audience="owner")
    assert d.ok and d.dry_run and hermes() == []
    rec = N.read_outbox()[-1]
    assert rec["dry_run"] is True and rec["target"] == "" and rec["text"] == "hello"


def test_env_and_flag_dry_run_never_call_hermes(hermes, monkeypatch):
    assert N.send(_settings(), OWNER, "a", dry_run=True).dry_run
    monkeypatch.setenv(N.DRY_RUN_ENV, "1")
    assert N.send(_settings(), FAMILY, "b").dry_run
    assert hermes() == [] and len(N.read_outbox()) == 2


def test_missing_hermes_binary_is_an_error_not_an_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path / "nothing-here"))
    monkeypatch.setattr(N.sys, "executable", str(tmp_path / "nopython"))
    monkeypatch.delenv(N.DRY_RUN_ENV, raising=False)
    d = N.send(_settings(), OWNER, "hello")
    assert not d.ok and "not found" in d.error
    assert N.read_outbox()[-1]["ok"] is False


def test_notify_owner_gets_the_photo_family_only_when_allowed(hermes, tmp_path):
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"\xff\xd8")
    out = N.notify(_settings(), owner_text="owner line", family_text="family line", media=photo)
    assert [d.audience for d in out] == ["owner", "family"] and all(d.ok for d in out)
    owner_argv, family_argv = hermes()
    assert owner_argv[2] == OWNER and "MEDIA:" in owner_argv[-1]
    assert family_argv[2] == FAMILY and "MEDIA:" not in family_argv[-1]

    N.notify(_settings(), owner_text=None, family_text="done!", media=photo, owner_media_only=False)
    assert "MEDIA:" in hermes()[-1][-1]


def test_notify_skips_empty_texts_and_dry_runs_empty_family_target(hermes):
    out = N.notify(_settings(family_target=""), owner_text="", family_text="aile")
    assert len(out) == 1 and out[0].audience == "family" and out[0].dry_run
    assert hermes() == []
    assert N.notify(_settings(), owner_text=None, family_text="  ") == []


def test_compose_ignores_missing_media(tmp_path):
    assert N.compose("hi", tmp_path / "missing.jpg") == "hi"
    p = tmp_path / "x.png"
    p.write_bytes(b"x")
    assert N.compose("", p) == f"MEDIA:{p.resolve()}"


def test_outbox_lives_in_the_data_dir(data_dir):
    N.send(_settings(), "", "x")
    assert N.outbox_path() == Path(data_dir) / "outbox.jsonl" and N.outbox_path().exists()
