"""hooks.py: who may start / clear / resume (D3), session identity (D2), the handler pass (D4), cron (fail
closed), the bounded hook (no camera, deadline; fix round 2), family approval requests, speaker context and audit.
No Hermes."""

from __future__ import annotations

import contextvars
import json
import socket
import sys
import threading
import time
import types

import pytest

from home3d_ws.home3d import hooks as hooks_mod
from home3d_ws.home3d import upgrades
from home3d_ws.home3d.backends.base import BackendError, SliceOptions
from home3d_ws.home3d.backends.simulator import SimulatorBackend
from home3d_ws.home3d.config import LOCAL_SENDER, Settings
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store

OWNER, MUM, STRANGER = "owner-id@s.whatsapp.net", "mum-id@s.whatsapp.net", "someone@s.whatsapp.net"


def settings(**over) -> Settings:
    base = dict(backend="simulator", persona_name="Mıstık", language="tr", owner_name="Owner", owner_ids=[OWNER],
                owner_target="whatsapp:<owner-chat>@g.us",
                household=[{"id": MUM, "name": "Mum", "address_as": "Anneciğim"}, {"id": "dad-id", "name": "Dad"}])
    base.update(over)
    return Settings(**base)


class CronCtx:
    def current_cron_execution(self):
        return {"job_id": "x"}


class BrokenCronCtx:
    def current_cron_execution(self):
        raise RuntimeError("cron identity unavailable")


class CountingSim(SimulatorBackend):
    def __init__(self):
        super().__init__()
        self.plate_checks = 0

    def check_plate(self):
        self.plate_checks += 1
        return super().check_plate()


@pytest.fixture(autouse=True)
def no_cron_env(monkeypatch):
    monkeypatch.delenv("HERMES_CRON_SESSION", raising=False)
    monkeypatch.delitem(sys.modules, "gateway.session_context", raising=False)
    monkeypatch.delitem(sys.modules, "cron.execution_identity", raising=False)


class Rig:
    def __init__(self, ctx=None, **over):
        self.be = CountingSim()
        self.store = Store()
        self.rt = Runtime(ctx, settings=settings(**over), store=self.store, backend=self.be)
        self.h = hooks_mod.make_hooks(self.rt)
        self.store.remember_sender("s-mum", MUM, "whatsapp")
        self.store.remember_sender("s-owner", OWNER, "whatsapp")
        self.store.remember_sender("s-stranger", STRANGER, "whatsapp")

    def queue_job(self, requester: str = "Mum") -> int:
        sliced = self.be.slice(1, SliceOptions(printer_preset="sim-autoeject"))
        item = self.be.queue_add(sliced.library_file_id, manual_start=True)
        self.store.upsert_job(item.id, name=item.name, requester=requester, sliced_file_id=sliced.library_file_id,
                              eject_planned=1, state="queued")
        return item.id

    def pre(self, tool, args, session=""):
        return self.h["pre_tool_call"](tool_name=tool, args=args, task_id="t", session_id=session, tool_call_id="c1")

    def handler(self, tool, args, session):
        """The tool handler right after an approved hook call (what Hermes runs next)."""
        from home3d_ws.home3d.tools import build_tools

        fn = {n: h for n, _s, h in build_tools(self.rt)}[tool]
        return json.loads(fn(args, session_id=session))

    def turn(self, session, sender="", platform="whatsapp", text="merhaba", first=True, parent=""):
        return self.h["pre_llm_call"](session_id=session, user_message=text, platform=platform, sender_id=sender,
                                      is_first_turn=first, parent_session_id=parent)


@pytest.fixture
def rig():
    return Rig()


def test_only_printer_actions_are_gated(rig):
    for tool, args in [("home3d_status", {}), ("terminal", {"command": "ls"}), ("home3d_queue", {"action": "add"}),
                       ("home3d_clear_plate", {"action": "check"}), ("home3d_stop", {"action": "stop"}),
                       ("home3d_stop", {"action": "pause"})]:
        assert rig.pre(tool, args, "s-mum") is None, tool
    assert hooks_mod.gated_action("home3d_stop", {"action": "resume"}) == ("resume", "home3d_stop")
    assert hooks_mod.gated_action("home3d_clear_plate", {"action": "confirm"}) == ("clear_plate", "home3d_clear_plate")


# ---- 1. cron (fails closed) ----------------------------------------------------------------------------
def test_cron_always_blocks():
    for ctx in (CronCtx(), BrokenCronCtx()):
        r = Rig(ctx=ctx)
        qid = r.queue_job()
        for tool, args in [("home3d_start", {"queue_item_id": qid}), ("home3d_clear_plate", {"action": "confirm"}),
                           ("home3d_stop", {"action": "resume"})]:
            d = r.pre(tool, args, "s-owner")
            assert d["action"] == "block" and "cron" in d["message"], (ctx, tool)
        assert not r.store.peek_pass("home3d_start", str(qid), "s-owner")


def test_in_cron_reads_hermes_markers_fail_closed(monkeypatch):
    """ctx.current_cron_execution() is None inside a cron agent's delegate_task children; the raw markers are not."""
    class NoCron:
        def current_cron_execution(self):
            return None

    rt = Runtime(NoCron(), settings=settings(), store=Store(), backend=SimulatorBackend())
    assert rt.in_cron() is False and Runtime(None, settings=settings()).in_cron() is False
    assert Runtime(BrokenCronCtx(), settings=settings()).in_cron() is True

    monkeypatch.setenv("HERMES_CRON_SESSION", "1")  # standalone cron entrypoint (no gateway module loaded)
    assert rt.in_cron() is True
    monkeypatch.delenv("HERMES_CRON_SESSION")

    # gateway: the session ContextVar is authoritative (a leaked process env does not count) ...
    values = {"HERMES_CRON_SESSION": ""}
    sc = types.ModuleType("gateway.session_context")
    sc.get_session_env = lambda name, default="": values.get(name, default)
    monkeypatch.setitem(sys.modules, "gateway.session_context", sc)
    monkeypatch.setenv("HERMES_CRON_SESSION", "1")
    assert rt.in_cron() is False
    values["HERMES_CRON_SESSION"] = "1"  # ... and it is copied into delegated children
    assert rt.in_cron() is True

    def boom(name, default=""):
        raise RuntimeError("x")

    sc.get_session_env = boom
    assert rt.in_cron() is True  # a marker that raises counts as cron
    values["HERMES_CRON_SESSION"] = ""
    sc.get_session_env = lambda name, default="": values.get(name, default)

    ei = types.ModuleType("cron.execution_identity")
    ei._CURRENT = contextvars.ContextVar("hermes_cron_execution_test", default=None)
    monkeypatch.setitem(sys.modules, "cron.execution_identity", ei)
    assert rt.in_cron() is False
    token = ei._CURRENT.set(object())  # the raw execution var (a child of a cron agent still sees it)
    try:
        assert rt.in_cron() is True
        r = Rig(ctx=NoCron())
        qid = r.queue_job()
        d = r.pre("home3d_start", {"queue_item_id": qid}, "s-owner")
        assert d["action"] == "block" and "cron" in d["message"]
    finally:
        ei._CURRENT.reset(token)


