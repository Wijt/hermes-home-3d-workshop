"""``/home3d`` slash command (CLI, TUI and messaging gateway; no model call).

  /home3d status                        printer, queue, plate and watcher state
  /home3d approve start <id> [jump]     owner: start queue item <id> now if the safety gate passes (with
                                        ``start_policy: known`` also a listed person, for their own job, no jump)
  /home3d approve clear                 owner: mark the plate clear now if the gate passes (also confirms the plate
                                        after a failed print)
  /home3d approve resume [ack]          owner: resume a paused print (``ack`` = resume despite a printer error)
  /home3d stop [reason] | pause [reason]  the owner and known people (``stop_policy``): stop / pause the print now
  /home3d collected <part id>           the owner and known people: a done-box part was picked up
  /home3d whoami                        the sender id / household person this chat maps to
  /home3d upgrades | moments            upgrade proposals / human-needed moments (last 30 days)
  /home3d help                          one line per subcommand, in the household language (``help_text``)

``approve`` only counts for the owner (and, for ``approve start`` under ``start_policy: known``, for the listed person
whose own job it is: ``hooks.who_may``): ``source.user_id`` equal (exactly, ``config.norm_id``) to an owner id, or a
local session when ``local_is_owner`` (no source = the classic CLI / TUI; a ``local`` platform source with a
``uid:<n>`` user = the gateway-hosted CLI). Hermes v0.22.5 also passes no source for slash commands typed in the
TUI, Desktop and the web dashboard, so whoever can use those surfaces counts as the local owner while
``local_is_owner`` is on (they can already edit ``config.yaml``, including ``owner_ids``); turn it off on a shared
or remotely reachable dashboard. ``source.chat_id`` is never accepted: in a group chat it names the group,
not the person. The command runs the same gate as the ``pre_tool_call`` hook and, when it passes, does the action
right away; nothing is stored that could authorise a later action. When the gate or the action fails, the owner is
told why and sends the command again when ready.

One code path: every printer action of the command goes through ``perform(rt, action, sender=...)``, which
returns ``{"ok", "code", "message"}`` (a Desktop screen or any other program can call it, or the slash command, as
the local owner). In this order it refuses a run nobody is present for (``Runtime.absent_reason``: cron, kanban
worker, ``chat -q``, ``-z``, ``--source tool``; even for the owner), a sender the rule does not allow
(``gates.approval_refusal`` / ``gates.stop_refusal``, the same rules as the agent path), a start / resume / plate
clear that arrived as a voice message, then runs the safety gate and the action.

Result marker: the reply of every action subcommand (``approve start|clear|resume``, ``stop``, ``pause``,
``collected``) ends with one line a program can read without guessing from the wording (``result_marker``)::

    [home3d:ok]                    the action was done
    [home3d:not_done:<code>]       it was not, with ``perform``'s ``code`` (not_owner, gate, nothing_printing, ...)

The Workshop screen in Hermes Desktop runs these commands and reads this line; people see it as a short tag.
"""

from __future__ import annotations

import json
import re
import shlex
import time
import uuid
from typing import Any, Callable, Optional

