"""Delivery: the durable outbox (notify.enqueue / flush / outbox_summary), origin and groups (route_for), who is
told, the done box and open human-needed moments. No real ``hermes send``: ``notify.send`` is replaced."""

from __future__ import annotations

import sqlite3
import types
from pathlib import Path

import pytest

from home3d_ws.home3d import notify as N
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.store import Store

OWNER = "whatsapp:<owner-chat>"
FAMILY = "whatsapp:<family-group>"


class FakeSend:
    """Replaces notify.send: records every real call, answers ok / failure from ``self.ok`` (bool or callable)."""

    def __init__(self, ok=True):
        self.ok, self.calls = ok, []

    def __call__(self, settings, target, text, media=None, *, audience="", dry_run=False, **kw):
        if dry_run or not target:  # what enqueue writes for a final record: the send log only
            return N.Delivery(target=target, ok=True, dry_run=True, audience=audience,
                              status=N.DRY_RUN if target else N.NO_TARGET)
        self.calls.append({"target": target, "text": text, "media": media, **kw})
        ok = self.ok(target, text) if callable(self.ok) else self.ok
        return N.Delivery(target=target, ok=ok, error="" if ok else "adapter not connected", audience=audience,
                          status=N.SENT if ok else N.FAILED)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.delenv(N.DRY_RUN_ENV, raising=False)
    f = FakeSend()
    monkeypatch.setattr(N, "send", f)
    return f


def _s(**kw) -> Settings:
    base = dict(owner_target=OWNER, family_target=FAMILY, owner_name="Sam", owner_ids=["owner-1"],
                household=[{"id": "fam-1", "name": "Mum"}])
    base.update(kw)
    return Settings(**base)


# ---- 1. outbox with real delivery state -------------------------------------------------------------------------
def test_an_empty_target_is_no_target_never_notified(fake):
    store, s = Store(), _s(owner_target="", family_target="")
    eid = store.add_event("finished", "vase", {})
    d = N.enqueue(s, store, audience="owner", target="", text="done", event_ids=[eid])
    assert d.status == N.NO_TARGET and fake.calls == []
    (rec,) = store.outbox()
    assert rec["status"] == "no_target" and rec["attempts"] == 0
    (ev,) = store.events()
    assert ev["owner_notified"] == 0 and ev["family_notified"] == 0


def test_notified_is_set_only_after_a_successful_send(fake):
    store, s = Store(), _s()
    eid = store.add_event("finished", "vase", {})
    assert N.enqueue(s, store, audience="family", target=FAMILY, text="done", event_ids=[eid], now=0) is None
    assert store.events()[0]["family_notified"] == 0  # queued, not sent
    fake.ok = False
    N.flush(s, store, now=0)
    assert store.events()[0]["family_notified"] == 0
    fake.ok = True
    N.flush(s, store, now=N.backoff_s(1) + 1)
    assert store.events()[0]["family_notified"] == 1 and store.events()[0]["owner_notified"] == 0
    (rec,) = store.outbox()
    assert rec["status"] == "sent" and rec["attempts"] == 2 and rec["last_error"] == "" and rec["sent_ts"]


def test_a_failed_send_is_retried_with_backoff_then_failed_and_surfaced_once(fake):
    store, s = Store(), _s()
    fake.ok = lambda target, text: target == OWNER  # the family chat is broken, the owner chat works
    N.enqueue(s, store, audience="family", target=FAMILY, text="your part is done", now=0)
    N.flush(s, store, now=0)
    assert len(fake.calls) == 1 and store.outbox()[0]["status"] == "pending"
    N.flush(s, store, now=N.backoff_s(1) - 1)  # not due yet: no attempt
    assert len(fake.calls) == 1
    clock = 0.0
    for n in range(1, N.MAX_ATTEMPTS + 3):
        clock += N.backoff_s(n)
        N.flush(s, store, now=min(clock, N.MAX_AGE_S - 1))  # inside the age cap: the attempt cap must end it
    family = [c for c in fake.calls if c["target"] == FAMILY]
    assert len(family) == N.MAX_ATTEMPTS
    rec = store.outbox(status="failed")[0]
    assert rec["attempts"] == N.MAX_ATTEMPTS and rec["surfaced"] == 1 and "adapter" in rec["last_error"]
    reports = [c for c in fake.calls if c["target"] == OWNER]
    assert len(reports) == 1 and "your part is done" in reports[0]["text"]  # told once, with what was lost
    N.flush(s, store, now=N.MAX_AGE_S - 1)
    assert len([c for c in fake.calls if c["target"] == OWNER]) == 1


