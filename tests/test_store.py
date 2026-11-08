"""store.py: single-use handler passes (atomic across processes), exact job lookup, plate confirmations,
session senders (no Hermes)."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from home3d_ws.home3d import store as store_mod
from home3d_ws.home3d.store import Store, norm_job_name

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store():
    return Store()


# ---- handler passes ----------------------------------------------------------------------------------
def test_pass_is_single_use_and_bound_to_tool_target_session(store):
    store.issue_pass("home3d_start", "7", "s-owner")
    assert not store.consume_pass("home3d_start", "8", "s-owner")  # another queue item
    assert not store.consume_pass("home3d_start", "7+jump", "s-owner")  # a jump is its own approval
    assert not store.consume_pass("home3d_start", "7", "s-mum")  # another session
    assert not store.consume_pass("home3d_stop", "7", "s-owner")  # another tool
    assert store.peek_pass("home3d_start", "7", "s-owner")
    assert store.consume_pass("home3d_start", "7", "s-owner")
    assert not store.consume_pass("home3d_start", "7", "s-owner")  # used up
    assert not store.peek_pass("home3d_start", "7", "s-owner")


def test_pass_expires_and_needs_a_session(store, monkeypatch):
    store.issue_pass("home3d_stop", "", "s1", ttl_s=60)
    real = time.time
    monkeypatch.setattr(store_mod.time, "time", lambda: real() + 61)
    assert not store.consume_pass("home3d_stop", "", "s1")
    monkeypatch.setattr(store_mod.time, "time", real)
    store.issue_pass("home3d_stop", "", "")  # no session: nothing is issued
    assert not store.consume_pass("home3d_stop", "", "")
    assert not store.consume_pass("", "", "s1")


def test_newer_pass_supersedes_the_older_one(store):
    store.issue_pass("home3d_clear_plate", "", "s1")
    store.issue_pass("home3d_clear_plate", "", "s1")
    assert store.consume_pass("home3d_clear_plate", "", "s1")
    assert not store.consume_pass("home3d_clear_plate", "", "s1")  # never two live passes for one key


def test_pass_single_use_across_threads(store):
    store.issue_pass("home3d_start", "7", "s1")
    results: list[bool] = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(store.consume_pass("home3d_start", "7", "s1"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1


_CHILD = r"""
import importlib.util, sys, time
from pathlib import Path
root, db, what, t0 = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], float(sys.argv[4])
spec = importlib.util.spec_from_file_location("home3d_ws", root / "__init__.py", submodule_search_locations=[str(root)])
mod = importlib.util.module_from_spec(spec)
sys.modules["home3d_ws"] = mod
spec.loader.exec_module(mod)
from home3d_ws.home3d.store import Store
s = Store(db)
while time.time() < t0:
    time.sleep(0.001)
if what == "pass":
    print("1" if s.consume_pass("home3d_stop", "", "s-owner") else "0")
else:
    print("1" if s.consume_approval("resume", "") else "0")
