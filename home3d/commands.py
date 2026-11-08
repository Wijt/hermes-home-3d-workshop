"""``/home3d`` slash command (CLI, TUI and messaging gateway; no model call).

  /home3d status                 printer, queue, plate and watcher state
  /home3d approve start <id> [jump]   owner: approve (15 min, single use) and start now if the gates pass
  /home3d approve clear          owner: approve + mark the plate clear if the camera agrees
  /home3d approve resume         owner: approve + resume a paused print
  /home3d whoami                 the sender id / household person this chat maps to
  /home3d upgrades | moments     upgrade proposals / human-needed moments (last 30 days)
  /home3d help

``approve`` only counts when ``source.user_id`` is an owner id, or when there is no source (a local CLI/TUI
session is the owner at the keyboard). ``source.chat_id`` is never accepted: in a group chat it names the
group, not the person. The printer action itself goes through the same gated tool handler the agent uses.
"""

from __future__ import annotations

import json
import shlex
import time
from typing import Any, Callable, Optional

from .hooks import APPROVAL_TTL_S, approval_target, approve_command

_T = {
    "help": (
        "/home3d status · approve start <id> [jump] · approve clear · approve resume · whoami · upgrades · "
        "moments · help",
        "/home3d status · approve start <no> [jump] · approve clear · approve resume · whoami · upgrades · "
        "moments · help"),
    "not_owner": ("Only the owner can approve ({who} is not in owner_ids).",
                  "Sadece sahibi onaylayabilir ({who} owner_ids listesinde değil)."),
    "no_user": ("Only the owner can approve (this platform did not say who sent the command).",
                "Sadece sahibi onaylayabilir (komutu kimin gönderdiği bilinmiyor)."),
    "usage_start": ("Usage: /home3d approve start <queue id> [jump]", "Kullanım: /home3d approve start <sıra no> [jump]"),
    "usage_approve": ("Usage: /home3d approve start <id> | clear | resume",
                      "Kullanım: /home3d approve start <no> | clear | resume"),
    "started": ("▶️ Started #{qid} \"{name}\"{who}. The watcher reports the finish and the plate.",
                "▶️ #{qid} \"{name}\" başladı{who}. Bitişi ve tablayı izleyip haber vereceğim."),
    "cleared": ("✅ Plate marked clear{extra}.", "✅ Tabla boş olarak işaretlendi{extra}."),
    "resumed": ("▶️ Resumed \"{name}\".", "▶️ \"{name}\" devam ediyor."),
    "pending": ("Approved for {ttl} min (single use), but not done now: {why}",
                "{ttl} dk geçerli onay verildi ama şu an yapılamadı: {why}"),
    "unknown": ("Unknown subcommand '{sub}'.", "Bilinmeyen alt komut: '{sub}'."),
    "no_upgrades": ("No upgrade proposals yet.", "Henüz yükseltme önerisi yok."),
    "no_moments": ("No human-needed moments in the last 30 days.", "Son 30 günde elle müdahale kaydı yok."),
}


def _t(key: str, lang: str, **kw: Any) -> str:
    text = _T[key][1 if lang == "tr" else 0]
    try:
        return text.format(**kw)
    except (KeyError, IndexError, ValueError):
        return text


def _src(source: Any, key: str) -> str:
    if source is None:
        return ""
    v = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
    if v is None:
        return ""
    return str(getattr(v, "value", v))  # Platform enums carry .value


def authorize(rt, source: Any) -> tuple[bool, str, str]:
    """(allowed, approver label, refusal text). No source = local owner session."""
    s = rt.settings
    lang = s.language
    if source is None:
        return True, f"{s.owner_name} (local)", ""
    uid = _src(source, "user_id")
    if not uid:
        return False, "", _t("no_user", lang)
    if s.is_owner(uid):
        person = s.person_for(uid)
        return True, person.name if person else s.owner_name, ""
    person = s.person_for(uid)
    return False, "", _t("not_owner", lang, who=person.name if person else uid)


def _pretty(name: str) -> str:
    for suf in (".gcode.3mf", ".3mf", ".gcode"):
        if name.lower().endswith(suf):
            return name[: -len(suf)]
    return name