# ---- 2. the safety gate ----------------------------------------------------------------------------------
def test_gate_failure_blocks_with_reasons(rig):
    d = rig.pre("home3d_start", {"queue_item_id": 999}, "s-owner")
    assert d["action"] == "block" and "999" in d["message"] and "not found" in d["message"]

    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.start(q1)
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "busy" in d["message"]
    assert not rig.store.peek_pass("home3d_start", str(q2), "s-owner")  # a blocked call gets no pass

    d = rig.pre("home3d_stop", {"action": "resume"}, "s-owner")
    assert d["action"] == "block" and "not paused" in d["message"]


def test_plate_not_verified_blocks_start_and_clear(rig):
    """The hook defers the plate to the handler (no camera in the hook); the handler's check blocks, and for the next
    2 minutes the hook blocks at once on that remembered result."""
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.set_scenario("eject_miss")  # the push misses: the part stays on the plate
    rig.be.start(q1)
    rig.be.advance(600)
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "approve" and "camera checks the plate right before starting" in d["message"]
    assert rig.be.plate_checks == 0
    res = rig.handler("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert res["ok"] is False and res["blocked"] and "plate" in res["error"] and rig.be.plate_checks == 1
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "plate is not empty" in d["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "block" and "plate" in d["message"].lower()
    assert rig.be.plate_checks == 1  # neither hook call looked again


def test_after_a_failed_print_only_a_confirmed_plate_allows_a_start(rig):
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.set_scenario("fail")
    rig.be.start(q1)
    rig.be.advance(600)
    st = rig.be.status()
    assert st.state == "FAILED"
    rig.be.human_clears_plate()  # the camera now says empty ...
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "approve clear" in d["message"]  # ... but that is not enough after a failure
    rig.store.confirm_plate(st.job_name, "Owner", status=st)  # what `/home3d approve clear` records
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "approve" and "camera checks the plate right before starting" in d["message"].lower()
    assert "verified" not in d["message"].lower()


# ---- 3. who is asking -----------------------------------------------------------------------------------
def test_non_owner_is_told_to_ask_the_owner(rig):
    qid = rig.queue_job()
    for session in ("s-mum", "s-stranger"):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block"
        assert hooks_mod.APPROVAL_MARKER in d["message"]
        assert f"/home3d approve start {qid}" in d["message"]
    assert "Mum is not the owner" in rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")["message"]
    assert "unknown sender" in rig.pre("home3d_start", {"queue_item_id": qid}, "s-stranger")["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    assert d["action"] == "block" and "/home3d approve clear" in d["message"]
    d = rig.pre("home3d_start", {"queue_item_id": qid, "allow_jump": True}, "s-mum")
    assert d["action"] == "block" and f"/home3d approve start {qid} jump" in d["message"]
    assert not any(rig.store.peek_pass("home3d_start", t, s) for t in (str(qid), f"{qid}+jump")
                   for s in ("s-mum", "s-stranger"))


def test_sessions_without_a_known_sender_are_blocked(rig):
    """The review: a subagent (platform "subagent", no sender) got the approval prompt; under yolo / approvals off /
    subagent_auto_approve that prompt is answered automatically, and its card went to the family member's chat."""
    qid = rig.queue_job()
    rig.turn("sub-1", "", "subagent")  # a delegate_task child without a parent sender
    rig.turn("cron-1", "", "cron")
    rig.turn("batch-1", "", "batch")
    rig.turn("noplat-1", "", "")
    rig.turn("wa-1", "", "whatsapp")  # a messaging turn that carried no sender
    for session in ("sub-1", "cron-1", "batch-1", "noplat-1", "wa-1", "never-seen", ""):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block" and "unknown sender" in d["message"], session
        assert f"/home3d approve start {qid}" in d["message"] and hooks_mod.APPROVAL_MARKER in d["message"]
        assert rig.store.sender_for(session) == ""


def test_a_turn_without_identity_clears_the_previous_speaker(rig):
    qid = rig.queue_job()
    rig.turn("group-1", OWNER, "whatsapp")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "group-1")["action"] == "approve"
    rig.turn("group-1", "", "whatsapp", first=False)  # next speaker unknown: never acts as the owner
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "group-1")["action"] == "block"


def test_child_session_inherits_the_parent_sender(rig):
    """A family member asks, the agent delegates: the subagent speaks for that family member, not for nobody."""
    qid = rig.queue_job()
    rig.turn("p-mum", MUM, "whatsapp")
    rig.turn("c-mum", "", "subagent", parent="p-mum")
    info = rig.store.sender_info("c-mum")
    assert info["sender_id"] == MUM and info["inherited_from"] == "p-mum"
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "c-mum")
    assert d["action"] == "block" and "Mum is not the owner" in d["message"]

    rig.turn("p-owner", OWNER, "whatsapp")
    rig.turn("c-owner", "", "subagent", parent="p-owner")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "c-owner")["action"] == "approve"

    rig.turn("p-cli", "", "cli")
    rig.turn("c-cli", "", "subagent", parent="p-cli")
    assert rig.store.sender_for("c-cli") == LOCAL_SENDER
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "c-cli")["action"] == "approve"

    rig.turn("c-own", MUM, "subagent", parent="p-owner")  # the turn's own sender wins over the parent's
    assert rig.store.sender_for("c-own") == MUM
    rig.turn("c-orphan", "", "subagent", parent="unknown-parent")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "c-orphan")["action"] == "block"


def test_matrix_and_email_lookalikes_cannot_start():
    r = Rig(owner_ids=["@sam:matrix.org", "sam@example.com"], owner_name="Sam")
    qid = r.queue_job()
    for session, sender, platform in (("m-evil", "@mallory:evil.org", "matrix"), ("m-evil2", "@sam:evil.org", "matrix"),
                                      ("e-evil", "sam@evil.com", "email")):
        r.turn(session, sender, platform)
        d = r.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block" and "unknown sender" in d["message"], sender
    for session, sender, platform in (("m-sam", "@sam:matrix.org", "matrix"), ("e-sam", "Sam@Example.com", "email")):
        r.turn(session, sender, platform)
        assert r.pre("home3d_start", {"queue_item_id": qid}, session)["action"] == "approve", sender


