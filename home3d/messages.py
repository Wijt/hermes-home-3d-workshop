"""Owner vs family message templates (tr / en). Pure, stdlib only.

``render(kind, audience, lang, **ctx)`` returns the text, or ``""`` when that audience should not get a
message for this kind (offline, HMS, ready-next and upgrade notices are owner-only).

Family: one or two short warm lines, plain words, addressed to the requester (``address_as`` or
``requester``) when known, never English words inside Turkish. Owner: technical (state, layer, temps,
HMS, links) but still short.

Family texts name the print by what the person asked for (``family_job``: the stored request text,
shortened with ``short_text``) and fall back to ``job`` (the pretty file name); owner texts always use
``job``. Plate wording is honest: the camera *thinks* the plate is empty, nothing is "verified".

ctx keys (all optional): persona, owner (owner display name), job, family_job, queue_item_id, requester,
address_as, progress, layer, total_layers, duration_min, grams, bed_temp, nozzle_temp, hms_code,
hms_message, wiki_url, filament (bool: the pause is a filament run-out), reason, eject_planned (bool),
plate_diff, next_job, next_id, ahead (list of {"id", "name"}: pending jobs ahead of ``next_id`` that the
workshop did not queue), foreign (list of {"id", "name", "since"}: such jobs on their own),
confirm_first (bool: the last print failed and nobody confirmed the plate yet), photo (bool: a fresh
photo is attached), upgrade_title, upgrade_id, upgrade_label, evidence, window_days, model_ref,
preview_url, offline_min, eject_in_gcode (bool: the end G-code already pushed the part before FINISH),
eject_result_follows (bool: the same message carries the camera result), missed_end ("" | "busy" | "idle":
the watcher did not see the print end; the printer went on to another job / is idle again), error (the
printer manager's error_message), action ("start" | "resume" | "clear") and who (the household member asking)
for approval requests, asked_by (ready_next: a household member asked to start this job), awaiting_clear
(ready_next: Bambuddy waits for the plate to be marked clear before any start), camera_said (ready_next: the same
message already gives the camera's reading; confirm_said: and the "confirm the plate" line), eject_unknown ("foreign" | "unknown": a finish the workshop did not
queue, so its eject plan is unknown) with camera_empty (bool: the camera thinks the plate is empty), stopped_by /
stop_reason (stopped: who stopped the print and why), not_paused (approval_request resume: the printer state now,
nothing is paused), state (online: the printer state now). ``ahead`` / ``foreign`` items may carry ``who`` (another
household member's workshop job).
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

KINDS = ("started", "finished", "finished_ejected", "plate_not_clear", "eject_unverified", "plate_clear",
         "failed", "paused", "hms", "offline", "ready_next", "queue_foreign", "upgrade_proposed", "eject_skipped",
         "light_left_on", "approval_request", "start_failed", "stopped", "online")
OWNER_ONLY = frozenset({"hms", "offline", "ready_next", "queue_foreign", "upgrade_proposed", "plate_clear",
                        "light_left_on", "approval_request", "start_failed", "stopped", "online"})
_STATE_WORDS = {"PREPARE": ("preparing", "hazırlanıyor"), "RUNNING": ("printing", "baskıda"),
                "PAUSE": ("paused", "duraklatıldı"), "FINISH": ("finished", "bitti"),
                "FAILED": ("failed", "yarıda kaldı"), "IDLE": ("idle", "boşta"), "UNKNOWN": ("unknown", "bilinmiyor")}
ERROR_MAX = 300  # owner texts quote at most this much of a printer manager's error message
FAMILY_JOB_MAX = 40  # family texts quote at most this many characters of the request text
AUDIENCES = ("owner", "family")

_TR_BACK = set("aıou")
_TR_FRONT = set("eiöü")
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


# ---- small formatting helpers ---------------------------------------------------------------
def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _num(v: Any) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Optional[int]:
    n = _num(v)
    return None if n is None else int(round(n))


def pct(v: Any, lang: str) -> str:
    """40 -> '%40' (tr) / '40%' (en); '' when unknown."""
    n = _int(v)
    if n is None:
        return ""
    return f"%{n}" if lang == "tr" else f"{n}%"


def grams(v: Any) -> str:
    n = _num(v)
    if n is None:
        return ""
    return f"{n:.1f} g" if n < 10 else f"{int(round(n))} g"


def duration(minutes: Any, lang: str, short: bool = False) -> str:
    """135 -> '2 saat 15 dakika' / '2 sa 15 dk' (tr), '2 hours 15 minutes' / '2 h 15 min' (en)."""
    m = _int(minutes)
    if m is None or m <= 0:
        return ""
    h, mm = divmod(m, 60)
    if lang == "tr":
        hu, mu = ("sa", "dk") if short else ("saat", "dakika")
        parts = [f"{h} {hu}"] if h else []
        if mm or not h:
            parts.append(f"{mm} {mu}")
        return " ".join(parts)
    if short:
        hu, mu = "h", "min"
    else:
        hu, mu = ("hour" if h == 1 else "hours"), ("minute" if mm == 1 else "minutes")
    parts = [f"{h} {hu}"] if h else []
    if mm or not h:
        parts.append(f"{mm} {mu}")
    return " ".join(parts)


def dative(name: str) -> str:
    """Turkish dative with apostrophe: Sam'a, Mehmet'e, Ali Baba'ya, Anne'ye."""
    name = _s(name)
    if not name:
        return ""
    low = name.translate(_TR_LOWER).lower()
    vowels = [c for c in low if c in _TR_BACK or c in _TR_FRONT]
    back = bool(vowels) and vowels[-1] in _TR_BACK
    buffer = "y" if low[-1] in _TR_BACK or low[-1] in _TR_FRONT else ""
    return f"{name}'{buffer}{'a' if back else 'e'}"


def short_text(text: Any, limit: int = FAMILY_JOB_MAX) -> str:
    """One line of at most ``limit`` characters, cut at a word boundary with "…" ("" for nothing)."""
    t = re.sub(r"\s+", " ", _s(text)).strip().strip("\"'“”‘’«»").strip()
    if len(t) <= limit:
        return t
    cut = t[: limit - 1]
    if " " in cut and cut.rfind(" ") >= limit // 2:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:-") + "…"


def _quote(job: Any, lang: str = "") -> str:
    """'"Rose box"'; without a name: "baskı" / "the print" (lang given) or ""."""
    j = _s(job)
    if j:
        return f'"{j}"'
    return {"tr": "baskı", "en": "the print"}.get(lang, "")


def _cap(text: str) -> str:
    """Upper-case the first letter after a leading emoji/space ("✅ baskı bitti" -> "✅ Baskı bitti")."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
        if ch in "\"'":
            return text
    return text


