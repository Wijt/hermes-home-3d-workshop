"""Runtime: the one object every Hermes surface (tools, hooks, commands, CLI) shares.

It resolves settings lazily on each access (so Desktop/config edits apply without a restart) and, inside Hermes,
rewrites the watcher's fallback snapshot whenever they changed; it owns the store, creates the backend on demand,
answers "who is talking" / "is a person present" / "did this arrive as a voice message", and remembers the last
plate check: a confident "empty" is reused by the next check (one camera check per start), and any recent result is
what the ``pre_tool_call`` hook sees (the hook never runs the camera itself, see hooks.py).

One definition of "nobody is present" (``Runtime.absent_reason`` / ``nobody_present``): a scheduled (cron) run, a
kanban worker, ``chat -q``, ``-z`` and ``--source tool``. The agent path, ``/home3d``, the tool handlers and the pure
gates all ask it, and it fails closed.

Voice (``note_inbound`` / ``note_turn`` / ``session_channel``), in memory only: the ``pre_gateway_dispatch`` hook
notes which sender just sent a voice message, the ``pre_llm_call`` hook turns that into "this session's turn came in
as voice", and the approval rule (``gates.approval_refusal``) refuses a start / resume / plate clear asked that way.
"""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .backends import Backend, make_backend
from .config import Person, Settings, data_dir, load_settings, norm_id, settings_hash, sync_snapshot
from .gates import TYPED, VOICE, Actor, who_is
from .store import Store

_TRUTHY = {"1", "true", "yes", "on"}
CRON_ENV = "HERMES_CRON_SESSION"
KANBAN_ENV = "HERMES_KANBAN_TASK"
SINGLE_QUERY_ENV = "HERMES_SINGLE_QUERY_SESSION"
SOURCE_ENV = "HERMES_SESSION_SOURCE"
UNATTENDED_SOURCES = frozenset({"kanban", "tool"})
LIGHT_FLAG = "light_left_on"
LIGHT_PENDING_KEY = "light_left_on:pending"  # a hook/handler plate check left the light on: the watcher tells the owner
ABSENT_CRON, ABSENT_UNATTENDED = "cron", "unattended"  # ``Runtime.absent_reason``
VOICE_MARK_TTL_S = 10 * 60.0  # a noted voice message counts for the sender's next turn this long (STT, a busy agent)
VOICE_COMMAND_S = 60.0  # a slash command counts as spoken when the sender's newest message is a voice note this fresh
INBOUND_MAX_SENDERS = 500  # senders whose voice notes are remembered per process (the oldest is dropped)
CHANNEL_MAX_SESSIONS = 2000  # per-session "how did the last turn arrive" records (the oldest is dropped)
# what Hermes v0.22.5 hands the agent for a voice message it could not turn into words (gateway STT notes)
_VOICE_NOTES = ("[voice message could not be transcribed", "[the user sent a voice message")
_LEADING_BRACKET = re.compile(r"^\s*\[[^\]\n]{0,400}\]\s*")


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def cron_markers() -> bool:
    """Hermes v0.22.5 cron markers besides ``ctx.current_cron_execution()`` (which reads None inside a cron agent's
    ``delegate_task`` children, cron/execution_identity.py:51-54):

    - ``HERMES_CRON_SESSION``: the scheduler sets it to "1" as a session ContextVar (cron/scheduler.py ``enter``),
      which ``copy_context()`` carries into delegated children; ``gateway.session_context.get_session_env`` reads it
      ContextVar-first with an ``os.environ`` fallback (standalone cron entrypoints).
    - ``cron.execution_identity._CURRENT``: the raw execution ContextVar, also copied into children.

    Both modules are looked up in ``sys.modules`` (never imported: they are only meaningful when Hermes already
    loaded them, and importing them would add private-import coupling). A marker that is missing in a future Hermes
    is skipped; a marker that exists but raises counts as cron (fail closed).
    """
    sc = sys.modules.get("gateway.session_context")
    getter = getattr(sc, "get_session_env", None) if sc is not None else None
    if callable(getter):
        try:
            if _truthy(getter(CRON_ENV, "")):
                return True
        except Exception:
            return True
    elif _truthy(os.environ.get(CRON_ENV)):
        return True
    ei = sys.modules.get("cron.execution_identity")
    var = getattr(ei, "_CURRENT", None) if ei is not None else None
    if var is not None and hasattr(var, "get"):
        try:
            if var.get() is not None:
                return True
        except Exception:
            return True
    return False


def _session_env(name: str) -> str:
    """Hermes' per-session env (``gateway.session_context.get_session_env``, ContextVar first) when Hermes loaded it,
    else the process env. Raises when the Hermes getter raises (callers fail closed)."""
    sc = sys.modules.get("gateway.session_context")
    getter = getattr(sc, "get_session_env", None) if sc is not None else None
    if callable(getter):
        return str(getter(name, "") or "")
    return str(os.environ.get(name, "") or "")


