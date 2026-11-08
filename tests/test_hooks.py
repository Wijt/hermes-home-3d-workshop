"""hooks.py: owner approval + safety gates before printer actions, speaker context, audit (no Hermes)."""

from __future__ import annotations

import json

import pytest

from home3d_ws.home3d import hooks as hooks_mod
from home3d_ws.home3d import upgrades
from home3d_ws.home3d.backends.base import BackendError, SliceOptions
from home3d_ws.home3d.backends.simulator import SimulatorBackend
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store

OWNER, MUM, STRANGER = "owner-id@s.whatsapp.net", "mum-id@s.whatsapp.net", "someone@s.whatsapp.net"


def settings(**over) -> Settings:
    base = dict(backend="simulator", persona_name="Mıstık", language="tr", owner_name="Owner", owner_ids=[OWNER],
                household=[{"id": MUM, "name": "Mum", "address_as": "Anneciğim"}, {"id": "dad-id", "name": "Dad"}])
    base.update(over)
    return Settings(**base)


class CronCtx:
    def current_cron_execution(self):
        return {"job_id": "x"}


class Rig:
    def __init__(self, ctx=None, **over):
        self.be = SimulatorBackend()
        self.store = Store()
        self.rt = Runtime(ctx, settings=settings(**over), store=self.store, backend=self.be)
        self.h = hooks_mod.make_hooks(self.rt)
        self.store.remember_sender("s-mum", MUM)
        self.store.remember_sender("s-owner", OWNER)
        self.store.remember_sender("s-stranger", STRANGER)

    def queue_job(self, requester: str = "Mum") -> int:
        sliced = self.be.slice(1, SliceOptions(printer_preset="sim-autoeject"))
        item = self.be.queue_add(sliced.library_file_id, manual_start=True)
        self.store.upsert_job(item.id, name=item.name, requester=requester, sliced_file_id=sliced.library_file_id,
                              eject_planned=1, state="queued")
        return item.id

    def pre(self, tool, args, session=""):
        return self.h["pre_tool_call"](tool_name=tool, args=args, task_id="t", session_id=session)


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


def test_cron_always_blocks():
    r = Rig(ctx=CronCtx())
    qid = r.queue_job()
    r.store.grant_approval("start", str(qid), "Owner")  # even an approval does not help in cron
    for tool, args in [("home3d_start", {"queue_item_id": qid}), ("home3d_clear_plate", {"action": "confirm"}),
                       ("home3d_stop", {"action": "resume"})]:
        d = r.pre(tool, args, "s-owner")
        assert d["action"] == "block" and "cron" in d["message"], tool
    assert r.store.peek_approval("start", str(qid)) is not None


def test_gate_failure_blocks_with_reasons(rig):
    d = rig.pre("home3d_start", {"queue_item_id": 999}, "s-owner")
    assert d["action"] == "block" and "999" in d["message"] and "not found" in d["message"]

    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.start(q1)
    rig.store.grant_approval("start", str(q2), "Owner")
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "busy" in d["message"]
    assert rig.store.peek_approval("start", str(q2)) is not None  # not used up by a blocked attempt

    d = rig.pre("home3d_stop", {"action": "resume"}, "s-owner")
    assert d["action"] == "block" and "not paused" in d["message"]