def _who(ctx: dict) -> str:
    return _s(ctx.get("address_as")) or _s(ctx.get("requester"))


def _fjob(ctx: dict, tr: bool) -> str:
    """The print as the family knows it: what they asked for, else the pretty file name, else "the print"."""
    return _quote(short_text(ctx.get("family_job")) or ctx.get("job"), "tr" if tr else "en")


def _owner_told(ctx: dict, lang: str) -> str:
    owner = _s(ctx.get("owner"))
    if lang == "tr":
        if not owner or owner.lower() == "owner":
            return "Yazıcının sahibine haber verdim."
        return f"{dative(owner)} haber verdim."
    return f"I've told {owner}." if owner and owner.lower() != "owner" else "I've told the owner."


def _lines(*parts: str) -> str:
    return "\n".join(p for p in parts if p)


def _join(parts: list[str], sep: str = " · ") -> str:
    return sep.join(p for p in parts if p)


def _layer(ctx: dict, lang: str) -> str:
    layer, total = _int(ctx.get("layer")), _int(ctx.get("total_layers"))
    if layer is None:
        return ""
    word = "katman" if lang == "tr" else "layer"
    return f"{word} {layer}/{total}" if total else f"{word} {layer}"


def _temps(ctx: dict, lang: str) -> str:
    bed, nozzle = _num(ctx.get("bed_temp")), _num(ctx.get("nozzle_temp"))
    out = []
    if bed is not None:
        out.append(f"{'tabla' if lang == 'tr' else 'bed'} {bed:.0f} °C")
    if nozzle is not None:
        out.append(f"{'nozul' if lang == 'tr' else 'nozzle'} {nozzle:.0f} °C")
    return ", ".join(out)


def _job_ref(ctx: dict) -> str:
    q, qid = _quote(ctx.get("job")), _s(ctx.get("queue_item_id"))
    return f"{q} (#{qid})" if q and qid else q or (f"#{qid}" if qid else "")


def _for(ctx: dict, lang: str) -> str:
    r = _s(ctx.get("requester"))
    if not r:
        return ""
    return f"isteyen: {r}" if lang == "tr" else f"for {r}"


def _hms_line(ctx: dict, lang: str) -> str:
    code = _s(ctx.get("hms_code"))
    if not code:
        return ""
    msg, wiki = _s(ctx.get("hms_message")), _s(ctx.get("wiki_url"))
    return _join([f"HMS {code}" + (f": {msg}" if msg else ""), wiki], " ")