from .config import LOCAL_SENDER, norm_id, scoped_sender
from .gates import MEMBER, TYPED, VOICE, refusal, stop_refusal
from .hooks import (TOOL_FOR_ACTION, absent_text, approve_command, evaluate, is_local_platform, watcher_fresh,
                    who_may)

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
    ("stop [reason]", "the owner and known people: stop the running print now",
     "sahibi ve tanınan kişiler: süren baskıyı hemen durdur"),
    ("pause [reason]", "the owner and known people: pause the running print (resume needs the owner)",
     "sahibi ve tanınan kişiler: süren baskıyı duraklat (devam için sahibi gerekir)"),
    ("collected <part id>", "the owner and known people: a part from the done box was picked up",
     "sahibi ve tanınan kişiler: bitmiş parça kutudan alındı"),
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
    "own_only": ("{who} can start only a print {who} asked for, and never with jump (start_policy: known).",
                 "{who} yalnızca kendi istediği baskıyı başlatabilir, jump ile asla (start_policy: known)."),
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
    "stopped": ("⏹️ Stopped \"{name}\" ({by}). Check the plate before the next print.",
                "⏹️ \"{name}\" durduruldu ({by}). Sonraki baskıdan önce tablaya bak."),
    "paused": ("⏸️ Paused \"{name}\" ({by}). Resume: /home3d approve resume", "⏸️ \"{name}\" duraklatıldı ({by}). "
               "Devam: /home3d approve resume"),
    "already_paused": ("⏸️ The print is already paused.", "⏸️ Baskı zaten duraklatılmış."),
    "nothing_printing": ("Nothing is printing, so no command was sent.", "Şu an baskı yok, komut gönderilmedi."),
    "usage_collected": ("Usage: /home3d collected <part id>", "Kullanım: /home3d collected <parça no>"),
    "collected": ("📦 \"{name}\" marked collected ({by}).", "📦 \"{name}\" alındı olarak işaretlendi ({by})."),
    "already_collected": ("📦 \"{name}\" was already marked collected.", "📦 \"{name}\" zaten alındı olarak işaretli."),
    "no_part": ("No part #{pid} in the done box.", "Bitmiş parçalar arasında #{pid} yok."),
    "collected_unknown": ("Only the owner and the people in the household list can mark a part collected.",
                          "Parçayı alındı olarak sadece sahibi ve ev listesindeki kişiler işaretleyebilir."),
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
    return scoped_sender(uid, plat), uid  # "irc:<nick>": a freely chosen id never matches a bare household id


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
        if sub in ("stop", "dur", "durdur", "pause", "duraklat"):
            action = "stop" if sub in ("stop", "dur", "durdur") else "pause"
            return _marked(self.act(action, source, session_id, platform, reason=" ".join(rest)[:200]))
        if sub in ("collected", "collect", "alındı", "alindi"):
            pid = _parse_id(rest[0]) if rest else None
            if pid is None:
                return _marked(_result(False, "usage", _t("usage_collected", lang)))
            return _marked(self.act("collected", source, session_id, platform, part_id=pid))
        if sub == "whoami":
            return self.whoami(source, session_id, platform, lang)
        if sub in ("upgrades", "upgrade"):
            return self.upgrades(lang)
        if sub in ("moments", "moment"):
            return self.moments(lang)
        return _t("unknown", lang, sub=sub[:30]) + "\n" + help_text(lang)

    # -- approve / stop / pause: all through perform() --
    def approve(self, rest: list[str], source: Any, session_id: str, platform: str, lang: str) -> str:
        what = rest[0] if rest else ""
        flags = {w.lower() for w in rest[1:]}
        if what in ("start", "başlat", "baslat"):
            qid = _parse_id(rest[1]) if len(rest) > 1 else None
            if qid is None:
                return _marked(_result(False, "usage", _t("usage_start", lang)))
            return _marked(self.act("start", source, session_id, platform, qid=qid,
                                    jump=bool(flags & {"jump", "--jump", "atla"})))
        if what in ("clear", "plate", "temizle", "tabla"):
            return _marked(self.act("clear", source, session_id, platform))
        if what in ("resume", "devam"):
            return _marked(self.act("resume", source, session_id, platform,
                                    ack=bool(flags & {"ack", "--ack", "onay", "tamam"})))
        return _marked(_result(False, "usage", _t("usage_approve", lang)))

    def act(self, action: str, source: Any, session_id: str, platform: str, **kw: Any) -> dict:
        """``perform`` for whoever sent this command (``identify``). A command whose sender's newest message at
        the gateway was a voice note (Hermes' voice mode hands a transcript on as text) counts as spoken."""
        sender, label = identify(source, platform)
        spoken = bool(source is not None and self.rt.spoken_command(_src(source, "user_id")))
        return perform(self.rt, action, sender=sender, label=label, platform=platform or _src(source, "platform"),
                       session_id=session_id, spoken=spoken, tool=self.tool, **kw)

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