"""


@pytest.mark.parametrize("what", ["pass", "approval"])
def test_single_use_across_processes(tmp_path, what):
    """The gateway and a CLI process share the DB: exactly one of them may use a pass / approval row."""
    db = tmp_path / "shared.db"
    s = Store(db)
    if what == "pass":
        s.issue_pass("home3d_stop", "", "s-owner")
    else:
        s.grant_approval("resume", "", "Sam")
    script = tmp_path / "child.py"
    script.write_text(_CHILD, encoding="utf-8")
    t0 = time.time() + 1.5
    procs = [subprocess.Popen([sys.executable, "-I", str(script), str(ROOT), str(db), what, str(t0)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
    outs = [p.communicate(timeout=60) for p in procs]
    assert all(p.returncode == 0 for p in procs), [o[1][-500:] for o in outs]
    assert [o[0].strip() for o in outs].count("1") == 1


def test_consume_approval_is_audit_only_and_single_use(store):
    store.grant_approval("start", "7", "Sam")
    assert store.consume_approval("start", "7")["approver"] == "Sam"
    assert store.consume_approval("start", "7") is None and store.peek_approval("start", "7") is None


# ---- job lookup ----------------------------------------------------------------------------------------
def test_norm_job_name():
    assert norm_job_name("  Kutu_Kapak.gcode.3mf ") == "kutu_kapak"
    assert norm_job_name("vase.3mf") == "vase" and norm_job_name("x.gcode") == "x" and norm_job_name(None) == ""


def test_job_by_name_is_exact_no_wildcards(store):
    """The review: ``LIKE 'kutu%'`` pinned kutuphane_rafi and kutu_kapak_v2 on Mum's old job."""
    store.upsert_job(5, name="kutu.gcode.3mf", requester="Mum", state="cleared", eject_planned=1)
    for other in ("kutuphane_rafi", "kutu_kapak_v2", "kutu_", "kut", "kutu%", "k_tu", "_utu", "%"):
        assert store.job_by_name(other) is None, other
    assert store.job_by_name("kutu")["queue_item_id"] == 5
    assert store.job_by_name("KUTU.gcode.3mf")["queue_item_id"] == 5
    assert store.job_by_name("") is None and store.job_by_name(None) is None


def test_job_by_name_prefers_active_then_recent_within_48h(store, monkeypatch):
    store.upsert_job(1, name="vase.gcode.3mf", requester="Dad", state="finished")
    store.upsert_job(2, name="vase.gcode.3mf", requester="Mum", state="queued")
    store.upsert_job(3, name="Vase", requester="Sam", state="printing")
    assert store.job_by_name("vase")["queue_item_id"] == 3  # printing beats queued beats finished
    store.upsert_job(3, state="finished")
    assert store.job_by_name("vase")["queue_item_id"] == 2
    store.upsert_job(2, state="cancelled")
    assert store.job_by_name("vase")["queue_item_id"] in (2, 3)  # most recently updated, both within 48 h
    real = time.time
    monkeypatch.setattr(store_mod.time, "time", lambda: real() + 49 * 3600)
    assert store.job_by_name("vase") is None  # nothing active, nothing recent: an old job is never reused


def test_active_job_ids_and_aliases(store):
    store.upsert_job(1, name="a", state="queued")
    store.upsert_job(2, name="b", state="printing")
    store.upsert_job(3, name="c", state="cancelled")
    store.upsert_job(4, name="d", state="finished")
    assert store.active_job_ids() == {1, 2}
    assert store.job_for_queue_item(3)["name"] == "c" and store.job_for_queue_item(99) is None


def test_kv_updated(store):
    assert store.kv_updated("watcher") is None
    before = time.time()
    store.kv_set("watcher", {"state": "IDLE"})
    assert before - 1 <= store.kv_updated("watcher") <= time.time() + 1


# ---- plate confirmations -------------------------------------------------------------------------------
def test_plate_confirmation_is_per_exact_job_name(store):
    assert not store.plate_confirmed("kutu")
    store.confirm_plate("kutu.gcode.3mf", "Sam")
    assert store.plate_confirmed("kutu") and store.plate_confirmed(" KUTU.3mf")
    assert not store.plate_confirmed("kutuphane") and not store.plate_confirmed("")


def test_plate_confirmation_is_voided_by_a_later_start_of_the_same_job(store, monkeypatch):
    store.confirm_plate("kutu", "Sam")
    time.sleep(0.01)
    store.add_event("start_requested", "other_job", {})
    assert store.plate_confirmed("kutu")  # another job's start does not matter
    store.add_event("started", "kutu.gcode.3mf", {})
    assert not store.plate_confirmed("kutu")  # it was about an earlier print of the same file
    store.confirm_plate("kutu", "Sam")
    assert store.plate_confirmed("kutu")
    real = time.time
    monkeypatch.setattr(store_mod.time, "time", lambda: real() + 25 * 3600)
    assert not store.plate_confirmed("kutu")  # a day-old confirmation is stale


