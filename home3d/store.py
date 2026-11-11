"""Durable household memory (SQLite in the plugin data dir).

Tables:
  requests      who asked for what, through which channel, and how it ended
  jobs          queue items this plugin created/started (link to request, eject plan, outcome)
  events        watcher events (state changes) + whether owner/family were notified
  human_needed  moments where a person had to act (remove part, clean plate, swap filament, ...)
  upgrades      upgrade proposals derived from human_needed (proposed -> accepted -> printing -> installed)
  approvals     audit of owner approvals (legacy; nothing authorises an action from it any more)
  passes        single-use handler passes: (tool, target, session) the owner approved a moment ago
  approval_requests  a household member asked for a start / plate clear / resume the owner must approve; the
                watcher tells the owner once (it authorises nothing: the owner still sends /home3d approve ...)
  outbox        every notice as a durable record with its real delivery state (pending | sent | failed | no_target |
                dry_run), attempt count and last error; a failed send is retried on later watcher passes (notify.py)
  done_box      delivered parts: who each one is for, which group, the photo, how it left the plate, collected or not
  kv            small key/value state (watcher last state, session -> sender map, plate confirmations, ...)

Where a request came from (``requests.platform`` / ``chat_id`` / ``sender_id``, the same three on ``jobs`` for a job
queued without a request) decides which group hears about its job. Human-needed moments are open until the event
that resolves them (``resolve_human_needed``). Columns added after the first release are added to existing databases
by ``_migrate`` (``ALTER TABLE ... ADD COLUMN``), so an old database keeps working.

One connection per call site; WAL mode lets the watcher script and the gateway write concurrently. Anything
that must be single-use across processes (passes, approvals) runs in a ``BEGIN IMMEDIATE`` transaction and
checks the UPDATE rowcount, so two processes can never both use the same row.
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
CREATE TABLE IF NOT EXISTS passes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  tool TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '',         -- hooks.approval_target(): "7", "7+jump", '' for clear/resume
  session_id TEXT NOT NULL,
  expires REAL NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,         -- 0 live | 1 used | 2 superseded by a newer pass
  detail TEXT NOT NULL DEFAULT ''          -- what the owner saw, e.g. "hms_ack:<codes>" for a resume with an error
);
CREATE INDEX IF NOT EXISTS passes_key ON passes(tool, target, session_id, used);
CREATE TABLE IF NOT EXISTS approval_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  action TEXT NOT NULL,                    -- start | clear_plate | resume
  queue_item_id INTEGER,                   -- start only
  who TEXT NOT NULL DEFAULT '',            -- the household member's name
  sender_id TEXT NOT NULL DEFAULT '',
  session_id TEXT NOT NULL DEFAULT '',
  announced_ts REAL,                       -- the watcher told the owner (NULL: not yet)
  resolved_ts REAL,                        -- the action ran meanwhile (NULL: still open)
  outcome TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS approval_requests_open ON approval_requests(announced_ts, resolved_ts);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,                        -- queued (wall clock, for display)
  clock_ts REAL NOT NULL,                  -- queued on the watcher's clock (retry schedule, age cap)
  audience TEXT NOT NULL DEFAULT '',       -- owner | family | team (the tone of who is told)
  group_name TEXT NOT NULL DEFAULT '',     -- the configured group ('' = owner chat / family_target)
  target TEXT NOT NULL DEFAULT '',         -- hermes send target ('' = nowhere to send)
  kinds TEXT NOT NULL DEFAULT '',          -- event kinds in this message, comma separated
  job_name TEXT NOT NULL DEFAULT '',
  requester TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL DEFAULT '',
  media TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | failed | no_target | dry_run
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT NOT NULL DEFAULT '',
  last_attempt_ts REAL,                    -- wall clock
  next_try_clock REAL,                     -- watcher clock: not before this (NULL = as soon as possible)
  sent_ts REAL,                            -- wall clock of the send that succeeded
  surfaced INTEGER NOT NULL DEFAULT 0,     -- failed for good: the owner was told (once)
  refs TEXT NOT NULL DEFAULT '{}'          -- {"event_ids": [...], "approval_request_ids": [...]}
);
CREATE INDEX IF NOT EXISTS outbox_status ON outbox(status, id);
CREATE TABLE IF NOT EXISTS done_box (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,                        -- when the print finished
  queue_item_id INTEGER,                   -- the workshop job
  request_id INTEGER,
  job_name TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',          -- what was asked for (or the file name without its suffix)
  requester TEXT NOT NULL DEFAULT '',      -- who it is for ('' = nobody named)
  group_name TEXT NOT NULL DEFAULT '',     -- the group that was told ('' = none / the family chat)
  photo TEXT NOT NULL DEFAULT '',          -- path of the photo of the finished part
  left_plate TEXT NOT NULL DEFAULT 'unknown',  -- pushed_off | on_plate | taken_off | unknown (DONE_BOX_STATES)
  collected INTEGER NOT NULL DEFAULT 0,
  collected_ts REAL,
  collected_by TEXT NOT NULL DEFAULT '',
  updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS done_box_open ON done_box(collected, ts);
"""