def result_marker(result: dict) -> str:
    """``[home3d:ok]`` or ``[home3d:not_done:<code>]`` for a ``perform`` result (see the module doc)."""
    if result.get("ok"):
        return "[home3d:ok]"
    code = re.sub(r"[^a-z0-9_]", "_", str(result.get("code") or "failed").lower())[:40] or "failed"
    return f"[home3d:not_done:{code}]"


def _marked(result: dict) -> str:
    """The reply text of an action subcommand: ``perform``'s message, then the result marker on its own line."""
    return f"{str(result.get('message') or '').rstrip()}\n{result_marker(result)}"


def _title(name: Any) -> str:
    """A job or file name as people say it (``mum-key-tag_v1.gcode.3mf`` -> ``Mum key tag v1``), as the Workshop
    screen shows it."""
    from .workshop import pretty_name

    return pretty_name(name)


def _sentence(text: Any) -> str:
    t = str(text or "").strip()
    return t if t.endswith((".", "!", "?")) else t + "."


def _parse_id(value: str) -> Optional[int]:
    v = str(value or "").strip().lstrip("#")
    return int(v) if v.isdigit() and int(v) > 0 else None


ACTIONS = ("start", "clear", "resume", "stop", "pause", "collected")
_APPROVAL = {"start": "start", "clear": "clear_plate", "resume": "resume"}


def _result(ok: bool, code: str, message: str, **extra: Any) -> dict:
    return {"ok": ok, "code": code, "message": message, **extra}