def format_status(data: dict, lang: str) -> str:
    """Short human text for a ``home3d_status`` result."""
    tr = lang == "tr"
    if not data.get("ok", True) and data.get("error"):
        return ("Durum okunamadı: " if tr else "Status failed: ") + str(data["error"])
    p = data.get("printer") or {}
    state = p.get("state", "?")
    head = f"🖨️ {p.get('printer_name') or data.get('backend') or 'printer'}: {state}"
    if p.get("error"):
        head += f" ({p['error']})"
    if p.get("job_name") and state not in ("IDLE", "OFFLINE"):
        head += f" · \"{_pretty(p['job_name'])}\""
    if state in ("PREPARE", "RUNNING", "PAUSE"):
        head += f" · {float(p.get('progress') or 0):.0f}%"
        if p.get("layer") and p.get("total_layers"):
            head += f" · {'katman' if tr else 'layer'} {p['layer']}/{p['total_layers']}"
        if p.get("remaining_min") is not None:
            head += f" · {p['remaining_min']} {'dk kaldı' if tr else 'min left'}"
    temps = []
    if p.get("bed_temp") is not None:
        temps.append(f"{'tabla' if tr else 'bed'} {p['bed_temp']:.0f}°C")
    if p.get("nozzle_temp") is not None:
        temps.append(f"{'nozul' if tr else 'nozzle'} {p['nozzle_temp']:.0f}°C")
    lines = [head + (f" · {', '.join(temps)}" if temps else "")]
    for h in p.get("hms") or []:
        lines.append(f"⚠️ HMS {h.get('code')}: {h.get('message') or ''}".rstrip(": "))
    queue = data.get("queue") or []
    if queue:
        lines.append(("Kuyruk:" if tr else "Queue:"))
        for q in queue[:6]:
            who = f" · {q['requester']}" if q.get("requester") else ("" if q.get("ours") else
                                                                    (" · başkası" if tr else " · not ours"))
            mins = f" · {q['print_time_min']} {'dk' if tr else 'min'}" if q.get("print_time_min") else ""
            lines.append(f"  #{q.get('id')} {q.get('status')} \"{_pretty(str(q.get('name') or ''))}\"{who}{mins}")
    else:
        lines.append("Kuyruk boş." if tr else "Queue empty.")
    plate = data.get("plate") or {}
    if plate.get("phase"):
        lines.append(f"{'Tabla' if tr else 'Plate'}: {plate['phase']}"
                     + (f" ({plate['reason']})" if plate.get("reason") else ""))
    w = data.get("watcher") or {}
    if not w.get("fresh"):
        lines.append("⚠️ " + ("İzleyici çalışmıyor (hermes home3d setup)." if tr
                              else "Watcher not running (hermes home3d setup)."))
    return "\n".join(lines)


