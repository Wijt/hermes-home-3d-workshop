"""End to end on the simulator, through the same surfaces Hermes uses.

Every agent tool call goes ``pre_tool_call`` -> handler -> ``post_tool_call`` (like ``model_tools``), the owner
approves with ``/home3d approve`` or the store, and the zero-token watcher (``watcher.run_once``) is the only
thing that notices the finish, the eject and the plate. Nothing is sent: ``deliver=False`` writes the outbox.
"""

from __future__ import annotations

import json

import pytest

from home3d_ws.home3d import watcher
from home3d_ws.home3d.backends.simulator import SimulatorBackend
from home3d_ws.home3d.commands import make_command
from home3d_ws.home3d.config import Settings
from home3d_ws.home3d.hooks import APPROVAL_MARKER, make_hooks
from home3d_ws.home3d.notify import read_outbox
from home3d_ws.home3d.runtime import Runtime
from home3d_ws.home3d.store import Store
from home3d_ws.home3d.tools import build_tools

OWNER, MUM, DAD = "owner-id@s.whatsapp.net", "mum-id@s.whatsapp.net", "dad-id@s.whatsapp.net"
OWNER_TARGET, FAMILY_TARGET = "whatsapp:<owner-chat>@g.us", "whatsapp:<family-group>@g.us"
FLOWER_BOX, COASTER = 1440000, 1440007  # simulator catalogue: 136 min box, 45 min coaster


class Source:  # what the gateway passes to a slash command
    def __init__(self, user_id):
        self.user_id, self.chat_id, self.platform = user_id, "<group>@g.us", "whatsapp"


class House:
    """One household: settings, simulated printer, store and the Hermes surfaces bound to one Runtime."""

    def __init__(self, lang: str = "tr"):
        self.settings = Settings(
            backend="simulator", language=lang, persona_name="Mıstık", owner_name="Sam", owner_ids=[OWNER],
            household=[{"id": MUM, "name": "Mum", "address_as": "Anneciğim"},
                       {"id": DAD, "name": "Dad", "address_as": "Babacığım"}],
            owner_target=OWNER_TARGET, family_target=FAMILY_TARGET)
        self.be = SimulatorBackend()
        self.store = Store()
        self.rt = Runtime(None, settings=self.settings, store=self.store, backend=self.be)
        self.tools = {name: handler for name, _schema, handler in build_tools(self.rt)}
        self.hooks = make_hooks(self.rt)
        self.cmd = make_command(self.rt)
        self.events: list[dict] = []
        self.prompts: list[dict] = []

    # -- Hermes emulation --
    def turn(self, session: str, sender: str, text: str) -> str:
        r = self.hooks["pre_llm_call"](session_id=session, user_message=text, platform="whatsapp",
                                       sender_id=sender, is_first_turn=True)
        return (r or {}).get("context", "")

    def call(self, name: str, args: dict, session: str) -> dict:
        d = self.hooks["pre_tool_call"](tool_name=name, args=args, task_id="t", session_id=session)
        if d and d.get("action") == "block":
            self.hooks["post_tool_call"](tool_name=name, args=args, result=json.dumps({"error": d["message"]}),
                                         session_id=session)
            return {"ok": False, "blocked": True, "error": d["message"]}
        if d and d.get("action") == "approve":  # Hermes asks the person at the keyboard; they approve once
            assert d["message"] and d["rule_key"].startswith(f"home3d:{name}:")
            self.prompts.append(d)
        raw = self.tools[name](args, session_id=session, task_id="t")
        self.hooks["post_tool_call"](tool_name=name, args=args, result=raw, session_id=session)
        out = json.loads(raw)
        assert isinstance(out, dict) and "ok" in out
        return out

    # -- time + watcher --
    def watch(self) -> list[dict]:
        res = watcher.run_once(self.settings, self.be, self.store, deliver=False)
        self.events += res
        return res

    def run_until(self, kinds: set[str], step_min: float = 5, max_steps: int = 120) -> list[str]:
        seen: list[str] = []
        for _ in range(max_steps):
            self.be.advance(step_min)
            seen += [r["kind"] for r in self.watch()]
            if kinds & set(seen):
                return seen
        raise AssertionError(f"none of {sorted(kinds)} after {max_steps} steps; saw {seen}")

    def kinds(self) -> list[str]:
        return [e["kind"] for e in self.events]

    # -- the request flow, as the agent runs it --
    def request(self, session: str, sender: str, model_id: int, text: str) -> int:
        self.turn(session, sender, text)
        found = self.call("home3d_find_models", {"urls": [f"https://makerworld.com/en/models/{model_id}"]}, session)
        assert found["ok"] and found["cards"][0]["a1_profiles"], found
        imp = self.call("home3d_import", {"model_id": model_id, "request_text": text, "channel": "voice"}, session)
        assert imp["ok"], imp
        sl = self.call("home3d_slice", {"library_file_id": imp["library_file_id"], "material": "PLA",
                                        "colour": "white", "request_id": imp["request_id"]}, session)
        assert sl["ok"] and sl["eject"]["planned"] is True, sl
        q = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl["sliced_file_id"],
                                       "request_id": imp["request_id"]}, session)
        assert q["ok"] and q["manual_start"] is True and q["eject_planned"] is True, q
        return q["queue_item_id"]