def unattended_markers() -> bool:
    """Hermes v0.22.5 runs with nobody present to answer an approval prompt, besides cron:

    - a kanban card worker (``HERMES_KANBAN_TASK`` set; it runs as a local ``cli`` session with ``uid:<n>``),
    - single-query ``hermes chat -q`` (``HERMES_SINGLE_QUERY_SESSION``) and a gateway-admitted finite turn
      (``gateway.session_finite.finite_turn_required() is True``, ``hermes -z`` / ``chat -q`` over the daemon),
    - ``hermes -z`` unattended turns (``gateway.session_finite.unattended_turn()``),
    - a session source of ``kanban`` or ``tool`` (``HERMES_SESSION_SOURCE``; ``hermes chat --source tool`` is meant
      for third-party integrations).

    Same lookup rules as ``cron_markers``: modules only from ``sys.modules``; a missing marker is skipped, one that
    raises counts as unattended (fail closed)."""
    for name, check in ((KANBAN_ENV, lambda v: bool(v.strip())), (SINGLE_QUERY_ENV, _truthy),
                        (SOURCE_ENV, lambda v: v.strip().lower() in UNATTENDED_SOURCES)):
        try:
            if check(_session_env(name)):
                return True
        except Exception:
            return True
    sf = sys.modules.get("gateway.session_finite")
    if sf is not None:
        for fn_name, hit in (("finite_turn_required", lambda v: v is True), ("unattended_turn", bool)):
            fn = getattr(sf, fn_name, None)
            if callable(fn):
                try:
                    if hit(fn()):
                        return True
                except Exception:
                    return True
    return False


def message_text(msg: Any) -> str:
    """The text of a ``pre_llm_call`` ``user_message`` (a string, or the text parts of a multimodal turn)."""
    if isinstance(msg, str):
        return msg[:2000]
    if isinstance(msg, list):
        parts = [p.get("text", "") for p in msg if isinstance(p, dict) and isinstance(p.get("text"), str)]
        return " ".join(parts)[:2000]
    return ""


def looks_like_voice(user_message: Any) -> bool:
    """The turn text has the shape Hermes v0.22.5 gives a voice message: the transcript as one quoted line
    (``"start my friend"``, after an optional ``[Name]`` / ``[Replying to: ...]`` prefix), or one of its "could not
    be transcribed" notes. A second signal beside ``note_inbound``. A typed message that is entirely one quoted
    line is taken for voice too (the safe direction: the person is asked to type it again)."""
    text = message_text(user_message).strip()
    if not text:
        return False
    low = text.lower()
    if any(mark in low for mark in _VOICE_NOTES):
        return True
    for _ in range(4):  # "[Name] ", "[Replying to: ...]" and similar prefixes Hermes puts before the text
        m = _LEADING_BRACKET.match(text)
        if not m:
            break
        text = text[m.end():]
    first = re.split(r"\n\s*\n", text.strip(), maxsplit=1)[0].strip()  # a caption may follow the transcript
    return len(first) > 2 and first[0] == '"' and first[-1] == '"' and '"' not in first[1:-1]


