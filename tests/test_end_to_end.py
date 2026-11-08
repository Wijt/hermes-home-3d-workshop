"""End to end on the simulator, through the same surfaces Hermes uses.

Every agent tool call goes ``pre_tool_call`` -> handler -> ``post_tool_call`` (like ``model_tools``). A gated
call (start, clear-plate confirm, resume) only runs when the hook approved it for an owner session and issued a
single-use pass that the handler uses up; the owner can also run it with ``/home3d approve`` (its own pass). A
direct handler call (``ctx.dispatch_tool`` skips the hooks) and a stored approval authorise nothing. The
zero-token watcher (``watcher.run_once``) is the only thing that notices the finish, the eject and the plate.
Nothing is sent: ``deliver=False`` writes the outbox.
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
    def turn(self, session: str, sender: str, text: str, platform: str = "whatsapp") -> str:
        r = self.hooks["pre_llm_call"](session_id=session, user_message=text, platform=platform,
                                       sender_id=sender, is_first_turn=True)
        return (r or {}).get("context", "")

    def local_turn(self, session: str, text: str = "3D printer status?") -> str:
        """The owner at the keyboard: a classic CLI session has no messaging sender."""
        return self.turn(session, "", text, platform="cli")

    def direct(self, name: str, args: dict, session: str) -> dict:
        """What ``ctx.dispatch_tool`` from another plugin does: the handler without any hook."""
        return json.loads(self.tools[name](args, session_id=session, task_id="t"))

    def slash(self, text: str, sender: str = OWNER, session: str = "s-owner") -> str:
        return self.cmd(text, source=Source(sender), session_id=session, platform="whatsapp")

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

    def last(self, kind: str) -> dict:
        return [e for e in self.events if e["kind"] == kind][-1]

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


def owner_message_with(text: str) -> str:
    """The newest owner message in the outbox that contains ``text`` (what the owner really receives)."""
    return next(r["text"] for r in reversed(read_outbox(limit=0)) if r["audience"] == "owner" and text in r["text"])


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

    # nothing gets around the hook: a direct handler call (ctx.dispatch_tool) has no pass ...
    direct = h.direct("home3d_start", {"queue_item_id": qid}, "s-mum")
    assert direct["blocked"] and "no approval pass found" in direct["error"]
    # ... and an owner approval stored earlier no longer authorises an agent call
    h.store.grant_approval("start", str(qid), "Sam", ttl_s=900)
    assert h.call("home3d_start", {"queue_item_id": qid}, "s-mum")["blocked"]
    assert h.be.status().state == "IDLE" and not h.prompts

    # the owner asks in his own chat: Hermes' prompt (approved once) -> single-use pass -> the handler starts it
    h.turn("s-owner", OWNER, "Mıstık, start Mum's flower box")
    started = h.call("home3d_start", {"queue_item_id": qid}, "s-owner")
    assert started["ok"] and started["requester"] == "Mum" and started["eject_planned"] is True, started
    prompt = h.prompts[-1]["message"]
    assert f"#{qid}" in prompt and "camera checks the plate right before" in prompt and "verified" not in prompt
    assert h.store.consume_pass("home3d_start", str(qid), "s-owner") is False  # the pass was used up
    assert h.be.status().state in ("PREPARE", "RUNNING")
    assert h.store.get_job(qid)["state"] == "printing"

    # Dad asks for a coaster meanwhile: queued behind Mum's job
    qid2 = h.request("s-dad", DAD, COASTER, "bardak altlığı")

    # zero-token watcher: the end G-code cools the bed and pushes the part off while the printer still says
    # RUNNING (the real A1 order); at FINISH the camera looks at once. One owner message: the finish facts, then
    # the camera's opinion with a fresh plate photo; the family hears the outcome with the last-layer photo.
    seen = h.run_until({"finished"})
    assert "plate_not_clear" not in seen and "eject_unverified" not in seen
    fin, ej = h.last("finished"), h.last("finished_ejected")
    assert fin["owner_text"] and not fin["family_text"]
    assert "Flower gift box" in fin["owner_text"]  # the owner sees the file name
    assert ej["owner_media"] and ej["family_media"] and ej["owner_media"] != ej["family_media"]
    assert ej["family_text"] == '✅ Anneciğim, "çiçek kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin.'
    assert "kameraya göre tabla boş" in ej["owner_text"]
    assert h.be.check_plate().is_empty is True
    assert (h.store.kv_get("watcher") or {})["plate_state"]["phase"] == "clear"
    assert h.store.get_job(qid)["state"] == "cleared" and h.store.get_job(qid)["outcome"] == "ejected"
    assert h.store.get_request(req["id"])["status"] == "done"
    assert not h.store.human_needed(kind="remove_part")

    # plate clear + our manual job waiting -> the owner is told, with a fresh photo (never auto-started)
    if "ready_next" not in h.kinds():
        h.run_until({"ready_next"})
    ready = h.last("ready_next")
    assert f"/home3d approve start {qid2}" in ready["owner_text"] and "jump" not in ready["owner_text"]
    assert not ready["family_text"] and ready["owner_media"]
    msg = owner_message_with(f"/home3d approve start {qid2}")  # one owner message: the camera line said once
    assert msg.lower().count("kameraya göre tabla boş") == 1, msg
    assert h.be.status().state == "FINISH"

    # outbox: owner (technical, photo) and family (by name) messages, nothing sent for real
    box = read_outbox(limit=0)
    owner = [r for r in box if r["audience"] == "owner"]
    family = [r for r in box if r["audience"] == "family"]
    assert owner and family
    assert all(r["target"] == OWNER_TARGET for r in owner) and all(r["target"] == FAMILY_TARGET for r in family)
    assert any(r.get("media") for r in owner)
    assert len(family) == 1 and "Anneciğim" in family[0]["text"] and "çiçek kutusu" in family[0]["text"]
    assert not any("Babacığım" in r["text"] for r in family)  # Dad's job has not printed yet
    assert all(r["dry_run"] for r in box)  # deliver=False: outbox only, nothing went through hermes send

    # the owner starts the next job with the slash command (no model call): its own pass, used at once
    assert h.slash(f"approve start {qid2}", MUM, "s-group").startswith("Sadece sahibi")
    reply = h.slash(f"approve start {qid2}")
    assert reply.startswith("▶️") and f"#{qid2}" in reply, reply
    assert h.be.status().state in ("PREPARE", "RUNNING")
    assert h.store.events(kind="approval_granted") and h.store.events(kind="approval_used")


def test_failed_print_needs_the_owners_plate_confirmation_before_the_next_start(house):
    h = house
    h.watch()
    h.local_turn("owner-local")
    h.be.set_scenario("fail")
    qid = h.request("s-mum", MUM, COASTER, "bardak altlığı")
    assert h.call("home3d_start", {"queue_item_id": qid}, "owner-local")["ok"]
    h.run_until({"failed"})
    h.be.set_scenario("ok")  # only this print fails
    failed = h.last("failed")
    assert failed["family_text"].startswith("⚠️ Anneciğim") and '"bardak altlığı"' in failed["family_text"]
    assert failed["owner_media"] and h.store.get_job(qid)["state"] == "failed"

    # someone takes the failed part off; the camera thinks the plate is empty, the owner is asked to confirm
    h.be.human_clears_plate()
    qid2 = h.request("s-dad", DAD, COASTER, "bardak altlığı 2")
    h.run_until({"plate_clear"})
    clear = h.last("plate_clear")
    assert "Kameraya göre tabla boş" in clear["owner_text"] and "/home3d approve clear" in clear["owner_text"]
    if "ready_next" not in h.kinds():
        h.run_until({"ready_next"})
    msg = owner_message_with(f"/home3d approve start {qid2}")
    assert msg.count("/home3d approve clear") == 1, msg  # asked once, not once per merged note

    # the camera alone is not enough after a failure: even the owner's start is blocked by the gate
    out = h.call("home3d_start", {"queue_item_id": qid2}, "owner-local")
    assert out["blocked"] and "last job failed" in out["error"] and h.be.status().state == "FAILED"
    # the owner looks and confirms the plate (command -> pass -> handler -> store.confirm_plate) ...
    reply = h.slash("approve clear")
    assert reply.startswith("✅"), reply
    assert h.store.plate_confirmed(h.be.status().job_name)
    # ... and the next start goes through the hook and the pass
    started = h.call("home3d_start", {"queue_item_id": qid2}, "owner-local")
    assert started["ok"], started
    assert h.be.status().state in ("PREPARE", "RUNNING")


def test_filament_runout_pause_resumes_only_with_the_owners_ack(house):
    h = house
    h.watch()
    h.turn("s-owner", OWNER, "start the coaster")
    h.be.set_scenario("pause_hms")
    qid = h.request("s-mum", MUM, COASTER, "bardak altlığı")
    assert h.call("home3d_start", {"queue_item_id": qid}, "s-owner")["ok"]
    h.run_until({"paused"})
    h.be.set_scenario("ok")  # the next print runs normally
    paused = h.last("paused")
    assert "filament bitti" in paused["family_text"] and '"bardak altlığı"' in paused["family_text"]
    owner = paused["owner_text"]
    assert "/home3d approve resume" in owner and "/home3d approve resume ack" in owner and "home3d_stop" not in owner
    assert h.store.human_needed(kind="filament_swap")

    # Mum cannot resume; the owner's resume is blocked while the printer error is active ...
    assert h.call("home3d_stop", {"action": "resume"}, "s-mum")["blocked"]
    out = h.call("home3d_stop", {"action": "resume"}, "s-owner")
    assert out["blocked"] and "resume ack" in out["error"] and h.be.status().state == "PAUSE"
    assert h.slash("approve resume").startswith("Yapılamadı")
    assert h.direct("home3d_stop", {"action": "resume", "ack_hms": True}, "s-owner")["blocked"]  # no pass
    # ... until the owner acknowledges it
    assert h.slash("approve resume ack").startswith("▶️")
    assert h.be.status().state == "RUNNING"
    ev = h.store.events(kind="resume_request")[0]
    assert "0700-2000-0002-0001" in ev["payload"]
    # anyone may still stop, without any approval
    stopped = h.call("home3d_stop", {"action": "stop", "reason": "spaghetti"}, "s-mum")
    assert stopped["ok"] and h.be.status().state == "FAILED"


def test_a_foreign_job_ahead_is_named_and_needs_an_explicit_jump(house):
    h = house
    h.watch()
    h.be.set_scenario("busy")  # a family member queued a job straight in the printer manager
    qid = h.request("s-dad", DAD, COASTER, "bardak altlığı")
    (ready,) = [r for r in h.watch() if r["kind"] == "ready_next"]
    text = ready["owner_text"]
    foreign = next(q for q in h.be.queue() if q.id != qid)
    assert f"/home3d approve start {qid} jump" in text and f"#{foreign.id}" in text
    assert f"approve start {foreign.id}" not in text and ready["owner_media"]
    assert h.watch() == []  # told once
    refused = h.slash(f"approve start {qid}")
    assert refused.startswith("Yapılamadı") and "başkasının işi" in refused and f"#{foreign.id}" in refused
    assert h.slash(f"approve start {qid} jump").startswith("▶️")
    assert h.be.status().state in ("PREPARE", "RUNNING")


def test_eject_miss_three_times_becomes_one_upgrade_proposal(house):
    h = house
    h.watch()
    h.local_turn("owner-local")  # the owner at the keyboard (classic CLI: no messaging sender)
    h.be.set_scenario("eject_miss")  # every push misses from now on
    for i in range(1, 4):
        qid = h.request("s-mum", MUM, COASTER, f"bardak altlığı {i}")
        # the local owner gets Hermes' approval prompt; the hook's pass lets the handler start it
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


# ---- fix round 2 ----------------------------------------------------------------------------------------
def test_a_family_start_request_reaches_the_owner_through_the_watcher(house):
    """cat/F2: the hook refuses Mum's start and records a request; the next watcher pass tells the owner once,
    with the exact command (and nothing starts by itself)."""
    h = house
    h.watch()
    h.local_turn("owner-local")
    dad = h.request("s-dad", DAD, COASTER, "bardak altlığı")
    assert h.call("home3d_start", {"queue_item_id": dad}, "owner-local")["ok"]
    h.be.advance(10)
    h.watch()
    qid = h.request("s-mum", MUM, FLOWER_BOX, "çiçek kutusu")
    assert h.call("home3d_start", {"queue_item_id": qid}, "s-mum")["blocked"]
    (a,) = [r for r in h.watch() if r["kind"] == "approval_request"]
    assert a["owner_text"].startswith(f'🙋 Mum #{qid} "Flower gift box" işinin başlatılmasını istiyor')
    assert a["owner_text"].endswith(f"/home3d approve start {qid}") and not a["family_text"]
    assert h.call("home3d_start", {"queue_item_id": qid}, "s-mum")["blocked"]  # asking again the same day ...
    assert not [r for r in h.watch() if r["kind"] == "approval_request"]  # ... is not a second message
    assert h.store.get_job(qid)["state"] == "queued"


def test_a_dispatch_the_printer_manager_rejects_is_told_to_the_owner(house):
    """hw/F2: the start is accepted, then the printer manager fails the item without starting it."""
    h = house
    h.watch()
    qid = h.request("s-mum", MUM, COASTER, "bardak altlığı")
    h.be.set_scenario("dispatch_fail")
    assert h.slash(f"approve start {qid}").startswith("▶️")  # Bambuddy accepted the start ...
    assert h.store.get_job(qid)["state"] == "printing"
    h.run_until({"start_failed"}, step_min=2)  # ... and then gave up on it
    sf = h.last("start_failed")
    assert "Başlatma gerçekleşmedi" in sf["owner_text"] and "MQTT" in sf["owner_text"] and not sf["family_text"]
    assert h.store.get_job(qid)["state"] == "start_failed" and h.be.status().state == "IDLE"
    assert h.store.request_for_queue_item(qid)["status"] == "start_failed"
    assert "finished" not in h.kinds() and "failed" not in h.kinds()


def _family_auto_item(h) -> int:
    from home3d_ws.home3d.backends.base import SliceOptions

    sliced = h.be.slice(1, SliceOptions(printer_preset="std"))  # a family member queues in the printer manager
    return h.be.queue_add(sliced.library_file_id, manual_start=False).id


def test_our_finish_hidden_by_a_family_auto_start_is_still_reported(house):
    """hw/F2, s5 shape on the simulator: the push runs inside the end G-code, FINISH comes, and the printer
    manager dispatches the family's auto-start item at once; no watcher pass ever sees our FINISH."""
    h = house
    h.watch()
    h.local_turn("owner-local")
    qid = h.request("s-mum", MUM, COASTER, "bardak altlığı")
    assert h.call("home3d_start", {"queue_item_id": qid}, "owner-local")["ok"]
    fam = _family_auto_item(h)
    seen = h.run_until({"finished"})
    assert "finished_ejected" not in seen and "plate_not_clear" not in seen
    fin = h.last("finished")
    assert fin["family_text"] == '✅ Anneciğim, "bardak altlığı" bitti.' and fin["family_media"]
    assert "Bitişini kaçırdım" in fin["owner_text"]
    assert h.store.get_job(qid)["state"] == "finished" and h.store.request_for_queue_item(qid)["status"] == "done"
    assert h.be.status().job_name == "Flower gift box"
    assert {q.id: q.status for q in h.be.queue()}[fam] == "printing"
    assert fam not in h.store.active_job_ids()  # the family's job is not the workshop's


def test_require_plate_clear_off_lets_a_family_job_start_on_a_missed_push(house):
    """R2-5: with Bambuddy's "Require plate clear" off, an auto-start item starts on a finished printer before any
    camera check, here on top of a part the push missed. The plugin cannot prevent it (doctor warns); the owner
    is told the plate was never checked."""
    h = house
    h.be.set_require_plate_clear(False)
    h.be.set_scenario("eject_miss")
    h.watch()
    h.local_turn("owner-local")
    qid = h.request("s-mum", MUM, COASTER, "bardak altlığı")
    assert h.call("home3d_start", {"queue_item_id": qid}, "owner-local")["ok"]
    _family_auto_item(h)
    h.run_until({"finished"})
    assert "tablayı kontrol edemedim" in h.last("finished")["owner_text"]
    assert h.be.status().job_name == "Flower gift box"  # started on top of the coaster
