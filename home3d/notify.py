"""Zero-token delivery with a real delivery state (no model call, works from the cron watcher).

Every notice is a durable OUTBOX record in the store (``Store.outbox_add``): ``pending`` until a send succeeded,
then ``sent``; ``no_target`` when there is nowhere to send it (never "notified"); ``dry_run`` in a dry run;
``failed`` once it was given up. ``flush`` sends what is due through ``hermes send``:

    hermes [-p <send_profile>] send -t <target> --json -- "<text>\\nMEDIA:<abs path>"

One attempt per record per pass, each bounded by ``send_timeout_s``, and all of them together by ``send_budget_s``
(an attempt only starts when a whole timeout still fits, so a pass never spends longer than the budget in sends;
what is left is carried to the next pass, not counted as an attempt). A failed attempt is retried on later passes
after ``RETRY_BACKOFF_S``; after ``MAX_ATTEMPTS`` attempts or ``MAX_AGE_S`` the record is ``failed`` and the owner
is told once (a ``delivery_failed`` notice, itself an outbox record). Records to one target go out in the order
they were written: while an older one is waiting for its retry, newer ones for the same chat wait behind it.

What a send that succeeded settles (``_settle``): the events of the message count as told (``owner_notified`` /
``family_notified``), and the approval requests in it as announced. A record that was given up closes its approval
requests ("the owner could not be told"), so the person can ask again.

``route_for`` decides who hears about a job: the group whose target is the chat the request came from, else the
group that lists its sender, else the household's ``family_target``; a requester in no group and not in the
household is not announced anywhere (the owner is told instead).

``outbox_summary`` is what the status tool and a UI read: counts per status and the last failures.

Every attempt (and every dry-run / no-target notice) is also appended to ``data_dir()/outbox.jsonl`` so the
simulator demo and the owner can see what went out (``read_outbox``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import messages
from .config import Person, Settings, data_dir

OUTBOX_FILE = "outbox.jsonl"
SEND_TIMEOUT_S = 20.0  # one `hermes send` (Settings.send_timeout_s overrides it)
PASS_BUDGET_S = 45.0  # all sends of one flush (Settings.send_budget_s overrides it)
RETRY_DELAY_S = 3.0  # the in-line retry of a direct send() (the outbox retries on later passes instead)
RETRY_BACKOFF_S = (60, 5 * 60, 15 * 60, 30 * 60, 3600, 2 * 3600, 4 * 3600)  # wait after attempt n (last repeats)
MAX_ATTEMPTS = 10  # then the record is failed (about 16 hours of trying with the backoff above)
MAX_AGE_S = 24 * 3600  # a notice older than this is not worth sending any more
DRY_RUN_ENV = "HOME3D_DRY_RUN"
SUMMARY_FAILURES = 5
SENT, FAILED, PENDING, NO_TARGET, DRY_RUN = "sent", "failed", "pending", "no_target", "dry_run"
FAILURE_KIND = "delivery_failed"


@dataclass
class Delivery:
    target: str
    ok: bool
    error: str = ""
    dry_run: bool = False
    audience: str = ""
    status: str = ""  # sent | failed | no_target | dry_run ("pending" in a flush report: it will be retried)
    record_id: Optional[int] = None  # the outbox record this attempt belongs to
    attempts: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Route:
    """Who hears about a job besides the owner. ``announce`` False: nobody (``why``: "owner" = the owner's own job,
    "nobody" = nobody is known to have asked, "outsider" = the requester is in no group and not in the household)."""
    announce: bool
    audience: str = "family"  # the tone: family | team
    language: str = "en"
    target: str = ""  # '' with announce True: there is a group but no chat to send to (the record is no_target)
    group: str = ""  # the configured group's name ('' = the household's family_target)
    why: str = ""


@dataclass
class FlushReport:
    deliveries: list = field(default_factory=list)  # Delivery per record handled in this flush
    carried: int = 0  # due records left for the next pass (no time left, or waiting behind an older one)
    gave_up: list = field(default_factory=list)  # records marked failed in this flush
    surfaced_text: str = ""  # the owner notice written about them ('' = none)
    surfaced_id: Optional[int] = None
    seconds: float = 0.0


# ---- routing: which chat hears about a job ----------------------------------------------------------------------
def _person_named(settings: Settings, name: str) -> Optional[Person]:
    n = (name or "").strip().lower()
    if not n:
        return None
    for p in settings.people():
        if n in (p.name.strip().lower(), (p.address_as or "").strip().lower()):
            return p
    return None


def route_for(settings: Settings, *, requester: str = "", platform: str = "", chat_id: str = "",
              sender_id: str = "") -> Route:
    """Where the notices about a job go, from who asked (``requester`` name) and where the request came from
    (``platform`` / ``chat_id`` / ``sender_id`` as stored with the request).

    1. the owner's own job: no group notice (the owner gets the technical one);
    2. the group whose target IS the origin chat, else the group that lists the sender (or the requester's
       household id): that group's target, language and tone;
    3. a household member outside every group: ``family_target`` in the household language (as before groups);
    4. anyone else: not announced (``why="outsider"``), or ``why="nobody"`` when nobody is known to have asked.
    """
    name = (requester or "").strip()
    person = _person_named(settings, name)
    sender = settings.person_for(sender_id) if sender_id else None
    owner = (settings.owner_name or "").strip().lower()
    sender_is_owner = bool(sender and sender.role == "owner")
    if (person and person.role == "owner") or (name and name.lower() == owner) or (not name and sender_is_owner):
        return Route(False, why="owner")
    group = settings.group_for(platform, chat_id, "" if sender_is_owner else sender_id)
    if group is None and person is not None and person.id:
        group = settings.group_for(sender_id=person.id)
    if group is not None:
        return Route(True, audience=group.tone, language=settings.group_language(group), target=group.target,
                     group=group.name)
    if person is not None or (sender is not None and not sender_is_owner):
        return Route(True, audience="family", language=settings.language, target=settings.family_target)
    if not name and not str(sender_id or "").strip() and not str(chat_id or "").strip():
        return Route(False, why="nobody")
    return Route(False, why="outsider")


# ---- hermes send ------------------------------------------------------------------------------------------------
def hermes_bin() -> Optional[str]:
    """``hermes`` on PATH, else next to the running interpreter (Hermes venv / cron), else None."""
    found = shutil.which("hermes")
    if found:
        return found
    local = Path(sys.executable).parent / "hermes"
    return str(local) if local.exists() else None


def _env_dry_run() -> bool:
    return os.environ.get(DRY_RUN_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def compose(text: str, media: Optional[Path] = None) -> str:
    """Message body with an optional ``MEDIA:<abs path>`` line (Hermes attaches it natively)."""
    text = (text or "").strip()
    if media is not None and str(media):
        path = Path(media).expanduser()
        if path.is_file():
            text = f"{text}\nMEDIA:{path.resolve()}" if text else f"MEDIA:{path.resolve()}"
    return text


def outbox_path() -> Path:
    return data_dir() / OUTBOX_FILE


def _outbox(audience: str, target: str, text: str, media: Optional[Path], d: Delivery) -> None:
    rec = {"ts": time.time(), "audience": audience, "target": target, "text": text,
           "media": str(media) if media else "", "ok": d.ok, "dry_run": d.dry_run, "error": d.error,
           "status": d.status}
    try:
        with outbox_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_outbox(limit: int = 50) -> list[dict]:
    """Last ``limit`` lines of the send log ``outbox.jsonl`` (oldest first): one per attempt / dry-run notice."""
    try:
        lines = outbox_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-limit:] if limit else lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _parse(stdout: str) -> dict:
    stdout = (stdout or "").strip()
    if not stdout:
        return {}
    try:
        val = json.loads(stdout)
        return val if isinstance(val, dict) else {}
    except ValueError:
        pass
    start = stdout.rfind("\n{")
    try:
        val = json.loads(stdout[start + 1:] if start >= 0 else stdout[stdout.find("{"):])
        return val if isinstance(val, dict) else {}
    except ValueError:
        return {}


def _attempt(cmd: list[str], timeout_s: Optional[float] = None) -> tuple[bool, str]:
    limit = float(timeout_s) if timeout_s else SEND_TIMEOUT_S
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=limit, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, f"hermes send timed out after {limit:g}s (it may still have been delivered)"
    except OSError as exc:
        return False, f"hermes send could not run: {exc}"
    payload = _parse(proc.stdout)
    if proc.returncode == 0 and (not payload or payload.get("success") or payload.get("skipped")) \
            and not payload.get("error"):
        return True, ""
    err = payload.get("error") or (proc.stderr or "").strip() or (proc.stdout or "").strip() \
        or f"exit {proc.returncode}"
    return False, str(err)[:300]


def send(settings: Settings, target: str, text: str, media: Optional[Path] = None, *,
         audience: str = "", dry_run: bool = False, retry: bool = True,
         timeout_s: Optional[float] = None) -> Delivery:
    """Send one message (with an optional photo) to ``target`` now. Never raises.

    ``Delivery.status`` says what really happened: ``sent``, ``failed``, ``dry_run`` or ``no_target`` (an empty
    target: nothing was sent; ``ok`` / ``dry_run`` are True for it as before, so ask ``status``). ``retry``: one
    more try after ``RETRY_DELAY_S`` (a direct send; the outbox passes False and retries on a later pass).
    ``timeout_s`` bounds each try (default ``SEND_TIMEOUT_S``)."""
    target = (target or "").strip()
    body = compose(text, media)
    if not target or dry_run or _env_dry_run():
        d = Delivery(target=target, ok=True, dry_run=True, audience=audience,
                     status=DRY_RUN if target else NO_TARGET)
        _outbox(audience, target, text, media, d)
        return d
    binary = hermes_bin()
    if not binary:
        d = Delivery(target=target, ok=False, error="hermes binary not found", audience=audience, status=FAILED)
        _outbox(audience, target, text, media, d)
        return d
    cmd = [binary]
    if (settings.send_profile or "").strip():
        cmd += ["-p", settings.send_profile.strip()]
    cmd += ["send", "-t", target, "--json", "--", body]
    ok, err = _attempt(cmd, timeout_s)
    if not ok and retry:
        time.sleep(RETRY_DELAY_S)
        ok, err2 = _attempt(cmd, timeout_s)
        err = "" if ok else (err2 or err)
    d = Delivery(target=target, ok=ok, error=err, audience=audience, status=SENT if ok else FAILED)
    _outbox(audience, target, text, media, d)
    return d


def notify(settings: Settings, *, owner_text: Optional[str], family_text: Optional[str],
           media: Optional[Path] = None, owner_media_only: bool = True,
           dry_run: bool = False) -> list[Delivery]:
    """Direct send to the two fixed targets, without the outbox (kept for callers that want a message out now):
    the owner gets the technical text (+ photo); family the plain line (photo only when ``owner_media_only`` is
    False). Empty texts are skipped. The watcher does not use this: it queues outbox records (``enqueue``)."""
    out: list[Delivery] = []
    if owner_text and owner_text.strip():
        out.append(send(settings, settings.owner_target, owner_text, media, audience="owner", dry_run=dry_run))
    if family_text and family_text.strip():
        out.append(send(settings, settings.family_target, family_text, None if owner_media_only else media,
                        audience="family", dry_run=dry_run))
    return out


# ---- the durable outbox -----------------------------------------------------------------------------------------
def _limits(settings: Settings) -> tuple[float, float]:
    """(seconds one send may take, seconds all sends of a pass may take)."""
    try:
        timeout = float(getattr(settings, "send_timeout_s", SEND_TIMEOUT_S) or SEND_TIMEOUT_S)
        budget = float(getattr(settings, "send_budget_s", PASS_BUDGET_S) or PASS_BUDGET_S)
    except (TypeError, ValueError):
        timeout, budget = SEND_TIMEOUT_S, PASS_BUDGET_S
    timeout = min(max(timeout, 1.0), 120.0)
    return timeout, max(budget, timeout)


def backoff_s(attempts: int) -> float:
    """How long to wait after the ``attempts``-th failed attempt before the next one."""
    n = max(1, int(attempts))
    return float(RETRY_BACKOFF_S[min(n - 1, len(RETRY_BACKOFF_S) - 1)])


def enqueue(settings: Settings, store: Any, *, audience: str, target: str, text: str,
            media: Optional[Path] = None, kinds: Any = (), job_name: str = "", requester: str = "", group: str = "",
            event_ids: Any = (), approval_request_ids: Any = (), now: Optional[float] = None,
            dry_run: bool = False) -> Optional[Delivery]:
    """Write one notice to the outbox. With a target (and no dry run) it is ``pending`` until ``flush`` sent it
    (returns None: nothing happened yet). Without a target it is ``no_target``, in a dry run ``dry_run``: both are
    final, nothing is sent, and the returned ``Delivery`` says so (its ``record_id`` is the outbox record).
    Empty text: nothing is written (None)."""
    if not (text or "").strip():
        return None
    target = (target or "").strip()
    refs = {"event_ids": [int(i) for i in event_ids or [] if i is not None],
            "approval_request_ids": [int(i) for i in approval_request_ids or [] if i is not None]}
    final = DRY_RUN if (dry_run or _env_dry_run()) and target else "" if target else NO_TARGET
    rid = store.outbox_add(audience=audience, target=target, text=text, media=str(media) if media else "",
                           kinds=kinds, job_name=job_name, requester=requester, group=group, refs=refs,
                           status=final or PENDING, clock=now)
    if not final:
        return None
    d = send(settings, target, text, media, audience=audience, dry_run=True)  # the send log; nothing goes out
    d.record_id, d.status = rid, final
    _settle(store, {"id": rid, "audience": audience, "refs": refs}, final)
    return d


def _settle(store: Any, rec: dict, status: str) -> None:
    """What the result of a record means for the things it is about (see the module docstring). Never raises."""
    refs = rec.get("refs") if isinstance(rec.get("refs"), dict) else {}
    try:
        if status == SENT:
            owner = rec.get("audience") == "owner"
            for eid in refs.get("event_ids") or []:
                store.mark_event_notified(int(eid), owner=True if owner else None, family=None if owner else True)
        for rid in refs.get("approval_request_ids") or []:
            if status in (SENT, NO_TARGET, DRY_RUN):  # written out once (cron output / dry run) or really sent
                store.mark_approval_request_announced(int(rid))
            elif status == FAILED:
                store.close_approval_request(int(rid), "the owner could not be told (delivery failed)")
    except Exception:
        pass


def _clock_now(now: Optional[float]) -> float:
    return float(now) if now is not None else time.time()


def _due(rec: dict, clock: float) -> bool:
    nxt = rec.get("next_try_clock")
    if nxt is None:
        return True
    # a retry time further away than any backoff means the clock changed (another printer, the simulator): due
    return float(nxt) <= clock or float(nxt) - clock > RETRY_BACKOFF_S[-1]


def _expired(rec: dict, clock: float) -> bool:
    queued = rec.get("clock_ts")
    if queued is None or (queued - clock) > RETRY_BACKOFF_S[-1]:  # unknown, or the clock changed: age from now on
        queued = clock
    return int(rec.get("attempts") or 0) >= MAX_ATTEMPTS or clock - float(queued) > MAX_AGE_S


def flush(settings: Settings, store: Any, *, now: Optional[float] = None, dry_run: bool = False) -> FlushReport:
    """Send the pending outbox records that are due (oldest first), within the pass budget. ``now`` is the watcher's
    clock (retry times and the age cap run on it). A dry run sends nothing and leaves pending records alone.
    Returns what happened; never raises."""
    report = FlushReport()
    if dry_run or _env_dry_run():
        return report
    started = time.monotonic()
    clock = _clock_now(now)
    timeout, budget = _limits(settings)
    waiting: set[str] = set()  # targets with an older record still waiting: newer ones go behind it
    try:
        pending = store.outbox_pending()
    except Exception:
        return report
    for rec in pending:
        target = str(rec.get("target") or "")
        if not target:  # the target was removed from the settings meanwhile
            if store.outbox_settle(rec["id"], NO_TARGET, attempted=False):
                _settle(store, rec, NO_TARGET)
            continue
        if _expired(rec, clock):
            _give_up(store, rec, report)
            continue
        if target in waiting or not _due(rec, clock):
            waiting.add(target)
            report.carried += 1 if _due(rec, clock) else 0
            continue
        if budget - (time.monotonic() - started) < timeout:
            report.carried += 1  # no time for a whole attempt: the next pass sends it (not counted as an attempt)
            waiting.add(target)
            continue
        report.deliveries.append(_send_record(settings, store, rec, clock, timeout, report, waiting))
    _surface(settings, store, report, clock, timeout, budget - (time.monotonic() - started))
    report.seconds = time.monotonic() - started
    return report


def _send_record(settings: Settings, store: Any, rec: dict, clock: float, timeout: float, report: FlushReport,
                 waiting: set) -> Delivery:
    media = Path(rec["media"]) if rec.get("media") else None
    try:
        d = send(settings, rec["target"], rec["text"], media, audience=rec.get("audience") or "", retry=False,
                 timeout_s=timeout)
    except Exception as exc:  # send() never raises; a replaced sender might
        d = Delivery(target=rec["target"], ok=False, error=f"{type(exc).__name__}: {exc}"[:300],
                     audience=rec.get("audience") or "", status=FAILED)
    d.record_id = rec["id"]
    attempts = int(rec.get("attempts") or 0) + 1
    d.attempts = attempts
    if d.status == DRY_RUN or (d.dry_run and d.ok):  # HOME3D_DRY_RUN was set meanwhile
        d.status = DRY_RUN
        if store.outbox_settle(rec["id"], DRY_RUN, attempted=False):
            _settle(store, rec, DRY_RUN)
        return d
    if d.ok:
        d.status = SENT
        if store.outbox_settle(rec["id"], SENT):
            _settle(store, rec, SENT)
        return d
    waiting.add(rec["target"])
    if attempts >= MAX_ATTEMPTS:
        rec = dict(rec, attempts=attempts, last_error=d.error)
        if store.outbox_settle(rec["id"], FAILED, error=d.error):
            _gave_up(store, rec, report)
        d.status = FAILED
        return d
    store.outbox_settle(rec["id"], PENDING, error=d.error, next_try_clock=clock + backoff_s(attempts))
    d.status = PENDING  # failed this time; it is retried on a later pass
    return d


def _give_up(store: Any, rec: dict, report: FlushReport) -> None:
    """A pending record past its attempt or age cap: failed for good."""
    why = rec.get("last_error") or "never sent"
    reason = "too many attempts" if int(rec.get("attempts") or 0) >= MAX_ATTEMPTS else "older than a day"
    if store.outbox_settle(rec["id"], FAILED, error=f"gave up ({reason}): {why}"[:300], attempted=False):
        _gave_up(store, rec, report)


def _gave_up(store: Any, rec: dict, report: FlushReport) -> None:
    report.gave_up.append(rec)
    _settle(store, rec, FAILED)
    if FAILURE_KIND in (rec.get("kinds") or []):  # the notice about failures itself: never a notice about that
        store.outbox_mark_surfaced([rec["id"]])


def _surface(settings: Settings, store: Any, report: FlushReport, clock: float, timeout: float,
             left_s: float) -> None:
    """Tell the owner ONCE about the records given up on: one ``delivery_failed`` notice, itself an outbox record
    (sent right away when the pass still has time, else on the next pass; ``no_target`` without an owner chat:
    the text is then in ``report.surfaced_text`` for the cron output)."""
    try:
        failures = store.outbox_unsurfaced_failures()
        if not failures:
            return
        items = [{"to": _to_label(f), "text": (f.get("text") or "").strip().splitlines()[0] if f.get("text") else "",
                  "error": f.get("last_error") or "", "attempts": f.get("attempts")} for f in failures]
        text = messages.render(FAILURE_KIND, "owner", settings.language, failures=items, count=len(items),
                               owner=settings.owner_name, persona=settings.persona_name)
        store.outbox_mark_surfaced([f["id"] for f in failures])
        d = enqueue(settings, store, audience="owner", target=settings.owner_target, text=text,
                    kinds=[FAILURE_KIND], now=clock)
        report.surfaced_text = text
        if d is not None:  # no owner chat: a final no_target record
            report.surfaced_id = d.record_id
            report.deliveries.append(d)
            return
        rec = next((r for r in reversed(store.outbox_pending()) if FAILURE_KIND in r["kinds"]), None)
        if rec is None:
            return
        report.surfaced_id = rec["id"]
        if left_s >= timeout:
            report.deliveries.append(_send_record(settings, store, rec, clock, timeout, report, set()))
        else:
            report.carried += 1
    except Exception:
        pass


def _to_label(rec: dict) -> str:
    """Who a record was for, in words the owner knows: the group's name, "the family chat", "your chat"."""
    if rec.get("group_name"):
        return str(rec["group_name"])
    if rec.get("audience") == "owner":
        return "owner chat"
    return "family chat" if rec.get("audience") == "family" else str(rec.get("audience") or "chat")