def test_a_notice_older_than_the_age_cap_is_given_up(fake):
    store, s = Store(), _s(owner_target="")
    fake.ok = False
    N.enqueue(s, store, audience="family", target=FAMILY, text="old news", now=0)
    N.flush(s, store, now=0)
    rep = N.flush(s, store, now=N.MAX_AGE_S + 1)
    assert [r["text"] for r in rep.gave_up] == ["old news"] and len(fake.calls) == 1
    assert "old news" in rep.surfaced_text  # no owner chat: the text is for the cron output
    assert store.outbox(status="no_target")[0]["kinds"] == [N.FAILURE_KIND]


def test_one_pass_never_sends_longer_than_its_budget(fake, monkeypatch):
    store, s = Store(), _s(send_timeout_s=10.0, send_budget_s=25.0)
    clock = {"t": 0.0}
    monkeypatch.setattr(N, "time", types.SimpleNamespace(time=lambda: 1.0, sleep=lambda x: None,
                                                         monotonic=lambda: clock["t"]))

    def slow(target, text):
        clock["t"] += 10.0  # every send uses its whole timeout
        return True

    fake.ok = slow
    for i in range(5):
        N.enqueue(s, store, audience="family", target=f"whatsapp:<g{i}>", text=f"n{i}", now=0)
    rep = N.flush(s, store, now=0)
    assert len(fake.calls) == 2 and rep.carried == 3  # 2 x 10 s fit in 25 s; the rest waits, not counted
    assert all(r["attempts"] == 0 for r in store.outbox_pending())
    assert all(c["timeout_s"] == 10.0 and c["retry"] is False for c in fake.calls)
    N.flush(s, store, now=1)
    N.flush(s, store, now=2)
    assert store.outbox_counts()["sent"] == 5 and store.outbox_counts()["pending"] == 0


def test_records_to_one_chat_keep_their_order(fake):
    store, s = Store(), _s()
    fake.ok = lambda target, text: text != "first"
    N.enqueue(s, store, audience="family", target=FAMILY, text="first", now=0)
    N.enqueue(s, store, audience="family", target=FAMILY, text="second", now=0)
    N.enqueue(s, store, audience="owner", target=OWNER, text="other chat", now=0)
    N.flush(s, store, now=0)
    assert [c["text"] for c in fake.calls] == ["first", "other chat"]  # "second" waits behind "first"


def test_a_dry_run_sends_nothing_and_leaves_pending_records(fake):
    store, s = Store(), _s()
    N.enqueue(s, store, audience="owner", target=OWNER, text="real", now=0)
    d = N.enqueue(s, store, audience="owner", target=OWNER, text="dry", now=0, dry_run=True)
    assert d.status == N.DRY_RUN
    N.flush(s, store, now=0, dry_run=True)
    assert fake.calls == [] and store.outbox_counts()["pending"] == 1


def test_outbox_summary_counts_and_last_failures(fake):
    store, s = Store(), _s()
    N.enqueue(s, store, audience="owner", target="", text="nowhere")
    N.enqueue(s, store, audience="owner", target=OWNER, text="ok", now=0)
    N.enqueue(s, store, audience="family", target=FAMILY, text="broken\nsecond line", now=0)
    fake.ok = lambda target, text: target == OWNER
    N.flush(s, store, now=0)
    out = N.outbox_summary(store)
    assert out["counts"]["sent"] == 1 and out["counts"]["pending"] == 1 and out["counts"]["no_target"] == 1
    assert out["undelivered"] == 1 and out["last_sent_ts"]
    (f,) = out["last_failures"]
    assert f["text"] == "broken" and f["attempts"] == 1 and f["last_error"] == "adapter not connected"


def test_a_failed_approval_message_closes_the_request_so_it_can_be_asked_again(fake):
    store, s = Store(), _s(owner_target=OWNER)
    rid = store.add_approval_request("start", 7, "Mum", "s-mum")
    fake.ok = False
    N.enqueue(s, store, audience="owner", target=OWNER, text="Mum asks", approval_request_ids=[rid], now=0)
    N.flush(s, store, now=N.MAX_AGE_S + 1)
    (row,) = store.approval_requests()
    assert row["resolved_ts"] is not None and row["announced_ts"] is None
    assert "could not be told" in row["outcome"]