def test_plate_not_verified_blocks_start_and_clear(rig):
    q1, q2 = rig.queue_job(), rig.queue_job()
    rig.be.set_scenario("eject_miss")  # the push misses: the part stays on the plate
    rig.be.start(q1)
    rig.be.advance(600)
    d = rig.pre("home3d_start", {"queue_item_id": q2}, "s-owner")
    assert d["action"] == "block" and "plate" in d["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "block" and "plate" in d["message"].lower()


def test_non_owner_is_told_to_ask_the_owner(rig):
    qid = rig.queue_job()
    for session in ("s-mum", "s-stranger"):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "block"
        assert hooks_mod.APPROVAL_MARKER in d["message"]
        assert f"/home3d approve start {qid}" in d["message"]
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum")
    assert d["action"] == "block" and "/home3d approve clear" in d["message"]


def test_owner_approval_token_allows_once(rig):
    qid = rig.queue_job()
    rig.store.grant_approval("start", str(qid), "Owner")
    assert rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum") is None
    assert rig.store.peek_approval("start", str(qid)) is None  # consumed
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert d["action"] == "block" and hooks_mod.APPROVAL_MARKER in d["message"]

    rig.store.grant_approval("clear_plate", "", "Owner")
    assert rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-mum") is None
    assert rig.store.peek_approval("clear_plate", "") is None


def test_jump_needs_its_own_approval(rig):
    qid = rig.queue_job()
    rig.store.grant_approval("start", str(qid), "Owner")
    d = rig.pre("home3d_start", {"queue_item_id": qid, "allow_jump": True}, "s-mum")
    assert d["action"] == "block" and f"/home3d approve start {qid} jump" in d["message"]
    assert rig.store.peek_approval("start", str(qid)) is not None
    rig.store.grant_approval("start", f"{qid}+jump", "Owner")
    assert rig.pre("home3d_start", {"queue_item_id": qid, "allow_jump": True}, "s-mum") is None


def test_owner_and_local_sessions_get_the_human_approval_gate(rig):
    qid = rig.queue_job()
    keys = set()
    for session in ("s-owner", "s-owner", "", "cli-session-without-sender"):
        d = rig.pre("home3d_start", {"queue_item_id": qid}, session)
        assert d["action"] == "approve"
        assert f"#{qid}" in d["message"] and "Mum" in d["message"] and "auto-eject" in d["message"]
        assert d["rule_key"].startswith(f"home3d:home3d_start:{qid}:")
        keys.add(d["rule_key"])
    assert len(keys) == 4  # unique: an "always" answer never sticks
    d = rig.pre("home3d_clear_plate", {"action": "confirm"}, "s-owner")
    assert d["action"] == "approve" and "plate" in d["message"] and d["rule_key"].startswith("home3d:home3d_clear_plate:-:")


def test_voice_request_is_noted_in_the_approval_prompt(rig):
    qid = rig.queue_job()
    rid = rig.store.add_request(requester="Mum", text="kutu", channel="voice")
    rig.store.update_request(rid, queue_item_id=qid)
    d = rig.pre("home3d_start", {"queue_item_id": qid}, "s-owner")
    assert d["action"] == "approve" and "voice" in d["message"]


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


def test_hooks_never_raise_on_garbage(rig):
    pre, post, llm = rig.h["pre_tool_call"], rig.h["post_tool_call"], rig.h["pre_llm_call"]
    assert pre() is None and pre(None, None) is None and pre(123, "x") is None and pre(["home3d_start"], {}) is None
    for args in ("garbage", None, {"queue_item_id": "abc"}, {"queue_item_id": True}, {"queue_item_id": -3}):
        d = pre("home3d_start", args, session_id="s-owner")
        assert d["action"] == "block" and "queue_item_id" in d["message"]
    assert pre("home3d_stop", {"action": None}) is None
    assert pre("home3d_stop", "resume") is None  # not a dict: not a resume
    for kw in ({}, {"session_id": None, "user_message": None, "sender_id": None},
               {"session_id": 5, "user_message": [{"type": "image_url"}, "x", 3], "sender_id": 42, "platform": None},
               {"session_id": "s", "user_message": {"odd": 1}, "is_first_turn": "yes"}):
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
    long = rig.h["pre_llm_call"](session_id="new-session", user_message="ok", platform="whatsapp",
                                 sender_id=STRANGER, is_first_turn=False)["context"]
    assert len(long) <= hooks_mod.CONTEXT_MAX and "stale" in long and "not in the household" in long

    local = rig.h["pre_llm_call"](session_id="cli-1", user_message="status?", platform="cli", sender_id="",
                                  is_first_turn=True)["context"]
    assert "Owner (owner, local session)" in local


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