class _Command:
    def __init__(self, rt):
        self.rt = rt
        self._tools: Optional[dict[str, Callable[..., str]]] = None

    def tool(self, name: str, args: dict, session_id: str = "") -> dict:
        if self._tools is None:
            from .tools import build_tools

            self._tools = {n: h for n, _schema, h in build_tools(self.rt)}
        raw = self._tools[name](args, session_id=session_id or "")
        try:
            out = json.loads(raw)
            return out if isinstance(out, dict) else {"ok": False, "error": str(out)}
        except ValueError:
            return {"ok": False, "error": str(raw)[:300]}

    def __call__(self, raw_args: str = "", source: Any = None, session_id: Any = None, platform: Any = None) -> str:
        try:
            return self.run(str(raw_args or ""), source, str(session_id or ""), str(platform or ""))
        except Exception as e:  # a slash command must answer, never crash the gateway
            return f"home3d: {type(e).__name__}: {e}"

    def run(self, raw: str, source: Any, session_id: str, platform: str) -> str:
        lang = self.rt.settings.language
        try:
            words = shlex.split(raw)
        except ValueError:
            words = raw.split()
        words = [w.lower() if i < 2 else w for i, w in enumerate(words)]
        sub, rest = (words[0], words[1:]) if words else ("help", [])
        if sub in ("help", "-h", "--help", "yardım", "yardim"):
            return _t("help", lang)
        if sub in ("status", "durum"):
            return format_status(self.tool("home3d_status", {}, session_id), lang)
        if sub in ("approve", "onay", "onayla"):
            return self.approve(rest, source, session_id, lang)
        if sub == "whoami":
            return self.whoami(source, session_id, platform, lang)
        if sub in ("upgrades", "upgrade"):
            return self.upgrades(lang)
        if sub in ("moments", "moment"):
            return self.moments(lang)
        return _t("unknown", lang, sub=sub[:30]) + "\n" + _t("help", lang)

    # -- approve --
    def approve(self, rest: list[str], source: Any, session_id: str, lang: str) -> str:
        what = rest[0] if rest else ""
        if what in ("start", "başlat", "baslat"):
            qid = _parse_id(rest[1]) if len(rest) > 1 else None
            if qid is None:
                return _t("usage_start", lang)
            jump = any(w.lower() in ("jump", "--jump", "atla") for w in rest[2:])
            action, tool, args = "start", "home3d_start", {"queue_item_id": qid, "allow_jump": jump}
        elif what in ("clear", "plate", "temizle", "tabla"):
            qid, jump = None, False
            action, tool, args = "clear_plate", "home3d_clear_plate", {"action": "confirm"}
        elif what in ("resume", "devam"):
            qid, jump = None, False
            action, tool, args = "resume", "home3d_stop", {"action": "resume", "reason": "owner approved resume"}
        else:
            return _t("usage_approve", lang)
        ok, approver, refusal = authorize(self.rt, source)
        if not ok:
            return refusal
        store = self.rt.store
        target = approval_target(action, qid, jump)
        store.grant_approval(action, target, approver, ttl_s=APPROVAL_TTL_S)
        store.add_event("approval_granted", "", {"action": action, "target": target, "approver": approver,
                                                 "command": approve_command(action, qid, jump)})
        res = self.tool(tool, args, session_id)
        if not res.get("ok"):
            why = res.get("message") or res.get("error") or "?"
            return _t("pending", lang, ttl=APPROVAL_TTL_S // 60, why=why)
        store.consume_approval(action, target)  # used right here
        if action == "start":
            who = f" ({res['requester']})" if res.get("requester") else ""
            return _t("started", lang, qid=qid, name=_pretty(str(res.get("name") or f"#{qid}")), who=who)
        if action == "clear_plate":
            plate = res.get("plate") or {}
            diff = plate.get("difference_pct")
            return _t("cleared", lang, extra=f" ({diff:g}%)" if isinstance(diff, (int, float)) else "")
        return _t("resumed", lang, name=_pretty(str(res.get("job") or "")))

    # -- info --
    def whoami(self, source: Any, session_id: str, platform: str, lang: str) -> str:
        s = self.rt.settings
        uid = _src(source, "user_id")
        plat = _src(source, "platform") or platform or ("cli" if source is None else "?")
        person = s.person_for(uid) if uid else None
        if source is None:
            who = f"{s.owner_name} (owner, local session)"
        elif person:
            who = f"{person.name} ({person.role})"
        else:
            who = "not in the household list" if lang != "tr" else "ev listesinde yok"
        owner = source is None or (bool(uid) and s.is_owner(uid))
        lines = [f"platform: {plat}", f"user_id: {uid or '-'}", f"person: {who}",
                 f"owner: {'yes' if owner else 'no'}"]
        if session_id:
            lines.append(f"session: {session_id[:40]}")
        if uid and not person:
            lines.append("add this id to owner_ids or household to be recognised")
        return "\n".join(lines)

    def upgrades(self, lang: str) -> str:
        from . import upgrades as up

        store = self.rt.store
        try:
            up.evaluate(store, self.rt.settings)
        except Exception:
            pass
        rows = [u for u in store.upgrades() if u.get("status") != "rejected"]
        if not rows:
            return _t("no_upgrades", lang)
        out = []
        for u in rows[:8]:
            out.append(f"💡 #{u['id']} [{u['status']}] {u['title']} · {u.get('evidence', 0)}×"
                       + (f"\n   {u['model_ref']}" if u.get("model_ref") else ""))
        persona = self.rt.settings.persona_name or ""
        if lang == "tr":
            from .messages import dative

            out.append(f"{dative(persona) if persona else 'Bana'} yaz: \"<no> numaralı öneriyi kabul et\" "
                       "(veya reddet / basılıyor / takıldı)")
        else:
            out.append(f"Tell {persona or 'me'}: \"accept upgrade <id>\" (or reject / printing / installed)")
        return "\n".join(out)

    def moments(self, lang: str) -> str:
        store = self.rt.store
        counts = store.human_needed_counts(30)
        if not counts:
            return _t("no_moments", lang)
        head = ("Son 30 gün: " if lang == "tr" else "Last 30 days: ") + ", ".join(
            f"{k} {n}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
        lines = [head]
        for m in store.human_needed(since_days=30, limit=5):
            when = time.strftime("%m-%d %H:%M", time.localtime(m.get("ts") or 0))
            bits = " · ".join(x for x in (m.get("job_name"), m.get("who"), (m.get("detail") or "")[:60]) if x)
            lines.append(f"  {when} {m['kind']}" + (f" · {bits}" if bits else ""))
        return "\n".join(lines)


def _parse_id(value: str) -> Optional[int]:
    v = str(value or "").strip().lstrip("#")
    return int(v) if v.isdigit() and int(v) > 0 else None


def make_command(rt) -> Callable[..., str]:
    """``handler(raw_args, source=None, session_id=None, platform=None) -> str`` for ``/home3d``."""
    cmd = _Command(rt)

    def home3d(raw_args: str = "", source: Any = None, session_id: Any = None, platform: Any = None) -> str:
        return cmd(raw_args, source=source, session_id=session_id, platform=platform)

    home3d.command = cmd  # type: ignore[attr-defined]  (tests / CLI demo reuse the tool cache)
    return home3d


__all__ = ["make_command", "authorize", "format_status"]