def test_unnamed_job_confirmation_is_voided_by_any_start(store):
    store.confirm_plate("", "Sam")
    assert store.plate_confirmed("")
    time.sleep(0.01)
    store.upsert_job(9, name="x", started_ts=time.time())
    assert not store.plate_confirmed("")


# ---- session senders -------------------------------------------------------------------------------------
def test_remember_sender_with_platform_and_parent(store):
    store.remember_sender("parent", "mum@s.whatsapp.net", "whatsapp")
    store.remember_sender("child", "mum@s.whatsapp.net", "subagent", inherited_from="parent")
    assert store.sender_for("child") == "mum@s.whatsapp.net"
    info = store.sender_info("child")
    assert info["platform"] == "subagent" and info["inherited_from"] == "parent"
    store.remember_sender("parent", "", "whatsapp")  # a turn without identity clears the earlier speaker
    assert store.sender_for("parent") == ""
    store.forget_sender("child")
    assert store.sender_for("child") == "" and store.sender_info("child") == {}
    assert store.sender_for("") == "" and store.sender_for(None) == ""


# ---- fix round 2 ---------------------------------------------------------------------------------------
def test_pass_detail_travels_with_the_pass(store):
    store.issue_pass("home3d_stop", "", "s-owner", detail="hms_ack:0700-2000-0002-0001")
    assert store.take_pass("home3d_stop", "", "s-owner") == {"detail": "hms_ack:0700-2000-0002-0001"}
    assert store.take_pass("home3d_stop", "", "s-owner") is None  # single use
    store.issue_pass("home3d_stop", "", "s-owner")
    assert store.take_pass("home3d_stop", "", "s-owner") == {"detail": ""}


def test_a_database_from_before_the_detail_column_is_migrated(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE passes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, tool TEXT NOT NULL, "
                "target TEXT NOT NULL DEFAULT '', session_id TEXT NOT NULL, expires REAL NOT NULL, "
                "used INTEGER NOT NULL DEFAULT 0)")
    con.commit()
    con.close()
    s = Store(path)
    s.issue_pass("home3d_start", "7", "s", detail="x")
    assert s.take_pass("home3d_start", "7", "s") == {"detail": "x"}
    Store(path)  # opening it again is fine


def test_unconfirmed_failure_lives_until_a_person_confirms_the_plate(store):
    """Safety 6 / e2e NEW-2: the printer forgets a failure after a power cycle; the store does not."""
    assert store.unconfirmed_failure() is None
    store.record_failure("clip", "watcher", "print failed")
    rec = store.unconfirmed_failure()
    assert rec and rec["job_name"] == "clip" and rec["source"] == "watcher"
    store.confirm_plate("", "Owner")  # after a reboot the printer reports no job name: any confirmation settles it
    assert store.unconfirmed_failure() is None
    store.record_failure("clip")
    store.clear_failure("a new print started")
    assert store.unconfirmed_failure() is None
    assert store.kv_get("failure:last")["settled"] == "a new print started"


# ---- fix round 2 (R2-7): family approval requests ---------------------------------------------------------------
def test_approval_requests_dedupe_per_action_item_and_person_per_day(store, monkeypatch):
    first = store.add_approval_request("start", 7, "Mum", "s-mum", sender_id="mum@s.whatsapp.net")
    assert isinstance(first, int)
    assert store.add_approval_request("start", 7, "mum", "s-other") is None  # same person (any case), same day
    assert isinstance(store.add_approval_request("start", 8, "Mum", "s-mum"), int)  # another item
    assert isinstance(store.add_approval_request("start", 7, "Dad", "s-dad"), int)  # another person
    assert isinstance(store.add_approval_request("clear_plate", None, "Mum", "s-mum"), int)
    assert store.add_approval_request("clear_plate", None, "Mum", "s-mum") is None
    assert store.add_approval_request("", 7, "Mum") is None
    pending = store.pending_approval_requests()
    assert [(r["action"], r["queue_item_id"], r["who"]) for r in pending] == [
        ("start", 7, "Mum"), ("start", 8, "Mum"), ("start", 7, "Dad"), ("clear_plate", None, "Mum")]
    assert pending[0]["sender_id"] == "mum@s.whatsapp.net" and pending[0]["session_id"] == "s-mum"
    later = time.time() + 25 * 3600
    monkeypatch.setattr(time, "time", lambda: later)
    assert isinstance(store.add_approval_request("start", 7, "Mum", "s-mum"), int)  # a day later: a new ask
    assert [r["queue_item_id"] for r in store.pending_approval_requests()] == [7]  # older ones are not announced