def _diff(ctx: dict, lang: str) -> str:
    d = _num(ctx.get("plate_diff"))
    if d is None:
        return ""
    return f"fark %{d:g}" if lang == "tr" else f"diff {d:g}%"


# English reasons produced by eject.step / gates -> Turkish (owner text); unknown reasons pass through.
_REASONS_TR = (
    (re.compile(r"part still on the plate after (\d+) checks?"), "{0} kontrolden sonra parça hâlâ tablada"),
    (re.compile(r"plate check inconclusive after (\d+) checks?"), "{0} kontrolde de kamera emin olamadı"),
    (re.compile(r"bed did not cool below ([\d.]+) ?C"), "tabla {0} °C altına soğumadı"),
    (re.compile(r"the plate could not be verified after the eject"), "düşürmeden sonra tabla doğrulanamadı"),
    (re.compile(r"no auto-eject planned.*"), "otomatik düşürme planlanmamıştı"),
    (re.compile(r"print failed.*"), "baskı başarısız oldu"),
    (re.compile(r"print ended without finishing.*"), "baskı bitmeden sona erdi"),
)


def reason_text(reason: Any, lang: str) -> str:
    r = _s(reason)
    if lang != "tr" or not r:
        return r
    for rx, tpl in _REASONS_TR:
        m = rx.fullmatch(r)
        if m:
            return tpl.format(*m.groups())
    return r


def _state_word(state: Any, tr: bool) -> str:
    st = _s(state).upper()
    return _STATE_WORDS.get(st, (st.lower(), st.lower()))[1 if tr else 0] if st else ""


def _link(ctx: dict) -> str:
    return _s(ctx.get("preview_url"))


# ---- family templates -------------------------------------------------------------------------
def _f_started(c: dict, tr: bool) -> str:
    who, job, dur = _who(c), _fjob(c, tr), duration(c.get("duration_min"), "tr" if tr else "en")
    if tr:
        head = f"🖨️ {who}, {job} basılmaya başladı" if who else f"🖨️ {job} basılmaya başladı"
        first = head + (f", yaklaşık {dur} sürecek." if dur else ".")
        second = "Bitince tabla soğuyacak, yazıcı parçayı kendisi düşürecek." if c.get("eject_planned") else ""
        return _lines(first, second)
    head = f"🖨️ {who}, {job} has started printing" if who else f"🖨️ {job} has started printing"
    first = head + (f", about {dur} to go." if dur else ".")
    second = "When it's done the bed cools and the printer pushes it off by itself." if c.get("eject_planned") else ""
    return _lines(first, second)


def _f_finished(c: dict, tr: bool) -> str:
    who, job = _who(c), _fjob(c, tr)
    if c.get("missed_end"):  # the watcher did not see the end: say nothing about where the part is
        if tr:
            return f"✅ {who}, {job} bitti." if who else f"✅ {job} bitti."
        return f"✅ {who}, {job} is done." if who else f"✅ {job} is done."
    if tr:
        return (f"✅ {who}, {job} bitti, yazıcıda seni bekliyor." if who
                else f"✅ {job} bitti, yazıcıda bekliyor.")
    return f"✅ {who}, {job} is done and waiting on the printer." if who else f"✅ {job} is done and waiting on the printer."


def _f_finished_ejected(c: dict, tr: bool) -> str:
    who, job = _who(c), _fjob(c, tr)
    if tr:
        return (f"✅ {who}, {job} bitti. Otomatik düşürüldü, kutudan alabilirsin." if who
                else f"✅ {job} bitti. Otomatik düşürüldü, kutudan alabilirsiniz.")
    return (f"✅ {who}, {job} is done. It dropped off by itself, you can take it from the box." if who
            else f"✅ {job} is done. It dropped off by itself, you can take it from the box.")


def _f_plate_not_clear(c: dict, tr: bool) -> str:
    who, job = _who(c), _fjob(c, tr)
    if tr:
        return (f"🙏 {who}, {job} bitti ama tablada kaldı, kendi düşmedi. Müsait olunca alabilir misin?" if who
                else f"🙏 {job} bitti ama tablada kaldı, kendi düşmedi. Biri alabilir mi?")
    return (f"🙏 {who}, {job} is done but stayed on the plate. Could you take it off when you have a moment?" if who
            else f"🙏 {job} is done but stayed on the plate. Could someone take it off?")


def _f_eject_unverified(c: dict, tr: bool) -> str:
    job = _fjob(c, tr)
    if tr:
        return f"🙏 {job} bitti ama tablanın boş olduğundan emin olamadım. Biri bir bakabilir mi?"
    return f"🙏 {job} is done, but I couldn't tell whether the plate is empty. Could someone take a look?"


