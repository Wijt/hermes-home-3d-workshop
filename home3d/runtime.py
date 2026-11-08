"""Runtime: the one object every Hermes surface (tools, hooks, commands, CLI) shares.

It resolves settings lazily on each access (so Desktop/config edits apply without a restart) and, inside Hermes,
rewrites the watcher's fallback snapshot whenever they changed; it owns the store, creates the backend on demand,
answers "who is talking" / "are we inside cron", and remembers the last plate check: a confident "empty" is reused
by the next check (one camera check per start), and any recent result is what the ``pre_tool_call`` hook sees
(the hook never runs the camera itself, see hooks.py).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .backends import Backend, make_backend
from .config import Person, Settings, data_dir, load_settings, settings_hash, sync_snapshot
from .store import Store

_TRUTHY = {"1", "true", "yes", "on"}
CRON_ENV = "HERMES_CRON_SESSION"
KANBAN_ENV = "HERMES_KANBAN_TASK"
SINGLE_QUERY_ENV = "HERMES_SINGLE_QUERY_SESSION"
SOURCE_ENV = "HERMES_SESSION_SOURCE"
UNATTENDED_SOURCES = frozenset({"kanban", "tool"})
LIGHT_FLAG = "light_left_on"
LIGHT_PENDING_KEY = "light_left_on:pending"  # a hook/handler plate check left the light on: the watcher tells the owner


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

    @staticmethod
    def now() -> float:
        return time.time()