class Runtime:
    def __init__(self, ctx: Any = None, *, settings: Optional[Settings] = None,
                 store: Optional[Store] = None, backend: Optional[Backend] = None):
        self.ctx = ctx
        self._fixed_settings = settings
        self._store = store
        self._backend = backend
        self._backend_key: Optional[tuple] = None
        self._plate_lock = threading.Lock()
        self._plate_cache: Optional[tuple[tuple, float, Any]] = None  # (key, ts, PlateCheck): a confident "empty"
        self._plate_last: Optional[tuple[tuple, float, Any]] = None  # (key, ts, PlateCheck): the last result, any
        self._snap_lock = threading.Lock()
        self._snap_hash: Optional[str] = None
        self._voice_lock = threading.Lock()
        self._inbound: dict[str, list[tuple[float, bool]]] = {}  # sender id -> [(ts, voice)], newest last
        self._channels: dict[str, tuple[str, float]] = {}  # session id -> (VOICE | TYPED, ts)

    # ---- settings / store / backend --------------------------------------------------------
    @property
    def settings(self) -> Settings:
        if self._fixed_settings is not None:
            return self._fixed_settings
        s = load_settings(self.ctx)
        if self.ctx is not None and hasattr(self.ctx, "get_config"):
            self._sync_snapshot(s)
        return s

    def _sync_snapshot(self, s: Settings) -> None:
        """Inside Hermes: keep the watcher's fallback snapshot equal to the live settings (written only when the
        content changed; the hash of the last synced content is kept in memory). Never raises."""
        try:
            h = settings_hash(s)
            if h == self._snap_hash:
                return
            with self._snap_lock:
                if h != self._snap_hash:
                    sync_snapshot(s)
                    self._snap_hash = h
        except Exception:
            pass  # a read-only data dir must not break a tool call; doctor reports the stale snapshot

    @property
    def store(self) -> Store:
        if self._store is None:
            self._store = Store()
        return self._store

    @property
    def backend(self) -> Backend:
        s = self.settings
        key = (s.backend, s.bambuddy_url, s.printer_id)
        if self._backend is None or (self._backend_key is not None and key != self._backend_key):
            self._backend = make_backend(s)
            self._backend_key = key
        return self._backend

    @property
    def media_dir(self) -> Path:
        p = data_dir() / "media"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def work_dir(self) -> Path:
        p = data_dir() / "work"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ---- plate check (shared by the hook and the handler) -------------------------------------
    @staticmethod
    def _plate_key(be: Any, st: Any) -> tuple:
        return (id(be), str(getattr(st, "state", "") or ""), str(getattr(st, "job_name", "") or ""))

    def plate_check(self, max_age_s: float = 90, status: Any = None):
        """``backend.check_plate()`` with a short cache keyed by (backend, printer state, job name).

        Only a confident "empty" result is reused (``is_empty is True`` and the light was not reported broken):
        a "not empty" / uncertain answer is re-checked every time, so a person who just cleared the plate is not
        told it is still occupied. Every result is remembered for ``recent_plate_check`` (the hook).
        ``status`` (a ``PrinterStatus`` the caller already read) saves a status call. Raises ``BackendError``
        like the backend; errors are never cached.
        """
        be = self.backend
        st = status if status is not None else be.status()
        key = self._plate_key(be, st)
        now = time.monotonic()
        with self._plate_lock:
            cached = self._plate_cache
            if cached is not None and cached[0] == key and now - cached[1] <= max(0.0, float(max_age_s)):
                return cached[2]
        plate = be.check_plate()
        if LIGHT_FLAG in str(getattr(plate, "message", "") or ""):
            try:  # the owner is told by the next watcher pass (an approval prompt / block text may not reach them)
                self.store.kv_set(LIGHT_PENDING_KEY, {"ts": time.time(), "note": str(plate.message)[:200]})
            except Exception:
                pass
        with self._plate_lock:
            stamp = time.monotonic()
            self._plate_last = (key, stamp, plate)
            if getattr(plate, "is_empty", None) is True and getattr(plate, "light_ok", None) is not False:
                self._plate_cache = (key, stamp, plate)
            else:
                self._plate_cache = None
        return plate

    def recent_plate_check(self, max_age_s: float = 120, status: Any = None):
        """The last plate check of this process (any result) when it is at most ``max_age_s`` old and was made for
        the same printer state and job (``status``); else None. No camera, no network: what the ``pre_tool_call``
        hook uses."""
        be = self.backend
        with self._plate_lock:
            last = self._plate_last
        if last is None or time.monotonic() - last[1] > max(0.0, float(max_age_s)):
            return None
        if status is not None and last[0] != self._plate_key(be, status):
            return None
        return last[2]

    def forget_plate_check(self) -> None:
        with self._plate_lock:
            self._plate_cache = None
            self._plate_last = None

    # ---- identity / context ------------------------------------------------------------------
    def sender_id(self, session_id: Optional[str]) -> str:
        """The recorded sender of ``session_id`` ('' = unknown; ``config.LOCAL_SENDER`` = a local session)."""
        return self.store.sender_for(session_id)

    def person(self, session_id: Optional[str]) -> Optional[Person]:
        return self.settings.person_for(self.sender_id(session_id))

    def is_owner(self, session_id: Optional[str]) -> bool:
        """The session's recorded sender is the owner (a local session counts when ``local_is_owner``)."""
        sender = self.sender_id(session_id) if session_id else ""
        return bool(sender) and self.settings.is_owner(sender)

    def requester_name(self, session_id: Optional[str], fallback: str = "") -> str:
        p = self.person(session_id)
        return p.name if p else fallback

    def in_cron(self) -> bool:
        """True inside a scheduled (cron) run. FAILS CLOSED: a ``current_cron_execution`` that raises counts as cron;
        the raw Hermes markers (``cron_markers``) also catch a cron agent's delegated children."""
        ctx = self.ctx
        if ctx is not None and hasattr(ctx, "current_cron_execution"):
            try:
                if ctx.current_cron_execution() is not None:
                    return True
            except Exception:
                return True
        try:
            return cron_markers()
        except Exception:
            return True

    def unattended(self) -> bool:
        """True in a run with nobody present to answer (kanban worker, ``chat -q``, ``-z``). Fails closed."""
        try:
            return unattended_markers()
        except Exception:
            return True

    def absent_reason(self) -> str:
        """Why nobody is present in this run: ``"cron"`` (a scheduled job), ``"unattended"`` (a kanban worker,
        ``chat -q``, ``-z``, ``--source tool``) or '' (a person may be there). THE definition every path uses: the
        ``pre_tool_call`` hook, ``/home3d``, the tool handlers and the gates. Fails closed."""
        try:
            if self.in_cron():
                return ABSENT_CRON
            return ABSENT_UNATTENDED if self.unattended() else ""
        except Exception:
            return ABSENT_UNATTENDED

    def nobody_present(self) -> bool:
        """True in a run nobody watches (``absent_reason``): it never starts, resumes or clears anything."""
        return bool(self.absent_reason())

    def actor_for(self, sender: Any, channel: str = "") -> Actor:
        """Who a recorded sender id is (``gates.who_is``), with whether a person is present in this run."""
        return who_is(self.settings, sender, present=not self.nobody_present(), channel=channel)

    def actor(self, session_id: Optional[str]) -> Actor:
        """Who is talking in ``session_id`` and how their last message arrived. No session: nobody."""
        sid = str(session_id or "")
        return self.actor_for(self.sender_id(sid) if sid else "", self.session_channel(sid))

    # ---- voice: how did the message that asks arrive ---------------------------------------------
    def note_inbound(self, user_id: Any, voice: bool) -> None:
        """A message from ``user_id`` just reached the gateway (``pre_gateway_dispatch``); ``voice``: it is a voice
        note. Kept in memory only, per sender id (``config.norm_id``; the platform is left out on purpose, so a
        platform that names itself differently at the gateway and in the agent still matches): the kind and the
        time of the newest few messages, and nothing at all for a sender who has sent no voice note lately."""
        key = norm_id(user_id)
        if not key:
            return
        now = time.time()
        with self._voice_lock:
            if not voice and key not in self._inbound:
                return  # typed messages matter only after a voice note (to tell which of the two is newer)
            events = [e for e in self._inbound.pop(key, []) if now - e[0] <= VOICE_MARK_TTL_S][-7:]
            self._inbound[key] = events + [(now, bool(voice))]  # re-inserted: ordered by last activity
            while len(self._inbound) > INBOUND_MAX_SENDERS:
                self._inbound.pop(next(iter(self._inbound)))

    def take_voice(self, user_id: Any) -> bool:
        """True when ``user_id`` sent a voice note (within ``VOICE_MARK_TTL_S``) that no turn has accounted for
        yet. The sender's noted messages are used up by this call: one turn each."""
        key = norm_id(user_id)
        if not key:
            return False
        now = time.time()
        with self._voice_lock:
            events = self._inbound.pop(key, [])
        return any(voice and now - ts <= VOICE_MARK_TTL_S for ts, voice in events)

    def spoken_command(self, user_id: Any) -> bool:
        """The sender's newest message is a voice note at most ``VOICE_COMMAND_S`` old: a slash command arriving
        now was spoken, not typed (Hermes' voice-channel mode hands a transcript on as message text)."""
        key = norm_id(user_id)
        if not key:
            return False
        with self._voice_lock:
            events = self._inbound.get(key) or []
            last = events[-1] if events else None
        return bool(last and last[1] and time.time() - last[0] <= VOICE_COMMAND_S)

    def note_turn(self, session_id: str, user_id: Any = "", user_message: Any = None, parent: str = "") -> str:
        """Record how this turn's message arrived and return it: ``VOICE`` when the sender's voice note was noted
        at the gateway, the text has the shape of a transcript (``looks_like_voice``), or this is a delegated
        child of a voice turn; else ``TYPED``. Called once per turn by ``pre_llm_call``."""
        voice = self.take_voice(user_id) or looks_like_voice(user_message)
        if not voice and parent and parent != session_id:
            voice = self.session_channel(parent) == VOICE
        channel = VOICE if voice else TYPED
        if session_id:
            with self._voice_lock:
                self._channels.pop(session_id, None)
                self._channels[session_id] = (channel, time.time())
                while len(self._channels) > CHANNEL_MAX_SESSIONS:
                    self._channels.pop(next(iter(self._channels)))
        return channel

    def session_channel(self, session_id: Optional[str]) -> str:
        """``VOICE`` / ``TYPED`` for the last turn of ``session_id`` in this process, '' when no turn was seen."""
        if not session_id:
            return ""
        with self._voice_lock:
            rec = self._channels.get(str(session_id))
        return rec[0] if rec else ""

    @staticmethod
    def now() -> float:
        return time.time()
