"""Hermes hooks: safety + approvals before printer actions, "who is speaking" context, and an audit trail.

``pre_tool_call``   gates ``home3d_start``, ``home3d_clear_plate`` (confirm) and ``home3d_stop`` (resume), in this
                    order: never from cron, and never from a run nobody is present for (kanban worker, ``chat -q``,
                    ``-z``, ``--source tool``); never when the safety gate fails; an unknown sender (no household
                    identity, e.g. a subagent whose parent had none) and a non-owner are blocked with the owner's
                    ``/home3d approve ...`` command; only an owner session (a local CLI/TUI session counts when
                    ``local_is_owner``) gets Hermes' human-approval prompt, plus a single-use handler pass bound to
                    (tool, target, session). Stored approvals never authorise an agent call.
``pre_llm_call``    remembers session -> sender (local sessions as ``LOCAL_SENDER``, delegated children inherit the
                    parent's sender) and injects a short context for household / printing turns only. No network.
``post_tool_call``  audits every ``home3d_*`` call, drops a pass the handler did not use (denied or vetoed call)
                    and logs approval friction as a human-needed moment.

Every hook is defensive: it never raises. ``pre_tool_call`` fails closed (blocks) on internal errors.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .backends.base import BackendError
from .config import LOCAL_SENDER, norm_id
from .gates import Gate, clear_plate_gate, describe, person_can_overrule, printer_blocks, resume_gate, start_gate

logger = logging.getLogger(__name__)

GATED_TOOLS = ("home3d_start", "home3d_clear_plate", "home3d_stop")
TOOL_FOR_ACTION = {"start": "home3d_start", "clear_plate": "home3d_clear_plate", "resume": "home3d_stop"}
APPROVAL_MARKER = "owner approval needed"
PASS_TTL_S = 10 * 60  # covers Hermes' approval prompt (approvals.timeout, default 300 s)
APPROVE_ONCE_NOTE = "(Approve once: every printer action is asked again, 'always' does not carry over.)"
HMS_ACK_PREFIX = "hms_ack:"  # pass detail: the printer error codes the owner acknowledged for a resume
LIGHT_FLAG = "light_left_on"
APPROVAL_TTL_S = PASS_TTL_S  # back-compat name
SKILL_REF = "home-3d-workshop:household-printing"
CONTEXT_MAX = 900
WATCHER_STALE_S = 10 * 60
MOMENT_DEDUPE_S = 10 * 60
# Hermes v0.22.5 surfaces with a person at this machine: classic CLI ("cli"; "local" when the gateway hosts it, with
# sender "uid:<n>"), TUI, desktop, ACP editors. Not local: "" (no platform), "subagent", "cron", "batch", messaging.
LOCAL_PLATFORMS = frozenset({"cli", "tui", "local", "desktop", "acp"})
_LOCAL_UID = re.compile(r"^uid:\d+$")
_LANG_NAMES = {"tr": "Turkish", "en": "English"}
# a turn that is probably about printing (word-bounded so "boilerplate", "print(x)" or "model" in a coding chat do not
# count)
_RELEVANT = re.compile(
    r"\b3 ?d\b|3 ?boyut|bask[ıi]|\bbas(ar|sana|abilir|al[ıi]m|maya|t[ıi]r)|\bprint(er|ers|ing)\b|\b3d ?print|"
    r"yaz[ıi]c[ıi]|makerworld|bambu|filament|\btabla|\bbuild ?plate\b|kuyru[kğ]|\beject|d[üu]ş[üu]r|\bstl\b|"
    r"\b3mf\b|dilimle|\bkutu|\bvazo|home3d",
    re.IGNORECASE)
_FOLD = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g",
                       "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"})


# ---- helpers ------------------------------------------------------------------------------------------
def _block(message: str) -> dict:
    return {"action": "block", "message": message}


def _qid(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(str(value).strip().lstrip("#"))
    except ValueError:
        return None
    try:
        return int(f) if f == int(f) and f > 0 else None
    except (OverflowError, ValueError):  # inf / nan
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "evet"}


def _fold(text: str) -> str:
    return text.translate(_FOLD).casefold()


def gated_action(tool_name: Any, args: Any) -> Optional[tuple[str, str]]:
    """``(approval action, tool)`` when this call needs the owner, else None. Pure, never raises."""
    if not isinstance(tool_name, str) or tool_name not in GATED_TOOLS:
        return None
    a = args if isinstance(args, dict) else {}
    if tool_name == "home3d_start":
        return "start", tool_name
    action = str(a.get("action") or "").strip().lower()
    if tool_name == "home3d_clear_plate":
        return ("clear_plate", tool_name) if action == "confirm" else None
    return ("resume", tool_name) if action == "resume" else None


def approve_command(action: str, qid: Optional[int] = None, jump: bool = False, ack: bool = False) -> str:
    """The ``/home3d approve ...`` text the owner sends for ``action``."""
    if action == "start":
        return f"/home3d approve start {qid if qid is not None else '<id>'}" + (" jump" if jump else "")
    if action == "resume":
        return "/home3d approve resume" + (" ack" if ack else "")
    return "/home3d approve " + ("clear" if action == "clear_plate" else action)


def approval_target(action: str, qid: Optional[int] = None, jump: bool = False) -> str:
    """Target a pass is bound to: the queue item for start (``"7"`` / ``"7+jump"``), '' otherwise."""
    if action != "start":
        return ""
    return f"{qid}+jump" if jump else str(qid)


def hms_ack_detail(codes: Any) -> str:
    """Pass detail for a resume the owner approved despite printer errors ``codes`` (sorted, comma separated)."""
    clean = sorted({str(c).strip().upper() for c in (codes or []) if str(c).strip()})
    return HMS_ACK_PREFIX + ",".join(clean) if clean else ""


def acked_codes(detail: Any) -> set[str]:
    """The printer error codes a pass detail acknowledges (empty when none)."""
    d = str(detail or "")
    if not d.startswith(HMS_ACK_PREFIX):
        return set()
    return {c for c in d[len(HMS_ACK_PREFIX):].split(",") if c}


def is_local_platform(platform: Any) -> bool:
    return str(getattr(platform, "value", platform) or "").strip().lower() in LOCAL_PLATFORMS


def session_sender(sender_id: Any, platform: Any) -> str:
    """The sender to record for a turn: ``LOCAL_SENDER`` for a local surface without a messaging identity (or the
    gateway-hosted CLI's ``uid:<n>``), '' when unknown, else the raw id. A messaging id that is literally "local"
    is quarantined (``<platform>:local``) so it can never pass as the local owner."""
    raw = str(sender_id or "").strip()
    plat = str(getattr(platform, "value", platform) or "").strip().lower()
    local = plat in LOCAL_PLATFORMS
    if not raw:
        return LOCAL_SENDER if local else ""
    if local and _LOCAL_UID.match(raw.lower()):
        return LOCAL_SENDER
    if norm_id(raw) == LOCAL_SENDER:
        return f"{plat or 'unknown'}:{raw}"
    return raw


def _minutes(seconds: Any) -> str:
    try:
        m = round(float(seconds) / 60)
    except (TypeError, ValueError):
        return ""
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m} min"


def _result_dict(result: Any) -> dict:
    if isinstance(result, dict):
        return result
    if isinstance(result, (str, bytes)):
        try:
            val = json.loads(result)
            return val if isinstance(val, dict) else {"value": val}
        except ValueError:
            return {"text": str(result)[:500]}
    return {}


def _pretty(name: str) -> str:
    for suf in (".gcode.3mf", ".3mf", ".gcode"):
        if name.lower().endswith(suf):
            return name[: -len(suf)]
    return name


# ---- the shared gate (hook and /home3d approve) --------------------------------------------------------
@dataclass
class Evaluation:
    ok: bool
    action: str
    tool: str
    reason: str = ""  # English, why it is blocked ("" when ok)
    message: str = ""  # the same in the household language
    summary: str = ""  # approval prompt text when ok
    qid: Optional[int] = None
    jump: bool = False
    ack: bool = False
    target: str = ""
    gate: Optional[Gate] = None
    hms: list[str] = field(default_factory=list)

    @property
    def pass_detail(self) -> str:
        """What the pass records beyond the target: the printer errors the owner acknowledged for a resume."""
        return hms_ack_detail(self.hms) if self.action == "resume" and self.ack else ""


def evaluate(rt, action: str, args: Any) -> Evaluation:
    """Cron check + safety gate for one gated action. Used by ``pre_tool_call`` and ``/home3d approve`` so both
    decide the same way. Raises only on internal errors (callers fail closed); a backend error is a block."""
    a = args if isinstance(args, dict) else {}
    tool = TOOL_FOR_ACTION[action]
    ev = Evaluation(ok=False, action=action, tool=tool)
    lang = rt.settings.language
    if action == "start":
        ev.qid = _qid(a.get("queue_item_id"))
        if ev.qid is None:
            ev.reason = ev.message = "home3d_start needs a numeric queue_item_id (see home3d_queue action=list)."
            return ev
        ev.jump = _truthy(a.get("allow_jump"))
    if action == "resume":
        ev.ack = _truthy(a.get("ack_hms"))
    ev.target = approval_target(action, ev.qid, ev.jump)
    if rt.in_cron():
        ev.reason = ev.message = f"{tool} never runs from a scheduled (cron) job; a person must be present."
        return ev
    try:
        _gate(rt, ev)
    except BackendError as e:
        ev.ok, ev.summary = False, ""
        ev.reason = ev.message = f"printer not reachable, {tool} was not run: {e}"
        return ev
    if ev.gate is not None and not ev.gate.ok:
        ev.reason, ev.message = describe(ev.gate, "en"), describe(ev.gate, lang)
    return ev


def _gate(rt, ev: Evaluation) -> None:
    be, store, s = rt.backend, rt.store, rt.settings
    status = be.status()
    in_cron = rt.in_cron()
    if ev.action == "resume":
        gate = resume_gate(status, in_cron=in_cron, hms_acknowledged=ev.ack)
        ev.gate, ev.ok = gate, gate.ok
        ev.hms = [h.code for h in status.blocking_hms]
        if gate.ok:
            hms = ", ".join(ev.hms)
            ev.summary = (f"Resume the paused 3D print \"{_pretty(status.job_name)}\" ({status.progress:.0f}%)."
                          + (f" Printer error still active: {hms} (acknowledged by the owner)." if hms else ""))
        return
    queue = be.queue()
    plate, skipped = None, printer_blocks(status, ev.action)
    if not skipped:  # the printer already blocks: no camera check (it may switch the chamber light, ~12 s)
        try:
            plate = rt.plate_check(status=status)
        except BackendError:
            plate = None  # the gate blocks on an unknown plate
    diff = f" ({plate.difference_pct:g}% difference)" if plate is not None and plate.difference_pct is not None else ""
    light = (" Note: the chamber light could not be switched off again after the plate check."
             if plate is not None and LIGHT_FLAG in str(plate.message or "") else "")
    if ev.action == "clear_plate":
        auto = [q for q in queue if q.is_pending and not q.manual_start]
        gate = clear_plate_gate(status, plate, in_cron=in_cron, cool_temp_c=s.eject_cool_temp_c,
                                auto_start_pending=auto, person_confirms=True, plate_skipped=skipped)
        ev.gate, ev.ok = gate, gate.ok
        if gate.ok:
            bed = f"bed {status.bed_temp:.0f} C" if status.bed_temp is not None else "bed temperature unknown"
            camera = (f"the camera is NOT sure{diff}: you confirm it is clear yourself, look at the plate first"
                      if person_can_overrule(plate) else f"the camera thinks the plate is empty{diff}")
            ev.summary = (f"Mark the 3D printer plate clear ({bed}; {camera}). "
                          f"The printer manager may then start the next job.{light}")
        return
    req = store.request_for_queue_item(ev.qid)
    gate = start_gate(status, queue, ev.qid, plate=plate, in_cron=in_cron, own_item_ids=store.active_job_ids(),
                      allow_jump=ev.jump, voice_request=bool(req and req.get("channel") == "voice"),
                      plate_confirmed=store.plate_confirmed(status.job_name),
                      after_failure=_after_failure(store), plate_skipped=skipped)
    ev.gate, ev.ok = gate, gate.ok
    if gate.ok:
        ev.summary = _start_summary(store, ev.qid, queue, gate.warnings, diff, plate) + light


def _after_failure(store) -> bool:
    """A failed print nobody has confirmed the plate of since (``Store.unconfirmed_failure``); fails closed."""
    try:
        return store.unconfirmed_failure() is not None
    except Exception:
        return True


def _start_summary(store, qid: int, queue: list, warnings: list[str], diff: str, plate=None) -> str:
    item = next((q for q in queue if q.id == qid), None)
    job = store.get_job(qid) or {}
    meta = (store.kv_get(f"slice:{job['sliced_file_id']}") or {}) if job.get("sliced_file_id") else {}
    name = _pretty((item.name if item else "") or job.get("name") or f"#{qid}")
    bits = [x for x in (_minutes(item.print_time_s) if item and item.print_time_s else "",
                        f"{meta['grams']:.0f} g" if isinstance(meta.get("grams"), (int, float)) else "",
                        "auto-eject" if job.get("eject_planned") else "no auto-eject") if x]
    who = job.get("requester") or "the household"
    camera = (f"The camera is not sure{diff}; the owner confirmed the plate is clear." if person_can_overrule(plate)
              else f"The camera thinks the plate is empty{diff}.")
    out = f"Start 3D print #{qid} \"{name}\" for {who} ({', '.join(bits)}). {camera}"
    if warnings:
        out += " Note: " + "; ".join(warnings) + "."
    return out


# ---- the hooks ----------------------------------------------------------------------------------------
class _Hooks:
    def __init__(self, rt):
        self.rt = rt
        self._moments: dict[tuple[str, str], float] = {}
        self._printer_line: dict[str, str] = {}

    # -- pre_tool_call --
    def pre_tool_call(self, tool_name: Any = None, args: Any = None, task_id: str = "", session_id: str = "",
                      **kw: Any) -> Optional[dict]:
        try:
            g = gated_action(tool_name, args)
        except Exception:
            return None
        if g is None:
            return None
        try:
            return self._decide(g[0], str(tool_name), args if isinstance(args, dict) else {}, str(session_id or ""))
        except Exception as e:  # fail closed: never run a printer action we could not check
            logger.warning("home3d pre_tool_call failed for %s: %s", tool_name, e, exc_info=True)
            return _block(f"BLOCKED: home3d safety check failed ({type(e).__name__}: {e}); {tool_name} was not run.")

    def _decide(self, action: str, tool: str, args: dict, session_id: str) -> dict:
        rt = self.rt
        if not rt.in_cron() and rt.unattended():  # 1b. like cron: nobody is present to answer a prompt
            qid = _qid(args.get("queue_item_id")) if action == "start" else None
            cmd = approve_command(action, qid, _truthy(args.get("allow_jump")), ack=_truthy(args.get("ack_hms")))
            return _block(f"BLOCKED: {tool} needs a person present, and nobody is in this run (kanban worker, "
                          f"single-query `chat -q`, `-z` or a tool integration). The owner sends `{cmd}` from a chat "
                          "or terminal.")
        ev = evaluate(rt, action, args)  # 1. cron, 2. safety gate
        if not ev.ok:
            return _block(f"BLOCKED: {ev.reason}")
        s = rt.settings
        cmd = approve_command(action, ev.qid, ev.jump, ack=bool(ev.hms))
        owner = s.owner_name or "the owner"
        sender = rt.sender_id(session_id) if session_id else ""
        person = s.person_for(sender) if sender else None
        if person is None:  # 3a. no household identity: never ask this chat to approve itself
            why = ("this session has no known sender" if not sender else "this sender is not in the household list")
            return _block(f"BLOCKED: {APPROVAL_MARKER}: unknown sender ({why}). {owner} approves with `{cmd}` "
                          f"(runs it right away, nothing is stored); tell the person you asked {owner}.")
        if not s.is_owner(sender):  # 3b. a household member who is not the owner
            hint = "" if s.owner_ids else " (no owner_ids are configured yet)"
            return _block(f"BLOCKED: {APPROVAL_MARKER}: {person.name} is not the owner{hint}. {owner} sends "
                          f"`{cmd}` (runs it right away, nothing is stored); tell {person.name} you asked {owner}.")
        # 4. the owner: Hermes asks them (or auto-approves under their own yolo/smart settings) BEFORE the handler
        # runs; the handler then needs this single-use pass, so nothing but this very call can use it.
        rt.store.issue_pass(tool, ev.target, session_id, ttl_s=PASS_TTL_S, detail=ev.pass_detail)
        # unique per call: an "always" answer in Hermes' prompt can never pre-approve a later printer action (it
        # only adds an allowlist entry nothing will match again), so the prompt says to approve once
        rule_key = f"home3d:{tool}:{ev.target or '-'}:{int(time.time())}:{uuid.uuid4().hex[:8]}"
        return {"action": "approve", "message": f"{ev.summary} {APPROVE_ONCE_NOTE}", "rule_key": rule_key}

    # -- pre_llm_call --
    def pre_llm_call(self, session_id: Any = "", user_message: Any = None, platform: Any = "", sender_id: Any = "",
                     is_first_turn: Any = False, parent_session_id: Any = "", **kw: Any) -> Optional[dict]:
        try:
            text = self._context(str(session_id or ""), user_message, str(getattr(platform, "value", platform) or ""),
                                 str(sender_id or ""), bool(is_first_turn), str(parent_session_id or ""))
            return {"context": text} if text else None
        except Exception as e:
            logger.debug("home3d pre_llm_call failed: %s", e)
            return None

    def _record_sender(self, session_id: str, sender: str, platform: str, parent: str) -> str:
        """Record and return who speaks in this session ('' = unknown)."""
        store = self.rt.store
        who = session_sender(sender, platform)
        inherited = ""
        if not who and parent and parent != session_id:
            who = store.sender_for(parent)  # a delegate_task child (or a rotated session) speaks for its parent
            inherited = parent if who else ""
        if session_id:
            store.remember_sender(session_id, who, platform, inherited_from=inherited)
        return who

    def _context(self, session_id: str, user_message: Any, platform: str, sender: str, first: bool,
                 parent: str) -> str:
        rt = self.rt
        s, store = rt.settings, rt.store
        who = self._record_sender(session_id, sender, platform, parent)
        mode = s.inject_context
        if mode == "never":
            return ""
        person = s.person_for(who) if who else None
        if who == LOCAL_SENDER:
            speaker = (f"Speaking: {s.owner_name} (owner, local session)." if person else
                       "Speaking: a local session (not treated as the owner: local_is_owner is off).")
        elif person:
            role = "owner" if person.role == "owner" else person.role or "family"
            speaker = f"Speaking: {person.name} ({role}); address them as \"{person.greeting_name}\"."
        elif who:
            speaker = "Speaking: someone not in the household list (no approvals; ask who they are if needed)."
        else:
            speaker = "Speaking: unknown sender (no approvals)."
        printer, state_key = self._printer_state(store)
        key = session_id or "-"
        changed = self._printer_line.get(key) != state_key
        self._printer_line[key] = state_key
        if len(self._printer_line) > 500:
            self._printer_line.clear()
        msg = _message_text(user_message)
        relevant = bool(_RELEVANT.search(msg)) or bool(s.persona_name and _fold(s.persona_name) in _fold(msg))
        if mode == "always" or person is not None:
            full = first or changed or relevant
        elif relevant:
            full = True
        else:  # auto: an unknown sender with an unrelated message gets nothing at all
            return ""
        if not full:  # later small-talk turns: who is speaking is enough (the rest is in the history)
            return f"[home-3d-workshop · {s.persona_name}] {speaker}"
        lang = _LANG_NAMES.get(s.language, "English")
        lines = [f"[home-3d-workshop] For this household's 3D printing you are {s.persona_name}, their printing "
                 f"helper (reply about printing in {lang}, short and warm).", speaker, printer]
        mine = self._open_requests(store, person.name) if person else ""
        if mine:
            lines.append(mine)
        lines.append(f"For a printing request load skill {SKILL_REF} first. Starting a print or clearing "
                     "the plate needs the owner's approval: never promise a start.")
        text = "\n".join(lines)
        return text if len(text) <= CONTEXT_MAX else text[: CONTEXT_MAX - 1].rstrip() + "…"

    @staticmethod
    def _printer_state(store) -> tuple[str, str]:
        """(one line for the model, a key that changes only when the state/job/plate phase changes)."""
        w = store.kv_get("watcher") or {}
        if not isinstance(w, dict) or not w.get("state"):
            return "Printer: unknown (watcher not running; home3d_status reads it live).", "unknown"
        updated = w.get("updated")
        age = time.time() - float(updated) if isinstance(updated, (int, float)) else None
        bits = [str(w.get("state"))]
        if w.get("job_name") and w.get("state") not in ("IDLE",):
            bits.append(f"\"{str(w['job_name'])[:40]}\"")
        if w.get("state") in ("PREPARE", "RUNNING", "PAUSE") and isinstance(w.get("progress"), (int, float)):
            bits.append(f"{w['progress']:.0f}%")
            if w.get("layer") and w.get("total_layers"):
                bits.append(f"layer {w['layer']}/{w['total_layers']}")
        plate = w.get("plate_state") if isinstance(w.get("plate_state"), dict) else {}
        phase = plate.get("phase") if plate else ""
        when = f"{round(age / 60)} min ago" if age is not None else "time unknown"
        line = f"Printer ({when}): " + " ".join(bits) + (f"; plate: {phase}" if phase and phase != "idle" else "")
        if age is None or age > WATCHER_STALE_S:
            line += " (stale: check home3d_status)"
        return line + ".", f"{w.get('state')}|{w.get('job_name')}|{phase}"

    @staticmethod
    def _open_requests(store, name: str) -> str:
        rows = [r for r in store.requests(requester=name, limit=10)
                if r.get("status") in ("open", "queued", "printing")][:3]
        if not rows:
            return ""
        items = [f"#{r['id']} \"{str(r.get('text') or r.get('model_ref') or '?')[:40]}\" ({r['status']})" for r in rows]
        return f"{name}'s open requests: " + ", ".join(items) + "."

    # -- post_tool_call --
    def post_tool_call(self, tool_name: Any = None, args: Any = None, result: Any = None, session_id: Any = "",
                       **kw: Any) -> None:
        try:
            if not isinstance(tool_name, str) or not tool_name.startswith("home3d_"):
                return None
            a = args if isinstance(args, dict) else {}
            sid = str(session_id or "")
            self._drop_unused_pass(tool_name, a, sid)
            self._audit(tool_name, a, result, sid, kw)
        except Exception as e:
            logger.debug("home3d post_tool_call failed: %s", e)
        return None

    def _drop_unused_pass(self, tool: str, args: dict, session_id: str) -> None:
        """A pass the handler did not use (Hermes' prompt was denied / timed out, another plugin vetoed the call)
        must not outlive the call it was issued for."""
        g = gated_action(tool, args)
        if g is None or not session_id:
            return
        qid = _qid(args.get("queue_item_id")) if g[0] == "start" else None
        if g[0] == "start" and qid is None:
            return
        self.rt.store.consume_pass(tool, approval_target(g[0], qid, _truthy(args.get("allow_jump"))), session_id)

    def _audit(self, tool: str, args: dict, result: Any, session_id: str, kw: dict) -> None:
        rt = self.rt
        store = rt.store
        data = _result_dict(result)
        error = str(data.get("error") or kw.get("error_message") or "")
        ok = bool(data["ok"]) if "ok" in data else not error
        payload: dict = {"tool": tool, "ok": ok, "status": str(kw.get("status") or "")}
        if error:
            payload["error"] = error[:300]
        for k in ("action", "queue_item_id", "sliced_file_id", "library_file_id", "request_id", "upgrade_id"):
            v = args.get(k, data.get(k))
            if isinstance(v, (str, int, float, bool)) and v != "":
                payload[k] = v if not isinstance(v, str) else v[:60]
        sender = rt.sender_id(session_id) if session_id else ""
        if sender:
            payload["sender"] = sender
        store.add_event("tool", str(data.get("name") or "")[:120], payload)

        if tool in GATED_TOOLS and APPROVAL_MARKER in (error or json.dumps(data, ensure_ascii=False)):
            g = gated_action(tool, args)
            qid = _qid(args.get("queue_item_id"))
            target = f"{g[0] if g else tool}:{qid or ''}"
            now = time.time()
            last = self._moments.get((session_id, target))
            if last is not None and now - last < MOMENT_DEDUPE_S:
                return
            if len(self._moments) > 500:
                self._moments.clear()
            self._moments[(session_id, target)] = now
            from . import upgrades

            who = rt.requester_name(session_id, "") if session_id else ""
            upgrades.log_moment(store, "approve_start", f"{tool} {target} waited for the owner's approval",
                                who=who, source="agent")


def _message_text(msg: Any) -> str:
    if isinstance(msg, str):
        return msg[:2000]
    if isinstance(msg, list):  # multimodal turn: text parts only
        parts = [p.get("text", "") for p in msg if isinstance(p, dict) and isinstance(p.get("text"), str)]
        return " ".join(parts)[:2000]
    return ""


def make_hooks(rt) -> dict[str, Callable]:
    """``{"pre_tool_call", "post_tool_call", "pre_llm_call"}`` bound to the shared Runtime."""
    h = _Hooks(rt)
    return {"pre_tool_call": h.pre_tool_call, "post_tool_call": h.post_tool_call, "pre_llm_call": h.pre_llm_call}


__all__ = ["make_hooks", "gated_action", "approve_command", "approval_target", "evaluate", "Evaluation",
           "hms_ack_detail", "acked_codes", "HMS_ACK_PREFIX",
           "session_sender", "is_local_platform", "APPROVAL_MARKER", "APPROVAL_TTL_S", "PASS_TTL_S", "GATED_TOOLS",
           "LOCAL_PLATFORMS", "SKILL_REF", "TOOL_FOR_ACTION"]