def test_local_owner_sessions(rig):
    """Classic CLI (platform cli, no sender), gateway-hosted CLI (platform local, sender uid:<n>), TUI, desktop."""
    qid = rig.queue_job()
    for session, sender, platform in (("cli-1", "", "cli"), ("gw-cli", "uid:1000", "local"), ("tui-1", "", "tui"),
                                      ("desk-1", "", "desktop"), ("acp-1", "", "acp")):
        out = rig.turn(session, sender, platform, text="status?")
        assert rig.store.sender_for(session) == LOCAL_SENDER, session
        assert "Owner (owner, local session)" in out["context"]
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "approve", session
    # a uid: sender on a messaging platform is just an unknown id; an auth subject on "local" is not uid-local
    rig.turn("wa-uid", "uid:1000", "whatsapp")
    rig.turn("dash", "auth:v1:[github,https://github.com,mallory]", "local")
    for session in ("wa-uid", "dash"):
        assert rig.pre("home3d_start", {"queue_item_id": qid}, session)["action"] == "block", session


def test_local_is_owner_off_blocks_local_sessions():
    r = Rig(local_is_owner=False)
    qid = r.queue_job()
    out = r.turn("cli-1", "", "cli", text="3d print status")
    assert "local_is_owner is off" in out["context"]
    d = r.pre("home3d_start", {"queue_item_id": qid}, "cli-1")
    assert d["action"] == "block" and "unknown sender" in d["message"]


def test_a_messaging_id_named_local_is_not_the_local_owner(rig):
    qid = rig.queue_job()
    rig.turn("wa-local", "local", "whatsapp")
    rig.turn("tg-local", " LOCAL ", "telegram")
    assert rig.store.sender_for("wa-local") == "whatsapp:local"
    for session in ("wa-local", "tg-local"):
        assert rig.pre("home3d_start", {"queue_item_id": qid}, session)["action"] == "block"


# ---- 4. the owner: Hermes' prompt + a single-use handler pass --------------------------------------------------
def test_owner_gets_the_human_approval_prompt_and_a_pass(rig):
    qid = rig.queue_job()
    rig.turn("cli-1", "", "cli")
    keys = set()
    for session in ("s-owner", "s-owner", "cli-1"):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "approve"
        assert f"#{qid}" in d["message"] and "Mum" in d["message"] and "auto-eject" in d["message"]
        assert "The camera checks the plate right before starting" in d["message"]
        assert d["rule_key"].startswith(f"home3d:home3d_start:{qid}:")
        keys.add(d["rule_key"])
        assert rig.store.peek_pass("home3d_start", str(qid), session)
    assert len(keys) == 3  # unique: an "always" answer never pre-approves a later printer action
    assert not rig.store.peek_pass("home3d_start", str(qid), "s-mum")
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "approve" and "looking at the plate yourself" in d["message"]
    assert d["rule_key"].startswith("home3d:home3d_clear_plate:-:")
    assert rig.store.peek_pass("home3d_clear_plate", "", "s-owner")
    d = rig.pre("home3d_start", {"queue_item_id": qid, "allow_jump": "yes"}, "s-owner")
    assert d["action"] == "approve" and rig.store.peek_pass("home3d_start", f"{qid}+jump", "s-owner")


def test_agent_sessions_never_use_stored_approvals(rig):
    """The old path: an owner grant in the approvals table let ANY session (Mum's) start or resume. Gone."""
    qid = rig.queue_job()
    rig.store.grant_approval("start", str(qid), "Owner")
    rig.store.grant_approval("clear_plate", "", "Owner")
    rig.store.grant_approval("resume", "", "Owner")
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert d["action"] == "block" and hooks_mod.APPROVAL_MARKER in d["message"]
    assert rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")["action"] == "block"
    assert rig.store.peek_approval("start", str(qid)) is not None  # untouched: nothing reads it any more


def test_resume_with_a_printer_error_needs_the_owner_ack(rig):
    qid = rig.queue_job()
    rig.be.set_scenario("pause_hms")
    rig.be.start(qid)
    rig.be.advance(60)
    st = rig.be.status()
    assert st.state == "PAUSE" and st.blocking_hms
    code = st.blocking_hms[0].code
    d = rig.pre("home3d_stop", {"action": "resume"}, "s-owner")
    assert d["action"] == "block" and "/home3d approve resume ack" in d["message"] and code in d["message"]
    assert not rig.store.peek_pass("home3d_stop", "", "s-owner")
    d = rig.pre("home3d_stop", {"action": "resume", "ack_hms": True}, "s-mum")
    assert d["action"] == "block" and "Mum is not the owner" in d["message"]
    assert "/home3d approve resume ack" in d["message"]
    d = rig.pre("home3d_stop", {"action": "resume", "ack_hms": "true"}, "s-owner")
    assert d["action"] == "approve" and code in d["message"] and "acknowledged" in d["message"]
    assert rig.store.peek_pass("home3d_stop", "", "s-owner")


def test_resume_without_errors(rig):
    qid = rig.queue_job()
    rig.be.start(qid)
    rig.be.advance(5)
    rig.be.pause()
    d = rig.pre("home3d_stop", {"action": "resume"}, "s-owner")
    assert d["action"] == "approve" and d["message"].startswith("Resume the paused 3D print")
    assert "error" not in d["message"].lower()


def test_post_tool_call_drops_a_pass_the_handler_did_not_use(rig):
    """Hermes' prompt denied / timed out, or another plugin vetoed: the call ends without the handler."""
    qid = rig.queue_job()
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")["action"] == "approve"
    rig.h["post_tool_call"](tool_name="home3d_start", args={"queue_item_id": qid}, result='{"error": "denied"}',
                            session_id="s-owner", status="blocked")
    assert not rig.store.peek_pass("home3d_start", str(qid), "s-owner")
    rig.store.issue_pass("home3d_stop", "", "s-owner")
    rig.h["post_tool_call"]("home3d_stop", {"action": "pause"}, "{}", session_id="s-owner")  # not a resume
    assert rig.store.peek_pass("home3d_stop", "", "s-owner")
    rig.h["post_tool_call"]("home3d_stop", {"action": "resume"}, "{}", session_id="s-owner")
    assert not rig.store.peek_pass("home3d_stop", "", "s-owner")