def perform(rt, action: str, *, sender: str, label: str = "", platform: str = "", session_id: str = "",
            qid: Optional[int] = None, jump: bool = False, ack: bool = False, reason: str = "", spoken: bool = False,
            tool: Optional[Callable[[str, dict, str], dict]] = None, part_id: Optional[int] = None) -> dict:
    """Do one printer action for an actor and say how it went: ``{"ok": bool, "code": str, "message": str}``.

    ``action``: ``start`` (``qid``, ``jump``), ``clear`` (mark the plate clear / confirm it), ``resume`` (``ack``:
    despite a printer error), ``stop``, ``pause`` (``reason``), ``collected`` (``part_id``: a done-box part was
    picked up; the owner and known people, no printer call). ``sender``: the id as the store records it
    (``identify``; ``config.LOCAL_SENDER`` = the local owner while ``local_is_owner``). ``spoken``: the ask came in
    as a voice message. ``tool``: how to call a ``home3d_*`` handler (tests and ``/home3d`` reuse their cache).

    ``code`` is ``ok`` or why not: ``usage``, ``unattended``, ``no_identity`` / ``local_off`` / ``not_owner``,
    ``voice_message``, ``stop_unknown`` / ``stop_owner_only`` / ``stop_unattended``, ``bad_request``,
    ``printer_unreachable``, ``gate``, ``nothing_printing``, ``failed``, ``collected_unknown``, ``no_part``. ``message`` is in the household language.
    Never raises for a refusal; nothing is stored that could authorise a later action."""
    s = rt.settings
    lang = s.language
    action = str(action or "").strip().lower()
    if action not in ACTIONS:
        return _result(False, "usage", _t("usage_approve", lang))
    if tool is None:
        tool = _Command(rt).tool
    sender = str(sender or "")
    if action == "collected":
        return _collected(rt, sender, part_id, lang)
    if action in ("stop", "pause"):
        cmd = f"/home3d {action}"
        actor = rt.actor_for(sender, VOICE if spoken else TYPED)
        why = stop_refusal(actor, s.stop_policy)
        if why:
            return _result(False, why, refusal(why, lang, cmd=cmd, who=actor.label(lang)))
        return _run(rt, "home3d_stop", {"action": action, "reason": reason or f"{action} by command"}, sender,
                    platform, tool, action, lang)
    gated = _APPROVAL[action]
    if action == "start" and qid is None:
        return _result(False, "usage", _t("usage_start", lang))
    command = approve_command(gated, qid, jump, ack=ack)
    tool_name = TOOL_FOR_ACTION[gated]
    absent = absent_text(rt, tool_name, command)  # 1. nobody present (cron, kanban, -q, -z, tool): even the owner
    if absent:
        return _result(False, "unattended", _t("not_done", lang, why=_sentence(
            refusal("unattended", lang, cmd=command) if lang == "tr" else absent)))
    actor = rt.actor_for(sender, VOICE if spoken else TYPED)
    why = who_may(rt, actor, gated, qid, jump)  # 2. the same rule as the agent path (hooks.pre_tool_call)
    if why == "unattended":  # the presence answer changed meanwhile: still refused
        return _result(False, why, refusal(why, lang, cmd=command))
    if why in ("no_identity", "not_owner", "local_off"):
        if why == "local_off":
            text = _t("local_off", lang)
        elif sender:
            text = _t("not_owner", lang, who=(s.person_for(sender).name if s.person_for(sender) else
                                              (label or sender)))
        else:
            text = _t("not_owner", lang, who=label) if label else _t("no_user", lang)
        if gated == "start" and s.start_policy == "known" and actor.role == MEMBER:
            text += " " + _t("own_only", lang, who=actor.name)  # why this start is not theirs to make
        return _result(False, why, text)
    if why:  # voice_message, or a rule this code does not know: refused
        return _result(False, why, refusal(why, lang, cmd=command, who=actor.label(lang)))
    store = rt.store
    approver = f"{s.owner_name} (local)" if sender == LOCAL_SENDER else actor.name
    if gated == "start":
        args: dict = {"queue_item_id": qid, "allow_jump": bool(jump)}
    elif gated == "clear_plate":
        args = {"action": "confirm"}
    else:
        args = {"action": "resume", "reason": "owner approved resume", "ack_hms": bool(ack)}
    store.add_event("approval_granted", "", {"action": gated, "approver": approver, "sender": sender,
                                             "command": command, "session": str(session_id or "")[:80]})
    ev = evaluate(rt, gated, args)  # 3. the same presence check + safety gate as the pre_tool_call hook
    if not ev.ok:
        return _result(False, ev.code or "gate", _t("not_done", lang, why=_sentence(ev.message or ev.reason)))
    # A private session id for this one command: the pass below can only be used by the call made right here,
    # never by another session (a group chat shares one session id) or by a later call.
    cmd_sid = f"home3d-approve-{uuid.uuid4().hex}"
    store.remember_sender(cmd_sid, sender, platform)
    store.issue_pass(tool_name, ev.target, cmd_sid, detail=ev.pass_detail)  # resume ack: the codes shown
    try:
        # The handler is called directly, not through ctx.dispatch_tool: Hermes' registry.dispatch skips the
        # pre_tool_call hooks anyway (v0.22.5), so the owner check above, ``evaluate`` and the single-use pass are
        # what authorise this call; the handler re-checks its gate and uses the pass.
        res = tool(tool_name, args, cmd_sid)
    finally:
        store.consume_pass(tool_name, ev.target, cmd_sid)  # nothing lingers, used or not
        store.forget_sender(cmd_sid)
    if not res.get("ok"):
        return _result(False, "failed", _t("not_done", lang, why=_sentence(res.get("message") or res.get("error")
                                                                           or "?")), result=res)
    store.add_event("approval_used", str(res.get("name") or res.get("job") or ""),
                    {"action": gated, "target": ev.target, "approver": approver, "tool": tool_name})
    if gated == "start":
        who = f" ({res['requester']})" if res.get("requester") else ""
        out = _t("started", lang, qid=qid, name=_title(res.get("name")) or f"#{qid}", who=who)
        out = out if watcher_fresh(store, s) else out + "\n" + _t("no_watcher", lang)
    elif gated == "clear_plate":
        plate = res.get("plate") or {}
        diff = plate.get("difference_pct")
        out = _t("cleared", lang, extra=f" ({diff:g}%)" if isinstance(diff, (int, float)) else "")
        nxt = res.get("next_job") if isinstance(res.get("next_job"), dict) else None
        if nxt and nxt.get("id"):
            out += "\n" + _t("next_job", lang, qid=nxt["id"], name=_title(nxt.get("name")))
    else:
        out = _t("resumed", lang, name=_title(res.get("job")))
    return _result(True, "ok", out, result=res)


