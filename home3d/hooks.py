"""Hermes hooks: safety + approvals before printer actions, "who is speaking" context, and an audit trail.

``pre_tool_call``   gates ``home3d_start``, ``home3d_clear_plate`` (confirm) and ``home3d_stop`` (resume):
                    never from cron, never when the safety gate fails, a non-owner needs the owner's
                    ``/home3d approve ...``, everyone else gets Hermes' human-approval prompt.
``pre_llm_call``    remembers session -> sender and injects a short context (persona, speaker, printer state
                    from the last watcher pass, open requests, skill reminder). No network.
``post_tool_call``  audits every ``home3d_*`` call and logs approval friction as a human-needed moment.

Every hook is defensive: it never raises. ``pre_tool_call`` fails closed (blocks) on internal errors.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Callable, Optional

from .backends.base import PAUSE, BackendError
from .gates import clear_plate_gate, describe, start_gate

logger = logging.getLogger(__name__)

GATED_TOOLS = ("home3d_start", "home3d_clear_plate", "home3d_stop")
APPROVAL_MARKER = "owner approval needed"
APPROVAL_TTL_S = 15 * 60
SKILL_REF = "home-3d-workshop:household-printing"
CONTEXT_MAX = 900
WATCHER_STALE_S = 10 * 60
MOMENT_DEDUPE_S = 10 * 60
LOCAL_PLATFORMS = {"", "cli", "tui", "local", "desktop", "acp"}
_LANG_NAMES = {"tr": "Turkish", "en": "English"}
# a turn that is probably about printing gets the full context (persona, open requests, skill reminder)
_RELEVANT = re.compile(
    r"3d|3 ?boyut|bask[ıi]|bas(ar|sana|abilir|al[ıi]m|maya|t[ıi]r)|print|yaz[ıi]c[ıi]|makerworld|model|"
    r"filament|tabla|plate|kuyruk|queue|eject|d[üu]ş[üu]r|stl|3mf|slice|dilimle|kutu|vazo|onay|approve",
    re.IGNORECASE)


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
    return int(f) if f == int(f) and f > 0 else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "evet"}


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


def approve_command(action: str, qid: Optional[int] = None, jump: bool = False) -> str:
    """The ``/home3d approve ...`` text the owner sends for ``action``."""
    if action == "start":
        return f"/home3d approve start {qid if qid is not None else '<id>'}" + (" jump" if jump else "")
    return "/home3d approve " + ("clear" if action == "clear_plate" else action)


def approval_target(action: str, qid: Optional[int] = None, jump: bool = False) -> str:
    """Store target of an approval: the queue item for start (``"7"`` / ``"7+jump"``), '' otherwise."""
    if action != "start":
        return ""
    return f"{qid}+jump" if jump else str(qid)


def _own_item_ids(store) -> set[int]:
    return {int(j["queue_item_id"]) for j in store.jobs(limit=1000) if j.get("queue_item_id") is not None}


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

    def _decide(self, action: str, tool: str, args: dict, session_id: str) -> Optional[dict]:
        rt = self.rt
        if rt.in_cron():
            return _block(f"BLOCKED: {tool} never runs from a scheduled (cron) job; a person must be present.")
        qid, jump = None, False
        if action == "start":
            qid = _qid(args.get("queue_item_id"))
            if qid is None:
                return _block("BLOCKED: home3d_start needs a numeric queue_item_id (see home3d_queue action=list).")
            jump = _truthy(args.get("allow_jump"))
        try:
            ok, why, summary = self._gate(action, qid, jump)
        except BackendError as e:
            return _block(f"BLOCKED: printer not reachable, {tool} was not run: {e}")
        if not ok:
            return _block(f"BLOCKED: {why}")

        store, s = rt.store, rt.settings
        target = approval_target(action, qid, jump)
        if store.consume_approval(action, target) is not None:
            store.add_event("approval_used", "", {"action": action, "target": target, "tool": tool})
            return None

        sender = rt.sender_id(session_id)
        if sender and not s.is_owner(sender):
            person = s.person_for(sender)
            who = person.name if person else "this sender"
            owner = s.owner_name or "the owner"
            hint = "" if s.owner_ids else " (no owner_ids are configured yet)"
            return _block(f"BLOCKED: {APPROVAL_MARKER}: {who} is not the owner{hint}. {owner} sends "
                          f"`{approve_command(action, qid, jump)}` (valid {APPROVAL_TTL_S // 60} min, single use); "
                          f"tell {who} you asked {owner}.")
        rule_key = f"home3d:{tool}:{target or '-'}:{int(time.time())}:{uuid.uuid4().hex[:8]}"
        return {"action": "approve", "message": summary, "rule_key": rule_key}

    def _gate(self, action: str, qid: Optional[int], jump: bool) -> tuple[bool, str, str]:
        """(ok, English reasons when blocked, human summary for the approval prompt)."""
        rt = self.rt
        be, store, s = rt.backend, rt.store, rt.settings
        status = be.status()
        if action == "resume":
            if status.state != PAUSE:
                return False, f"the printer is not paused (state {status.state}): nothing to resume", ""
            hms = ", ".join(h.code for h in status.blocking_hms)
            summary = (f"Resume the paused 3D print \"{status.job_name}\" ({status.progress:.0f}%)."
                       + (f" HMS still active: {hms}." if hms else ""))
            return True, "", summary
        queue = be.queue()
        try:
            plate = be.check_plate()
        except BackendError:
            plate = None  # the gate blocks on an unknown plate
        if action == "clear_plate":
            auto = [q for q in queue if q.is_pending and not q.manual_start]
            gate = clear_plate_gate(status, plate, in_cron=rt.in_cron(), cool_temp_c=s.eject_cool_temp_c,
                                    auto_start_pending=auto)
            if not gate.ok:
                return False, describe(gate, "en"), ""
            bed = f"bed {status.bed_temp:.0f} C" if status.bed_temp is not None else "bed temperature unknown"
            diff = f", diff {plate.difference_pct:g}%" if plate and plate.difference_pct is not None else ""
            return True, "", (f"Mark the 3D printer plate clear ({bed}, camera: empty{diff}). "
                              "The printer manager may then start the next job.")
        req = store.request_for_queue_item(qid)
        gate = start_gate(status, queue, qid, plate=plate, in_cron=rt.in_cron(), own_item_ids=_own_item_ids(store),
                          allow_jump=jump, voice_request=bool(req and req.get("channel") == "voice"))
        if not gate.ok:
            return False, describe(gate, "en"), ""
        return True, "", self._start_summary(qid, queue, gate.warnings)

    def _start_summary(self, qid: int, queue: list, warnings: list[str]) -> str:
        store = self.rt.store
        item = next((q for q in queue if q.id == qid), None)
        job = store.get_job(qid) or {}
        meta = (store.kv_get(f"slice:{job['sliced_file_id']}") or {}) if job.get("sliced_file_id") else {}
        name = (item.name if item else "") or job.get("name") or f"#{qid}"
        for suf in (".gcode.3mf", ".3mf"):
            if name.lower().endswith(suf):
                name = name[: -len(suf)]
        bits = [x for x in (_minutes(item.print_time_s) if item and item.print_time_s else "",
                            f"{meta['grams']:.0f} g" if isinstance(meta.get("grams"), (int, float)) else "",
                            "auto-eject" if job.get("eject_planned") else "no auto-eject") if x]
        who = job.get("requester") or "the household"
        out = f"Start 3D print #{qid} \"{name}\" for {who} ({', '.join(bits)}). Plate verified empty."
        if warnings:
            out += " Note: " + "; ".join(warnings) + "."
        return out

    # -- pre_llm_call --
    def pre_llm_call(self, session_id: Any = "", user_message: Any = None, platform: Any = "", sender_id: Any = "",
                     is_first_turn: Any = False, **kw: Any) -> Optional[dict]:
        try:
            text = self._context(str(session_id or ""), user_message, str(platform or ""), str(sender_id or ""),
                                 bool(is_first_turn))
            return {"context": text} if text else None
        except Exception as e:
            logger.debug("home3d pre_llm_call failed: %s", e)
            return None

    def _context(self, session_id: str, user_message: Any, platform: str, sender: str, first: bool) -> str:
        rt = self.rt
        s, store = rt.settings, rt.store
        if session_id and sender:
            store.remember_sender(session_id, sender, platform)
        person = s.person_for(sender) if sender else None
        if person:
            role = "owner" if person.role == "owner" else person.role or "family"
            speaker = f"Speaking: {person.name} ({role}); address them as \"{person.greeting_name}\"."
        elif sender:
            speaker = "Speaking: someone not in the household list (no approvals; ask who they are if needed)."
        elif platform.lower() in LOCAL_PLATFORMS:
            speaker = f"Speaking: {s.owner_name} (owner, local session)."
        else:
            speaker = "Speaking: unknown sender."
        printer, state_key = self._printer_state(store)
        key = session_id or "-"
        changed = self._printer_line.get(key) != state_key
        self._printer_line[key] = state_key
        if len(self._printer_line) > 500:
            self._printer_line.clear()
        full = first or changed or bool(_RELEVANT.search(_message_text(user_message)))
        if not full:  # later small-talk turns: who is speaking is enough (the rest is in the history)
            return f"[home-3d-workshop · {s.persona_name}] {speaker}"
        lang = _LANG_NAMES.get(s.language, "English")
        lines = [f"[home-3d-workshop] You are {s.persona_name}, this household's 3D-printing helper. "
                 f"Reply in {lang}, short and warm.", speaker, printer]
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
            self._audit(tool_name, args if isinstance(args, dict) else {}, result, str(session_id or ""), kw)
        except Exception as e:
            logger.debug("home3d post_tool_call failed: %s", e)
        return None

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


__all__ = ["make_hooks", "gated_action", "approve_command", "approval_target", "APPROVAL_MARKER",
           "APPROVAL_TTL_S", "GATED_TOOLS", "SKILL_REF"]