def test_the_hook_never_runs_the_camera_the_handler_does(rig, monkeypatch):
    """catalog F1: a lit plate check (light on, ~12 s wait, check) inside pre_tool_call could pass Hermes' 30 s hook
    budget. The hook only reads status + queue; the handler checks the plate once; a recent check counts in the hook
    for HOOK_PLATE_MAX_AGE_S."""
    qid = rig.queue_job()
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")["action"] == "approve"
    assert rig.be.plate_checks == 0
    plate = rig.rt.plate_check()  # what the handler does right after
    assert plate.is_empty is True and rig.be.plate_checks == 1
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")  # a recent "empty" in this process
    assert d["action"] == "approve" and "camera thinks the plate is empty" in d["message"]
    assert rig.be.plate_checks == 1
    q2 = rig.queue_job()
    rig.be.set_scenario("eject_miss")
    rig.be.start(qid)
    rig.be.advance(600)  # FINISH with the part still on the plate: a new state key, the old "empty" does not count
    assert rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")["action"] == "approve"
    occupied = rig.rt.plate_check()
    assert occupied.is_empty is not True and rig.be.plate_checks == 2
    assert rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")["action"] == "block"
    later = time.monotonic() + hooks_mod.HOOK_PLATE_MAX_AGE_S + 1
    monkeypatch.setattr(time, "monotonic", lambda: later)
    assert rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")["action"] == "approve"  # too old: deferred
    assert rig.be.plate_checks == 2


def test_backend_and_internal_errors_fail_closed(rig):
    class Broken(SimulatorBackend):
        def __init__(self, exc):
            super().__init__()
            self.exc = exc

        def status(self):
            raise self.exc

    for exc, text in ((BackendError("GET /printers/1/status: 502"), "not reachable"),
                      (RuntimeError("boom"), "safety check failed")):
        r = Runtime(None, settings=settings(), store=rig.store, backend=Broken(exc))
        d = hooks_mod.make_hooks(r)["pre_tool_call"]("home3d_start", {"queue_item_id": 1}, session_id="s-owner")
        assert d["action"] == "block" and text in d["message"]
        assert not rig.store.peek_pass("home3d_start", "1", "s-owner")


def test_hooks_never_raise_on_garbage(rig):
    pre, post, llm = rig.h["pre_tool_call"], rig.h["post_tool_call"], rig.h["pre_llm_call"]
    assert pre() is None and pre(None, None) is None and pre(123, "x") is None and pre(["home3d_start"], {}) is None
    for args in ("garbage", None, {"queue_item_id": "abc"}, {"queue_item_id": True}, {"queue_item_id": -3},
                 {"queue_item_id": "inf"}, {"queue_item_id": "nan"}):
        d = pre("home3d_start", args, session_id="s-owner")
        assert d["action"] == "block" and "queue_item_id" in d["message"]
    assert pre("home3d_stop", {"action": None}) is None
    assert pre("home3d_stop", "resume") is None  # not a dict: not a resume
    for kw in ({}, {"session_id": None, "user_message": None, "sender_id": None},
               {"session_id": 5, "user_message": [{"type": "image_url"}, "x", 3], "sender_id": 42, "platform": None},
               {"session_id": "s", "user_message": {"odd": 1}, "is_first_turn": "yes", "parent_session_id": 7}):
        out = llm(**kw)
        assert out is None or isinstance(out.get("context"), str)
    for args in ((None,), ("home3d_start", None, object()), ("home3d_queue", "x", b"\xff"), ("home3d_x", {}, "{"),
                 ("home3d_start", {"queue_item_id": {"a": 1}}, '{"error": "owner approval needed"}')):
        assert post(*args) is None

    broken = Runtime(None, settings=settings(), backend=rig.be)
    broken._store = object()  # every store call raises AttributeError
    h = hooks_mod.make_hooks(broken)
    assert h["pre_llm_call"](session_id="s", user_message="3d baskı", sender_id=MUM) is None
    assert h["post_tool_call"]("home3d_status", {}, "{}", session_id="s") is None
    d = h["pre_tool_call"]("home3d_start", {"queue_item_id": 1}, session_id="s")
    assert d["action"] == "block"


# ---- pre_llm_call: identity + context ------------------------------------------------------------------------
def test_pre_llm_call_context(rig):
    rid = rig.store.add_request(requester="Mum", text="çiçek kutusu", channel="voice")
    rig.store.kv_set("watcher", {"state": "RUNNING", "job_name": "Gül kutusu", "progress": 45.2, "layer": 12,
                                 "total_layers": 40, "plate_state": {"phase": "printing"},
                                 "updated": __import__("time").time()})
    out = rig.h["pre_llm_call"](session_id="new-session", user_message="Mıstık bana bir kutu basar mısın?",
                                platform="whatsapp", sender_id=MUM, is_first_turn=True)
    ctx = out["context"]
    assert rig.store.sender_for("new-session") == MUM
    assert len(ctx) <= hooks_mod.CONTEXT_MAX
    assert "Mıstık" in ctx and "Turkish" in ctx and "Mum" in ctx and "Anneciğim" in ctx
    assert 'RUNNING "Gül kutusu" 45%' in ctx and "layer 12/40" in ctx
    assert f"#{rid}" in ctx and "çiçek kutusu" in ctx
    assert hooks_mod.SKILL_REF in ctx

    # a later small-talk turn with an unchanged printer: who is speaking is enough
    short = rig.h["pre_llm_call"](session_id="new-session", user_message="teşekkürler", platform="whatsapp",
                                  sender_id="dad-id", is_first_turn=False)["context"]
    assert short.startswith("[home-3d-workshop") and "Dad" in short and "skill" not in short
    assert rig.store.sender_for("new-session") == "dad-id"  # group chat: the current speaker wins

    rig.store.kv_set("watcher", {"state": "FINISH", "job_name": "Gül kutusu" * 40, "updated": 0})
    long = rig.h["pre_llm_call"](session_id="new-session", user_message="is the 3D printer done?",
                                 platform="whatsapp", sender_id=STRANGER, is_first_turn=False)["context"]
    assert len(long) <= hooks_mod.CONTEXT_MAX and "stale" in long and "not in the household" in long

    local = rig.h["pre_llm_call"](session_id="cli-1", user_message="status?", platform="cli", sender_id="",
                                  is_first_turn=True)["context"]
    assert "Owner (owner, local session)" in local


def test_unknown_senders_with_unrelated_messages_get_no_context(rig):
    """The review: every session in the profile (a coding chat, a stranger) got the persona."""
    for i, text in enumerate(("can you refactor this function?", "print(x) returns None",
                              "which model is best for this?", "the boilerplate is too long", "hi")):
        assert rig.turn(f"x-{i}", "", "whatsapp", text=text) is None, text
        assert rig.turn(f"y-{i}", STRANGER, "telegram", text=text) is None, text
        assert rig.turn(f"z-{i}", "", "subagent", text=text) is None, text
    # printing-relevant or naming the persona: context, even for strangers (they still cannot approve anything)
    for i, text in enumerate(("is the 3D printer busy?", "Mistik, are you there?", "MIŞTIK?",
                              "can you 3d print a vase?", "baskı ne durumda?")):
        out = rig.turn(f"w-{i}", STRANGER, "telegram", text=text)
        assert out and "Mıstık" in out["context"] and "not in the household" in out["context"], text