def _f_failed(c: dict, tr: bool) -> str:
    who, job, p = _who(c), _fjob(c, tr), pct(c.get("progress"), "tr" if tr else "en")
    told = _owner_told(c, "tr" if tr else "en")
    if tr:
        head = f"⚠️ {who}, yazıcı durdu" if who else "⚠️ Yazıcı durdu"
        return f"{head}, {job} yarıda kaldı" + (f" ({p})" if p else "") + f". {told}"
    head = f"⚠️ {who}, the printer stopped" if who else "⚠️ The printer stopped"
    return f"{head}, {job} didn't finish" + (f" ({p})" if p else "") + f". {told}"


def _f_paused(c: dict, tr: bool) -> str:
    who, job, p = _who(c), _fjob(c, tr), pct(c.get("progress"), "tr" if tr else "en")
    told = _owner_told(c, "tr" if tr else "en")
    head = f"⏸️ {who}, " if who else "⏸️ "
    if tr:
        why = ", filament bitti" if c.get("filament") else ""
        return f"{head}{job} baskısı durakladı" + (f" ({p})" if p else "") + f"{why}. {told}"
    why = ", the filament ran out" if c.get("filament") else ""
    return f"{head}{job} is paused" + (f" ({p})" if p else "") + f"{why}. {told}"


def _f_eject_skipped(c: dict, tr: bool) -> str:
    job = _fjob(c, tr)
    if tr:
        return f"ℹ️ {job} kendi düşmeyecek, bitince yazıcıdan alınması gerekecek."
    return f"ℹ️ {job} won't drop off by itself, someone will need to take it off when it's done."