# ---- what the status tool and a UI read -----------------------------------------------------------------------
def _brief(rec: dict) -> dict:
    text = (rec.get("text") or "").strip()
    return {"id": rec.get("id"), "ts": rec.get("ts"), "audience": rec.get("audience") or "",
            "group": rec.get("group_name") or "", "target": rec.get("target") or "",
            "kinds": list(rec.get("kinds") or []), "job": rec.get("job_name") or "",
            "requester": rec.get("requester") or "", "status": rec.get("status") or "",
            "attempts": int(rec.get("attempts") or 0), "last_error": rec.get("last_error") or "",
            "last_attempt_ts": rec.get("last_attempt_ts"), "sent_ts": rec.get("sent_ts"),
            "text": text.splitlines()[0][:160] if text else "", "has_photo": bool(rec.get("media"))}


def outbox_summary(store: Any, failures: int = SUMMARY_FAILURES) -> dict:
    """The outbox at a glance, for the status tool and a UI. Never raises.

    ``{"counts": {"pending", "sent", "failed", "no_target", "dry_run"}, "undelivered": pending + failed,
    "pending": [oldest pending records], "last_failures": [newest records that failed for good or are pending
    after a failed attempt], "last_sent_ts": epoch seconds or None}``; each record is ``{"id", "ts", "audience",
    "group", "target", "kinds", "job", "requester", "status", "attempts", "last_error", "last_attempt_ts",
    "sent_ts", "text" (first line), "has_photo"}``."""
    try:
        counts = store.outbox_counts()
        pending = store.outbox_pending(limit=200)
        failed = store.outbox(status=FAILED, limit=max(1, int(failures)))
        sent = store.outbox(status=SENT, limit=1)
    except Exception as exc:
        return {"counts": {}, "undelivered": 0, "pending": [], "last_failures": [], "last_sent_ts": None,
                "error": f"{type(exc).__name__}: {exc}"[:200]}
    retrying = [r for r in pending if int(r.get("attempts") or 0) > 0]
    last = sorted(failed + retrying, key=lambda r: float(r.get("last_attempt_ts") or r.get("ts") or 0), reverse=True)
    return {"counts": counts, "undelivered": int(counts.get(PENDING, 0)) + int(counts.get(FAILED, 0)),
            "pending": [_brief(r) for r in pending[: max(1, int(failures))]],
            "last_failures": [_brief(r) for r in last[: max(1, int(failures))]],
            "last_sent_ts": sent[0].get("sent_ts") if sent else None}
