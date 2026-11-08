"""``/home3d`` slash command (CLI, TUI and messaging gateway; no model call).

  /home3d status                        printer, queue, plate and watcher state
  /home3d approve start <id> [jump]     owner: start queue item <id> now if the safety gate passes
  /home3d approve clear                 owner: mark the plate clear now if the gate passes (also confirms the plate
                                        after a failed print)
  /home3d approve resume [ack]          owner: resume a paused print (``ack`` = resume despite a printer error)
  /home3d whoami                        the sender id / household person this chat maps to
  /home3d upgrades | moments            upgrade proposals / human-needed moments (last 30 days)
  /home3d help                          one line per subcommand, in the household language (``help_text``)

``approve`` only counts for the owner: ``source.user_id`` equal (exactly, ``config.norm_id``) to an owner id, or a
local session when ``local_is_owner`` (no source = the classic CLI / TUI; a ``local`` platform source with a
``uid:<n>`` user = the gateway-hosted CLI). Hermes v0.22.5 also passes no source for slash commands typed in the
TUI, Desktop and the web dashboard, so whoever can use those surfaces counts as the local owner while
``local_is_owner`` is on (they can already edit ``config.yaml``, including ``owner_ids``); turn it off on a shared
or remotely reachable dashboard. ``source.chat_id`` is never accepted: in a group chat it names the group,
not the person. The command runs the same gate as the ``pre_tool_call`` hook and, when it passes, does the action
right away; nothing is stored that could authorise a later action. When the gate or the action fails, the owner is
told why and sends the command again when ready.
"""

from __future__ import annotations

import json
import re
import shlex
import time
import uuid
from typing import Any, Callable, Optional

from .config import LOCAL_SENDER, norm_id
from .hooks import TOOL_FOR_ACTION, approve_command, evaluate, is_local_platform, watcher_fresh

_LOCAL_UID = re.compile(r"^uid:\d+$")

# (usage, English description, Turkish description): one line each in ``/home3d help``
HELP_LINES = (
    ("status", "printer, queue, plate and watcher state", "yazıcı, kuyruk, tabla ve izleyici durumu"),
    ("approve start <id> [jump]", "owner: start queue item <id> now; the safety gate and the camera check run first "
     "(jump = skip jobs waiting ahead)", "sahibi: <no> numaralı işi şimdi başlat; önce güvenlik kontrolü ve kamera "
     "(jump = öndeki işleri atla)"),
    ("approve clear", "owner: mark the plate clear (also confirms the plate after a failed print)",
     "sahibi: tablayı boş işaretle (yarıda kalan baskıdan sonra tablayı da onaylar)"),
    ("approve resume [ack]", "owner: resume a paused print (ack = despite an active printer error)",
     "sahibi: duraklatılan baskıya devam et (ack = yazıcı hatasına rağmen)"),
    ("whoami", "which household person this chat is (and whether it is the owner)",
     "bu sohbet evden kim (sahibi mi)"),
    ("upgrades", "upgrade proposals from repeated hands-on moments",
     "tekrarlanan elle müdahalelerden yükseltme önerileri"),
    ("moments", "when a person had to step in (last 30 days)", "elle müdahale gereken anlar (son 30 gün)"),
    ("help", "this list", "bu liste"),
)


def help_text(lang: str) -> str:
    """One line per subcommand with a short description, in ``lang``."""
    tr = lang == "tr"
    rows = [(f"/home3d {usage}" if not tr else f"/home3d {usage.replace('<id>', '<no>')}", desc_tr if tr else desc)
            for usage, desc, desc_tr in HELP_LINES]
    width = max(len(u) for u, _d in rows)
    return "\n".join(f"{u:<{width}}  {d}" for u, d in rows)