# Columns added after the first release: (table, column, DDL). ``_migrate`` adds the missing ones.
_ADDED_COLUMNS = (
    ("passes", "detail", "TEXT NOT NULL DEFAULT ''"),
    ("requests", "platform", "TEXT NOT NULL DEFAULT ''"),  # where the request came from
    ("requests", "chat_id", "TEXT NOT NULL DEFAULT ''"),  # the chat or group it was sent in ('' = unknown)
    ("jobs", "platform", "TEXT NOT NULL DEFAULT ''"),  # who queued it and where (used when it has no request)
    ("jobs", "chat_id", "TEXT NOT NULL DEFAULT ''"),
    ("jobs", "sender_id", "TEXT NOT NULL DEFAULT ''"),
    ("human_needed", "resolved_ts", "REAL"),
    ("human_needed", "resolved_by", "TEXT NOT NULL DEFAULT ''"),  # the event that closed it
)

_lock = threading.Lock()

OUTBOX_STATUSES = ("pending", "sent", "failed", "no_target", "dry_run")
OUTBOX_KEEP_S = 30 * 86400  # settled outbox records are kept this long
DONE_BOX_STATES = ("pushed_off", "on_plate", "taken_off", "unknown")
# Human-needed kinds that are a state a person still has to resolve, and stay open until the resolving event.
# Everything else (and what the agent logs after the fact) is recorded closed: there is nothing left to wait for.
OPEN_KINDS = ("remove_part", "failure_check", "camera_check", "filament_swap", "approve_start")
PLATE_KINDS = ("remove_part", "failure_check", "camera_check")  # closed by a person's plate confirmation

ACTIVE_JOB_STATES = ("queued", "printing")
RECENT_JOB_S = 48 * 3600
APPROVAL_REQUEST_DEDUPE_S = 24 * 3600
PLATE_CONFIRM_TTL_S = 24 * 3600
_JOB_SUFFIXES = (".gcode.3mf", ".3mf", ".gcode")
_START_EVENTS = ("started", "start_requested")


def norm_job_name(name: object) -> str:
    """Job / file name for exact comparison: trim, lower, without ``.gcode.3mf`` / ``.3mf`` / ``.gcode``."""
    n = str(name or "").strip().lower()
    for suf in _JOB_SUFFIXES:
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
            break
    return n


def print_signature(status: Any) -> dict:
    """What tells one failed print from another of the same name on a printer that just says FAILED: the state,
    job name and where it stopped (layer, total layers, whole percent). Compared exactly (``plate_confirmed``)."""
    def num(v: Any) -> Optional[int]:
        try:
            return None if v is None else int(round(float(v)))
        except (TypeError, ValueError):
            return None
    return {"state": str(getattr(status, "state", "") or ""), "job": norm_job_name(getattr(status, "job_name", "")),
            "layer": num(getattr(status, "layer", None)), "total_layers": num(getattr(status, "total_layers", None)),
            "progress": num(getattr(status, "progress", None))}


