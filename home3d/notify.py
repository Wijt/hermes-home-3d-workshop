"""Zero-token delivery through ``hermes send`` (no model call, works from the cron watcher).

``hermes [-p <send_profile>] send -t <target> --json -- "<text>\\nMEDIA:<abs path>"`` via ``subprocess.run``
(timeout 60 s), success = exit 0 / ``{"success": true}``, one retry. Every message is also appended to
``data_dir()/outbox.jsonl`` so the simulator demo (and the owner) can see what went out. An empty target,
``dry_run=True`` or ``HOME3D_DRY_RUN=1`` only writes the outbox.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .config import Settings, data_dir

OUTBOX_FILE = "outbox.jsonl"
SEND_TIMEOUT_S = 60
RETRY_DELAY_S = 3.0
DRY_RUN_ENV = "HOME3D_DRY_RUN"


@dataclass
class Delivery:
    target: str
    ok: bool
    error: str = ""
    dry_run: bool = False
    audience: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


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
    if media is not None:
        path = Path(media).expanduser()
        if path.is_file():
            text = f"{text}\nMEDIA:{path.resolve()}" if text else f"MEDIA:{path.resolve()}"
    return text


def outbox_path() -> Path:
    return data_dir() / OUTBOX_FILE


def _outbox(audience: str, target: str, text: str, media: Optional[Path], d: Delivery) -> None:
    rec = {"ts": time.time(), "audience": audience, "target": target, "text": text,
           "media": str(media) if media else "", "ok": d.ok, "dry_run": d.dry_run, "error": d.error}
    try:
        with outbox_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_outbox(limit: int = 50) -> list[dict]:
    """Last ``limit`` outbox records (oldest first)."""
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


def _attempt(cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=SEND_TIMEOUT_S,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, f"hermes send timed out after {SEND_TIMEOUT_S}s"
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
         audience: str = "", dry_run: bool = False) -> Delivery:
    """Send one message (with an optional photo) to ``target``. Never raises."""
    target = (target or "").strip()
    body = compose(text, media)
    if not target or dry_run or _env_dry_run():
        d = Delivery(target=target, ok=True, dry_run=True, audience=audience)
        _outbox(audience, target, text, media, d)
        return d
    binary = hermes_bin()
    if not binary:
        d = Delivery(target=target, ok=False, error="hermes binary not found", audience=audience)
        _outbox(audience, target, text, media, d)
        return d
    cmd = [binary]
    if (settings.send_profile or "").strip():
        cmd += ["-p", settings.send_profile.strip()]
    cmd += ["send", "-t", target, "--json", "--", body]
    ok, err = _attempt(cmd)
    if not ok:
        time.sleep(RETRY_DELAY_S)
        ok, err2 = _attempt(cmd)
        err = "" if ok else (err2 or err)
    d = Delivery(target=target, ok=ok, error=err, audience=audience)
    _outbox(audience, target, text, media, d)
    return d


def notify(settings: Settings, *, owner_text: Optional[str], family_text: Optional[str],
           media: Optional[Path] = None, owner_media_only: bool = True,
           dry_run: bool = False) -> list[Delivery]:
    """Owner gets the technical text (+ photo); family the plain line (photo only when
    ``owner_media_only`` is False, i.e. for ``finished*``). Empty texts are skipped."""
    out: list[Delivery] = []
    if owner_text and owner_text.strip():
        out.append(send(settings, settings.owner_target, owner_text, media, audience="owner", dry_run=dry_run))
    if family_text and family_text.strip():
        out.append(send(settings, settings.family_target, family_text, None if owner_media_only else media,
                        audience="family", dry_run=dry_run))
    return out