def _run(rt, tool_name: str, args: dict, sender: str, platform: str, tool: Callable[[str, dict, str], dict],
         action: str, lang: str) -> dict:
    """Stop or pause through the ``home3d_stop`` handler, as ``sender`` (a private session id for this one call, so
    the handler records who really did it and re-checks ``stop_policy`` itself)."""
    store = rt.store
    cmd_sid = f"home3d-cmd-{uuid.uuid4().hex}"
    store.remember_sender(cmd_sid, sender, platform)
    try:
        res = tool(tool_name, args, cmd_sid)
    finally:
        store.forget_sender(cmd_sid)
    if not res.get("ok"):
        code = str(res.get("code") or ("nothing_printing" if "nothing is printing" in str(res.get("error"))
                                       else "failed"))
        if code == "nothing_printing":
            return _result(False, code, _t("nothing_printing", lang), result=res)
        return _result(False, code, str(res.get("message") or "") or
                       _t("not_done", lang, why=_sentence(res.get("error") or "?")), result=res)
    name = _title(res.get("job"))
    if action == "pause" and res.get("note") == "already paused":
        return _result(True, "ok", _t("already_paused", lang), result=res)
    return _result(True, "ok", _t("stopped" if action == "stop" else "paused", lang, name=name,
                                  by=str(res.get("by") or "?")), result=res)


def _collected(rt, sender: str, part_id: Optional[int], lang: str) -> dict:
    """Mark a done-box part collected (``Store.set_collected``) for the owner or a known person; anyone else, and a
    run nobody is present for, is refused."""
    if part_id is None:
        return _result(False, "usage", _t("usage_collected", lang))
    actor = rt.actor_for(sender, TYPED)
    if not actor.present:
        return _result(False, "unattended", refusal("unattended", lang, cmd=f"/home3d collected {part_id}"))
    if not actor.known:
        return _result(False, "collected_unknown", _t("collected_unknown", lang))
    store = rt.store
    part = store.get_done_part(int(part_id))
    if part is None:
        return _result(False, "no_part", _t("no_part", lang, pid=part_id))
    name = str(part.get("title") or "").strip() or _title(part.get("job_name")) or f"#{part_id}"
    if part.get("collected"):
        return _result(True, "ok", _t("already_collected", lang, name=name), part_id=int(part_id))
    by = actor.name or rt.settings.owner_name or ""
    store.set_collected(int(part_id), True, by=by)
    store.add_event("part_collected", str(part.get("job_name") or ""), {"part_id": int(part_id), "by": by,
                                                                        "sender": sender})
    return _result(True, "ok", _t("collected", lang, name=name, by=by), part_id=int(part_id))


def make_command(rt) -> Callable[..., str]:
    """``handler(raw_args, source=None, session_id=None, platform=None) -> str`` for ``/home3d``."""
    cmd = _Command(rt)

    def home3d(raw_args: str = "", source: Any = None, session_id: Any = None, platform: Any = None) -> str:
        return cmd(raw_args, source=source, session_id=session_id, platform=platform)

    home3d.command = cmd  # type: ignore[attr-defined]  (tests / CLI demo reuse the tool cache)
    return home3d


__all__ = ["make_command", "perform", "result_marker", "ACTIONS", "authorize", "authorize_sender", "identify", "format_status", "help_text", "HELP_LINES"]