def test_inject_context_modes():
    never = Rig(inject_context="never")
    assert never.turn("s1", MUM, "whatsapp", text="3d baskı?") is None
    assert never.store.sender_for("s1") == MUM  # identity is still recorded
    always = Rig(inject_context="always")
    out = always.turn("s2", STRANGER, "whatsapp", text="hello there")
    assert out and "not in the household" in out["context"] and "Mıstık" in out["context"]
    later = always.turn("s2", STRANGER, "whatsapp", text="ok", first=False)
    assert later["context"].startswith("[home-3d-workshop ·")


def test_post_tool_call_audits_and_logs_approval_friction(rig):
    post = rig.h["post_tool_call"]
    post("home3d_status", {}, json.dumps({"ok": True, "printer": {}}), session_id="s-mum", status="ok")
    post("terminal", {"command": "ls"}, "ok", session_id="s-mum")
    ev = rig.store.events(kind="tool")
    assert len(ev) == 1 and json.loads(ev[0]["payload"])["tool"] == "home3d_status"

    blocked = json.dumps({"error": "BLOCKED: owner approval needed: Mum is not the owner."})
    for _ in range(3):  # the agent retrying does not inflate the evidence
        post("home3d_start", {"queue_item_id": 7}, blocked, session_id="s-mum", status="blocked",
             error_type="plugin_block")
    kind = upgrades.normalize_kind("approve_start")
    moments = rig.store.human_needed(kind=kind)
    assert len(moments) == 1 and moments[0]["who"] == "Mum" and "7" in moments[0]["detail"]
    payload = json.loads(rig.store.events(kind="tool")[0]["payload"])
    assert payload["ok"] is False and payload["queue_item_id"] == 7 and payload["sender"] == MUM

    post("home3d_clear_plate", {"action": "confirm"}, blocked, session_id="s-mum", status="blocked")
    assert len(rig.store.human_needed(kind=kind)) == 2
    post("home3d_start", {"queue_item_id": 8}, json.dumps({"ok": False, "error": "printer busy"}), session_id="s-mum")
    assert len(rig.store.human_needed(kind=kind)) == 2  # other failures are not approval friction


def test_session_sender_rules():
    ss = hooks_mod.session_sender
    assert ss("", "cli") == LOCAL_SENDER and ss("", "TUI") == LOCAL_SENDER and ss("uid:501", "local") == LOCAL_SENDER
    assert ss("", "subagent") == "" and ss("", "") == "" and ss("", "cron") == "" and ss(None, "whatsapp") == ""
    assert ss("uid:501", "telegram") == "uid:501" and ss("uid:x", "local") == "uid:x"
    assert ss("local", "matrix") == "matrix:local" and ss("@sam:matrix.org", "matrix") == "@sam:matrix.org"


# ---- fix round 2 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("marker", ["kanban", "single_query", "source_tool", "finite_turn", "unattended_turn",
                                    "finite_raises"])
def test_runs_with_nobody_present_never_get_an_approval(rig, monkeypatch, marker):
    """hermes-api N1: a kanban worker / `chat -q` / `-z` / `--source tool` run is a local `cli` session with a
    `uid:<n>` sender (= the local owner), but nobody can answer Hermes' prompt (or it auto-approves)."""
    qid = rig.queue_job()
    rig.turn("s-kanban", sender="uid:1000", platform="cli")
    assert rig.store.sender_for("s-kanban") == LOCAL_SENDER
    if marker == "kanban":
        monkeypatch.setenv("HERMES_KANBAN_TASK", "t_42")
    elif marker == "single_query":
        monkeypatch.setenv("HERMES_SINGLE_QUERY_SESSION", "1")
    elif marker == "source_tool":
        monkeypatch.setenv("HERMES_SESSION_SOURCE", "tool")
    else:
        mod = types.ModuleType("gateway.session_finite")
        mod.finite_turn_required = (lambda: True) if marker == "finite_turn" else (lambda: None)
        mod.unattended_turn = (lambda: True) if marker == "unattended_turn" else (lambda: False)
        if marker == "finite_raises":
            mod.finite_turn_required = lambda: (_ for _ in ()).throw(LookupError("no turn"))
        monkeypatch.setitem(sys.modules, "gateway.session_finite", mod)
    before = rig.be.plate_checks
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-kanban")
    assert d["action"] == "block" and "needs a person present" in d["message"]
    assert f"/home3d approve start {qid}" in d["message"]
    assert not rig.store.peek_pass("home3d_start", str(qid), "s-kanban") and rig.be.plate_checks == before


def test_an_ordinary_local_session_is_not_unattended(rig, monkeypatch):
    mod = types.ModuleType("gateway.session_finite")
    mod.finite_turn_required, mod.unattended_turn = (lambda: None), (lambda: False)
    monkeypatch.setitem(sys.modules, "gateway.session_finite", mod)
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "cli")
    qid = rig.queue_job()
    rig.turn("s-cli", platform="cli")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-cli")["action"] == "approve"


def test_no_camera_check_when_the_printer_already_blocks(rig):
    """safety 10 / hermes-api N4: Mum asking to start during a print cost two chamber-light POSTs and ~12 s."""
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.start(q1)
    rig.be.advance(30)
    assert rig.be.status().state == "RUNNING"
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "busy" in d["message"]
    for session in ("s-mum", "s-stranger"):  # refused on identity, before any gate
        d = rig.pre("home3d_start", {"queue_item_id": q2}, session)
        assert d["action"] == "block" and "owner approval needed" in d["message"]
    assert rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")["action"] == "block"
    assert rig.be.plate_checks == 0


def test_non_owner_is_refused_before_any_camera_check_on_an_idle_printer(rig):
    """The sender check runs before the safety gate: a family member's or a stranger's start never costs a
    plate check (camera + chamber light) on an idle printer."""
    qid = rig.queue_job()
    assert rig.be.status().state == "IDLE"
    for session in ("s-mum", "s-stranger", "s-nobody"):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block" and "owner approval needed" in d["message"]
        assert f"/home3d approve start {qid}" in d["message"]
    assert rig.be.plate_checks == 0


