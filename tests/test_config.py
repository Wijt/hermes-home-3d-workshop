"""config.py: exact sender-id matching (D1), the local owner, new settings (no Hermes)."""

from __future__ import annotations

import pytest

from home3d_ws.home3d.config import LOCAL_SENDER, Settings, load_settings, norm_id

# fictional numbers (555 range), built at runtime so the CI personal-data scan stays meaningful
PHONE, MUM_PHONE = "905551112233", "905554445566"
OWNER_WA = f"{PHONE}@s.whatsapp.net"


def settings(**over) -> Settings:
    base = dict(owner_name="Sam", owner_ids=[OWNER_WA, "@sam:matrix.org", "sam@example.com", "123456789"],
                household=[{"id": f"{MUM_PHONE}@s.whatsapp.net", "name": "Mum"},
                           {"id": "998877@lid", "name": "Dad"},
                           {"id": "uid:3", "name": "Kid"}])
    base.update(over)
    return Settings(**base)


@pytest.mark.parametrize("raw,expected", [
    (f"{PHONE}@s.whatsapp.net", PHONE),
    (f"+{PHONE}@s.whatsapp.net", PHONE),
    (f"{PHONE}:17@s.whatsapp.net", PHONE),
    (f"{PHONE}@c.us", PHONE),
    (f" +{PHONE} ", PHONE),
    (PHONE, PHONE),
    (f"{PHONE}@lid", f"{PHONE}@lid"),
    (f"{PHONE}:4@LID", f"{PHONE}@lid"),
    ("@Sam:Matrix.org", "@sam:matrix.org"),
    ("Sam@Example.com", "sam@example.com"),
    ("uid:1000", "uid:1000"),
    ("", ""),
    (None, ""),
])
def test_norm_id(raw, expected):
    assert norm_id(raw) == expected


def test_matrix_and_email_lookalikes_are_not_the_owner():
    """The review's CRITICAL: the part before "@" used to decide (empty for every Matrix id)."""
    s = settings()
    for intruder in ("@mallory:evil.org", "@sam:evil.org", "sam@evil.com", "sam@example.com.evil.org",
                     "@sam", "sam", "mallory@s.whatsapp.net", "@:matrix.org"):
        assert s.person_for(intruder) is None, intruder
        assert not s.is_owner(intruder), intruder
    for real in ("@sam:matrix.org", "@SAM:matrix.org", "sam@example.com", " Sam@Example.com "):
        assert s.is_owner(real), real


def test_whatsapp_variants_match_but_lid_is_another_id_space():
    s = settings()
    for v in (f"{PHONE}@s.whatsapp.net", f"+{PHONE}@s.whatsapp.net", f"{PHONE}:3@s.whatsapp.net",
              f"{PHONE}@c.us", PHONE, f"+{PHONE}"):
        assert s.is_owner(v), v
    assert s.person_for(f"{PHONE}@lid") is None  # a @lid id never equals a phone number
    assert s.person_for("998877@lid").name == "Dad" and s.person_for("998877:2@lid").name == "Dad"
    assert s.person_for("998877@s.whatsapp.net") is None and s.person_for("998877") is None
    assert s.person_for(f"{PHONE[:-1]}@s.whatsapp.net") is None  # one digit short
    assert s.person_for(f"{PHONE}4@s.whatsapp.net") is None  # one digit more


def test_numeric_and_uid_ids_compare_exactly():
    s = settings()
    assert s.is_owner("123456789") and not s.is_owner("12345678") and not s.is_owner("1234567890")
    assert s.person_for("uid:3").name == "Kid" and s.person_for("uid:30") is None and s.person_for("uid:") is None


def test_local_sender_is_the_owner_only_when_configured():
    s = settings()
    assert s.is_owner(LOCAL_SENDER) and s.person_for(LOCAL_SENDER).name == "Sam"
    assert s.person_for(" LOCAL ").role == "owner"
    off = settings(local_is_owner=False)
    assert not off.is_owner(LOCAL_SENDER) and off.person_for(LOCAL_SENDER) is None
    # a configured id "local" never turns into a person (the value is reserved)
    odd = settings(local_is_owner=False, household=[{"id": "local", "name": "Mallory"}])
    assert odd.person_for("local") is None


