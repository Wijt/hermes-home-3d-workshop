"""Runtime: the one object every Hermes surface (tools, hooks, commands, CLI) shares.

It resolves settings lazily on each access (so Desktop/config edits apply without a restart), owns the
store, creates the backend on demand, and answers "who is talking" / "are we inside cron".
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from .backends import Backend, make_backend
from .config import Person, Settings, data_dir, load_settings
from .store import Store


class Runtime:
    def __init__(self, ctx: Any = None, *, settings: Optional[Settings] = None,
                 store: Optional[Store] = None, backend: Optional[Backend] = None):
        self.ctx = ctx
        self._fixed_settings = settings
        self._store = store
        self._backend = backend
        self._backend_key: Optional[tuple] = None

    # ---- settings / store / backend --------------------------------------------------------
    @property
    def settings(self) -> Settings:
        if self._fixed_settings is not None:
            return self._fixed_settings
        return load_settings(self.ctx)

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

    # ---- identity / context ------------------------------------------------------------------
    def sender_id(self, session_id: Optional[str]) -> str:
        return self.store.sender_for(session_id)

    def person(self, session_id: Optional[str]) -> Optional[Person]:
        return self.settings.person_for(self.sender_id(session_id))

    def requester_name(self, session_id: Optional[str], fallback: str = "") -> str:
        p = self.person(session_id)
        return p.name if p else fallback

    def in_cron(self) -> bool:
        if self.ctx is None or not hasattr(self.ctx, "current_cron_execution"):
            return False
        try:
            return self.ctx.current_cron_execution() is not None
        except Exception:
            return False

    @staticmethod
    def now() -> float:
        return time.time()
