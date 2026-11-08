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