def test_approval_requests_are_announced_once_and_settled_by_the_action(store):
    a = store.add_approval_request("start", 7, "Mum", "s-mum")
    b = store.add_approval_request("resume", None, "Dad", "s-dad")
    assert store.mark_approval_request_announced(a) is True
    assert store.mark_approval_request_announced(a) is False  # once
    assert store.mark_approval_request_announced(9999) is False
    assert [r["id"] for r in store.pending_approval_requests()] == [b]
    assert store.latest_approval_request("start", 7, "MUM")["announced_ts"] is not None
    assert store.latest_approval_request("start", 8, "Mum") is None
    assert store.resolve_approval_requests("resume", None, "resumed by Owner") == 1
    assert store.pending_approval_requests() == []
    assert store.resolve_approval_requests("start", "7") == 1  # settled even after it was announced
    rows = {r["id"]: r for r in store.approval_requests()}
    assert rows[b]["outcome"] == "resumed by Owner" and rows[a]["resolved_ts"] is not None


def test_a_new_ask_after_the_owner_settled_the_first_is_a_new_request(store):
    """Same day, same person, same action: once the owner ran it, asking again is a new request (it is not
    swallowed by the dedupe, and an old announcement does not count for it)."""
    first = store.add_approval_request("clear_plate", None, "Mum", "s-mum")
    assert store.mark_approval_request_announced(first) is True
    assert store.add_approval_request("clear_plate", None, "Mum", "s-mum") is None  # still open: deduped
    assert store.resolve_approval_requests("clear_plate", None, "cleared by Owner") == 1
    assert store.latest_approval_request("clear_plate", None, "Mum") is None  # settled: not "already told"
    second = store.add_approval_request("clear_plate", None, "Mum", "s-mum")
    assert isinstance(second, int) and second != first
    assert [r["id"] for r in store.pending_approval_requests()] == [second]
    assert store.latest_approval_request("clear_plate", None, "Mum")["announced_ts"] is None


# ---- review round 3 ---------------------------------------------------------------------------------------
def test_r3_a_plate_confirmation_covers_only_the_failed_print_it_was_made_on():
    """S6: confirmed after "Box" failed at layer 5; a later same-name print (an archive reprint nobody here saw
    start) fails at layer 12: the old confirmation does not count for it."""
    from home3d_ws.home3d.backends.base import FAILED, IDLE, PrinterStatus

    store = Store()
    first = PrinterStatus(state=FAILED, job_name="Box", progress=12.4, layer=5, total_layers=40)
    store.confirm_plate("Box", "Owner", status=first)
    assert store.plate_confirmed("Box", status=first)
    assert store.plate_confirmed("Box", status=PrinterStatus(state=FAILED, job_name="Box", progress=12.0, layer=5,
                                                             total_layers=40))
    later = PrinterStatus(state=FAILED, job_name="Box", progress=31.0, layer=12, total_layers=40)
    assert not store.plate_confirmed("Box", status=later)
    assert store.plate_confirmed("Box", status=PrinterStatus(state=IDLE))  # not FAILED: the name rule as before
    store.confirm_plate("Box", "Owner")  # no status recorded: on a FAILED printer it fails closed
    assert not store.plate_confirmed("Box", status=first) and store.plate_confirmed("Box")


def test_r3_active_job_requesters():
    store = Store()
    store.upsert_job(1, requester="Mum", state="queued")
    store.upsert_job(2, requester="", state="printing")
    store.upsert_job(3, requester="Dad", state="finished")
    assert store.active_job_requesters() == {1: "Mum", 2: ""}