class Store:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else data_dir() / "workshop.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)
            self._migrate(c)

    @staticmethod
    def _migrate(c: sqlite3.Connection) -> None:
        """Add the columns an older database does not have yet (``_ADDED_COLUMNS``). Existing rows keep working: a
        request without an origin is routed like before (by its requester's name)."""
        have: dict[str, set] = {}
        added: set[tuple[str, str]] = set()
        for table, column, ddl in _ADDED_COLUMNS:
            if table not in have:
                have[table] = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
            if column in have[table]:
                continue
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                added.add((table, column))
            except sqlite3.OperationalError:  # another process added it meanwhile
                pass
        if ("human_needed", "resolved_ts") in added:
            # Moments from before open/closed tracking were never closed. Only what the watcher (or an approval
            # that is still waiting) logged in the last day can still be waiting for a person; the rest is history.
            marks = ",".join("?" for _ in OPEN_KINDS)
            c.execute(f"UPDATE human_needed SET resolved=1, resolved_ts=ts, resolved_by=? WHERE resolved=0 AND NOT "
                      f"(ts>=? AND kind IN ({marks}) AND (source='watcher' OR kind='approve_start'))",
                      ("recorded before open/closed tracking", time.time() - 86400, *OPEN_KINDS))

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

    @contextmanager
    def _write_txn(self) -> Iterator[sqlite3.Connection]:
        """One ``BEGIN IMMEDIATE`` transaction: holds SQLite's write lock from the first read, across processes."""
        with _lock, self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            c.execute("COMMIT")

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

    def kv_delete(self, key: str) -> None:
        self._exec("DELETE FROM kv WHERE key=?", (key,))

    def kv_updated(self, key: str) -> Optional[float]:
        """When ``key`` was last written (epoch seconds), or None."""
        rows = self._rows("SELECT updated FROM kv WHERE key=?", (key,))
        try:
            return float(rows[0]["updated"]) if rows else None
        except (TypeError, ValueError):
            return None

    # ---- session -> sender (who is talking in this session) ----------------------------------
    def remember_sender(self, session_id: str, sender_id: str, platform: str = "", inherited_from: str = "",
                        chat_id: str = "") -> None:
        """Record who is speaking in ``session_id`` and in which chat. An empty ``sender_id`` records "unknown" (it
        clears an earlier speaker, so a later turn without an identity never acts as the previous one). ``chat_id``
        is the chat or group the turn came from ('' = not known): where a request made in this session came from."""
        if not session_id:
            return
        rec = {"sender_id": str(sender_id or ""), "platform": str(platform or ""), "ts": time.time()}
        if inherited_from:
            rec["inherited_from"] = str(inherited_from)
        if chat_id:
            rec["chat_id"] = str(chat_id)[:200]
        self.kv_set(f"sender:{session_id}", rec)

    def session_origin(self, session_id: Optional[str]) -> dict:
        """``{"platform", "chat_id", "sender_id"}`` of the session as the ``pre_llm_call`` hook recorded it (empty
        strings when unknown): what ``add_request`` / ``upsert_job`` store as the origin."""
        info = self.sender_info(session_id)
        return {"platform": str(info.get("platform") or ""), "chat_id": str(info.get("chat_id") or ""),
                "sender_id": str(info.get("sender_id") or "")}

    def sender_info(self, session_id: Optional[str]) -> dict:
        if not session_id:
            return {}
        v = self.kv_get(f"sender:{session_id}") or {}
        return v if isinstance(v, dict) else {}

    def sender_for(self, session_id: Optional[str]) -> str:
        return str(self.sender_info(session_id).get("sender_id") or "")

    def forget_sender(self, session_id: str) -> None:
        if session_id:
            self.kv_delete(f"sender:{session_id}")

    # ---- requests ---------------------------------------------------------------------------
    def add_request(self, *, requester: str, text: str, channel: str = "text", sender_id: str = "",
                    model_ref: str = "", platform: str = "", chat_id: str = "", session_id: str = "") -> int:
        """Record a request and where it came from. ``platform`` / ``chat_id`` / ``sender_id`` are the origin; what
        is not given is taken from the session (``session_origin(session_id)``: what the hook recorded for it)."""
        if session_id and not (platform and chat_id and sender_id):
            origin = self.session_origin(session_id)
            platform = platform or origin["platform"]
            chat_id = chat_id or origin["chat_id"]
            sender_id = sender_id or origin["sender_id"]
        now = time.time()
        cur = self._exec("INSERT INTO requests(ts,requester,sender_id,channel,text,model_ref,platform,chat_id,updated) "
                         "VALUES(?,?,?,?,?,?,?,?,?)", (now, requester, str(sender_id or ""), channel, text, model_ref,
                                                       str(platform or ""), str(chat_id or "")[:200], now))
        return int(cur.lastrowid)

    def update_request(self, request_id: int, **fields: Any) -> None:
        allowed = {"model_ref", "library_file_id", "sliced_file_id", "queue_item_id", "status", "outcome",
                   "requester", "text", "platform", "chat_id", "sender_id"}
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
                   "max_z_mm", "state", "started_ts", "finished_ts", "outcome", "platform", "chat_id", "sender_id"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        now = time.time()
        self._exec("INSERT OR IGNORE INTO jobs(queue_item_id, updated) VALUES(?,?)", (queue_item_id, now))
        if sets:
            cols = ", ".join(f"{k}=?" for k in sets) + ", updated=?"
            self._exec(f"UPDATE jobs SET {cols} WHERE queue_item_id=?", (*sets.values(), now, queue_item_id))

    def get_job(self, queue_item_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM jobs WHERE queue_item_id=?", (queue_item_id,))
        return rows[0] if rows else None

    job_for_queue_item = get_job

    def job_by_name(self, name: str) -> Optional[dict]:
        """The workshop job printing under ``name`` (Bambuddy reports it without the ``.gcode.3mf`` suffix).

        EXACT match on ``norm_job_name`` (no prefix / LIKE wildcards: ``kutu`` never matches ``kutuphane_rafi``).
        A printing job wins, then a queued one; otherwise the most recently updated one from the last 48 h; else None.
        """
        want = norm_job_name(name)
        if not want:
            return None
        placeholders = ",".join("?" for _ in ACTIVE_JOB_STATES)
        rows = self._rows(f"SELECT * FROM jobs WHERE state IN ({placeholders}) OR updated>=? "
                          "ORDER BY updated DESC, queue_item_id DESC LIMIT 1000",
                          (*ACTIVE_JOB_STATES, time.time() - RECENT_JOB_S))
        matches = [r for r in rows if norm_job_name(r.get("name")) == want]
        active = sorted((r for r in matches if r.get("state") in ACTIVE_JOB_STATES),
                        key=lambda r: r.get("state") != "printing")  # stable: newest first within a state
        pick = active or [r for r in matches if float(r.get("updated") or 0) >= time.time() - RECENT_JOB_S]
        return pick[0] if pick else None

    def active_job_ids(self) -> set[int]:
        """Queue item ids of workshop jobs still queued or printing (what "ours" means for the jump check)."""
        placeholders = ",".join("?" for _ in ACTIVE_JOB_STATES)
        rows = self._rows(f"SELECT queue_item_id FROM jobs WHERE state IN ({placeholders})", ACTIVE_JOB_STATES)
        return {int(r["queue_item_id"]) for r in rows if r.get("queue_item_id") is not None}

    def active_job_requesters(self) -> dict[int, str]:
        """Queue item id -> requester name ('' = nobody named, i.e. the owner) of the workshop jobs still queued or
        printing: whose job each "ours" item is (the start gate's jump check)."""
        placeholders = ",".join("?" for _ in ACTIVE_JOB_STATES)
        rows = self._rows(f"SELECT queue_item_id, requester FROM jobs WHERE state IN ({placeholders})",
                          ACTIVE_JOB_STATES)
        return {int(r["queue_item_id"]): str(r.get("requester") or "") for r in rows
                if r.get("queue_item_id") is not None}

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
                         source: str = "agent", is_open: Optional[bool] = None) -> int:
        """Record a moment a person had to step in. It is OPEN (a person still has to act) when the watcher saw the
        state (``source="watcher"``) or it is an approval that is still waiting (``approve_start``), and its kind
        has a resolving event (``OPEN_KINDS``); what the agent or a person logs after the fact is recorded closed.
        ``is_open`` overrides that. An open moment is closed by ``resolve_human_needed``."""
        if is_open is None:
            is_open = kind in OPEN_KINDS and (source == "watcher" or kind == "approve_start")
        now = time.time()
        cur = self._exec("INSERT INTO human_needed(ts,kind,detail,job_name,who,source,resolved,resolved_ts,resolved_by)"
                         " VALUES(?,?,?,?,?,?,?,?,?)",
                         (now, kind, detail, job_name, who, source, 0 if is_open else 1, None if is_open else now,
                          "" if is_open else "logged after the fact"))
        return int(cur.lastrowid)

    def human_needed(self, kind: Optional[str] = None, since_days: Optional[float] = None,
                     limit: int = 50, open_only: bool = False) -> list[dict]:
        sql, params = "SELECT * FROM human_needed WHERE 1=1", []
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        if since_days is not None:
            sql += " AND ts>=?"
            params.append(time.time() - since_days * 86400)
        if open_only:
            sql += " AND resolved=0"
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        return self._rows(sql, tuple(params))

    def open_human_needed(self, limit: int = 50) -> list[dict]:
        """The moments still waiting for a person, newest first (each row: id, ts, kind, detail, job_name, who,
        source). A row leaves this list when its resolving event happens (``resolve_human_needed``)."""
        return self.human_needed(limit=limit, open_only=True)

    def resolve_human_needed(self, kinds: Any = None, by: str = "", *, job_name: Optional[str] = None,
                             moment_id: Optional[int] = None) -> int:
        """Close the open moments of ``kinds`` (None = every kind) because the event ``by`` resolved them (e.g.
        "plate confirmed clear by Sam", "print resumed"). ``job_name`` narrows it to one job (exact, normalised
        name), ``moment_id`` to one row. Returns how many were closed; a closed moment is never closed again."""
        sql, params = "SELECT id, job_name FROM human_needed WHERE resolved=0", []
        names = [str(k) for k in ([kinds] if isinstance(kinds, str) else list(kinds or []))]
        if names:
            sql += f" AND kind IN ({','.join('?' for _ in names)})"
            params += names
        if moment_id is not None:
            sql += " AND id=?"
            params.append(int(moment_id))
        with self._write_txn() as c:
            ids = [r["id"] for r in c.execute(sql, tuple(params)).fetchall()
                   if job_name is None or norm_job_name(r["job_name"]) == norm_job_name(job_name)]
            now = time.time()
            for i in ids:
                c.execute("UPDATE human_needed SET resolved=1, resolved_ts=?, resolved_by=? WHERE id=? AND resolved=0",
                          (now, str(by or "resolved")[:200], i))
        return len(ids)

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

    # ---- plate confirmations (after a failed print a person says the plate is clear) ------------
    def confirm_plate(self, job_name: str, by: str, status: Any = None) -> None:
        """A person confirmed the plate is clear after ``job_name`` (owner ``/home3d approve clear``). This also
        settles any unconfirmed failure (``unconfirmed_failure``): a person has looked at the plate now. ``status``
        (the printer status the confirmation was made on) is remembered as the print's signature (``print_sig``):
        on a printer that says FAILED, only a confirmation made on that same failed print counts."""
        rec = {"job_name": str(job_name or ""), "by": str(by or ""), "ts": time.time()}
        if status is not None:
            rec["print_sig"] = print_signature(status)
        self.kv_set(f"plate_confirmed:{norm_job_name(job_name)}", rec)
        self.clear_failure(f"plate confirmed by {by or 'owner'}")
        # the moments that were waiting for exactly this (part on the plate, failed print, camera unsure) are closed
        self.resolve_human_needed(PLATE_KINDS, f"plate confirmed clear by {by or 'owner'}")
        self.plate_emptied()

    def plate_emptied(self) -> int:
        """The plate is empty now (a person confirmed it, or the camera saw it): done-box parts that were waiting
        on the plate were taken off by a person. Returns how many records changed."""
        cur = self._exec("UPDATE done_box SET left_plate='taken_off', updated=? WHERE left_plate='on_plate'",
                         (time.time(),))
        return int(cur.rowcount or 0)

    # ---- failed prints nobody has confirmed yet ----------------------------------------------------
    # The printer forgets a failure (a power cycle or a cancel ends in IDLE, an empty job name), so the start gate
    # cannot rely on ``state == FAILED``. The watcher records every failure it sees; only a person's plate
    # confirmation (``confirm_plate``) or a new print starting settles it.
    def record_failure(self, job_name: str, source: str = "watcher", reason: str = "") -> None:
        self.kv_set("failure:last", {"job_name": str(job_name or ""), "source": str(source or ""),
                                     "reason": str(reason or "")[:200], "ts": time.time()})

    def unconfirmed_failure(self) -> Optional[dict]:
        """The last failed print nobody has confirmed the plate of since (``{"job_name", "ts", ...}``), or None."""
        rec = self.kv_get("failure:last")
        if not isinstance(rec, dict) or rec.get("settled"):
            return None
        return rec

    def clear_failure(self, why: str = "") -> None:
        rec = self.kv_get("failure:last")
        if isinstance(rec, dict) and not rec.get("settled"):
            rec.update(settled=str(why or "settled")[:120], settled_ts=time.time())
            self.kv_set("failure:last", rec)

    def plate_confirmed(self, job_name: str, status: Any = None) -> bool:
        """A confirmation exists for exactly this (normalised) job name, made after its latest start and within the
        last 24 h. A later start of the same name (or of anything, for an unnamed job) voids it: it was about an
        earlier print. ``status`` (the printer now): when it says FAILED, the confirmation must have been made on
        this very failed print (same ``print_signature``): a same-name print that failed later (an archive reprint
        nobody here saw start) is not covered by it. Fails closed (no signature recorded: not confirmed)."""
        want = norm_job_name(job_name)
        rec = self.kv_get(f"plate_confirmed:{want}")
        if not isinstance(rec, dict):
            return False
        try:
            ts = float(rec.get("ts"))
        except (TypeError, ValueError):
            return False
        if ts < time.time() - PLATE_CONFIRM_TTL_S:
            return False
        if status is not None and str(getattr(status, "state", "") or "") == "FAILED":
            if rec.get("print_sig") != print_signature(status):
                return False
        placeholders = ",".join("?" for _ in _START_EVENTS)
        later = [r["job_name"] for r in self._rows(
            f"SELECT job_name FROM events WHERE kind IN ({placeholders}) AND ts>?", (*_START_EVENTS, ts))]
        later += [r["name"] for r in self._rows("SELECT name FROM jobs WHERE started_ts>?", (ts,))]
        return not any(not want or norm_job_name(n) == want for n in later)

    # ---- handler passes (single use, bound to tool + target + session) ------------------------
    def issue_pass(self, tool: str, target: str, session_id: str, ttl_s: int = 600, detail: str = "") -> None:
        """Let ONE call of ``tool`` on ``target`` from ``session_id`` through the handler within ``ttl_s``.

        Issued by the ``pre_tool_call`` hook (owner session, gates passed) and by ``/home3d approve``. A newer pass
        for the same key supersedes the older one, so at most one is ever live. No session, no pass. ``detail``
        records what the owner approved beyond the target (``"hms_ack:<codes>"``); ``take_pass`` returns it.
        """
        if not tool or not session_id:
            return
        now = time.time()
        with self._write_txn() as c:
            c.execute("DELETE FROM passes WHERE expires<? OR (used!=0 AND ts<?)", (now - 86400, now - 86400))
            c.execute("UPDATE passes SET used=2 WHERE tool=? AND target=? AND session_id=? AND used=0",
                      (tool, str(target or ""), session_id))
            c.execute("INSERT INTO passes(ts,tool,target,session_id,expires,detail) VALUES(?,?,?,?,?,?)",
                      (now, tool, str(target or ""), session_id, now + max(1, int(ttl_s)), str(detail or "")))

    def take_pass(self, tool: str, target: str, session_id: str) -> Optional[dict]:
        """Use the live pass for (tool, target, session) once and return ``{"detail": ...}``; None when there is
        none or it expired. Atomic across processes."""
        if not tool or not session_id:
            return None
        with self._write_txn() as c:
            row = c.execute("SELECT id, detail FROM passes WHERE tool=? AND target=? AND session_id=? AND used=0 "
                            "AND expires>=? ORDER BY id DESC LIMIT 1",
                            (tool, str(target or ""), session_id, time.time())).fetchone()
            if row is None:
                return None
            cur = c.execute("UPDATE passes SET used=1 WHERE id=? AND used=0", (row["id"],))
            return {"detail": str(row["detail"] or "")} if cur.rowcount == 1 else None

    def consume_pass(self, tool: str, target: str, session_id: str) -> bool:
        """Use the live pass for (tool, target, session) once. Atomic across processes; False when none/expired."""
        return self.take_pass(tool, target, session_id) is not None

    def peek_pass(self, tool: str, target: str, session_id: str) -> bool:
        rows = self._rows("SELECT id FROM passes WHERE tool=? AND target=? AND session_id=? AND used=0 AND expires>=?",
                          (tool, str(target or ""), session_id, time.time()))
        return bool(rows)

    # ---- approvals (audit only: no code path authorises an action from this table) -------------
    def grant_approval(self, action: str, target: str, approver: str, ttl_s: int = 900) -> int:
        now = time.time()
        cur = self._exec("INSERT INTO approvals(ts,action,target,approver,expires) VALUES(?,?,?,?,?)",
                         (now, action, str(target), approver, now + ttl_s))
        return int(cur.lastrowid)

    def consume_approval(self, action: str, target: str) -> Optional[dict]:
        """Mark (once) a still-valid approval row used. Atomic across processes. Audit only."""
        now = time.time()
        with self._write_txn() as c:
            row = c.execute("SELECT * FROM approvals WHERE action=? AND target=? AND used=0 AND expires>=? "
                            "ORDER BY ts DESC LIMIT 1", (action, str(target), now)).fetchone()
            if row is None:
                return None
            cur = c.execute("UPDATE approvals SET used=1 WHERE id=? AND used=0", (row["id"],))
            return dict(row) if cur.rowcount == 1 else None

    def peek_approval(self, action: str, target: str) -> Optional[dict]:
        rows = self._rows("SELECT * FROM approvals WHERE action=? AND target=? AND used=0 AND expires>=? "
                          "ORDER BY ts DESC LIMIT 1", (action, str(target), time.time()))
        return rows[0] if rows else None

    # ---- family approval requests (the hook records them, the watcher tells the owner) ------------------------
    @staticmethod
    def _request_key(action: str, queue_item_id: Optional[int]) -> tuple[str, Optional[int]]:
        qid = None
        if queue_item_id is not None and not isinstance(queue_item_id, bool):
            try:
                qid = int(queue_item_id)
            except (TypeError, ValueError):
                qid = None
        return str(action or "").strip().lower(), qid

    def add_approval_request(self, action: str, queue_item_id: Optional[int], who: str, session_id: str = "", *,
                             sender_id: str = "", dedupe_s: float = APPROVAL_REQUEST_DEDUPE_S) -> Optional[int]:
        """Record that ``who`` (a household member) asked for ``action`` (start / clear_plate / resume) on
        ``queue_item_id`` (start only). Returns the new id, or None when the same person asked for the same action
        and item within ``dedupe_s`` and that ask is still open (one open request per action + item + person per
        day; once the owner settled it, a new ask is a new request). Authorises nothing."""
        action, qid = self._request_key(action, queue_item_id)
        name = str(who or "").strip()
        if not action:
            return None
        now = time.time()
        with self._write_txn() as c:
            row = c.execute("SELECT id FROM approval_requests WHERE action=? AND queue_item_id IS ? "
                            "AND lower(who)=lower(?) AND ts>=? AND resolved_ts IS NULL ORDER BY id DESC LIMIT 1",
                            (action, qid, name, now - max(0.0, float(dedupe_s)))).fetchone()
            if row is not None:
                return None
            cur = c.execute("INSERT INTO approval_requests(ts,action,queue_item_id,who,sender_id,session_id) "
                            "VALUES(?,?,?,?,?,?)", (now, action, qid, name, str(sender_id or ""),
                                                    str(session_id or "")))
            return int(cur.lastrowid)

    def latest_approval_request(self, action: str, queue_item_id: Optional[int], who: str,
                                within_s: float = APPROVAL_REQUEST_DEDUPE_S) -> Optional[dict]:
        """The newest still-open request for (action, item, person) made within ``within_s``, or None."""
        action, qid = self._request_key(action, queue_item_id)
        rows = self._rows("SELECT * FROM approval_requests WHERE action=? AND queue_item_id IS ? "
                          "AND lower(who)=lower(?) AND ts>=? AND resolved_ts IS NULL ORDER BY id DESC LIMIT 1",
                          (action, qid, str(who or "").strip(), time.time() - max(0.0, float(within_s))))
        return rows[0] if rows else None

    def pending_approval_requests(self, max_age_s: float = APPROVAL_REQUEST_DEDUPE_S) -> list[dict]:
        """Requests the owner has not been told about yet (and that did not run meanwhile), oldest first. Requests
        older than ``max_age_s`` are not announced any more (a watcher that was off for days stays quiet)."""
        return self._rows("SELECT * FROM approval_requests WHERE announced_ts IS NULL AND resolved_ts IS NULL "
                          "AND ts>=? ORDER BY id", (time.time() - max(0.0, float(max_age_s)),))

    def mark_approval_request_announced(self, request_id: int) -> bool:
        """The watcher told the owner (once). False when it was already announced or does not exist."""
        cur = self._exec("UPDATE approval_requests SET announced_ts=? WHERE id=? AND announced_ts IS NULL",
                         (time.time(), int(request_id)))
        return cur.rowcount == 1

    def resolve_approval_requests(self, action: str, queue_item_id: Optional[int] = None,
                                  outcome: str = "") -> int:
        """The owner ran ``action`` (on ``queue_item_id`` for a start): open requests for it are settled and never
        announced again. Returns how many were settled."""
        action, qid = self._request_key(action, queue_item_id)
        cur = self._exec("UPDATE approval_requests SET resolved_ts=?, outcome=? WHERE action=? AND queue_item_id IS ? "
                         "AND resolved_ts IS NULL", (time.time(), str(outcome or "")[:200], action, qid))
        # the same event closes the human-needed moment that was waiting for it
        moment = {"start": ("approve_start",), "resume": ("filament_swap",)}.get(action)
        if moment:
            self.resolve_human_needed(moment, str(outcome or "") or ("start approved" if action == "start"
                                                                    else "print resumed"))
        return int(cur.rowcount or 0)

    def close_approval_request(self, request_id: int, outcome: str = "") -> bool:
        """Settle ONE open approval request without the action having run (e.g. the owner could not be told about
        it): the person may ask again, which is a new request. False when it was already settled."""
        cur = self._exec("UPDATE approval_requests SET resolved_ts=?, outcome=? WHERE id=? AND resolved_ts IS NULL",
                         (time.time(), str(outcome or "")[:200], int(request_id)))
        return cur.rowcount == 1

    def approval_requests(self, limit: int = 20) -> list[dict]:
        return self._rows("SELECT * FROM approval_requests ORDER BY id DESC LIMIT ?", (int(limit),))

    # ---- outbox: every notice with its real delivery state (notify.py sends and settles) --------------------
    def outbox_add(self, *, audience: str, target: str, text: str, media: str = "", kinds: Any = (),
                   job_name: str = "", requester: str = "", group: str = "", refs: Optional[dict] = None,
                   status: str = "pending", clock: Optional[float] = None) -> int:
        """Queue one notice. ``status``: "pending" (to be sent), "no_target" (nowhere to send: never "notified") or
        "dry_run" (a dry run: nothing is sent). ``clock`` is the watcher's clock (the retry schedule runs on it).
        Settled records older than ``OUTBOX_KEEP_S`` are dropped here."""
        if status not in OUTBOX_STATUSES:
            status = "pending"
        now = time.time()
        clock_ts = float(clock) if clock is not None else now
        names = ",".join(dict.fromkeys(str(k) for k in ([kinds] if isinstance(kinds, str) else kinds or []) if k))
        with self._write_txn() as c:
            c.execute("DELETE FROM outbox WHERE status!='pending' AND ts<? AND NOT (status='failed' AND surfaced=0)",
                      (now - OUTBOX_KEEP_S,))
            cur = c.execute(
                "INSERT INTO outbox(ts,clock_ts,audience,group_name,target,kinds,job_name,requester,text,media,status,"
                "refs) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (now, clock_ts, str(audience or ""), str(group or ""), str(target or "").strip(), names,
                 str(job_name or ""), str(requester or ""), str(text or ""), str(media or ""), status,
                 json.dumps(refs or {}, ensure_ascii=False)))
            return int(cur.lastrowid)

    @staticmethod
    def _outbox_row(row: Any) -> dict:
        rec = dict(row)
        try:
            refs = json.loads(rec.get("refs") or "{}")
        except ValueError:
            refs = {}
        rec["refs"] = refs if isinstance(refs, dict) else {}
        rec["kinds"] = [k for k in str(rec.get("kinds") or "").split(",") if k]
        return rec

    def outbox_get(self, record_id: int) -> Optional[dict]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM outbox WHERE id=?", (int(record_id),)).fetchone()
        return self._outbox_row(row) if row is not None else None

    def outbox(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Outbox records, newest first (``status``: one of ``OUTBOX_STATUSES``, None = all). Each row: id, ts,
        audience, group_name, target, kinds (list), job_name, requester, text, media, status, attempts, last_error,
        last_attempt_ts, next_try_clock, sent_ts, surfaced, refs (dict)."""
        with self._conn() as c:
            if status:
                rows = c.execute("SELECT * FROM outbox WHERE status=? ORDER BY id DESC LIMIT ?",
                                 (status, int(limit))).fetchall()
            else:
                rows = c.execute("SELECT * FROM outbox ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [self._outbox_row(r) for r in rows]

    def outbox_pending(self, limit: int = 200) -> list[dict]:
        """The records still to be sent, oldest first (the order they are sent in)."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY id LIMIT ?",
                             (int(limit),)).fetchall()
        return [self._outbox_row(r) for r in rows]

    def outbox_counts(self) -> dict[str, int]:
        """``{status: number of records}`` for every status in ``OUTBOX_STATUSES`` (0 when there are none)."""
        rows = self._rows("SELECT status, count(*) AS n FROM outbox GROUP BY status")
        counts = {s: 0 for s in OUTBOX_STATUSES}
        counts.update({str(r["status"]): int(r["n"]) for r in rows})
        return counts

    def outbox_settle(self, record_id: int, status: str, *, error: str = "", attempted: bool = True,
                      next_try_clock: Optional[float] = None) -> bool:
        """Write the result of one delivery attempt on a PENDING record: ``sent`` (records ``sent_ts``), ``pending``
        again with the error and ``next_try_clock`` (a retry), ``failed`` (given up), ``no_target`` or ``dry_run``.
        ``attempted`` counts the attempt. False when the record is not pending any more (another pass settled it)."""
        if status not in OUTBOX_STATUSES:
            return False
        now = time.time()
        cur = self._exec(
            "UPDATE outbox SET status=?, attempts=attempts+?, last_error=?, last_attempt_ts=CASE WHEN ? THEN ? ELSE "
            "last_attempt_ts END, next_try_clock=?, sent_ts=CASE WHEN ?='sent' THEN ? ELSE sent_ts END "
            "WHERE id=? AND status='pending'",
            (status, 1 if attempted else 0, "" if status == "sent" else str(error or "")[:300],
             1 if attempted else 0, now, next_try_clock if status == "pending" else None, status, now,
             int(record_id)))
        return cur.rowcount == 1

    def outbox_unsurfaced_failures(self, limit: int = 20) -> list[dict]:
        """Records given up on that the owner has not been told about yet, oldest first."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM outbox WHERE status='failed' AND surfaced=0 ORDER BY id LIMIT ?",
                             (int(limit),)).fetchall()
        return [self._outbox_row(r) for r in rows]

    def outbox_mark_surfaced(self, record_ids: Any) -> None:
        for rid in record_ids or []:
            self._exec("UPDATE outbox SET surfaced=1 WHERE id=?", (int(rid),))

    def outbox_open_refs(self, key: str) -> set[int]:
        """Ids listed under ``refs[key]`` of the records still pending (e.g. the approval requests a message that
        has not gone out yet is about: the watcher does not write a second message for them)."""
        out: set[int] = set()
        for rec in self.outbox_pending():
            for v in rec["refs"].get(key) or []:
                try:
                    out.add(int(v))
                except (TypeError, ValueError):
                    continue
        return out

    # ---- done box: delivered parts a person collects ------------------------------------------------------------
    def record_done_part(self, queue_item_id: Optional[int], *, job_name: str = "", title: str = "",
                         requester: str = "", group: str = "", photo: str = "", left_plate: str = "unknown",
                         request_id: Optional[int] = None, ts: Optional[float] = None) -> int:
        """Record (or update) the finished part of a workshop job: who it is for, which group was told, the photo and
        how it left the plate (``DONE_BOX_STATES``: pushed_off = the end G-code pushed it into the done box, on_plate
        = it waits on the plate for a person, taken_off = a person took it off the plate, unknown). One record per
        queue item: a later call updates it (an empty ``photo`` / ``group`` / ``requester`` never erases a known
        one) and never touches ``collected``. Returns the record id."""
        state = left_plate if left_plate in DONE_BOX_STATES else "unknown"
        now = time.time()
        with self._write_txn() as c:
            row = None
            if queue_item_id is not None:
                row = c.execute("SELECT * FROM done_box WHERE queue_item_id=? ORDER BY id DESC LIMIT 1",
                                (int(queue_item_id),)).fetchone()
            if row is None:
                cur = c.execute(
                    "INSERT INTO done_box(ts,queue_item_id,request_id,job_name,title,requester,group_name,photo,"
                    "left_plate,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (float(ts) if ts is not None else now, queue_item_id, request_id, str(job_name or ""),
                     str(title or ""), str(requester or ""), str(group or ""), str(photo or ""), state, now))
                return int(cur.lastrowid)
            c.execute("UPDATE done_box SET job_name=?, title=?, requester=?, group_name=?, photo=?, left_plate=?, "
                      "request_id=?, updated=? WHERE id=?",
                      (str(job_name or "") or row["job_name"], str(title or "") or row["title"],
                       str(requester or "") or row["requester"], str(group or "") or row["group_name"],
                       str(photo or "") or row["photo"], state,
                       request_id if request_id is not None else row["request_id"], now, row["id"]))
            return int(row["id"])

    def set_done_part_state(self, queue_item_id: int, left_plate: str) -> bool:
        """Update how the part of ``queue_item_id`` left the plate (it was pushed off after all, a person took it
        off). False when there is no record for it."""
        if left_plate not in DONE_BOX_STATES:
            return False
        cur = self._exec("UPDATE done_box SET left_plate=?, updated=? WHERE id=(SELECT id FROM done_box WHERE "
                         "queue_item_id=? ORDER BY id DESC LIMIT 1)", (left_plate, time.time(), int(queue_item_id)))
        return cur.rowcount == 1

    def done_box(self, collected: Optional[bool] = None, requester: Optional[str] = None,
                 group: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Delivered parts, newest first. ``collected=False``: what still waits to be picked up. Each row: id, ts,
        queue_item_id, request_id, job_name, title, requester, group_name, photo, left_plate, collected (0/1),
        collected_ts, collected_by, updated."""
        sql, params = "SELECT * FROM done_box WHERE 1=1", []
        if collected is not None:
            sql += " AND collected=?"
            params.append(1 if collected else 0)
        if requester:
            sql += " AND lower(requester)=lower(?)"
            params.append(str(requester))
        if group:
            sql += " AND lower(group_name)=lower(?)"
            params.append(str(group))
        sql += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(int(limit))
        return self._rows(sql, tuple(params))

    def get_done_part(self, part_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM done_box WHERE id=?", (int(part_id),))
        return rows[0] if rows else None

    def set_collected(self, part_id: int, collected: bool = True, by: str = "") -> bool:
        """Mark a done-box part collected (or put it back with ``collected=False``). ``by`` is who took it. False
        when there is no such part."""
        now = time.time()
        cur = self._exec("UPDATE done_box SET collected=?, collected_ts=?, collected_by=?, updated=? WHERE id=?",
                         (1 if collected else 0, now if collected else None, str(by or "") if collected else "",
                          now, int(part_id)))
        return cur.rowcount == 1
