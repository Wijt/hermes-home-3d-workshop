"""Durable household memory (SQLite in the plugin data dir).

Tables:
  requests      who asked for what, through which channel, and how it ended
  jobs          queue items this plugin created/started (link to request, eject plan, outcome)
  events        watcher events (state changes) + whether owner/family were notified
  human_needed  moments where a person had to act (remove part, clean plate, swap filament, ...)
  upgrades      upgrade proposals derived from human_needed (proposed -> accepted -> printing -> installed)
  approvals     short-lived owner approvals for start / clear-plate (from /home3d approve)
  kv            small key/value state (watcher last state, session -> sender map, ...)

One connection per call site; WAL mode lets the watcher script and the gateway write concurrently.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from .config import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  requester TEXT NOT NULL DEFAULT '',      -- person name ('' = unknown)
  sender_id TEXT NOT NULL DEFAULT '',
  channel TEXT NOT NULL DEFAULT '',        -- text | voice | photo | link | cli
  text TEXT NOT NULL DEFAULT '',
  model_ref TEXT NOT NULL DEFAULT '',      -- MakerWorld url/id or template name
  library_file_id INTEGER,
  sliced_file_id INTEGER,
  queue_item_id INTEGER,
  status TEXT NOT NULL DEFAULT 'open',     -- open | queued | printing | done | failed | cancelled
  outcome TEXT NOT NULL DEFAULT '',
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  queue_item_id INTEGER PRIMARY KEY,
  request_id INTEGER,
  name TEXT NOT NULL DEFAULT '',
  requester TEXT NOT NULL DEFAULT '',
  sliced_file_id INTEGER,
  eject_planned INTEGER NOT NULL DEFAULT 0,
  eject_reason TEXT NOT NULL DEFAULT '',
  max_z_mm REAL,
  state TEXT NOT NULL DEFAULT 'queued',    -- queued | printing | finished | failed | cancelled | cleared
  started_ts REAL,
  finished_ts REAL,
  outcome TEXT NOT NULL DEFAULT '',
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,                      -- finished | failed | paused | hms | offline | plate_clear | plate_not_clear | ...
  job_name TEXT NOT NULL DEFAULT '',
  payload TEXT NOT NULL DEFAULT '{}',
  owner_notified INTEGER NOT NULL DEFAULT 0,
  family_notified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS human_needed (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,                      -- see upgrades.KINDS
  detail TEXT NOT NULL DEFAULT '',
  job_name TEXT NOT NULL DEFAULT '',
  who TEXT NOT NULL DEFAULT '',            -- who had to act
  source TEXT NOT NULL DEFAULT 'agent',    -- agent | watcher | person
  resolved INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS upgrades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,                      -- human_needed kind it removes
  title TEXT NOT NULL,
  proposal TEXT NOT NULL DEFAULT '',
  model_ref TEXT NOT NULL DEFAULT '',      -- e.g. MakerWorld url of the parts to print
  evidence INTEGER NOT NULL DEFAULT 0,     -- number of human_needed moments behind it
  status TEXT NOT NULL DEFAULT 'proposed', -- proposed | accepted | printing | installed | rejected
  notes TEXT NOT NULL DEFAULT '',
  created REAL NOT NULL,
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  action TEXT NOT NULL,                    -- start | clear_plate
  target TEXT NOT NULL DEFAULT '',         -- queue item id or ''
  approver TEXT NOT NULL DEFAULT '',
  expires REAL NOT NULL,
  used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated REAL NOT NULL
);
"""

_lock = threading.Lock()