def test_unknown_and_empty_ids():
    s = settings()
    assert s.person_for("") is None and s.person_for(None) is None and not s.is_owner("")
    nobody = Settings()  # no owner_ids, empty household
    assert nobody.person_for("anything") is None and nobody.is_owner(LOCAL_SENDER)


def test_new_settings_load_and_validate():
    assert Settings().local_is_owner is True and Settings().inject_context == "auto"
    s = load_settings(overrides={"local_is_owner": "false", "inject_context": "NEVER"})
    assert s.local_is_owner is False and s.inject_context == "never"
    assert load_settings(overrides={"inject_context": "sometimes"}).inject_context == "auto"
    assert load_settings(overrides={"inject_context": "always", "local_is_owner": "yes"}).local_is_owner is True
    snap = settings(local_is_owner=False).to_snapshot()
    assert snap["local_is_owner"] is False and snap["inject_context"] == "auto"


class Ctx:
    def __init__(self, **cfg):
        self.cfg = cfg

    def get_config(self, key, default=None):
        return self.cfg.get(key, default)


def test_settings_from_hermes_config():
    s = load_settings(Ctx(local_is_owner=False, inject_context="always", owner_ids=["@sam:matrix.org"]))
    assert not s.local_is_owner and s.inject_context == "always" and s.is_owner("@sam:matrix.org")
    assert not s.is_owner(LOCAL_SENDER) and not s.is_owner("@mallory:matrix.org")


# ---- fix round 2 (R2-1, R2-8): the watcher reads the live plugin settings ------------------------------------
import json  # noqa: E402

from home3d_ws.home3d import config as config_mod  # noqa: E402
from home3d_ws.home3d.config import (load_watcher_settings, read_snapshot, settings_diff,  # noqa: E402
                                     write_snapshot)


def _json_yaml(monkeypatch):
    """The dev/CI venv has no YAML library: JSON is valid YAML, so a JSON parser stands in for it here."""
    monkeypatch.setattr(config_mod, "_yaml_load", lambda text: (json.loads(text), "json-as-yaml"))


def _config(tmp_path, monkeypatch, entries: dict, key: str = "home-3d-workshop"):
    path = tmp_path / "hermes" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": {"default": "x"}, "plugins": {"enabled": [key], "entries": entries}}),
                    encoding="utf-8")
    monkeypatch.setenv(config_mod.CONFIG_ENV, str(path))
    return path


def test_english_is_the_default_language():
    assert Settings().language == "en" and load_settings(overrides={}).language == "en"
    assert load_settings(overrides={"language": "tr"}).language == "tr"
    assert load_settings(overrides={"language": "de"}).language == "en"


def test_the_watcher_reads_the_live_config_not_the_snapshot(tmp_path, monkeypatch):
    """hw F1: after setup the owner switched family notices off and the backend to bambuddy; the watcher kept the
    setup-time snapshot (family group still messaged, the real printer unwatched)."""
    _json_yaml(monkeypatch)
    write_snapshot(Settings(backend="simulator", family_target="whatsapp:<family>@g.us", owner_name="Owner"))
    _config(tmp_path, monkeypatch, {"home-3d-workshop": {"settings": {
        "backend": "bambuddy", "bambuddy_url": "http://192.168.1.50:8000", "family_target": "",
        "owner_name": "Sam", "local_is_owner": "no"}, "config": {"persona_name": "Legacy", "owner_name": "Old"}}})
    s, source = load_watcher_settings()
    assert source == "config.yaml (json-as-yaml)"
    assert (s.backend, s.family_target, s.owner_name, s.local_is_owner) == ("bambuddy", "", "Sam", False)
    assert s.persona_name == "Legacy"  # the legacy ``config`` subtree fills what ``settings`` leaves out
    assert load_settings() == s  # what the watcher's main() calls


def test_a_category_install_is_found_by_its_registry_key(tmp_path, monkeypatch):
    _json_yaml(monkeypatch)
    _config(tmp_path, monkeypatch, {"printing/home-3d-workshop": {"settings": {"owner_name": "Sam"}}},
            key="printing/home-3d-workshop")
    assert load_watcher_settings()[0].owner_name == "Sam"