def test_a_failure_the_printer_forgot_still_needs_the_owners_confirmation(rig):
    """safety 6 / e2e NEW-2: RUNNING -> IDLE (cancel, power loss) or FAILED -> reboot -> IDLE; the camera then
    (wrongly) says empty. The watcher recorded the failure; the hook must still want the owner's confirmation."""
    qid = rig.queue_job()
    assert rig.be.status().state == "IDLE"
    rig.store.record_failure("clip", "watcher", "print ended without finishing")
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")
    assert d["action"] == "block" and "approve clear" in d["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "approve"  # the owner may confirm the plate (that is the way out)
    rig.store.confirm_plate(rig.be.status().job_name, "Owner")  # what the confirm handler records
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")["action"] == "approve"


def test_the_owner_can_get_out_of_the_false_positive_band(rig, monkeypatch):
    """e2e NEW-1: an empty plate read at 19.9 % (light on, calibrated) blocked approve clear AND start forever. The
    hook defers the plate; a recent band reading shows up as "NOT sure" and passes for the owner's confirmation."""
    from home3d_ws.home3d.backends.base import PlateCheck

    band = PlateCheck(is_empty=None, difference_pct=19.9, message="uncertain: band", light_ok=True,
                      uncertain_band=True)
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.set_scenario("fail")
    rig.be.start(q1)
    rig.be.advance(600)
    st = rig.be.status()
    assert st.state == "FAILED"
    monkeypatch.setattr(rig.be, "check_plate", lambda: band)
    rig.rt.plate_check()  # e.g. the confirm handler a moment ago
    assert rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")["action"] == "block"
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "approve" and "NOT sure" in d["message"] and "19.9" in d["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    assert d["action"] == "block" and "Mum is not the owner" in d["message"]
    rig.store.confirm_plate(st.job_name, "Owner", status=st)  # what the approved confirm records
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "approve" and "owner confirmed the plate is clear" in d["message"]
    occupied = PlateCheck(is_empty=False, difference_pct=40.0, light_ok=True)
    monkeypatch.setattr(rig.be, "check_plate", lambda: occupied)
    rig.rt.forget_plate_check()
    rig.rt.plate_check()
    assert rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")["action"] == "block"  # never "occupied"


def test_the_resume_pass_records_the_errors_the_owner_was_shown(rig):
    qid = rig.queue_job()
    rig.be.set_scenario("pause_hms")
    rig.be.start(qid)
    rig.be.advance(60)
    code = rig.be.status().blocking_hms[0].code
    assert rig.pre("home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")["action"] == "approve"
    assert rig.store.take_pass("home3d_stop", "", "s-owner") == {"detail": hooks_mod.hms_ack_detail([code])}
    assert hooks_mod.acked_codes(hooks_mod.hms_ack_detail([code.lower(), " "])) == {code.upper()}


def test_a_light_left_on_reaches_the_owner(rig, monkeypatch):
    """safety 10: a plate check (now the handler's) that could not switch the light off again is handed to the
    watcher, and a recent one shows up in the next approval prompt."""
    from home3d_ws.home3d.backends.base import PlateCheck

    qid = rig.queue_job()
    lit = PlateCheck(is_empty=True, difference_pct=1.0, light_ok=True,
                     message="empty (light_left_on: the chamber light could not be switched off again (mqtt))")
    monkeypatch.setattr(rig.be, "check_plate", lambda: lit)
    rig.rt.plate_check()
    assert "light_left_on" in rig.store.kv_get("light_left_on:pending")["note"]
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")
    assert d["action"] == "approve" and "chamber light could not be switched off" in d["message"]


# ---- fix round 2 (R2-6): the hook is bounded --------------------------------------------------------------------
class FakeBambuddy:
    """A Bambuddy HTTP server stand-in: records every request (method, path, timeout) and answers GETs."""

    def __init__(self, hang: "threading.Event | None" = None, timeout_hang: bool = False):
        self.calls: list[tuple[str, str, float]] = []
        self.hang, self.timeout_hang = hang, timeout_hang

    def __call__(self, req, timeout):
        import io
        from urllib.parse import urlparse

        path = urlparse(req.full_url).path.replace("/api/v1", "", 1)
        self.calls.append((req.get_method(), path, float(timeout)))
        if self.hang is not None:  # a printer manager that never answers
            self.hang.wait(30)
            raise socket.timeout("timed out")
        if self.timeout_hang:  # what urllib raises once ``timeout`` has passed without an answer
            raise socket.timeout("timed out")
        if path.endswith("/status"):
            body = {"connected": True, "state": "IDLE", "subtask_name": "", "progress": 0, "chamber_light": False,
                    "temperatures": {"bed": 24.0, "nozzle": 25.0}, "hms_errors": []}
        elif path.startswith("/queue"):
            body = [{"id": 7, "status": "pending", "library_file_name": "box.gcode.3mf", "position": 1,
                     "manual_start": True}]
        else:
            body = {"is_empty": True, "difference_percent": 1.0}

        class Resp(io.BytesIO):
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp(json.dumps(body).encode())


def _bambuddy_rig(monkeypatch, fake):
    from home3d_ws.home3d.backends import bambuddy

    monkeypatch.setattr(bambuddy, "_urlopen", fake)
    be = bambuddy.BambuddyBackend("http://192.168.1.50:8000", printer_id=1)
    be._sleep = lambda s: None
    store = Store()
    rt = Runtime(None, settings=settings(backend="bambuddy", bambuddy_url="http://192.168.1.50:8000"), store=store,
                 backend=be)
    store.remember_sender("s-owner", OWNER, "whatsapp")
    store.upsert_job(7, name="box.gcode.3mf", requester="Mum", state="queued", eject_planned=1)
    return rt, hooks_mod.make_hooks(rt)["pre_tool_call"], store


def test_the_hook_reads_only_status_and_queue_with_short_timeouts(monkeypatch):
    fake = FakeBambuddy()
    rt, pre, store = _bambuddy_rig(monkeypatch, fake)
    d = pre("home3d_start", {"queue_item_id": 7}, session_id="s-owner")
    assert d["action"] == "approve" and "camera checks the plate right before starting" in d["message"]
    d = pre("home3d_clear_plate", {"action": "confirm"}, session_id="s-owner")
    assert d["action"] == "approve"
    pre("home3d_stop", {"action": "resume"}, session_id="s-owner")
    paths = [(m, p) for m, p, _t in fake.calls]
    assert set(paths) <= {("GET", "/printers/1/status"), ("GET", "/queue/")}, paths
    assert not any("camera" in p or "chamber-light" in p or m != "GET" for m, p in paths)  # no camera, no light
    assert max(t for _m, _p, t in fake.calls) <= hooks_mod.HOOK_REQUEST_TIMEOUT_S <= 5
    assert rt.backend.timeout_cap is None  # the shared backend keeps its normal timeouts


def test_a_bambuddy_that_times_out_blocks_within_the_budget(monkeypatch):
    """Every request times out: the hook blocks ("not reachable"); the worst case it waited is the sum of the
    per-request timeouts (status only: the gate stops there), far below Hermes' 30 s."""
    fake = FakeBambuddy(timeout_hang=True)
    rt, pre, store = _bambuddy_rig(monkeypatch, fake)
    d = pre("home3d_start", {"queue_item_id": 7}, session_id="s-owner")
    assert d["action"] == "block" and "not reachable" in d["message"] and "home3d_start was not run" in d["message"]
    assert sum(t for _m, _p, t in fake.calls) <= 2 * hooks_mod.HOOK_REQUEST_TIMEOUT_S < 15
    assert not store.peek_pass("home3d_start", "7", "s-owner")


def test_a_hanging_bambuddy_cannot_hold_the_hook_past_its_deadline(monkeypatch):
    """A printer manager that never answers (or a DNS lookup that hangs: no socket timeout covers it): the hook
    returns a block at HOOK_DEADLINE_S, and the late result never turns into a pass."""
    monkeypatch.setattr(hooks_mod, "HOOK_DEADLINE_S", 0.3)
    hang = threading.Event()
    fake = FakeBambuddy(hang=hang)
    rt, pre, store = _bambuddy_rig(monkeypatch, fake)
    t0 = time.monotonic()
    d = pre("home3d_start", {"queue_item_id": 7}, session_id="s-owner")
    took = time.monotonic() - t0
    assert d["action"] == "block" and "did not answer within" in d["message"] and took < 2
    hang.set()  # the stuck request finally ends: still no pass, nothing issued later
    time.sleep(0.2)
    assert not store.peek_pass("home3d_start", "7", "s-owner")
    assert not any("camera" in p or "chamber-light" in p for _m, p, _t in fake.calls)


def test_the_bounded_gate_still_sees_cron_markers(monkeypatch):
    """The gate runs in a worker thread with the caller's context: a cron ContextVar stays visible (fail closed)."""
    class NoCron:
        def current_cron_execution(self):
            return None

    ei = types.ModuleType("cron.execution_identity")
    ei._CURRENT = contextvars.ContextVar("hermes_cron_execution_thread_test", default=None)
    monkeypatch.setitem(sys.modules, "cron.execution_identity", ei)
    r = Rig(ctx=NoCron())
    qid = r.queue_job()
    ev = hooks_mod._Hooks(r.rt)
    token = ei._CURRENT.set(object())
    try:
        out = ev._evaluate_bounded("start", {"queue_item_id": qid})
    finally:
        ei._CURRENT.reset(token)
    assert out.ok is False and "cron" in out.reason


# ---- fix round 2 (R2-7): a family member's ask reaches the owner ---------------------------------------------
def _watcher_ran(store, minutes_ago: float = 1) -> None:
    store.kv_set("watcher", {"state": "IDLE", "updated": time.time() - minutes_ago * 60})


def test_a_family_ask_becomes_one_approval_request(rig):
    qid = rig.queue_job()
    _watcher_ran(rig.store)
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert d["action"] == "block" and f"/home3d approve start {qid}" in d["message"]
    assert "Owner gets this request on the next watcher pass (about 2 min)" in d["message"]
    assert "Do not promise a start" in d["message"] and "you asked" not in d["message"]
    pending = rig.store.pending_approval_requests()
    assert [(r["action"], r["queue_item_id"], r["who"], r["sender_id"]) for r in pending] == \
        [("start", qid, "Mum", MUM)]
    rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")  # asking again (same day) adds nothing
    assert len(rig.store.pending_approval_requests()) == 1
    rig.store.mark_approval_request_announced(pending[0]["id"])
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert "already got this request" in d["message"]
    rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    rig.pre("home3d_stop", {"action": "resume"}, "s-mum")
    assert [(r["action"], r["queue_item_id"]) for r in rig.store.pending_approval_requests()] == \
        [("clear_plate", None), ("resume", None)]
    assert rig.be.plate_checks == 0


@pytest.mark.parametrize("target", ["whatsapp:<owner-chat>@g.us", ""])
def test_without_a_watcher_the_block_says_to_ask_the_owner_directly(target):
    rig = Rig(owner_target=target)
    qid = rig.queue_job()
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")  # the watcher never ran
    assert "The watcher is off, so Owner is not told automatically: Mum should ask Owner directly" in d["message"]
    _watcher_ran(rig.store, minutes_ago=60)  # stale
    d = rig.pre("home3d_start", {"queue_item_id": qid, "allow_jump": True}, "s-mum")
    assert "watcher is off" in d["message"] and f"/home3d approve start {qid} jump" in d["message"]


def test_strangers_and_unknown_senders_leave_no_request(rig):
    qid = rig.queue_job()
    _watcher_ran(rig.store)
    for session in ("s-stranger", "s-nobody", ""):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block" and "is not told about this" in d["message"]
    assert rig.store.pending_approval_requests() == []


def test_the_owner_starting_it_settles_the_request(rig):
    qid = rig.queue_job()
    _watcher_ran(rig.store)
    rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert len(rig.store.pending_approval_requests()) == 1
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")["action"] == "approve"
    res = rig.handler("home3d_start", {"queue_item_id": qid}, "s-owner")
    assert res["ok"], res
    assert rig.store.pending_approval_requests() == []  # started meanwhile: never announced


def test_interval_text():
    it = hooks_mod._interval_text
    assert it("2m") == "2 min" and it("90s") == "90 s" and it("1h") == "1 h" and it("every 5m") == "5 min"
    assert it("") == "2 min" and it("*/2 * * * *") == "*/2 * * * *"


def test_a_second_ask_after_the_owner_settled_the_first_is_passed_on_again(rig):
    """Mum asks to clear the plate, the owner clears it; later the same day she asks again: a new request that the
    watcher passes on (not "already got this request", and not a promise that nobody keeps)."""
    _watcher_ran(rig.store)
    rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    (first,) = rig.store.pending_approval_requests()
    rig.store.mark_approval_request_announced(first["id"])
    assert "already got this request" in rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")["message"]
    rig.store.resolve_approval_requests("clear_plate", None, "cleared by Owner")
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    assert "Owner gets this request on the next watcher pass" in d["message"]
    assert "already got" not in d["message"]
    (second,) = rig.store.pending_approval_requests()
    assert second["id"] != first["id"] and second["action"] == "clear_plate"
    rig.store.mark_approval_request_announced(second["id"])
    rig.store.resolve_approval_requests("resume", None, "resumed")  # another action settles nothing here
    assert "already got this request" in rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")["message"]


def test_without_an_owner_chat_the_block_does_not_promise_the_owner_is_told():
    """owner_target empty: the watcher's owner notices only reach the cron output / outbox, so the block says to
    ask the owner directly, even with a running watcher and after an announcement."""
    r = Rig(owner_target="")
    qid = r.queue_job()
    _watcher_ran(r.store)
    d = r.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert "No owner chat is set (owner_target), so Owner may not be told automatically: Mum should ask Owner " \
           "directly" in d["message"]
    assert "gets this request" not in d["message"]
    (req,) = r.store.pending_approval_requests()
    r.store.mark_approval_request_announced(req["id"])
    d = r.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert "already got" not in d["message"] and "should ask Owner directly" in d["message"]


def test_the_hook_deadline_follows_a_lower_hermes_hook_timeout(monkeypatch):
    """plugins.hook_callback_timeout below 30 s: the gate's deadline shrinks to 0.4 of it, so the hook answers
    (a block) before Hermes times it out (which would block every tool call, stop included, for 60 s)."""
    fake_plugins = types.ModuleType("hermes_cli.plugins")
    limit = {"t": 30.0}
    fake_plugins._resolve_hook_callback_timeout = lambda: limit["t"]
    monkeypatch.setitem(sys.modules, "hermes_cli.plugins", fake_plugins)
    assert hooks_mod.hook_deadline_s() == hooks_mod.HOOK_DEADLINE_S == 12
    limit["t"] = 8.0
    assert hooks_mod.hook_deadline_s() == pytest.approx(3.2)
    limit["t"] = 0  # Hermes without a hook time limit: our own deadline
    assert hooks_mod.hook_deadline_s() == 12
    fake_plugins._resolve_hook_callback_timeout = lambda: (_ for _ in ()).throw(RuntimeError("config"))
    assert hooks_mod.hook_deadline_s() == 12  # unreadable: Hermes' default (30 s) applies
    limit["t"] = 1.0
    fake_plugins._resolve_hook_callback_timeout = lambda: limit["t"]
    hang = threading.Event()
    fake = FakeBambuddy(hang=hang)
    rt, pre, store = _bambuddy_rig(monkeypatch, fake)
    t0 = time.monotonic()
    d = pre("home3d_start", {"queue_item_id": 7}, session_id="s-owner")
    took = time.monotonic() - t0
    hang.set()
    assert d["action"] == "block" and "did not answer within 0.4 s" in d["message"] and took < 1.0, (took, d)
    time.sleep(0.2)
    assert not store.peek_pass("home3d_start", "7", "s-owner")


# ---- review round 3 ---------------------------------------------------------------------------------------
def test_r3_the_hook_names_another_persons_workshop_job_ahead():
    """S2: Mum's workshop job waits ahead of Sam's; the owner's start of Sam's job is blocked (jump), naming Mum."""
    rig = Rig(language="en", household=[{"id": MUM, "name": "Mum"}, {"id": "sam-id", "name": "Sam"}])
    mum, sam = rig.queue_job("Mum"), rig.queue_job("Sam")
    d = rig.pre("home3d_start", {"queue_item_id": sam}, "s-owner")
    assert d["action"] == "block" and "for Mum" in d["message"] and "/home3d approve" not in d["message"]
    d = rig.pre("home3d_start", {"queue_item_id": sam, "allow_jump": True}, "s-owner")
    assert d["action"] == "approve" and "for Mum" in d["message"] and "jumping ahead" in d["message"]
    assert rig.pre("home3d_start", {"queue_item_id": mum}, "s-owner")["action"] == "approve"


def test_r3_an_irc_nick_equal_to_the_owners_id_is_not_the_owner():
    """S5: IRC nicks are chosen freely: a nick equal to the owner's (Slack) id never counts; only an "irc:<nick>"
    entry names an IRC sender. Other platforms match as before."""
    assert hooks_mod.session_sender("U02ABCDEF", "irc") == "irc:U02ABCDEF"
    assert hooks_mod.session_sender("irc:U02ABCDEF", "slack") == "slack:irc:U02ABCDEF"  # no lookalike
    assert hooks_mod.session_sender("U02ABCDEF", "slack") == "U02ABCDEF"
    rig = Rig(owner_ids=["U02ABCDEF"])
    qid = rig.queue_job()
    rig.turn("s-irc", sender="u02abcdef", platform="irc")
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-irc")
    assert d["action"] == "block" and "not in the household list" in d["message"]
    rig.turn("s-slack", sender="U02ABCDEF", platform="slack")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-slack")["action"] == "approve"
    rig2 = Rig(owner_ids=["irc:SamNick"])
    rig2.turn("s-irc", sender="samnick", platform="irc")
    assert rig2.pre("home3d_start", {"queue_item_id": rig2.queue_job()}, "s-irc")["action"] == "approve"


def test_r3_a_longer_watch_interval_does_not_make_the_watcher_look_off():
    """R3-ROB-2 / J3-6: with watch_interval 15m, a pass 11 minutes ago is a running watcher (3 intervals)."""
    rig = Rig(watch_interval="15m", language="en")
    rig.store.kv_set("watcher", {"state": "IDLE", "updated": time.time() - 11 * 60})
    assert hooks_mod.watcher_fresh(rig.store, rig.rt.settings)
    assert not hooks_mod.watcher_fresh(rig.store, settings())  # 2m: stale after 10 min
    assert hooks_mod.watcher_stale_s(settings(watch_interval="every 20m")) == 3600
    assert hooks_mod.watcher_stale_s(settings(watch_interval="*/5 * * * *")) == hooks_mod.WATCHER_STALE_S
    d = rig.pre("home3d_start", {"queue_item_id": rig.queue_job()}, "s-mum")
    assert "watcher is off" not in d["message"] and "next watcher pass (about 15 min)" in d["message"]


def test_the_turn_records_the_chat_it_came_from(rig, monkeypatch):
    """Delivery: the origin chat of a request (Hermes binds it as HERMES_SESSION_CHAT_ID; a child inherits it)."""
    import sys
    import types

    fake = types.ModuleType("gateway.session_context")
    fake.get_session_env = lambda name, default="": "<family-group>" if name == "HERMES_SESSION_CHAT_ID" else default
    monkeypatch.setitem(sys.modules, "gateway.session_context", fake)
    rig.turn("s-group", MUM, "whatsapp")
    assert rig.store.session_origin("s-group") == {"platform": "whatsapp", "chat_id": "<family-group>",
                                                   "sender_id": MUM}
    monkeypatch.delitem(sys.modules, "gateway.session_context")
    monkeypatch.delenv("HERMES_SESSION_CHAT_ID", raising=False)
    rig.turn("s-child", "", "whatsapp", parent="s-group")
    assert rig.store.session_origin("s-child")["chat_id"] == "<family-group>"