def test_an_old_database_is_migrated_and_keeps_working(data_dir):
    path = Path(data_dir) / "workshop.db"
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE requests (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, requester TEXT NOT NULL DEFAULT '',
      sender_id TEXT NOT NULL DEFAULT '', channel TEXT NOT NULL DEFAULT '', text TEXT NOT NULL DEFAULT '',
      model_ref TEXT NOT NULL DEFAULT '', library_file_id INTEGER, sliced_file_id INTEGER, queue_item_id INTEGER,
      status TEXT NOT NULL DEFAULT 'open', outcome TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
    CREATE TABLE jobs (queue_item_id INTEGER PRIMARY KEY, request_id INTEGER, name TEXT NOT NULL DEFAULT '',
      requester TEXT NOT NULL DEFAULT '', sliced_file_id INTEGER, eject_planned INTEGER NOT NULL DEFAULT 0,
      eject_reason TEXT NOT NULL DEFAULT '', max_z_mm REAL, state TEXT NOT NULL DEFAULT 'queued', started_ts REAL,
      finished_ts REAL, outcome TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
    CREATE TABLE human_needed (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, kind TEXT NOT NULL,
      detail TEXT NOT NULL DEFAULT '', job_name TEXT NOT NULL DEFAULT '', who TEXT NOT NULL DEFAULT '',
      source TEXT NOT NULL DEFAULT 'agent', resolved INTEGER NOT NULL DEFAULT 0);
    INSERT INTO requests(ts, requester, text, updated) VALUES (1, 'Mum', 'a hook', 1);
    INSERT INTO human_needed(ts, kind, source) VALUES (1, 'remove_part', 'watcher');
    """)
    c.commit()
    c.close()
    store = Store(path)
    assert store.get_request(1)["chat_id"] == "" and store.get_request(1)["requester"] == "Mum"
    rid = store.add_request(requester="Sam", text="x", platform="whatsapp", chat_id="<lab-group>", sender_id="u1")
    assert store.get_request(rid)["chat_id"] == "<lab-group>"
    store.upsert_job(5, name="x", platform="whatsapp", chat_id="<lab-group>", sender_id="u1")
    assert store.get_job(5)["chat_id"] == "<lab-group>"
    assert store.open_human_needed() == []  # an old moment is history, not an open one


# ---- 2. origin and groups ---------------------------------------------------------------------------------------
LAB = {"name": "Lab", "target": "telegram:<lab-group>", "language": "en", "tone": "team", "members": ["u-alex"]}
HOME = {"name": "Home", "target": "whatsapp:<family-group>", "language": "tr", "tone": "family", "members": "fam-1"}


def test_groups_are_parsed_leniently():
    s = Settings(groups=[LAB, {"name": "lab", "target": "x"}, {"target": "no name"},
                         {"name": "Odd", "tone": "loud", "language": "de", "members": "a, b"}, "junk"])
    lab, odd = s.group_list()
    assert lab.name == "Lab" and lab.tone == "team" and lab.members == ["u-alex"]  # first of a name wins
    assert odd.tone == "family" and odd.language == "" and odd.members == ["a", "b"]
    assert s.group_language(odd) == s.language and s.group_named("LAB") == lab


def test_target_is_chat_compares_platform_and_chat_exactly():
    from home3d_ws.home3d.config import target_is_chat

    assert target_is_chat("telegram:<lab-group>", "telegram", "<lab-group>")
    assert not target_is_chat("telegram:<lab-group>", "whatsapp", "<lab-group>")
    assert not target_is_chat("telegram:<lab-group>", "telegram", "<lab-group>-2")
    assert not target_is_chat("", "telegram", "") and not target_is_chat("telegram:x", "telegram", "")


def test_route_origin_chat_wins_then_member_then_household_then_nobody():
    s = _s(groups=[LAB, HOME], household=[{"id": "fam-1", "name": "Mum"}, {"id": "fam-2", "name": "Dad"}])
    # asked in the lab chat: the lab hears, even a household member
    r = N.route_for(s, requester="Mum", platform="telegram", chat_id="<lab-group>", sender_id="fam-1")
    assert (r.announce, r.group, r.audience, r.language, r.target) == (True, "Lab", "team", "en",
                                                                      "telegram:<lab-group>")
    # asked in a DM: the group that lists the sender
    r = N.route_for(s, requester="Alex", platform="telegram", chat_id="<dm>", sender_id="u-alex")
    assert r.group == "Lab"
    r = N.route_for(s, requester="Mum", platform="whatsapp", chat_id="<dm>", sender_id="fam-1")
    assert (r.group, r.audience, r.language) == ("Home", "family", "tr")
    # a household member in no group: family_target, as before groups existed
    r = N.route_for(s, requester="Dad", sender_id="fam-2")
    assert (r.announce, r.group, r.target) == (True, "", FAMILY)
    # nobody in a group or the household: not announced (the owner is told)
    r = N.route_for(s, requester="Alex", platform="telegram", chat_id="<dm>", sender_id="u-other")
    assert (r.announce, r.why) == (False, "outsider")
    assert N.route_for(s, requester="Sam").why == "owner"
    assert N.route_for(s).why == "nobody"
    # the owner queued it for Mum from the owner's DM: Mum's group
    assert N.route_for(s, requester="Mum", chat_id="<owner-dm>", sender_id="owner-1").group == "Home"


def test_without_groups_routing_is_unchanged_for_household_members():
    r = N.route_for(_s(), requester="Mum")
    assert (r.announce, r.audience, r.target, r.group) == (True, "family", FAMILY, "")


def test_session_chat_id_reads_the_documented_session_env(monkeypatch):
    import sys

    from home3d_ws.home3d.config import CHAT_ID_ENV, session_chat_id

    monkeypatch.delenv(CHAT_ID_ENV, raising=False)
    monkeypatch.delitem(sys.modules, "gateway.session_context", raising=False)
    assert session_chat_id() == ""
    fake = types.ModuleType("gateway.session_context")
    fake.get_session_env = lambda name, default="": "<lab-group>" if name == CHAT_ID_ENV else default
    monkeypatch.setitem(sys.modules, "gateway.session_context", fake)
    assert session_chat_id() == "<lab-group>"


def test_a_request_takes_its_origin_from_the_session():
    store = Store()
    store.remember_sender("s-1", "u-alex", "telegram", chat_id="<lab-group>")
    rid = store.add_request(requester="Alex", text="bracket", session_id="s-1")
    req = store.get_request(rid)
    assert (req["platform"], req["chat_id"], req["sender_id"]) == ("telegram", "<lab-group>", "u-alex")
    assert store.session_origin("nope") == {"platform": "", "chat_id": "", "sender_id": ""}


# ---- 5. human-needed moments are open until the event that resolves them ----------------------------------------
def test_open_moments_are_closed_by_their_resolving_event():
    store = Store()
    a = store.add_human_needed("remove_part", "part on the plate", job_name="vase.gcode.3mf", source="watcher")
    store.add_human_needed("remove_part", "logged later", source="agent")  # after the fact: closed at once
    rid = store.add_approval_request("start", 7, "Mum", "s-mum")
    store.add_human_needed("approve_start", "Mum asks", source="hook")
    assert sorted(m["kind"] for m in store.open_human_needed()) == ["approve_start", "remove_part"]
    store.confirm_plate("vase", by="Sam")
    assert [m["kind"] for m in store.open_human_needed()] == ["approve_start"]
    assert store.human_needed(kind="remove_part")[-1]["id"] == a
    assert "plate confirmed clear by Sam" in next(m for m in store.human_needed() if m["id"] == a)["resolved_by"]
    store.resolve_approval_requests("start", 7, "started")
    assert store.open_human_needed() == [] and rid


def test_a_person_confirming_the_plate_marks_waiting_parts_taken_off():
    store = Store()
    store.record_done_part(8, job_name="bracket", requester="Alex", left_plate="on_plate")
    store.record_done_part(7, job_name="box", requester="Mum", left_plate="pushed_off")
    store.confirm_plate("bracket", by="Sam")
    states = {p["queue_item_id"]: p["left_plate"] for p in store.done_box()}
    assert states == {8: "taken_off", 7: "pushed_off"}
    store.record_done_part(8, photo="")  # an update never erases what is known
    part = next(p for p in store.done_box() if p["queue_item_id"] == 8)
    assert part["requester"] == "Alex" and part["left_plate"] == "taken_off"


def test_team_wording_has_no_family_forms_of_address():
    from home3d_ws.home3d import messages as M

    ctx = dict(requester="Mum", address_as="Mum dear", family_job='"sensor bracket"', job="bracket", progress=40,
               owner="Sam")
    for lang in ("en", "tr"):
        for kind in ("started", "finished", "finished_ejected", "plate_not_clear", "failed", "paused"):
            text = M.render(kind, "team", lang, **ctx)
            assert text and "Mum dear" not in text and "Mum" in text, (kind, lang, text)
        assert "Mum dear" in M.render("finished", "family", lang, **ctx)  # family keeps today's wording
    assert M.render("hms", "team", "en", **ctx) == ""  # owner-only kinds stay owner-only


# ---- review fixes -----------------------------------------------------------------------------------------------
def test_a_known_sender_decides_who_asked_not_a_matching_household_name():
    """Review: the model writes the requester name; a lab sender named like a household person is not family."""
    lab = {"name": "Lab", "target": "telegram:<lab>", "tone": "team", "members": ["lab-1"]}
    s = _s(household=[{"id": "fam-1", "name": "Alex"}], groups=[lab])
    r = N.route_for(s, requester="Alex", platform="telegram", chat_id="", sender_id="lab-9")
    assert r.announce is False and r.why == "outsider" and r.target == ""
    # the household person themselves, the owner asking for them, or no sender id at all: family as before
    assert N.route_for(s, requester="Alex", sender_id="fam-1").target == FAMILY
    assert N.route_for(s, requester="Alex", sender_id="owner-1").target == FAMILY
    assert N.route_for(s, requester="Alex").target == FAMILY


def _passes(s, store, fake, start, end, step=60.0):
    t = start
    while t <= end:
        N.flush(s, store, now=t)
        t += step
    return t


def test_one_bad_message_does_not_block_its_chat_for_hours(fake):
    """Review: a record the gateway always rejects held back every later notice to that chat for about 16 h."""
    store, s = Store(), _s()
    fake.ok = lambda target, text: text != "rejected"
    N.enqueue(s, store, audience="owner", target=OWNER, text="rejected", now=0)
    N.enqueue(s, store, audience="owner", target=OWNER, text="approve #7?", now=10)
    _passes(s, store, fake, 0, 5 * 60)
    texts = [c["text"] for c in fake.calls]
    assert "approve #7?" in texts and texts.index("approve #7?") >= 2  # it kept its place for the first retry
    assert store.outbox_counts()["sent"] == 1


def test_a_send_that_works_again_releases_the_chat_at_once(fake):
    """Review: after an outage, nothing went out until the oldest record's next backoff time."""
    store, s = Store(), _s()
    down = {"v": True}
    fake.ok = lambda target, text: not down["v"]
    N.enqueue(s, store, audience="family", target=FAMILY, text="old", now=0)
    _passes(s, store, fake, 0, 2 * 3600)
    assert store.outbox_pending()[0]["attempts"] >= 3  # in a long backoff now
    down["v"] = False
    N.enqueue(s, store, audience="family", target=FAMILY, text="new", now=2 * 3600 + 300)
    N.flush(s, store, now=2 * 3600 + 300)
    N.flush(s, store, now=2 * 3600 + 360)
    assert store.outbox_counts()["sent"] == 2 and store.outbox_counts()["pending"] == 0


def test_a_retry_time_far_ahead_means_the_clock_changed_and_is_due(fake):
    store, s = Store(), _s()
    fake.ok = False
    N.enqueue(s, store, audience="family", target=FAMILY, text="x", now=10 * 86400)
    N.flush(s, store, now=10 * 86400)  # fails: retry at 10 days + 60 s
    fake.ok = True
    N.flush(s, store, now=100.0)  # the watcher's clock went back (another printer, the simulator)
    assert store.outbox_counts()["sent"] == 1


def test_starting_one_job_closes_only_its_own_approval_wait():
    """Review: approving one start closed the open approve_start moments of every job."""
    store = Store()
    store.upsert_job(7, name="vase.gcode.3mf", requester="Mum", state="queued")
    store.upsert_job(8, name="clip.gcode.3mf", requester="Dad", state="queued")
    store.add_human_needed("approve_start", "start:7 waits", job_name="vase.gcode.3mf", source="agent")
    store.add_human_needed("approve_start", "start:8 waits", job_name="clip.gcode.3mf", source="agent")
    store.resolve_approval_requests("start", 7, "started")
    assert [m["job_name"] for m in store.open_human_needed()] == ["clip.gcode.3mf"]