@pytest.mark.parametrize("case", ["no_entry", "no_yaml_library", "broken_yaml", "missing_file", "switched_off"])
def test_the_snapshot_is_only_the_fallback(tmp_path, monkeypatch, case):
    write_snapshot(Settings(owner_name="FromSnapshot"))
    path = _config(tmp_path, monkeypatch, {"other-plugin": {"settings": {"owner_name": "Nope"}}})
    _json_yaml(monkeypatch)
    if case == "no_yaml_library":
        def no_lib(text):
            raise LookupError("no YAML library")
        monkeypatch.setattr(config_mod, "_yaml_load", no_lib)
    elif case == "broken_yaml":
        path.write_text("{not json", encoding="utf-8")
    elif case == "missing_file":
        path.unlink()
    elif case == "switched_off":
        monkeypatch.setenv(config_mod.CONFIG_ENV, "")
    s, source = load_watcher_settings()
    assert s.owner_name == "FromSnapshot" and source.startswith("snapshot (")
    (config_mod.data_dir() / config_mod.SNAPSHOT_FILE).unlink()
    assert load_watcher_settings()[1].startswith("defaults (")


def test_tests_and_the_demo_never_read_the_real_profile(monkeypatch, tmp_path):
    """HOME3D_DATA_DIR (set for every test) switches the live read off unless a config path is named."""
    monkeypatch.delenv(config_mod.CONFIG_ENV, raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "real"))
    assert config_mod.live_config_path() is None
    monkeypatch.delenv("HOME3D_DATA_DIR")
    assert config_mod.live_config_path() == tmp_path / "real" / "config.yaml"
    assert config_mod.watch_script_path() == tmp_path / "real" / "scripts" / "home3d_watch.py"


def test_a_real_yaml_parser_reads_hermes_config(tmp_path, monkeypatch):
    """With the parser Hermes ships (hermes_yaml / ruamel) or PyYAML, when one is installed."""
    try:
        config_mod._yaml_load("a: 1")
    except LookupError:
        pytest.skip("no YAML library in this interpreter")
    path = tmp_path / "config.yaml"
    path.write_text("plugins:\n  enabled:\n    - home-3d-workshop\n  entries:\n    home-3d-workshop:\n"
                    "      settings:\n        owner_name: Sam\n        local_is_owner: no\n"
                    "        owner_ids:\n          - '@sam:matrix.org'\n", encoding="utf-8")
    monkeypatch.setenv(config_mod.CONFIG_ENV, str(path))
    s, source = load_watcher_settings()
    assert source.startswith("config.yaml") and s.owner_name == "Sam" and s.owner_ids == ["@sam:matrix.org"]
    assert s.local_is_owner is False


def test_runtime_rewrites_the_snapshot_when_the_settings_change(monkeypatch):
    from home3d_ws.home3d.runtime import Runtime

    ctx = Ctx(owner_name="Sam", family_target="whatsapp:<family>@g.us")
    rt = Runtime(ctx)
    assert rt.settings.owner_name == "Sam" and read_snapshot()["family_target"] == "whatsapp:<family>@g.us"
    writes = []
    real = config_mod.write_snapshot
    monkeypatch.setattr(config_mod, "write_snapshot", lambda s: writes.append(s) or real(s))
    for _ in range(5):
        rt.settings  # unchanged: the in-memory hash says so, nothing is written
    assert writes == []
    ctx.cfg["family_target"] = ""  # the owner switches family notices off (Desktop / config edit)
    assert rt.settings.family_target == "" and read_snapshot()["family_target"] == "" and len(writes) == 1
    assert Runtime(ctx).settings and len(writes) == 1  # a new process: same content on disk, no rewrite


def test_runtime_without_hermes_never_writes_the_snapshot():
    from home3d_ws.home3d.runtime import Runtime

    Runtime(None).settings
    Runtime(None, settings=Settings(owner_name="Fixed")).settings
    assert read_snapshot() == {}


def test_settings_diff():
    assert settings_diff(Settings(), Settings()) == []
    assert settings_diff(Settings(backend="bambuddy", owner_ids=["a"]), Settings()) == ["backend", "owner_ids"]