@pytest.fixture
def house():
    return House()


def test_request_to_plate_clear_full_loop(house):
    h = house
    assert h.watch() == []  # baseline pass is silent

    # Mum asks by voice; pre_llm_call knows who is speaking
    ctx = h.turn("s-mum", MUM, "Mıstık, çiçekler için küçük bir kutu basar mısın?")
    assert "Mum" in ctx and "Anneciğim" in ctx and "household-printing" in ctx

    qid = h.request("s-mum", MUM, FLOWER_BOX, "çiçek kutusu")
    job = h.store.get_job(qid)
    assert job["requester"] == "Mum" and job["eject_planned"] == 1
    req = h.store.request_for_queue_item(qid)
    assert req["requester"] == "Mum" and req["channel"] == "voice" and req["status"] == "queued"

    # Mum's chat cannot start it: the hook blocks before the handler runs
    blocked = h.call("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert blocked["blocked"] and APPROVAL_MARKER in blocked["error"] and f"approve start {qid}" in blocked["error"]
    assert h.be.status().state == "IDLE"
    assert h.store.human_needed(kind="approve_start")  # approval friction is a logged moment

    # the owner grants the approval; the next agent call in Mum's chat consumes it
    h.store.grant_approval("start", str(qid), "Sam", ttl_s=900)
    started = h.call("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert started["ok"] and started["requester"] == "Mum" and started["eject_planned"] is True, started
    assert h.store.peek_approval("start", str(qid)) is None  # single use
    assert h.be.status().state in ("PREPARE", "RUNNING")
    assert h.store.get_job(qid)["state"] == "printing"

    # Dad asks for a coaster meanwhile: queued behind Mum's job
    qid2 = h.request("s-dad", DAD, COASTER, "bardak altlığı")

    # zero-token watcher: finish (owner only, the family hears the eject outcome) ...
    h.run_until({"finished"})
    fin = next(e for e in h.events if e["kind"] == "finished")
    assert fin["owner_text"] and not fin["family_text"] and fin["owner_media"]
    assert h.store.get_job(qid)["state"] == "finished"

    # ... bed cools, the end G-code pushes the part off, the camera verifies the plate
    seen = h.run_until({"finished_ejected"})
    assert "plate_not_clear" not in seen and "eject_unverified" not in seen
    ej = next(e for e in h.events if e["kind"] == "finished_ejected")
    assert "Anneciğim" in ej["family_text"] and "Flower gift box" in ej["family_text"]
    assert h.be.check_plate().is_empty is True
    assert (h.store.kv_get("watcher") or {})["plate_state"]["phase"] == "clear"
    assert h.store.get_job(qid)["state"] == "cleared" and h.store.get_job(qid)["outcome"] == "ejected"
    assert h.store.get_request(req["id"])["status"] == "done"
    assert not h.store.human_needed(kind="remove_part")

    # plate clear + manual job waiting -> the owner is told (never auto-started)
    if "ready_next" not in h.kinds():
        h.run_until({"ready_next"})
    ready = next(e for e in h.events if e["kind"] == "ready_next")
    assert f"/home3d approve start {qid2}" in ready["owner_text"] and not ready["family_text"]
    assert h.be.status().state == "FINISH"

    # outbox: owner (technical, photo) and family (by name) messages, nothing sent for real
    box = read_outbox(limit=0)
    owner = [r for r in box if r["audience"] == "owner"]
    family = [r for r in box if r["audience"] == "family"]
    assert owner and family
    assert all(r["target"] == OWNER_TARGET for r in owner) and all(r["target"] == FAMILY_TARGET for r in family)
    assert any(r.get("media") for r in owner)
    assert len(family) == 1 and "Anneciğim" in family[0]["text"]
    assert not any("Babacığım" in r["text"] for r in family)  # Dad's job has not printed yet
    assert all(r["dry_run"] for r in box)  # deliver=False: outbox only, nothing went through hermes send

    # the owner starts the next job with the slash command (no model call)
    reply = h.cmd(f"approve start {qid2}", source=Source(OWNER), session_id="s-owner", platform="whatsapp")
    assert reply.startswith("▶️") and f"#{qid2}" in reply, reply
    assert h.be.status().state in ("PREPARE", "RUNNING")
    assert h.store.events(kind="approval_granted")


def test_eject_miss_three_times_becomes_one_upgrade_proposal(house):
    h = house
    h.watch()
    h.be.set_scenario("eject_miss")  # every push misses from now on
    for i in range(1, 4):
        qid = h.request("s-mum", MUM, COASTER, f"bardak altlığı {i}")
        # the owner at the keyboard (local session: no messaging sender) gets Hermes' approval prompt
        started = h.call("home3d_start", {"queue_item_id": qid}, "owner-local")
        assert started["ok"], started
        assert h.prompts and f"#{qid}" in h.prompts[-1]["message"]

        seen = h.run_until({"plate_not_clear"})
        assert "finished_ejected" not in seen
        miss = [e for e in h.events if e["kind"] == "plate_not_clear"][-1]
        assert "Anneciğim" in miss["family_text"] and miss["owner_text"]
        assert len(h.store.human_needed(kind="remove_part")) == i
        assert h.be.check_plate().is_empty is False

        # a person takes the coaster off; the watcher sees the empty plate on its next check
        h.be.human_clears_plate()
        h.run_until({"plate_clear"})
        assert h.store.get_job(qid)["state"] == "cleared" and h.store.get_job(qid)["outcome"] == "removed"

        proposals = [e for e in h.events if e["kind"] == "upgrade_proposed"]
        assert len(proposals) == (1 if i == 3 else 0)

    rows = h.store.human_needed(kind="remove_part")
    assert len(rows) == 3 and all(r["source"] == "watcher" and r["job_name"] for r in rows)
    ups = h.store.upgrades()
    assert len(ups) == 1
    up = ups[0]
    assert up["kind"] == "remove_part" and up["status"] == "proposed" and up["evidence"] == 3
    assert "2335000" in up["model_ref"]

    note = next(e for e in h.events if e["kind"] == "upgrade_proposed")
    assert note["owner_text"] and not note["family_text"]
    upgrade_msgs = [r for r in read_outbox(limit=0) if "2335000" in r["text"]]
    assert len(upgrade_msgs) == 1 and upgrade_msgs[0]["audience"] == "owner"

    # evaluating again does not duplicate it; the owner moves it along through the tool
    assert h.call("home3d_upgrades", {"action": "evaluate"}, "owner-local")["new_proposals"] == []
    acc = h.call("home3d_upgrades", {"action": "accept", "upgrade_id": up["id"]}, "owner-local")
    assert acc["ok"] and acc["status"] == "accepted"
    denied = h.call("home3d_upgrades", {"action": "installed", "upgrade_id": up["id"]}, "s-mum")
    assert not denied["ok"]  # only the owner decides
    assert len(h.store.upgrades()) == 1
