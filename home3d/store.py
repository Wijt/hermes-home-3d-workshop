"""Durable household memory (SQLite in the plugin data dir).

Tables:
  requests      who asked for what, through which channel, and how it ended
  jobs          queue items this plugin created/started (link to request, eject plan, outcome)
  events        watcher events (state changes) + whether owner/family were notified
  human_needed  moments where a person had to act (remove part, clean plate, swap filament, ...)
  upgrades      upgrade proposals derived from human_needed (proposed -> accepted -> printing -> installed)
  approvals     audit of owner approvals (legacy; nothing authorises an action from it any more)
  passes        single-use handler passes: (tool, target, session) the owner approved a moment ago
  kv            small key/value state (watcher last state, session -> sender map, plate confirmations, ...)

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
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated REAL NOT NULL
);
"""

_lock = threading.Lock()

ACTIVE_JOB_STATES = ("queued", "printing")
RECENT_JOB_S = 48 * 3600
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


class Store:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else data_dir() / "workshop.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)
            cols = {r["name"] for r in c.execute("PRAGMA table_info(passes)").fetchall()}
            if "detail" not in cols:  # a database from before fix round 2
                try:
                    c.execute("ALTER TABLE passes ADD COLUMN detail TEXT NOT NULL DEFAULT ''")
                except sqlite3.OperationalError:  # another process added it meanwhile
                    pass

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
    def remember_sender(self, session_id: str, sender_id: str, platform: str = "", inherited_from: str = "") -> None:
        """Record who is speaking in ``session_id``. An empty ``sender_id`` records "unknown" (it clears an earlier
        speaker, so a later turn without an identity never acts as the previous one)."""
        if not session_id:
            return
        rec = {"sender_id": str(sender_id or ""), "platform": str(platform or ""), "ts": time.time()}
        if inherited_from:
            rec["inherited_from"] = str(inherited_from)
        self.kv_set(f"sender:{session_id}", rec)

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

    # ---- plate confirmations (after a failed print a person says the plate is clear) ------------
    def confirm_plate(self, job_name: str, by: str) -> None:
        """A person confirmed the plate is clear after ``job_name`` (owner ``/home3d approve clear``). This also
        settles any unconfirmed failure (``unconfirmed_failure``): a person has looked at the plate now."""
        self.kv_set(f"plate_confirmed:{norm_job_name(job_name)}",
                    {"job_name": str(job_name or ""), "by": str(by or ""), "ts": time.time()})
        self.clear_failure(f"plate confirmed by {by or 'owner'}")

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

    def plate_confirmed(self, job_name: str) -> bool:
        """A confirmation exists for exactly this (normalised) job name, made after its latest start and within the
        last 24 h. A later start of the same name (or of anything, for an unnamed job) voids it: it was about an
        earlier print."""
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
