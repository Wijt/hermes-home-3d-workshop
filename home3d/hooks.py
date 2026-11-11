"""Hermes hooks: safety + approvals before printer actions, "who is speaking" context, and an audit trail.

``pre_tool_call``   gates ``home3d_start``, ``home3d_clear_plate`` (confirm) and ``home3d_stop`` (resume), in this
                    order (``gates.approval_refusal``, the same rule ``/home3d approve`` uses): never from a run
                    nobody is present for (cron, kanban worker, ``chat -q``, ``-z``, ``--source tool``:
                    ``Runtime.absent_reason``); an unknown sender (no household identity, e.g. a subagent whose
                    parent had none) and a non-owner are blocked with the owner's ``/home3d approve ...`` command
                    (a household member's ask is recorded as an approval request the watcher passes on to the
                    owner); never when the owner's message came in as a VOICE note (a typed confirmation is asked
                    for); never when the safety gate fails; only an owner session (a local CLI/TUI session counts
                    when ``local_is_owner``) gets Hermes' human-approval prompt, plus a single-use handler pass
                    bound to (tool, target, session). Stored approvals never authorise an agent call. Hermes
                    answers that prompt by itself when the owner runs with ``--yolo`` or ``approvals.mode: off``
                    (tools/approval.py, v0.22.5), which is why the unattended, identity and voice rules are BLOCKS
                    decided here and never left to the prompt.
                    BOUNDED: Hermes runs hook callbacks with a 30 s timeout and a timed-out ``pre_tool_call`` blocks
                    EVERY tool call of the process for 60 s (stop included). So the hook never runs the camera or
                    switches the chamber light: it reads status + queue only (each request capped at
                    ``HOOK_REQUEST_TIMEOUT_S``) under an overall ``HOOK_DEADLINE_S`` (less when Hermes'
                    ``plugins.hook_callback_timeout`` is set lower: ``hook_deadline_s``), and blocks when the printer
                    does not answer in time. The plate is judged by the handler right before the action (the
                    authoritative check) and by ``/home3d approve``; a recent plate check of this process that said
                    occupied / unsure still blocks here.
``pre_llm_call``    remembers session -> sender (local sessions as ``LOCAL_SENDER``, delegated children inherit the
                    parent's sender) and how the turn's message arrived (voice or typed, ``Runtime.note_turn``), and
                    injects a short context for household / printing turns only. No network.
``pre_gateway_dispatch``  notes, in memory, that a sender's inbound message is a voice note: it reads the message
                    type and the sender id of the event and nothing else (never the text), stores nothing on disk,
                    and always returns None, so dispatch is never changed (Hermes fires it once per inbound message
                    at the gateway, before auth; never for local CLI/TUI/Desktop turns). Hermes tells no other hook
                    or tool that a message was spoken: ``pre_llm_call`` only gets the transcript as text.
``post_tool_call``  audits every ``home3d_*`` call, drops a pass the handler did not use (denied or vetoed call)
                    and logs approval friction as a human-needed moment.

Every hook is defensive: it never raises. ``pre_tool_call`` fails closed (blocks) on internal errors.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .backends.base import BackendError
from .config import LOCAL_SENDER, norm_id, scoped_sender
from .gates import (VOICE, Gate, approval_refusal, clear_plate_gate, describe, person_can_overrule, printer_blocks,
                    resume_gate, start_gate)
from .runtime import ABSENT_CRON, message_text

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
HOOK_REQUEST_TIMEOUT_S = 5.0  # per printer request inside pre_tool_call (status, queue)
HOOK_DEADLINE_S = 12.0  # the whole gate inside pre_tool_call (Hermes gives a hook callback 30 s)
HOOK_TIMEOUT_SHARE = 0.4  # with a lower plugins.hook_callback_timeout the gate gets this share of it
HOOK_PLATE_MAX_AGE_S = 120.0  # a plate check this recent (same printer state + job) still counts in the hook
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
def hook_deadline_s() -> float:
    """The gate's deadline inside ``pre_tool_call``: ``HOOK_DEADLINE_S``, or ``HOOK_TIMEOUT_SHARE`` of Hermes'
    hook-callback timeout when that is set lower, so the hook always answers before Hermes gives up on it (a
    timed-out ``pre_tool_call`` would block every tool call, stop included, for 60 s)."""
    try:
        from .config import hook_callback_timeout

        limit = float(hook_callback_timeout(read_config=False)[0])
    except Exception:
        limit = 30.0
    return deadline_for(limit)


def deadline_for(hook_timeout_s: float) -> float:
    """The gate's deadline under a Hermes hook-callback timeout of ``hook_timeout_s`` (0 or less: no limit)."""
    if hook_timeout_s <= 0:  # Hermes runs hook callbacks without a time limit
        return HOOK_DEADLINE_S
    return min(HOOK_DEADLINE_S, HOOK_TIMEOUT_SHARE * hook_timeout_s)


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
    gateway-hosted CLI's ``uid:<n>``), '' when unknown, else the raw id (``"irc:<nick>"`` on a platform whose ids the
    sender chooses, ``config.scoped_sender``). A messaging id that is literally "local" is quarantined
    (``<platform>:local``) so it can never pass as the local owner."""
    raw = str(sender_id or "").strip()
    plat = str(getattr(platform, "value", platform) or "").strip().lower()
    local = plat in LOCAL_PLATFORMS
    if not raw:
        return LOCAL_SENDER if local else ""
    if local and _LOCAL_UID.match(raw.lower()):
        return LOCAL_SENDER
    if norm_id(raw) == LOCAL_SENDER:
        return f"{plat or 'unknown'}:{raw}"
    return scoped_sender(raw, plat)  # "irc:<nick>": a freely chosen id only matches an entry scoped the same way


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


_INTERVAL = re.compile(r"\s*(?:every\s+)?(\d+)\s*([smhd]?)\w*\s*", re.IGNORECASE)


def interval_seconds(interval: Any) -> Optional[float]:
    """'2m' -> 120, '90s' -> 90, '1h' -> 3600, 'every 15m' -> 900, '15' -> 900 (minutes); None when it is not a
    plain interval (e.g. a cron expression)."""
    m = _INTERVAL.fullmatch(str(interval or "2m"))
    if not m:
        return None
    return float(int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[(m.group(2) or "m").lower()])


def watcher_stale_s(settings: Any = None) -> float:
    """After how long without a pass the watcher counts as not running: ``WATCHER_STALE_S`` (10 min), or three
    watch intervals when ``watch_interval`` is longer (a 15-minute watcher is not "off" 11 minutes after a pass)."""
    try:
        sec = interval_seconds(getattr(settings, "watch_interval", None)) if settings is not None else None
    except Exception:
        sec = None
    return max(float(WATCHER_STALE_S), 3.0 * sec) if sec else float(WATCHER_STALE_S)


def watcher_fresh(store, settings: Any = None) -> bool:
    """The zero-token watcher ran a pass in the last ``watcher_stale_s(settings)``."""
    try:
        w = store.kv_get("watcher") or {}
        updated = w.get("updated") if isinstance(w, dict) else None
        if not isinstance(updated, (int, float)):
            updated = store.kv_updated("watcher")
        return isinstance(updated, (int, float)) and 0 <= time.time() - float(updated) < watcher_stale_s(settings)
    except Exception:
        return False


def _interval_text(interval: Any) -> str:
    """'2m' -> '2 min', '90s' -> '90 s', '1h' -> '1 h'; anything else as given ('2 min' when empty)."""
    m = re.fullmatch(r"\s*(?:every\s+)?(\d+)\s*([smhd]?)\w*\s*", str(interval or "2m"))
    if not m:
        return str(interval)
    unit = {"s": "s", "m": "min", "h": "h", "d": "d", "": "min"}[m.group(2)]
    return f"{m.group(1)} {unit}"


# ---- the shared gate (hook and /home3d approve) --------------------------------------------------------
@dataclass
class Evaluation:
    ok: bool
    action: str
    tool: str
    reason: str = ""  # English, why it is blocked ("" when ok)
    message: str = ""  # the same in the household language
    code: str = ""  # why it is blocked, for programs: bad_request | unattended | printer_unreachable | gate
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


def absent_text(rt, tool: str, cmd: str = "") -> str:
    """Why ``tool`` does not run now, when nobody is present in this run (``Runtime.absent_reason``); '' when a
    person may be there. English, for the agent and logs."""
    why = rt.absent_reason()
    if not why:
        return ""
    if why == ABSENT_CRON:
        return f"{tool} never runs from a scheduled (cron) job; a person must be present."
    return (f"{tool} needs a person present, and nobody is in this run (kanban worker, single-query `chat -q`, "
            f"`-z` or a tool integration)." + (f" The owner sends `{cmd}` from a chat or terminal." if cmd else ""))


def evaluate(rt, action: str, args: Any, *, in_hook: bool = False) -> Evaluation:
    """Presence check + safety gate for one gated action. Used by ``pre_tool_call`` (``in_hook``) and
    ``commands.perform`` (``/home3d approve``, a UI) so both decide the same way. Raises only on internal errors
    (callers fail closed); a backend error is a block.

    ``in_hook``: bounded, for Hermes' hook budget: printer requests capped at ``HOOK_REQUEST_TIMEOUT_S`` and NO
    camera / chamber light: the plate check is deferred to the handler (only a recent remembered check counts).
    Otherwise (``/home3d approve``) the plate is checked here like in the handler (one cached check for both)."""
    a = args if isinstance(args, dict) else {}
    tool = TOOL_FOR_ACTION[action]
    ev = Evaluation(ok=False, action=action, tool=tool)
    lang = rt.settings.language
    if action == "start":
        ev.qid = _qid(a.get("queue_item_id"))
        if ev.qid is None:
            ev.code = "bad_request"
            ev.reason = ev.message = "home3d_start needs a numeric queue_item_id (see home3d_queue action=list)."
            return ev
        ev.jump = _truthy(a.get("allow_jump"))
    if action == "resume":
        ev.ack = _truthy(a.get("ack_hms"))
    ev.target = approval_target(action, ev.qid, ev.jump)
    absent = absent_text(rt, tool, approve_command(action, ev.qid, ev.jump, ack=ev.ack))
    if absent:  # cron, kanban worker, chat -q, -z, --source tool: the one definition, on every path
        ev.code = "unattended"
        ev.reason = ev.message = absent
        return ev
    try:
        _gate(rt, ev, in_hook=in_hook)
    except BackendError as e:
        ev.ok, ev.summary = False, ""
        ev.code = "printer_unreachable"
        ev.reason = ev.message = f"printer not reachable, {tool} was not run: {e}"
        return ev
    if ev.gate is not None and not ev.gate.ok:
        ev.code = "gate"
        ev.reason, ev.message = describe(ev.gate, "en"), describe(ev.gate, lang)
    return ev


def bounded_backend(be: Any, seconds: float = HOOK_REQUEST_TIMEOUT_S) -> Any:
    """``be.with_timeout(seconds)`` when the backend has it (network backends), else ``be`` (the simulator)."""
    fn = getattr(be, "with_timeout", None)
    if callable(fn):
        try:
            return fn(seconds)
        except Exception:
            return be
    return be


def _gate(rt, ev: Evaluation, *, in_hook: bool = False) -> None:
    be, store, s = rt.backend, rt.store, rt.settings
    if in_hook:
        be = bounded_backend(be)
    status = be.status()
    in_cron = rt.nobody_present()  # cron and every other run nobody watches (evaluate blocked those already)
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
        if in_hook:  # never the camera here: only what this process saw a moment ago
            plate = rt.recent_plate_check(max_age_s=HOOK_PLATE_MAX_AGE_S, status=status)
        else:
            try:
                plate = rt.plate_check(status=status)
            except BackendError:
                plate = None  # the gate blocks on an unknown plate
    deferred = in_hook and plate is None and not skipped
    diff = f" ({plate.difference_pct:g}% difference)" if plate is not None and plate.difference_pct is not None else ""
    light = (" Note: the chamber light could not be switched off again after the plate check."
             if plate is not None and LIGHT_FLAG in str(plate.message or "") else "")
    if ev.action == "clear_plate":
        auto = [q for q in queue if q.is_pending and not q.manual_start]
        gate = clear_plate_gate(status, plate, in_cron=in_cron, cool_temp_c=s.eject_cool_temp_c,
                                auto_start_pending=auto, person_confirms=True, plate_skipped=skipped,
                                plate_deferred=deferred)
        ev.gate, ev.ok = gate, gate.ok
        if gate.ok:
            bed = f"bed {status.bed_temp:.0f} C" if status.bed_temp is not None else "bed temperature unknown"
            if deferred:
                camera = ("confirm only after looking at the plate yourself: the camera checks it right before "
                          "(an unsure reading is accepted on your word, an occupied plate still stops it)")
            elif person_can_overrule(plate):
                camera = f"the camera is NOT sure{diff}: you confirm it is clear yourself, look at the plate first"
            else:
                camera = f"the camera thinks the plate is empty{diff}"
            ev.summary = (f"Mark the 3D printer plate clear ({bed}; {camera}). "
                          f"The printer manager may then start the next job.{light}")
        return
    req = store.request_for_queue_item(ev.qid)
    gate = start_gate(status, queue, ev.qid, plate=plate, in_cron=in_cron, own_item_ids=store.active_job_ids(),
                      requesters=store.active_job_requesters(), owner_name=s.owner_name,
                      allow_jump=ev.jump, voice_request=bool(req and req.get("channel") == "voice"),
                      plate_confirmed=store.plate_confirmed(status.job_name, status=status),
                      after_failure=_after_failure(store), plate_skipped=skipped, plate_deferred=deferred)
    ev.gate, ev.ok = gate, gate.ok
    if gate.ok:
        ev.summary = _start_summary(store, ev.qid, queue, gate, diff, plate, deferred) + light


def _after_failure(store) -> bool:
    """A failed print nobody has confirmed the plate of since (``Store.unconfirmed_failure``); fails closed."""
    try:
        return store.unconfirmed_failure() is not None
    except Exception:
        return True


def _start_summary(store, qid: int, queue: list, gate: Gate, diff: str, plate=None, deferred: bool = False) -> str:
    item = next((q for q in queue if q.id == qid), None)
    job = store.get_job(qid) or {}
    meta = (store.kv_get(f"slice:{job['sliced_file_id']}") or {}) if job.get("sliced_file_id") else {}
    name = _pretty((item.name if item else "") or job.get("name") or f"#{qid}")
    bits = [x for x in (_minutes(item.print_time_s) if item and item.print_time_s else "",
                        f"{meta['grams']:.0f} g" if isinstance(meta.get("grams"), (int, float)) else "",
                        "auto-eject" if job.get("eject_planned") else "no auto-eject") if x]
    who = job.get("requester") or "the household"
    if deferred:
        camera = ("The camera checks the plate right before starting: an occupied or unsure plate still stops "
                  "the start.")
    elif person_can_overrule(plate):
        camera = f"The camera is not sure{diff}; the owner confirmed the plate is clear."
    else:
        camera = f"The camera thinks the plate is empty{diff}."
    out = f"Start 3D print #{qid} \"{name}\" for {who} ({', '.join(bits)}). {camera}"
    warns = [i for i in gate.items if i.get("level") == "warn"]  # in the same order as gate.warnings
    notes = [text for i, text in zip(warns, gate.warnings) if i.get("code") != "plate_deferred"]
    if notes:
        out += " Note: " + "; ".join(notes) + "."
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
        s = rt.settings
        owner = s.owner_name or "the owner"
        qid = _qid(args.get("queue_item_id")) if action == "start" else None
        cmd = approve_command(action, qid, _truthy(args.get("allow_jump")), ack=_truthy(args.get("ack_hms")))
        actor = rt.actor(session_id)  # who asks, how the message arrived, is a person present
        sender = actor.sender
        person = s.person_for(sender) if sender else None
        why = approval_refusal(actor)  # the same rule /home3d approve uses (commands.perform)
        if why == "unattended":  # 1. cron, kanban worker, chat -q, -z, --source tool: nobody can answer a prompt
            return _block("BLOCKED: " + (absent_text(rt, tool, cmd) or f"{tool} needs a person present."))
        if why in ("no_identity", "not_owner", "local_off"):
            # 2. who asks, before the safety gate: a family member or a stranger is refused without any printer
            # call on their behalf (the owner's command runs the gate itself)
            return self._refuse(person, sender, cmd, owner, action=action, qid=qid, session_id=session_id)
        if why == "voice_message":
            # 3. voice is for asking, never for starting: speech-to-text can hear another sentence. A block, not an
            # approval prompt: Hermes answers its prompt by itself under --yolo / approvals.mode off.
            return _block(f"BLOCKED: voice message: {owner}'s last message came in as a voice note, and a voice "
                          "note never starts or resumes a print or marks the plate clear (speech can be heard "
                          f"wrong). Ask {owner} to confirm in writing: a typed message here, or `{cmd}` (runs it "
                          "right away). Do not call this again before a typed message arrives.")
        if why:  # a rule this hook does not know: fail closed
            return _block(f"BLOCKED: {tool} was not run ({why}). {owner} sends `{cmd}`.")
        ev = self._evaluate_bounded(action, args)  # 4. presence again + the safety gate (bounded, no camera)
        if not ev.ok:
            return _block(f"BLOCKED: {ev.reason}")
        cmd = approve_command(action, ev.qid, ev.jump, ack=bool(ev.hms))
        if approval_refusal(rt.actor(session_id)):  # defensive: the answer changed while the gate ran
            return self._refuse(person, sender, cmd, owner)
        # 5. the owner, present, typing: Hermes asks them BEFORE the handler runs (it answers by itself under their
        # own --yolo / approvals.mode off, verified in tools/approval.py v0.22.5); the handler then needs this
        # single-use pass, so nothing but this very call can use it.
        rt.store.issue_pass(tool, ev.target, session_id, ttl_s=PASS_TTL_S, detail=ev.pass_detail)
        # unique per call: an "always" answer in Hermes' prompt can never pre-approve a later printer action (it
        # only adds an allowlist entry nothing will match again), so the prompt says to approve once
        rule_key = f"home3d:{tool}:{ev.target or '-'}:{int(time.time())}:{uuid.uuid4().hex[:8]}"
        return {"action": "approve", "message": f"{ev.summary} {APPROVE_ONCE_NOTE}", "rule_key": rule_key}

    def _evaluate_bounded(self, action: str, args: dict) -> Evaluation:
        """``evaluate(in_hook=True)`` under a hard deadline. The gate runs in a worker thread (with this thread's
        context, so the cron / session markers stay visible); when it does not finish within ``HOOK_DEADLINE_S``
        the call is blocked and the late result is dropped: no pass is ever issued after the deadline. A lower
        ``plugins.hook_callback_timeout`` shortens the deadline (``hook_deadline_s``)."""
        box: dict[str, Any] = {}
        deadline = hook_deadline_s()
        ctx = contextvars.copy_context()

        def work() -> None:
            try:
                box["ev"] = ctx.run(evaluate, self.rt, action, args, in_hook=True)
            except BaseException as e:  # handed to the caller, which fails closed
                box["exc"] = e

        worker = threading.Thread(target=work, name="home3d-pre-tool-gate", daemon=True)
        worker.start()
        worker.join(deadline)
        if worker.is_alive() or ("ev" not in box and "exc" not in box):
            tool = TOOL_FOR_ACTION[action]
            ev = Evaluation(ok=False, action=action, tool=tool)
            ev.reason = ev.message = (f"the printer did not answer within {deadline:g} s, {tool} was not run "
                                      "(try again in a minute; stop and pause are not affected)")
            return ev
        if "exc" in box:
            raise box["exc"]
        return box["ev"]

    def _refuse(self, person, sender: str, cmd: str, owner: str, *, action: str = "", qid: Optional[int] = None,
                session_id: str = "") -> dict:
        rt = self.rt
        s = rt.settings
        if person is None:  # 2a. no household identity: never ask this chat to approve itself, nothing is passed on
            why = ("this session has no known sender" if not sender else "this sender is not in the household list")
            return _block(f"BLOCKED: {APPROVAL_MARKER}: unknown sender ({why}). Only {owner} can approve, with "
                          f"`{cmd}` (runs it right away, nothing is stored). {owner} is not told about this: the "
                          f"person has to ask {owner} directly.")
        # 2b. a household member who is not the owner: the ask becomes an approval request the watcher passes on
        hint = "" if s.owner_ids else " (no owner_ids are configured yet)"
        relay = self._relay(person.name, owner, action, qid, session_id, sender)
        return _block(f"BLOCKED: {APPROVAL_MARKER}: {person.name} is not the owner{hint}. {owner} sends "
                      f"`{cmd}` (runs it right away, nothing is stored). {relay} Do not promise a start.")

    def _relay(self, who: str, owner: str, action: str, qid: Optional[int], session_id: str, sender: str) -> str:
        """Record the approval request (once per action + item + person per day) and say truthfully what happens."""
        store = self.rt.store
        announced = False
        if action:
            try:
                if store.add_approval_request(action, qid, who, session_id, sender_id=sender) is None:
                    prev = store.latest_approval_request(action, qid, who) or {}
                    announced = prev.get("announced_ts") is not None
            except Exception as e:  # recording is best effort: the refusal itself must stand
                logger.debug("home3d approval request not recorded: %s", e)
                return f"The request could not be recorded: {who} should ask {owner} directly."
        chat = bool(str(self.rt.settings.owner_target or "").strip())  # where the watcher sends owner notices
        if announced and chat:
            return f"{owner} already got this request from the watcher; tell {who} it is up to {owner} now."
        fresh = watcher_fresh(store, self.rt.settings)
        if fresh and chat:
            return (f"{owner} gets this request on the next watcher pass (about "
                    f"{_interval_text(self.rt.settings.watch_interval)}); tell {who} you passed it on.")
        if fresh or announced:  # the watcher runs, but owner notices have no chat to go to (cron output / outbox)
            return (f"No owner chat is set (owner_target), so {owner} may not be told automatically: {who} should "
                    f"ask {owner} directly.")
        return (f"The watcher is off, so {owner} is not told automatically: {who} should ask {owner} directly "
                "(the watcher is started with `hermes home3d setup` and needs `hermes gateway` running).")

    # -- pre_gateway_dispatch --
    def pre_gateway_dispatch(self, event: Any = None, **kw: Any) -> None:
        """Note that a sender's inbound message is (or is not) a voice note. Reads ``event.message_type`` and
        ``event.source.user_id`` only, keeps it in memory (``Runtime.note_inbound``) and ALWAYS returns None: the
        message is dispatched exactly as without this plugin. Never raises."""
        try:
            source = getattr(event, "source", None)
            user = getattr(source, "user_id", None) or getattr(event, "user_id", None)
            if user:
                kind = getattr(event, "message_type", None)
                kind = str(getattr(kind, "value", kind) or "").strip().lower()
                self.rt.note_inbound(user, kind == VOICE)
        except Exception as e:
            logger.debug("home3d pre_gateway_dispatch failed: %s", e)
        return None

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
        # how the message arrived is noted first: a store error in _record_sender must not leave a stale TYPED
        spoken = rt.note_turn(session_id, sender, user_message, parent) == VOICE  # before any early return
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
        if spoken:
            speaker += (" This message came in as a voice note: it can ask for anything, but starting, resuming or "
                        "marking the plate clear needs a typed message.")
        printer, state_key = self._printer_state(store, watcher_stale_s(s))
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
    def _printer_state(store, stale_s: float = WATCHER_STALE_S) -> tuple[str, str]:
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
        if age is None or age > stale_s:
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


_message_text = message_text  # multimodal turn: text parts only (runtime.message_text)


def make_hooks(rt) -> dict[str, Callable]:
    """``{"pre_tool_call", "post_tool_call", "pre_llm_call", "pre_gateway_dispatch"}`` bound to the shared
    Runtime (exactly the hooks ``plugin.yaml`` declares)."""
    h = _Hooks(rt)
    return {"pre_tool_call": h.pre_tool_call, "post_tool_call": h.post_tool_call, "pre_llm_call": h.pre_llm_call,
            "pre_gateway_dispatch": h.pre_gateway_dispatch}


__all__ = ["make_hooks", "gated_action", "approve_command", "approval_target", "evaluate", "Evaluation",
           "absent_text",
           "hms_ack_detail", "acked_codes", "HMS_ACK_PREFIX", "bounded_backend", "watcher_fresh",
           "watcher_stale_s", "interval_seconds",
           "HOOK_DEADLINE_S", "HOOK_REQUEST_TIMEOUT_S", "HOOK_PLATE_MAX_AGE_S", "HOOK_TIMEOUT_SHARE",
           "hook_deadline_s", "deadline_for",
           "session_sender", "is_local_platform", "APPROVAL_MARKER", "APPROVAL_TTL_S", "PASS_TTL_S", "GATED_TOOLS",
           "LOCAL_PLATFORMS", "SKILL_REF", "TOOL_FOR_ACTION"]