# ---- owner templates --------------------------------------------------------------------------
def _o_started(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    eject = c.get("eject_planned")
    ej = ("otomatik düşürme: " if tr else "auto-eject: ") + (("açık" if tr else "on") if eject else ("kapalı" if tr else "off"))
    if not eject and _s(c.get("reason")):
        ej += f" ({reason_text(c.get('reason'), lang)})"
    head = ("▶️ Başladı: " if tr else "▶️ Started: ") + _job_ref(c)
    return _lines(_join([head, duration(c.get("duration_min"), lang, short=True), grams(c.get("grams")), ej,
                         _for(c, lang)]), _link(c))


def _missed(c: dict, tr: bool) -> str:
    """The watcher did not see the print end (``missed_end``): what that means for the plate."""
    how = _s(c.get("missed_end"))
    if how == "busy":
        return ("Bitişini kaçırdım: yazıcı hemen başka bir işe geçti, tablayı kontrol edemedim." if tr
                else "I missed its end: the printer went straight on to another job, so I could not check the plate.")
    if how:
        return ("Bitişini kaçırdım (yazıcı şimdi boşta); tablayı kamerayla kontrol edeceğim." if tr
                else "I missed its end (the printer is idle again); I'll check the plate with the camera.")
    return ""


def _o_finished(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("✅ Bitti: " if tr else "✅ Finished: ") + _job_ref(c)
    first = _join([head, _layer(c, lang), duration(c.get("duration_min"), lang, short=True), grams(c.get("grams")),
                   _temps(c, lang), _for(c, lang)])
    if c.get("missed_end"):
        return _lines(first, _missed(c, tr))
    unknown = _s(c.get("eject_unknown"))
    if unknown:  # not queued through the workshop: nobody here knows whether it was sliced with auto-eject
        camera = _camera_empty(c, tr)
        camera = camera[:1].lower() + camera[1:]
        if tr:
            why = "Atölye üzerinden eklenmedi" if unknown == "foreign" else "Bu baskının düşürme planı bilinmiyor"
            second = (f"{why}; {camera}." if c.get("camera_empty")
                      else f"{why}: parça hâlâ tablada ise alınmalı, sonra /home3d approve clear.")
        else:
            why = "Not queued through the workshop" if unknown == "foreign" else "No eject plan known for this print"
            second = (f"{why}; {camera}." if c.get("camera_empty")
                      else f"{why}: take the part off if it is still there, then /home3d approve clear.")
        return _lines(first, second)
    if c.get("eject_planned") and c.get("eject_result_follows"):
        return first  # the camera result is the next paragraph of the same message
    if c.get("eject_planned") and c.get("eject_in_gcode"):
        second = ("Baskının sonunda itildi; kamerayla kontrol ediyorum." if tr
                  else "Pushed off at the end of the print; checking the camera.")
        return _lines(first, second)
    if c.get("eject_planned"):
        second = ("Otomatik düşürme bekleniyor: tabla soğuyunca itilecek, sonra kamerayla kontrol edeceğim." if tr
                  else "Auto-eject pending: the part is pushed off once the bed cools, then I check the camera.")
    else:
        second = ("Otomatik düşürme yok: parça elle alınmalı, sonra /home3d approve clear." if tr
                  else "No auto-eject: take the part off, then /home3d approve clear.")
    return _lines(first, second)


def _o_finished_ejected(c: dict, tr: bool) -> str:
    d = _diff(c, "tr" if tr else "en")
    if tr:
        return f"✅ {_job_ref(c)} otomatik düşürüldü, kameraya göre tabla boş" + (f" ({d})" if d else "") + "."
    return f"✅ {_job_ref(c)} was pushed off; the camera thinks the plate is empty" + (f" ({d})" if d else "") + "."


def _o_plate_not_clear(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    detail = ", ".join(x for x in (reason_text(c.get("reason"), lang), _diff(c, lang)) if x)
    if tr:
        return (f"⚠️ {_job_ref(c)}: tabla boş değil" + (f" ({detail})" if detail else "")
                + ". Parça elle alınmalı, sonra /home3d approve clear.")
    return (f"⚠️ {_job_ref(c)}: the plate is not empty" + (f" ({detail})" if detail else "")
            + ". Take the part off, then /home3d approve clear.")


def _o_eject_unverified(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    detail = ", ".join(x for x in (reason_text(c.get("reason"), lang), _diff(c, lang)) if x)
    if tr:
        return (f"❓ {_job_ref(c)}: otomatik düşürme doğrulanamadı" + (f" ({detail})" if detail else "")
                + ". Kameraya bakıp tablayı kontrol et; boşsa /home3d approve clear.")
    return (f"❓ {_job_ref(c)}: auto-eject could not be verified" + (f" ({detail})" if detail else "")
            + ". Check the plate on the camera; if it is empty, /home3d approve clear.")


def _camera_empty(c: dict, tr: bool) -> str:
    """"the camera thinks the plate is empty (diff 1.8%)": the camera's opinion, never "verified"."""
    d = _diff(c, "tr" if tr else "en")
    if tr:
        return "Kameraya göre tabla boş" + (f" ({d})" if d else "")
    return "The camera thinks the plate is empty" + (f" ({d})" if d else "")


def _confirm_first(c: dict, tr: bool) -> str:
    if not c.get("confirm_first"):
        return ""
    if tr:
        return "Son baskı yarıda kaldı: sıradaki işten önce tablaya bakıp /home3d approve clear ile onayla."
    return "The last print failed: look at the plate and confirm it with /home3d approve clear before the next start."


def _photo_hint(c: dict, tr: bool) -> str:
    if not c.get("photo"):
        return ""
    return "Fotoğrafa bak, kamera ince parçaları kaçırabilir." if tr else "Check the photo: the camera can miss thin parts."


def _o_plate_clear(c: dict, tr: bool) -> str:
    job = _job_ref(c)
    if tr:
        first = "✅ " + _camera_empty(c, tr) + (f", {job} alınmış görünüyor." if job else ".")
    else:
        first = "✅ " + _camera_empty(c, tr) + (f"; {job} looks taken off." if job else ".")
    return _lines(first, _confirm_first(c, tr), _photo_hint(c, tr))


def _o_failed(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("❌ Baskı başarısız: " if tr else "❌ Print failed: ") + _job_ref(c)
    first = _join([head, pct(c.get("progress"), lang), _layer(c, lang), _for(c, lang), _temps(c, lang)])
    tail = ("Tabla ve nozul kontrol edilmeli, temizlenince /home3d approve clear." if tr
            else "Check the plate and nozzle; once clean, /home3d approve clear.")
    return _lines(first, _hms_line(c, lang), _missed(c, tr) if _s(c.get("missed_end")) == "busy" else "", tail)


def _o_stopped(c: dict, tr: bool) -> str:
    """A person stopped the print (home3d_stop): not a failure, but the plate still needs a look."""
    lang = "tr" if tr else "en"
    head = ("⏹️ Durduruldu: " if tr else "⏹️ Stopped: ") + _job_ref(c)
    first = _join([head, pct(c.get("progress"), lang), _layer(c, lang), _for(c, lang)])
    who, why = _s(c.get("stopped_by")), _s(c.get("stop_reason"))
    if tr:
        by = (f"{who} durdurdu" if who else "Biri durdurdu") + (f": {why}" if why else "") + "."
        tail = "Arıza değil. Tablada yarım parça kalmış olabilir: temizleyip /home3d approve clear."
    else:
        by = (f"Stopped by {who}" if who else "Stopped on request") + (f": {why}" if why else "") + "."
        tail = "Not a failure. A half-printed part may be on the plate: clear it, then /home3d approve clear."
    return _lines(first, f"{by} {tail}")


def _o_online(c: dict, tr: bool) -> str:
    """The printer manager answers again after the owner was told it is unreachable."""
    lang = "tr" if tr else "en"
    mins = _int(c.get("offline_min"))
    state = _state_word(c.get("state"), tr)
    job = _quote(c.get("job")) if _s(c.get("state")).upper() not in ("", "IDLE") else ""
    now = _join([state, job, pct(c.get("progress"), lang)], " ")
    if tr:
        return ("📶 Yazıcıya yeniden ulaşılıyor" + (f" ({mins} dakika sonra)" if mins else "")
                + (f": {now}." if now else "."))
    return "📶 Printer reachable again" + (f" after {mins} min" if mins else "") + (f": {now}." if now else ".")


def _o_paused(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("⏸️ Duraklatıldı: " if tr else "⏸️ Paused: ") + _job_ref(c)
    first = _join([head, pct(c.get("progress"), lang), _layer(c, lang), _for(c, lang)])
    hms = _hms_line(c, lang)
    if hms:
        ack = (" (HMS hâlâ etkinse: /home3d approve resume ack)" if tr
               else " (if the HMS is still active: /home3d approve resume ack)")
        tail = ("Filamenti değiştirince: /home3d approve resume" if c.get("filament") and tr else
                "Swap the filament, then: /home3d approve resume" if c.get("filament") else
                "Hata giderilince: /home3d approve resume" if tr else
                "Once it is fixed: /home3d approve resume") + ack + "."
    else:
        tail = ("HMS yok: biri yazıcıdan ya da uygulamadan duraklatmış olabilir. Devam ettirmedim; "
                "devam için: /home3d approve resume." if tr
                else "No HMS: someone may have paused it on the printer or in the app. I did not resume it; "
                     "to resume: /home3d approve resume.")
    return _lines(first, hms, tail)


def _o_hms(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    where = ", ".join(x for x in (_job_ref(c), pct(c.get("progress"), lang)) if x)
    return "⚠️ " + (_hms_line(c, lang) or "HMS") + (f" ({where})" if where else "")


def _o_offline(c: dict, tr: bool) -> str:
    mins, reason = _int(c.get("offline_min")), _s(c.get("reason"))
    if tr:
        return ("📴 Yazıcıya " + (f"{mins} dakikadır " if mins else "") + "ulaşılamıyor"
                + (f" ({reason})" if reason else "") + ".")
    return ("📴 Printer unreachable" + (f" for {mins} min" if mins else "") + (f" ({reason})" if reason else "") + ".")


def _refs(items: Any, lang: str, with_since: bool = False) -> str:
    """'"Soap dish" (#73), "Hook" (#74)' for a list of {"id", "name"[, "since"]} (or plain strings)."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            if _s(it):
                out.append(_s(it))
            continue
        name, qid, since = _quote(it.get("name")), _s(it.get("id")), _s(it.get("since"))
        who = _s(it.get("who"))  # another household member's workshop job
        extra = ", ".join(x for x in (f"#{qid}" if qid else "",
                                      (f"isteyen: {who}" if lang == "tr" else f"for {who}") if who else "",
                                      (f"eklenme {since}" if lang == "tr" else f"added {since}")
                                      if with_since and since else "") if x)
        out.append(_join([name, f"({extra})" if extra else ""], " ") or f"#{qid}")
    return ", ".join(x for x in out if x)


def _o_ready_next(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    nid, name = _s(c.get("next_id")), _quote(c.get("next_job"))
    ref = f"{name} (#{nid})" if name and nid else name or f"#{nid}"
    ahead = _refs(c.get("ahead"), lang)
    cmd = f"/home3d approve start {nid}" + (" jump" if ahead else "") if nid else ""
    asked = _s(c.get("asked_by"))
    camera = "" if c.get("camera_said") else f"{_camera_empty(c, tr)}. "  # said earlier in the same message
    if tr:
        first = _join([f"▶️ {camera}Sıradaki atölye işi hazır: {ref}", _for(c, lang)])
        foreign = (f"Önünde atölyeden eklenmemiş iş var: {ahead}. Onları ben başlatmam; bizimkini öne almak için "
                   "komutun sonunda jump var." if ahead else "")
        asked_line = f"🙋 {asked} başlatılmasını istedi." if asked else ""
        start = (("Fotoğrafa bakıp başlatmak için: " if c.get("photo") else "Başlatmak için: ") + cmd) if cmd else ""
        clear_first = ("Bambuddy tablanın boş işaretlenmesini bekliyor: önce /home3d approve clear"
                       if c.get("awaiting_clear") and not (c.get("confirm_first") or c.get("confirm_said")) else "")
    else:
        first = _join([f"▶️ {camera}Next workshop job ready: {ref}", _for(c, lang)])
        foreign = (f"Ahead of it, not queued through the workshop: {ahead}. I never start those; the command below "
                   "jumps ahead of them." if ahead else "")
        asked_line = f"🙋 {asked} asked to start it." if asked else ""
        start = (("Check the photo, then start it: " if c.get("photo") else "To start it: ") + cmd) if cmd else ""
        clear_first = ("Bambuddy waits for the plate to be marked clear: first /home3d approve clear"
                       if c.get("awaiting_clear") and not (c.get("confirm_first") or c.get("confirm_said")) else "")
    return _lines(first, foreign, _confirm_first(c, tr), asked_line, clear_first, start)


def _o_queue_foreign(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    refs = _refs(c.get("foreign"), lang, with_since=True)
    if not refs:
        return ""
    if tr:
        return (f"ℹ️ Kuyrukta atölye üzerinden eklenmemiş iş bekliyor: {refs}. Ben başlatmam ve önermem; "
                "gerekiyorsa Bambuddy'den başlat ya da kaldır.")
    return (f"ℹ️ Waiting in the queue, not added through the workshop: {refs}. I won't start or suggest it; start or "
            "remove it in Bambuddy if needed.")


def _o_upgrade_proposed(c: dict, tr: bool) -> str:
    uid, title = _s(c.get("upgrade_id")), _s(c.get("upgrade_title"))
    n, days, label = _int(c.get("evidence")), _int(c.get("window_days")), _s(c.get("upgrade_label"))
    persona = _s(c.get("persona"))
    ref = f"#{uid} " if uid else ""
    if tr:
        first = f"💡 Yükseltme önerisi {ref}" + (f"({persona})" if persona else "") + f": {title}"
        why = (f"Son {days} günde {n} kez biri elle müdahale etti" if n and days else
               f"{n} kez biri elle müdahale etti" if n else "") + (f" ({label})." if label and n else "." if n else "")
        act = (f"Kabul için {dative(persona) if persona else 'bana'} yaz: \"{uid} numaralı öneriyi kabul et\""
               if uid else "")
    else:
        first = f"💡 Upgrade proposal {ref}" + (f"({persona})" if persona else "") + f": {title}"
        why = (f"A person had to step in {n} times in {days} days" if n and days else
               f"A person had to step in {n} times" if n else "") + (f" ({label})." if label and n else "." if n else "")
        act = f"To accept, tell {persona or 'me'}: \"accept upgrade {uid}\"" if uid else ""
    return _lines(first.replace(" :", ":"), _join([why, _s(c.get("model_ref"))], " "), act)


def _o_eject_skipped(c: dict, tr: bool) -> str:
    reason = reason_text(c.get("reason"), "tr" if tr else "en")
    if tr:
        return f"ℹ️ {_job_ref(c)} için otomatik düşürme kapalı" + (f": {reason}" if reason else "") + ". Bitince parça elle alınmalı."
    return f"ℹ️ Auto-eject is off for {_job_ref(c)}" + (f": {reason}" if reason else "") + ". The part must be taken off by hand."


def _o_light_left_on(c: dict, tr: bool) -> str:
    """The chamber light was switched on for a camera check and could not be switched off again."""
    if tr:
        return ("💡 Kamera kontrolü için açtığım hazne ışığı kapanmadı, hâlâ açık. İstersen yazıcıdan ya da Bambu "
                "Handy'den kapat.")
    return ("💡 I switched the chamber light on for a camera check and could not switch it off again: it is still "
            "on. Switch it off on the printer or in Bambu Handy if you want.")


def _o_approval_request(c: dict, tr: bool) -> str:
    """A household member asked for something only the owner may approve (the hook refused it): one owner text
    with the exact command. It never says the start will happen."""
    lang = "tr" if tr else "en"
    who = _s(c.get("who")) or _s(c.get("requester")) or ("Biri" if tr else "Someone")
    action = _s(c.get("action")) or "start"
    qid, job = _s(c.get("queue_item_id")), _quote(c.get("job"))
    if action == "resume" and _s(c.get("not_paused")):
        state = _state_word(c.get("not_paused"), tr)
        if tr:
            return (f"🙋 {who} baskının devam etmesini istedi, ama şu an duraklatılmış bir baskı yok ({state}). "
                    "Yapılacak bir şey yok.")
        return (f"🙋 {who} asked to resume the print, but nothing is paused now ({state}). Nothing to do.")
    if action == "resume":
        if tr:
            return (f"🙋 {who} duraklatılan baskının" + (f" ({job})" if job else "") + " devam etmesini istiyor. "
                    "Devam ettirmek için: /home3d approve resume")
        return (f"🙋 {who} asks to resume the paused print" + (f" {job}" if job else "") + ". "
                "To resume it: /home3d approve resume")
    if action in ("clear", "clear_plate", "confirm_clear"):
        if tr:
            return (f"🙋 {who} tablanın boş olduğunu söylüyor ve onaylamanı istiyor. Önce tablaya ya da kameraya bak; "
                    "onaylamak için: /home3d approve clear")
        return (f"🙋 {who} says the plate is clear and asks you to confirm it. Look at the plate or the camera first; "
                "to confirm: /home3d approve clear")
    ref = _join([f"#{qid}" if qid else "", job], " ")
    extra = ", ".join(x for x in (duration(c.get("duration_min"), lang, short=True), grams(c.get("grams"))) if x)
    ahead = _refs(c.get("ahead"), lang)
    cmd = f"/home3d approve start {qid}" + (" jump" if ahead else "") if qid else ""
    if tr:
        first = (f"🙋 {who} {ref} işinin başlatılmasını istiyor" if ref else f"🙋 {who} bir baskının başlatılmasını "
                 "istiyor") + (f" ({extra})" if extra else "") + "."
        ahead_line = (f"Önünde başkasının işi var: {ahead}; komutun sonundaki jump onları atlar." if ahead else "")
        return _lines(first, ahead_line, f"Başlatmak için: {cmd}" if cmd else "")
    first = (f"🙋 {who} asks to start {ref}" if ref else f"🙋 {who} asks to start a print") + \
        (f" ({extra})" if extra else "") + "."
    ahead_line = f"Ahead of it, someone else's: {ahead}; jump goes ahead of them." if ahead else ""
    return _lines(first, ahead_line, f"To start it: {cmd}" if cmd else "")


def _o_start_failed(c: dict, tr: bool) -> str:
    """The printer manager gave up on a start (queue item failed, never started): nothing is printing."""
    lang = "tr" if tr else "en"
    err = short_text(c.get("error"), ERROR_MAX)
    head = _join([("⚠️ Başlatma gerçekleşmedi: " if tr else "⚠️ The start did not happen: ") + _job_ref(c),
                  _for(c, lang)])
    tail = ("Hiçbir şey basılmıyor. Sorunu giderip işi yeniden sıraya ekle." if tr
            else "Nothing is printing. Fix the cause, then queue it again.")
    return _lines(head, f"Bambuddy: {err}" if err else "", tail)


_FAMILY: dict[str, Callable[[dict, bool], str]] = {
    "started": _f_started, "finished": _f_finished, "finished_ejected": _f_finished_ejected,
    "plate_not_clear": _f_plate_not_clear, "eject_unverified": _f_eject_unverified, "failed": _f_failed,
    "paused": _f_paused, "eject_skipped": _f_eject_skipped,
}
_OWNER: dict[str, Callable[[dict, bool], str]] = {
    "started": _o_started, "finished": _o_finished, "finished_ejected": _o_finished_ejected,
    "plate_not_clear": _o_plate_not_clear, "eject_unverified": _o_eject_unverified, "plate_clear": _o_plate_clear,
    "failed": _o_failed, "paused": _o_paused, "hms": _o_hms, "offline": _o_offline, "ready_next": _o_ready_next,
    "queue_foreign": _o_queue_foreign, "upgrade_proposed": _o_upgrade_proposed, "eject_skipped": _o_eject_skipped,
    "light_left_on": _o_light_left_on, "approval_request": _o_approval_request, "start_failed": _o_start_failed,
    "stopped": _o_stopped, "online": _o_online,
}


def render(kind: str, audience: str, lang: str, **ctx: Any) -> str:
    """Message text for ``kind`` and ``audience`` ("owner" | "family"); "" = nothing to send."""
    tr = lang == "tr"
    if audience == "family":
        fn = _FAMILY.get(kind)
        if fn is None:
            return ""
        return "\n".join(_cap(line) for line in fn(ctx, tr).strip().splitlines())
    fn = _OWNER.get(kind)
    if fn is None:
        job = _job_ref(ctx)
        return f"ℹ️ {kind}" + (f": {job}" if job else "")
    return fn(ctx, tr).strip()