class Store:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else data_dir() / "workshop.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        try:
            yield conn
        finally:
            conn.close()

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with _lock, self._conn() as c:
            return c.execute(sql, params)

    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # ---- kv ---------------------------------------------------------------------------------
    def kv_get(self, key: str, default: Any = None) -> Any:
        rows = self._rows("SELECT value FROM kv WHERE key=?", (key,))
        if not rows:
            return default
        try:
            return json.loads(rows[0]["value"])
        except ValueError:
            return default

    def kv_set(self, key: str, value: Any) -> None:
        self._exec("INSERT INTO kv(key,value,updated) VALUES(?,?,?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
                   (key, json.dumps(value, ensure_ascii=False), time.time()))

    # ---- session -> sender (who is talking in this session) ----------------------------------
    def remember_sender(self, session_id: str, sender_id: str, platform: str = "") -> None:
        if session_id and sender_id:
            self.kv_set(f"sender:{session_id}", {"sender_id": sender_id, "platform": platform,
                                                  "ts": time.time()})

    def sender_for(self, session_id: Optional[str]) -> str:
        if not session_id:
            return ""
        v = self.kv_get(f"sender:{session_id}") or {}
        return str(v.get("sender_id", ""))

    # ---- requests ---------------------------------------------------------------------------
    def add_request(self, *, requester: str, text: str, channel: str = "text", sender_id: str = "",
                    model_ref: str = "") -> int:
        now = time.time()
        cur = self._exec("INSERT INTO requests(ts,requester,sender_id,channel,text,model_ref,updated) "
                         "VALUES(?,?,?,?,?,?,?)", (now, requester, sender_id, channel, text, model_ref, now))
        return int(cur.lastrowid)

    def update_request(self, request_id: int, **fields: Any) -> None:
        allowed = {"model_ref", "library_file_id", "sliced_file_id", "queue_item_id", "status", "outcome",
                   "requester", "text"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets) + ", updated=?"
        self._exec(f"UPDATE requests SET {cols} WHERE id=?", (*sets.values(), time.time(), request_id))

    def get_request(self, request_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM requests WHERE id=?", (request_id,))
        return rows[0] if rows else None

    def requests(self, requester: Optional[str] = None, limit: int = 20, status: Optional[str] = None) -> list[dict]:
        sql, params = "SELECT * FROM requests WHERE 1=1", []
        if requester:
            sql += " AND lower(requester)=lower(?)"
            params.append(requester)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        return self._rows(sql, tuple(params))

    def request_for_queue_item(self, queue_item_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM requests WHERE queue_item_id=? ORDER BY ts DESC LIMIT 1", (queue_item_id,))
        return rows[0] if rows else None

    # ---- jobs -------------------------------------------------------------------------------
    def upsert_job(self, queue_item_id: int, **fields: Any) -> None:
        allowed = {"request_id", "name", "requester", "sliced_file_id", "eject_planned", "eject_reason",
                   "max_z_mm", "state", "started_ts", "finished_ts", "outcome"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        now = time.time()
        self._exec("INSERT OR IGNORE INTO jobs(queue_item_id, updated) VALUES(?,?)", (queue_item_id, now))
        if sets:
            cols = ", ".join(f"{k}=?" for k in sets) + ", updated=?"
            self._exec(f"UPDATE jobs SET {cols} WHERE queue_item_id=?", (*sets.values(), now, queue_item_id))

    def get_job(self, queue_item_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM jobs WHERE queue_item_id=?", (queue_item_id,))
        return rows[0] if rows else None

    def job_by_name(self, name: str) -> Optional[dict]:
        if not name:
            return None
        rows = self._rows("SELECT * FROM jobs WHERE name=? ORDER BY updated DESC LIMIT 1", (name,))
        if rows:
            return rows[0]
        # Bambuddy reports the subtask name without the .gcode.3mf suffix
        rows = self._rows("SELECT * FROM jobs WHERE ? LIKE replace(replace(name,'.gcode.3mf',''),'.3mf','') || '%' "
                          "ORDER BY updated DESC LIMIT 1", (name,))
        return rows[0] if rows else None

    def jobs(self, state: Optional[str] = None, limit: int = 20) -> list[dict]:
        if state:
            return self._rows("SELECT * FROM jobs WHERE state=? ORDER BY updated DESC LIMIT ?", (state, limit))
        return self._rows("SELECT * FROM jobs ORDER BY updated DESC LIMIT ?", (limit,))

    # ---- events -----------------------------------------------------------------------------
    def add_event(self, kind: str, job_name: str = "", payload: Optional[dict] = None) -> int:
        cur = self._exec("INSERT INTO events(ts,kind,job_name,payload) VALUES(?,?,?,?)",
                         (time.time(), kind, job_name, json.dumps(payload or {}, ensure_ascii=False)))
        return int(cur.lastrowid)

    def mark_event_notified(self, event_id: int, *, owner: Optional[bool] = None, family: Optional[bool] = None) -> None:
        if owner is not None:
            self._exec("UPDATE events SET owner_notified=? WHERE id=?", (1 if owner else 0, event_id))
        if family is not None:
            self._exec("UPDATE events SET family_notified=? WHERE id=?", (1 if family else 0, event_id))

    def events(self, limit: int = 20, kind: Optional[str] = None) -> list[dict]:
        if kind:
            return self._rows("SELECT * FROM events WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))
        return self._rows("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))

    # ---- human-needed moments ---------------------------------------------------------------
    def add_human_needed(self, kind: str, detail: str = "", *, job_name: str = "", who: str = "",
                         source: str = "agent") -> int:
        cur = self._exec("INSERT INTO human_needed(ts,kind,detail,job_name,who,source) VALUES(?,?,?,?,?,?)",
                         (time.time(), kind, detail, job_name, who, source))
        return int(cur.lastrowid)

    def human_needed(self, kind: Optional[str] = None, since_days: Optional[float] = None,
                     limit: int = 50) -> list[dict]:
        sql, params = "SELECT * FROM human_needed WHERE 1=1", []
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        if since_days is not None:
            sql += " AND ts>=?"
            params.append(time.time() - since_days * 86400)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        return self._rows(sql, tuple(params))

    def human_needed_counts(self, since_days: float = 30) -> dict[str, int]:
        rows = self._rows("SELECT kind, count(*) AS n FROM human_needed WHERE ts>=? GROUP BY kind",
                          (time.time() - since_days * 86400,))
        return {r["kind"]: int(r["n"]) for r in rows}

    # ---- upgrades ---------------------------------------------------------------------------
    def add_upgrade(self, *, kind: str, title: str, proposal: str = "", model_ref: str = "",
                    evidence: int = 0, status: str = "proposed") -> int:
        now = time.time()
        cur = self._exec("INSERT INTO upgrades(kind,title,proposal,model_ref,evidence,status,created,updated) "
                         "VALUES(?,?,?,?,?,?,?,?)", (kind, title, proposal, model_ref, evidence, status, now, now))
        return int(cur.lastrowid)

    def update_upgrade(self, upgrade_id: int, **fields: Any) -> None:
        allowed = {"title", "proposal", "model_ref", "evidence", "status", "notes"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets) + ", updated=?"
        self._exec(f"UPDATE upgrades SET {cols} WHERE id=?", (*sets.values(), time.time(), upgrade_id))

    def upgrades(self, status: Optional[str] = None) -> list[dict]:
        if status:
            return self._rows("SELECT * FROM upgrades WHERE status=? ORDER BY updated DESC", (status,))
        return self._rows("SELECT * FROM upgrades ORDER BY updated DESC")

    def upgrade_for_kind(self, kind: str) -> Optional[dict]:
        rows = self._rows("SELECT * FROM upgrades WHERE kind=? AND status!='rejected' ORDER BY updated DESC LIMIT 1",
                          (kind,))
        return rows[0] if rows else None

    # ---- approvals --------------------------------------------------------------------------
    def grant_approval(self, action: str, target: str, approver: str, ttl_s: int = 900) -> int:
        now = time.time()
        cur = self._exec("INSERT INTO approvals(ts,action,target,approver,expires) VALUES(?,?,?,?,?)",
                         (now, action, str(target), approver, now + ttl_s))
        return int(cur.lastrowid)

    def consume_approval(self, action: str, target: str) -> Optional[dict]:
        """Use (once) a still-valid owner approval for ``action`` on ``target``."""
        now = time.time()
        with _lock, self._conn() as c:
            row = c.execute("SELECT * FROM approvals WHERE action=? AND target=? AND used=0 AND expires>=? "
                            "ORDER BY ts DESC LIMIT 1", (action, str(target), now)).fetchone()
            if row is None:
                return None
            c.execute("UPDATE approvals SET used=1 WHERE id=?", (row["id"],))
            return dict(row)

    def peek_approval(self, action: str, target: str) -> Optional[dict]:
        rows = self._rows("SELECT * FROM approvals WHERE action=? AND target=? AND used=0 AND expires>=? "
                          "ORDER BY ts DESC LIMIT 1", (action, str(target), time.time()))
        return rows[0] if rows else None
