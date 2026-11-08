"""Owner vs family message templates (tr / en). Pure, stdlib only.

``render(kind, audience, lang, **ctx)`` returns the text, or ``""`` when that audience should not get a
message for this kind (offline, HMS, ready-next and upgrade notices are owner-only).

Family: one or two short warm lines, plain words, addressed to the requester (``address_as`` or
``requester``) when known, never English words inside Turkish. Owner: technical (state, layer, temps,
HMS, links) but still short.

ctx keys (all optional): persona, owner (owner display name), job, queue_item_id, requester, address_as,
progress, layer, total_layers, duration_min, grams, bed_temp, nozzle_temp, hms_code, hms_message,
wiki_url, filament (bool: the pause is a filament run-out), reason, eject_planned (bool), plate_diff,
next_job, next_id, upgrade_title, upgrade_id, upgrade_label, evidence, window_days, model_ref,
preview_url, offline_min.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

KINDS = ("started", "finished", "finished_ejected", "plate_not_clear", "eject_unverified", "plate_clear",
         "failed", "paused", "hms", "offline", "ready_next", "upgrade_proposed", "eject_skipped")
OWNER_ONLY = frozenset({"hms", "offline", "ready_next", "upgrade_proposed", "plate_clear"})
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


def _link(ctx: dict) -> str:
    return _s(ctx.get("preview_url"))


# ---- family templates -------------------------------------------------------------------------
def _f_started(c: dict, tr: bool) -> str:
    who, job, dur = _who(c), _quote(c.get("job"), "tr" if tr else "en"), duration(c.get("duration_min"), "tr" if tr else "en")
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
    who, job = _who(c), _quote(c.get("job"), "tr" if tr else "en")
    if tr:
        return (f"✅ {who}, {job} bitti, yazıcıda seni bekliyor." if who
                else f"✅ {job} bitti, yazıcıda bekliyor.")
    return f"✅ {who}, {job} is done and waiting on the printer." if who else f"✅ {job} is done and waiting on the printer."


def _f_finished_ejected(c: dict, tr: bool) -> str:
    who, job = _who(c), _quote(c.get("job"), "tr" if tr else "en")
    if tr:
        return (f"✅ {who}, {job} bitti. Otomatik düşürüldü, kutudan alabilirsin." if who
                else f"✅ {job} bitti. Otomatik düşürüldü, kutudan alabilirsiniz.")
    return (f"✅ {who}, {job} is done. It dropped off by itself, you can take it from the box." if who
            else f"✅ {job} is done. It dropped off by itself, you can take it from the box.")


def _f_plate_not_clear(c: dict, tr: bool) -> str:
    who, job = _who(c), _quote(c.get("job"), "tr" if tr else "en")
    if tr:
        return (f"🙏 {who}, {job} bitti ama tablada kaldı, kendi düşmedi. Müsait olunca alabilir misin?" if who
                else f"🙏 {job} bitti ama tablada kaldı, kendi düşmedi. Biri alabilir mi?")
    return (f"🙏 {who}, {job} is done but stayed on the plate. Could you take it off when you have a moment?" if who
            else f"🙏 {job} is done but stayed on the plate. Could someone take it off?")


def _f_eject_unverified(c: dict, tr: bool) -> str:
    job = _quote(c.get("job"), "tr" if tr else "en")
    if tr:
        return f"🙏 {job} bitti ama tablanın boş olduğundan emin olamadım. Biri bir bakabilir mi?"
    return f"🙏 {job} is done, but I couldn't tell whether the plate is empty. Could someone take a look?"


def _f_failed(c: dict, tr: bool) -> str:
    who, job, p = _who(c), _quote(c.get("job"), "tr" if tr else "en"), pct(c.get("progress"), "tr" if tr else "en")
    told = _owner_told(c, "tr" if tr else "en")
    if tr:
        head = f"⚠️ {who}, yazıcı durdu" if who else "⚠️ Yazıcı durdu"
        return f"{head}, {job} yarıda kaldı" + (f" ({p})" if p else "") + f". {told}"
    head = f"⚠️ {who}, the printer stopped" if who else "⚠️ The printer stopped"
    return f"{head}, {job} didn't finish" + (f" ({p})" if p else "") + f". {told}"


def _f_paused(c: dict, tr: bool) -> str:
    job, p = _quote(c.get("job"), "tr" if tr else "en"), pct(c.get("progress"), "tr" if tr else "en")
    told = _owner_told(c, "tr" if tr else "en")
    if tr:
        why = ", filament bitti" if c.get("filament") else ""
        return f"⏸️ {job} baskısı durakladı" + (f" ({p})" if p else "") + f"{why}. {told}"
    why = ", the filament ran out" if c.get("filament") else ""
    return f"⏸️ {job} is paused" + (f" ({p})" if p else "") + f"{why}. {told}"


def _f_eject_skipped(c: dict, tr: bool) -> str:
    job = _quote(c.get("job"), "tr" if tr else "en")
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


def _o_finished(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("✅ Bitti: " if tr else "✅ Finished: ") + _job_ref(c)
    first = _join([head, _layer(c, lang), duration(c.get("duration_min"), lang, short=True), grams(c.get("grams")),
                   _temps(c, lang), _for(c, lang)])
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
        return f"✅ {_job_ref(c)} otomatik düşürüldü, kamera tablayı boş görüyor" + (f" ({d})" if d else "") + "."
    return f"✅ {_job_ref(c)} was pushed off; the camera sees an empty plate" + (f" ({d})" if d else "") + "."


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
                + ". Kameraya bakıp tablayı kontrol et.")
    return (f"❓ {_job_ref(c)}: auto-eject could not be verified" + (f" ({detail})" if detail else "")
            + ". Check the plate on the camera.")


def _o_plate_clear(c: dict, tr: bool) -> str:
    d = _diff(c, "tr" if tr else "en")
    job = _job_ref(c)
    if tr:
        return "✅ Tabla boş görünüyor" + (f" ({d})" if d else "") + (f", {job} alınmış." if job else ".")
    return "✅ The plate looks empty" + (f" ({d})" if d else "") + (f", {job} was taken off." if job else ".")


def _o_failed(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("❌ Baskı başarısız: " if tr else "❌ Print failed: ") + _job_ref(c)
    first = _join([head, pct(c.get("progress"), lang), _layer(c, lang), _for(c, lang), _temps(c, lang)])
    tail = ("Tabla ve nozul kontrol edilmeli, temizlenince /home3d approve clear." if tr
            else "Check the plate and nozzle; once clean, /home3d approve clear.")
    return _lines(first, _hms_line(c, lang), tail)


def _o_paused(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    head = ("⏸️ Duraklatıldı: " if tr else "⏸️ Paused: ") + _job_ref(c)
    first = _join([head, pct(c.get("progress"), lang), _layer(c, lang), _for(c, lang)])
    hms = _hms_line(c, lang)
    if hms:
        tail = ("Filament değişince devam için home3d_stop resume." if c.get("filament") and tr else
                "Swap the filament, then home3d_stop resume." if c.get("filament") else
                "Hata giderilince devam için home3d_stop resume." if tr else
                "Resume with home3d_stop resume once it is fixed.")
    else:
        tail = ("HMS yok: biri yazıcıdan ya da uygulamadan duraklatmış olabilir. Devam ettirmedim." if tr
                else "No HMS: someone may have paused it on the printer or in the app. I did not resume it.")
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


def _o_ready_next(c: dict, tr: bool) -> str:
    lang = "tr" if tr else "en"
    nid, name = _s(c.get("next_id")), _quote(c.get("next_job"))
    ref = f"{name} (#{nid})" if name and nid else name or f"#{nid}"
    if tr:
        first = _join([f"▶️ Tabla boş, sıradaki iş hazır: {ref}", _for(c, lang)])
        return _lines(first, f"Başlatmak için: /home3d approve start {nid}" if nid else "")
    first = _join([f"▶️ Plate clear, next job ready: {ref}", _for(c, lang)])
    return _lines(first, f"To start it: /home3d approve start {nid}" if nid else "")


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


_FAMILY: dict[str, Callable[[dict, bool], str]] = {
    "started": _f_started, "finished": _f_finished, "finished_ejected": _f_finished_ejected,
    "plate_not_clear": _f_plate_not_clear, "eject_unverified": _f_eject_unverified, "failed": _f_failed,
    "paused": _f_paused, "eject_skipped": _f_eject_skipped,
}
_OWNER: dict[str, Callable[[dict, bool], str]] = {
    "started": _o_started, "finished": _o_finished, "finished_ejected": _o_finished_ejected,
    "plate_not_clear": _o_plate_not_clear, "eject_unverified": _o_eject_unverified, "plate_clear": _o_plate_clear,
    "failed": _o_failed, "paused": _o_paused, "hms": _o_hms, "offline": _o_offline, "ready_next": _o_ready_next,
    "upgrade_proposed": _o_upgrade_proposed, "eject_skipped": _o_eject_skipped,
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