_T = {
    "not_owner": ("Only the owner can approve ({who} is not in owner_ids).",
                  "Sadece sahibi onaylayabilir ({who} owner_ids listesinde değil)."),
    "no_user": ("Only the owner can approve (this platform did not say who sent the command).",
                "Sadece sahibi onaylayabilir (komutu kimin gönderdiği bilinmiyor)."),
    "local_off": ("Only the owner can approve (local sessions are not the owner: local_is_owner is off).",
                  "Sadece sahibi onaylayabilir (yerel oturum sahibi sayılmıyor: local_is_owner kapalı)."),
    "usage_start": ("Usage: /home3d approve start <queue id> [jump]", "Kullanım: /home3d approve start <sıra no> [jump]"),
    "usage_approve": ("Usage: /home3d approve start <id> | clear | resume [ack]",
                      "Kullanım: /home3d approve start <no> | clear | resume [ack]"),
    "started": ("▶️ Started #{qid} \"{name}\"{who}. The watcher reports the finish and the plate.",
                "▶️ #{qid} \"{name}\" başladı{who}. Bitişi ve tablayı izleyip haber vereceğim."),
    "no_watcher": ("⚠️ The watcher is not running, so nobody is told about the finish: hermes home3d doctor.",
                   "⚠️ İzleyici çalışmıyor, bitişi kimseye haber veremem: hermes home3d doctor."),
    "cleared": ("✅ Plate marked clear{extra}.", "✅ Tabla boş olarak işaretlendi{extra}."),
    "next_job": ("Next workshop job: #{qid} \"{name}\": /home3d approve start {qid}",
                 "Sıradaki atölye işi: #{qid} \"{name}\": /home3d approve start {qid}"),
    "resumed": ("▶️ Resumed \"{name}\".", "▶️ \"{name}\" devam ediyor."),
    "not_done": ("Not done: {why} Nothing was kept: send the command again when ready.",
                 "Yapılamadı: {why} Onay saklanmadı, hazır olunca komutu tekrar gönder."),
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


def identify(source: Any, platform: str = "") -> tuple[str, str]:
    """(sender id as the store records it, label) of whoever sent a command. ``LOCAL_SENDER`` for a local session:
    no source (classic CLI / TUI) or a ``local``-platform source whose user is ``uid:<n>`` (gateway-hosted CLI)."""
    if source is None:
        return LOCAL_SENDER, "local session"
    uid = _src(source, "user_id").strip()
    plat = _src(source, "platform") or platform
    if is_local_platform(plat) and _LOCAL_UID.match(uid.lower()):
        return LOCAL_SENDER, f"local session ({uid})"
    if uid and norm_id(uid) == LOCAL_SENDER:  # a messaging user literally named "local" is not the local owner
        return "", uid
    return uid, uid


def authorize_sender(rt, source: Any, platform: str = "") -> tuple[bool, str, str, str]:
    """(allowed, approver label, sender id, refusal text)."""
    s = rt.settings
    lang = s.language
    sender, label = identify(source, platform)
    if sender == LOCAL_SENDER:
        if s.local_is_owner:
            return True, f"{s.owner_name} (local)", sender, ""
        return False, "", sender, _t("local_off", lang)
    if not sender:
        return False, "", "", (_t("not_owner", lang, who=label) if label else _t("no_user", lang))
    person = s.person_for(sender)
    if person is not None and s.is_owner(sender):
        return True, person.name, sender, ""
    return False, "", sender, _t("not_owner", lang, who=person.name if person else sender)


def authorize(rt, source: Any, platform: str = "") -> tuple[bool, str, str]:
    """(allowed, approver label, refusal text). See ``authorize_sender``."""
    ok, approver, _sender, refusal = authorize_sender(rt, source, platform)
    return ok, approver, refusal


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
    if p.get("awaiting_plate_clear") is True:
        lines.append("⚠️ " + ("Yazıcı yöneticisi tablanın boş işaretlenmesini bekliyor: /home3d approve clear" if tr
                              else "The printer manager waits for the plate to be marked clear: /home3d approve clear"))
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
        lines.append("⚠️ " + _watcher_line(w, tr))
    return "\n".join(lines)


def _watcher_line(w: dict, tr: bool) -> str:
    """Why the watcher is not reporting, and what to do (tools._watcher_info ``state``)."""
    state = w.get("state") or ("stale" if w.get("last_run_age_s") is not None else "not_installed")
    if state == "stale":
        mins = round(float(w.get("last_run_age_s") or 0) / 60)
        return (f"İzleyici {mins} dakikadır çalışmadı: Hermes zamanlayıcısı çalışıyor mu? (`hermes gateway`, "
                "`hermes cron status`)" if tr else
                f"Watcher not running: last pass {mins} min ago. Is the Hermes scheduler running? "
                "(`hermes gateway`, check `hermes cron status`)")
    if state == "never_ran":
        return ("İzleyici kurulu ama Hermes zamanlayıcısı çalışmıyor: `hermes gateway` başlat "
                "(`hermes cron status`)." if tr else
                "Watcher not running: installed, but the Hermes scheduler is not running: start `hermes gateway` "
                "(check `hermes cron status`).")
    return ("İzleyici çalışmıyor: kurmak için `hermes home3d setup` (`hermes gateway` açık olmalı)." if tr else
            "Watcher not running: set it up with `hermes home3d setup` (needs `hermes gateway` running).")


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
            return help_text(lang)
        if sub in ("status", "durum"):
            return format_status(self.tool("home3d_status", {}, session_id), lang)
        if sub in ("approve", "onay", "onayla"):
            return self.approve(rest, source, session_id, platform, lang)
        if sub == "whoami":
            return self.whoami(source, session_id, platform, lang)
        if sub in ("upgrades", "upgrade"):
            return self.upgrades(lang)
        if sub in ("moments", "moment"):
            return self.moments(lang)
        return _t("unknown", lang, sub=sub[:30]) + "\n" + help_text(lang)

    # -- approve --
    def approve(self, rest: list[str], source: Any, session_id: str, platform: str, lang: str) -> str:
        what = rest[0] if rest else ""
        flags = {w.lower() for w in rest[1:]}
        if what in ("start", "başlat", "baslat"):
            qid = _parse_id(rest[1]) if len(rest) > 1 else None
            if qid is None:
                return _t("usage_start", lang)
            jump = bool(flags & {"jump", "--jump", "atla"})
            action, args = "start", {"queue_item_id": qid, "allow_jump": jump}
        elif what in ("clear", "plate", "temizle", "tabla"):
            qid, jump = None, False
            action, args = "clear_plate", {"action": "confirm"}
        elif what in ("resume", "devam"):
            qid, jump = None, False
            ack = bool(flags & {"ack", "--ack", "onay", "tamam"})
            action, args = "resume", {"action": "resume", "reason": "owner approved resume", "ack_hms": ack}
        else:
            return _t("usage_approve", lang)
        ok, approver, sender, refusal = authorize_sender(self.rt, source, platform)
        if not ok:
            return refusal
        store, tool = self.rt.store, TOOL_FOR_ACTION[action]
        command = approve_command(action, qid, jump, ack=bool(args.get("ack_hms")))
        store.add_event("approval_granted", "", {"action": action, "approver": approver, "sender": sender,
                                                 "command": command, "session": session_id[:80]})
        ev = evaluate(self.rt, action, args)  # the same cron check + safety gate as the pre_tool_call hook
        if not ev.ok:
            return _t("not_done", lang, why=_sentence(ev.message or ev.reason))
        # A private session id for this one command: the pass below can only be used by the call made right here,
        # never by another session (a group chat shares one session id) or by a later call.
        cmd_sid = f"home3d-approve-{uuid.uuid4().hex}"
        store.remember_sender(cmd_sid, sender, platform or _src(source, "platform"))
        store.issue_pass(tool, ev.target, cmd_sid, detail=ev.pass_detail)  # resume ack: the codes shown
        try:
            # The handler is called directly, not through ctx.dispatch_tool: Hermes' registry.dispatch skips the
            # pre_tool_call hooks anyway (v0.22.5), so the owner check above, ``evaluate`` and the single-use pass are
            # what authorise this call; the handler re-checks its gate and uses the pass.
            res = self.tool(tool, args, cmd_sid)
        finally:
            store.consume_pass(tool, ev.target, cmd_sid)  # nothing lingers, used or not
            store.forget_sender(cmd_sid)
        if not res.get("ok"):
            return _t("not_done", lang, why=_sentence(res.get("message") or res.get("error") or "?"))
        store.add_event("approval_used", str(res.get("name") or res.get("job") or ""),
                        {"action": action, "target": ev.target, "approver": approver, "tool": tool})
        if action == "start":
            who = f" ({res['requester']})" if res.get("requester") else ""
            out = _t("started", lang, qid=qid, name=_pretty(str(res.get("name") or f"#{qid}")), who=who)
            return out if watcher_fresh(store) else out + "\n" + _t("no_watcher", lang)
        if action == "clear_plate":
            plate = res.get("plate") or {}
            diff = plate.get("difference_pct")
            out = _t("cleared", lang, extra=f" ({diff:g}%)" if isinstance(diff, (int, float)) else "")
            nxt = res.get("next_job") if isinstance(res.get("next_job"), dict) else None
            if nxt and nxt.get("id"):
                out += "\n" + _t("next_job", lang, qid=nxt["id"], name=_pretty(str(nxt.get("name") or "")))
            return out
        return _t("resumed", lang, name=_pretty(str(res.get("job") or "")))

    # -- info --
    def whoami(self, source: Any, session_id: str, platform: str, lang: str) -> str:
        s = self.rt.settings
        uid = _src(source, "user_id")
        plat = _src(source, "platform") or platform or ("cli" if source is None else "?")
        sender, _label = identify(source, platform)
        person = s.person_for(sender) if sender else None
        if sender == LOCAL_SENDER:
            who = f"{s.owner_name} (owner, local session)" if person else "local session (local_is_owner is off)"
        elif person:
            who = f"{person.name} ({person.role})"
        else:
            who = "not in the household list" if lang != "tr" else "ev listesinde yok"
        owner = bool(sender) and s.is_owner(sender)
        lines = [f"platform: {plat}", f"user_id: {uid or '-'}", f"person: {who}",
                 f"owner: {'yes' if owner else 'no'}"]
        if session_id:
            lines.append(f"session: {session_id[:40]}")
        if uid and not person and sender != LOCAL_SENDER:
            lines.append("add this id to owner_ids or household to be recognised (ids must match exactly)")
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
        tr = lang == "tr"
        for u in rows[:8]:
            status = up.status_label(u["status"], lang)
            out.append(f"💡 #{u['id']} [{status}] {_upgrade_title(u, tr)} · {u.get('evidence', 0)}×"
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
        """The last 30 days of hands-on moments. Turkish shows the kind's Turkish label and the detail only when
        ``upgrades.detail_text`` can translate it (the watcher and the hook write details in English)."""
        from . import upgrades as up

        store = self.rt.store
        tr = lang == "tr"
        counts = store.human_needed_counts(30)
        if not counts:
            return _t("no_moments", lang)
        head = ("Son 30 gün: " if tr else "Last 30 days: ") + ", ".join(
            f"{_kind_label(k, tr)} {n}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
        lines = [head]
        for m in store.human_needed(since_days=30, limit=5):
            when = time.strftime("%m-%d %H:%M", time.localtime(m.get("ts") or 0))
            raw = str(m.get("detail") or "")
            if tr:
                try:
                    shown = up.detail_text(raw, "tr")
                except Exception:
                    shown = raw
                detail = shown[:60] if shown != raw.strip() else ""
            else:
                detail = raw[:60]
            bits = " · ".join(x for x in (_pretty(str(m.get("job_name") or "")), m.get("who"), detail) if x)
            lines.append(f"  {when} {_kind_label(m['kind'], tr)}" + (f" · {bits}" if bits else ""))
        return "\n".join(lines)


def _kind_label(kind: str, tr: bool) -> str:
    """A moment kind for people: the raw kind in English (the owner knows them), the Turkish label in Turkish."""
    if not tr:
        return kind
    from .upgrades import KINDS

    info = KINDS.get(kind) if isinstance(KINDS.get(kind), dict) else {}
    return str(info.get("label_tr") or kind)


def _upgrade_title(row: dict, tr: bool) -> str:
    """The stored title, or the kind's Turkish title in Turkish when the stored one is the English default."""
    title = str(row.get("title") or "")
    if not tr:
        return title
    from .upgrades import KINDS

    info = KINDS.get(str(row.get("kind") or "")) if isinstance(KINDS.get(str(row.get("kind") or "")), dict) else {}
    return str(info.get("title_tr") or title) if info and title == info.get("title") else title


def _sentence(text: Any) -> str:
    t = str(text or "").strip()
    return t if t.endswith((".", "!", "?")) else t + "."


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


__all__ = ["make_command", "authorize", "authorize_sender", "identify", "format_status", "help_text", "HELP_LINES"]
