"""Pure safety decisions: may we start a queued job, mark the plate clear, resume a paused print?

No I/O: callers pass the printer status, queue and the latest plate check. Every block carries a stable
code (``Gate.items``) so ``describe()`` can say it in Turkish or English without ``messages.py``.
Approval itself is enforced by the ``pre_tool_call`` hook and the handler pass; gates only decide whether
the action is possible at all. Everything fails closed: an unknown printer state, an unknown bed
temperature, a plate check that is unsure or ran in the dark, and an unacknowledged printer error block.

A person can overrule exactly one kind of camera doubt: Bambuddy's known false-positive band (an empty plate
read at 18-25 %, ``PlateCheck.uncertain_band``). The owner's ``/home3d approve clear`` accepts it, and a start
accepts it once that confirmation is recorded for the last job (``plate_confirmed``). "Occupied", a dark
check, a check that could not run and a missing calibration are never overruled.

``plate_deferred`` (the ``pre_tool_call`` hook, which must stay fast and never runs the camera): no plate check is
needed now because the handler runs the authoritative one right before the action. A plate check that IS passed in
(a recent one the process remembers) still decides as usual, so a fresh "occupied" or "unsure" blocks at once.

Who may ask (also pure): ``who_is`` turns a recorded sender id into an ``Actor`` (owner / member / guest / nobody,
how the message arrived, whether a person is present), and three rules decide from it: ``approval_refusal`` (start,
resume, plate clear: the owner, present, not by voice), ``stop_refusal`` (stop, pause: ``stop_policy``) and
``write_refusal`` (prepare a print: known people, or ``allow_guests``). Every surface asks these same functions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping, Optional

from .backends.base import (ACTIVE_STATES, FAILED, FINISH, IDLE, OFFLINE, PAUSE, PlateCheck, PrinterStatus,
                            QueueItem)
from .config import LOCAL_SENDER, norm_id

# code -> (en, tr); ``{x}`` placeholders are filled from the item params
_TEXT: dict[str, tuple[str, str]] = {
    "in_cron": ("never from a scheduled job or another run nobody watches, a person must be present",
                "zamanlanmış görevden ya da başında kimsenin olmadığı çalışmadan asla, başında biri olmalı"),
    "offline": ("the printer is offline", "yazıcıya ulaşılamıyor"),
    "busy": ("the printer is busy ({state}{job_sfx})", "yazıcı şu an meşgul ({state}{job_sfx})"),
    "state_unknown": ("the printer state is not idle ({state})", "yazıcının durumu boşta değil ({state})"),
    "hms": ("printer error {codes}", "yazıcıda hata var: {codes}"),
    "item_missing": ("queue item {item} not found", "{item} numaralı iş kuyrukta yok"),
    "item_not_pending": ("queue item {item} is {status}, not pending",
                         "{item} numaralı iş bekleyen değil ({status})"),
    "plate_unknown": ("no plate check yet: look at the camera first",
                      "tabla henüz kontrol edilmedi, önce kameraya bakmak lazım"),
    "plate_occupied": ("the plate is not empty ({detail})", "tabla boş değil ({detail})"),
    "plate_uncertain": ("the plate check is not sure the plate is empty ({detail})",
                        "kamera tablanın boş olduğundan emin değil ({detail})"),
    "plate_dark": ("the chamber light was off for the plate check, so the camera cannot judge the plate",
                   "kabin ışığı kapalıydı, kamera tablayı göremedi"),
    "after_job": ("the last job {state}: the plate must be cleared first",
                  "son iş {state}, önce tablanın temizlenmesi gerek"),
    "awaiting_plate_clear": ("the printer manager waits for the plate to be marked clear first (/home3d approve clear)",
                             "yazıcı yöneticisi önce tablanın boş işaretlenmesini bekliyor (/home3d approve clear)"),
    "after_failure": ("the last job failed: the owner must confirm the plate is clear first "
                      "(/home3d approve clear)",
                      "son iş yarıda kaldı: önce sahibinin tablanın boş olduğunu onaylaması gerek "
                      "(/home3d approve clear)"),
    "jump": ("{name} (#{other}{for_who}) is waiting ahead and is {whose}",
             "sırada önde başkasının işi var: {name} (#{other}{for_who_tr})"),
    "bed_hot": ("the bed is still hot ({bed:.0f} C > {limit:.0f} C)",
                "tabla hâlâ sıcak ({bed:.0f} °C, sınır {limit:.0f} °C)"),
    "auto_start_pending": ("auto-start items pending ({names}): marking the plate clear would start them. "
                           "If they should start, look at the plate and mark it clear in Bambuddy yourself",
                           "otomatik başlayacak işler var ({names}), tabla boş denirse hemen başlarlar. "
                           "Başlamaları gerekiyorsa tablaya bak ve Bambuddy'de boş olarak kendin işaretle"),
    "bed_unknown": ("the bed temperature is unknown, so it may still be hot",
                    "tabla sıcaklığı bilinmiyor, hâlâ sıcak olabilir"),
    "not_paused": ("the printer is not paused ({state})", "yazıcı duraklatılmış değil ({state})"),
    "hms_unacknowledged": ("printer error {codes}: the owner must acknowledge it first "
                           "(/home3d approve resume ack)",
                           "yazıcıda hata var ({codes}): önce sahibinin onaylaması gerek "
                           "(/home3d approve resume ack)"),
    # warnings
    "voice": ("voice request: a written confirmation is required", "sesli istek: yazılı onay gerekiyor"),
    "hms_ignored": ("ignored harmless HMS {codes}", "zararsız uyarı yok sayıldı: {codes}"),
    "jump_allowed": ("jumping ahead of {name} (#{other}{for_who}) as allowed",
                     "izinle {name} (#{other}{for_who_tr}) işinin önüne geçiliyor"),
    "not_ours": ("queue item {item} was not queued through the workshop",
                 "{item} numaralı iş atölye üzerinden eklenmedi"),
    "needs_calibration": ("plate detection needs calibration", "tabla algılamanın kalibrasyonu gerekiyor"),
    "not_manual": ("queue item {item} starts automatically", "{item} numaralı iş kendiliğinden başlayacak şekilde"),
    "camera_only": ("only the camera thinks the plate is empty ({detail}); nobody has confirmed it",
                    "tablanın boş olduğunu yalnızca kamera düşünüyor ({detail}), kimse bakıp onaylamadı"),
    "plate_unsure_confirmed": ("the camera is unsure ({detail}); the owner confirmed the plate is clear",
                               "kamera emin değil ({detail}), sahibi tablanın boş olduğunu onayladı"),
    "plate_unsure_person": ("the camera is unsure ({detail}): you confirm the plate is clear yourself, look at it first",
                            "kamera emin değil ({detail}): tablanın boş olduğunu sen onaylıyorsun, önce bak"),
    "hms_acknowledged": ("resuming despite printer error {codes} (acknowledged by the owner)",
                         "sahibi onayladı, yazıcı hatasına rağmen devam: {codes}"),
    "plate_deferred": ("the camera checks the plate right before the start",
                       "kamera başlatmadan hemen önce tablaya bakacak"),
    "plate_deferred_clear": ("the camera checks the plate right before it is marked clear",
                             "kamera tabla boş işaretlenmeden hemen önce bakacak"),
}

# ---- who is asking --------------------------------------------------------------------------------------
OWNER, MEMBER, GUEST, NOBODY = "owner", "member", "guest", "nobody"
VOICE, TYPED = "voice", "typed"
GUEST_NAME = "Guest"
UNKNOWN_LABEL = ("an unknown sender", "tanınmayan biri")
APPROVAL_ACTIONS = ("start", "clear_plate", "resume")
STOP_ACTIONS = ("stop", "pause")


@dataclass(frozen=True)
class Actor:
    """Whoever asks for something, as far as the plugin knows it. Built by ``who_is`` (pure) from the sender id the
    ``pre_llm_call`` hook recorded for a session, or from the ``source`` of a slash command.

    ``role``: ``owner`` (an ``owner_ids`` entry, or a local session while ``local_is_owner``), ``member`` (another
    person in the household list), ``guest`` (a sender id that is in no list, or a local session that is not the
    owner) or ``nobody`` (no sender id at all). ``name`` is never empty for an owner, member or guest, so a request
    or a job is never stored without a requester. ``channel``: how the message that asks arrived (``voice`` /
    ``typed`` / '' unknown). ``present``: False in a run nobody watches (cron, kanban worker, ``chat -q``, ``-z``,
    ``--source tool``): such a run is never the owner for a printer action."""
    sender: str = ""
    name: str = ""
    role: str = NOBODY
    channel: str = ""
    present: bool = True
    local: bool = False

    @property
    def is_owner(self) -> bool:
        return self.role == OWNER

    @property
    def known(self) -> bool:
        return self.role in (OWNER, MEMBER)

    def label(self, lang: str = "en") -> str:
        """The name, or "an unknown sender" in ``lang`` when there is none."""
        return self.name or UNKNOWN_LABEL[1 if lang == "tr" else 0]


def guest_name(sender: object) -> str:
    """The requester name of a sender who is in no list: ``Guest (…1234)`` (the last characters of the id keep two
    guests apart), ``Guest (local)`` for a local session, ``Guest`` without an id."""
    sid = norm_id(sender)
    if not sid:
        return GUEST_NAME
    if sid == LOCAL_SENDER:
        return f"{GUEST_NAME} (local)"
    tail = "".join(ch for ch in sid.split("@", 1)[0] if ch.isalnum())[-4:]
    return f"{GUEST_NAME} (…{tail})" if tail else GUEST_NAME


def who_is(settings, sender: object, *, present: bool = True, channel: str = "") -> Actor:
    """The ``Actor`` for a recorded sender id ('' = unknown, ``config.LOCAL_SENDER`` = a local session). Pure."""
    sid = str(sender if sender is not None else "").strip()
    local = norm_id(sid) == LOCAL_SENDER
    person = settings.person_for(sid) if sid else None
    if person is not None:
        role = OWNER if person.role == "owner" else MEMBER
        name = str(person.name or "").strip() or ("Owner" if role == OWNER else guest_name(sid))
    elif sid:
        role, name = GUEST, guest_name(sid)
    else:
        role, name = NOBODY, ""
    return Actor(sender=sid, name=name, role=role, channel=str(channel or ""), present=bool(present), local=local)


def approval_refusal(actor: Actor) -> str:
    """Why ``actor`` may not start / resume / mark the plate clear ('' = may): ``unattended`` (nobody is present),
    ``no_identity`` / ``local_off`` / ``not_owner`` (not the owner), ``voice_message`` (the ask arrived as voice).
    The same rule for the agent path (``pre_tool_call``) and the typed path (``/home3d approve``, a UI)."""
    if not actor.present:
        return "unattended"
    if not actor.is_owner:
        if actor.role == NOBODY:
            return "no_identity"
        return "local_off" if actor.local else "not_owner"
    if actor.channel == VOICE:
        return "voice_message"
    return ""


def stop_refusal(actor: Actor, policy: str) -> str:
    """Why ``actor`` may not stop or pause ('' = may) under ``stop_policy``: ``anyone`` never refuses; ``known``
    (default; also any unreadable value) wants the owner or a listed person; ``owner`` wants the owner. A run with
    nobody present is nobody (``stop_unattended``). A voice message may stop: stopping is the safe direction."""
    policy = str(policy or "").strip().lower()
    if policy == "anyone":
        return ""
    if not actor.present:
        return "stop_unattended"
    if policy == "owner":
        return "" if actor.is_owner else "stop_owner_only"
    return "" if actor.known else "stop_unknown"


def write_refusal(actor: Actor, allow_guests: bool) -> str:
    """Why ``actor`` may not prepare a print or change anything ('' = may): ``guest`` unless they are the owner, a
    listed person, or ``allow_guests`` is on."""
    return "" if actor.known or bool(allow_guests) else "guest"


def requester_name(actor: Actor) -> str:
    """The name a request or job of ``actor`` is recorded under: never empty (``Guest`` without any identity)."""
    return actor.name or GUEST_NAME


def refusal(code: str, lang: str, **params) -> str:
    """The refusal sentence for an access ``code`` in ``lang`` (``messages.access_text``)."""
    from .messages import access_text

    return access_text(code, lang, **params)


_OK_TEXT = {
    "start": ("Start possible (owner approval still needed).", "Başlatılabilir (sahibinin onayı gerekli)."),
    "clear_plate": ("The plate can be marked clear.", "Tabla boş olarak işaretlenebilir."),
    "resume": ("Resume possible (owner approval still needed).", "Devam ettirilebilir (sahibinin onayı gerekli)."),
    "": ("OK.", "Tamam."),
}
_BLOCK_TEXT = {
    "start": ("Cannot start: ", "Başlatamam: "),
    "clear_plate": ("Cannot mark the plate clear: ", "Tablayı boş işaretleyemem: "),
    "resume": ("Cannot resume: ", "Devam ettiremem: "),
    "": ("Blocked: ", "Engellendi: "),
}


@dataclass
class Gate:
    ok: bool
    reasons: list[str] = field(default_factory=list)  # English, for logs / the agent
    warnings: list[str] = field(default_factory=list)
    needs_owner: bool = False
    action: str = ""  # "start" | "clear_plate" | "resume"
    items: list[dict] = field(default_factory=list)  # [{"code", "level": "block"|"warn", "params"}]

    def block(self, code: str, **params) -> None:
        self.items.append({"code": code, "level": "block", "params": params})
        self.reasons.append(_render(code, params, "en"))
        self.ok = False

    def warn(self, code: str, **params) -> None:
        self.items.append({"code": code, "level": "warn", "params": params})
        self.warnings.append(_render(code, params, "en"))

    @property
    def codes(self) -> list[str]:
        return [i["code"] for i in self.items if i["level"] == "block"]

    def to_dict(self) -> dict:
        return asdict(self)


_STATE_WORDS = {"PREPARE": ("preparing", "hazırlanıyor"), "RUNNING": ("printing", "baskıda"),
                "PAUSE": ("paused", "duraklatıldı"), "FINISH": ("finished", "bitti"),
                "FAILED": ("failed", "yarıda kaldı"), "IDLE": ("idle", "boşta"),
                "UNKNOWN": ("unknown", "bilinmiyor"), "OFFLINE": ("offline", "bağlantı yok")}


def _render(code: str, params: dict, lang: str) -> str:
    i = 1 if lang == "tr" else 0
    p = dict(params)
    if "state" in p:
        p["state"] = _STATE_WORDS.get(p["state"], (p["state"], p["state"]))[i]
    if "job" in p:
        p["job_sfx"] = f": {p['job']}" if p["job"] else ""
    if code in ("jump", "jump_allowed"):  # another person's workshop job ("who") or a job queued elsewhere
        who = str(p.get("who") or "").strip()
        p["for_who"] = f", for {who}" if who else ""
        p["for_who_tr"] = f", isteyen: {UNKNOWN_LABEL[1] if who == UNKNOWN_LABEL[0] else who}" if who else ""
        p["whose"] = "someone else's" if who else "not ours"
    if "pct" in p or "msg" in p:
        pct = p.get("pct")
        if pct is not None:
            p["detail"] = f"%{pct:g}" if i else f"{pct:g}%"
        else:  # the backend message is English: keep it out of Turkish text
            p["detail"] = "" if i else str(p.get("msg") or "")[:60]
    text = _TEXT.get(code, (code, code))[i]
    try:
        return text.format(**p).replace(" ()", "")
    except (KeyError, IndexError, ValueError):
        return text


def _codes(hms: Iterable) -> str:
    return ", ".join(h.code for h in hms)


def person_can_overrule(plate: Optional[PlateCheck]) -> bool:
    """The plate check's only doubt is the known false-positive band (lit, calibrated, a small difference)."""
    return (plate is not None and plate.is_empty is None and bool(getattr(plate, "uncertain_band", False))
            and getattr(plate, "light_ok", None) is not False and not plate.needs_calibration)


def _check_plate(gate: Gate, plate: Optional[PlateCheck], *, skipped: bool = False,
                 person: str = "", deferred: str = "") -> Optional[bool]:
    """Block unless a lit plate check explicitly says empty. Returns True when the plate is empty, False when it
    is not (or unknown and blocked), None when the check is deferred (``deferred`` = the warning code).

    ``skipped``: the caller did not look because the printer already blocks; honoured only when the gate has
    already blocked (so it can never open a gate). ``person``: "confirmed" (the owner confirmed this plate
    earlier) or "confirming" (the owner is confirming it now) lets a band-only doubt pass with a warning.
    ``deferred``: no check yet because the handler runs it right before the action (the hook): no block, a warning."""
    if plate is None:
        if skipped and not gate.ok:
            return False
        if deferred:
            gate.warn(deferred)
            return None
        gate.block("plate_unknown")
        return False
    if plate.needs_calibration:
        gate.warn("needs_calibration")
    if getattr(plate, "light_ok", None) is False:
        gate.block("plate_dark")
        return False
    if plate.is_empty is True:
        return True
    if person and person_can_overrule(plate):
        gate.warn("plate_unsure_confirmed" if person == "confirmed" else "plate_unsure_person",
                  pct=plate.difference_pct, msg=plate.message)
        return True
    gate.block("plate_occupied" if plate.is_empty is False else "plate_uncertain",
               pct=plate.difference_pct, msg=plate.message)
    return False


def _offline(status: PrinterStatus) -> bool:
    return status.state == OFFLINE or status.connected is not True


def _idle_like(gate: Gate, status: PrinterStatus) -> None:
    """Block an active printer and any state that is not known to be idle (UNKNOWN included)."""
    if status.state in ACTIVE_STATES:
        gate.block("busy", state=status.state, job=status.job_name)
    elif status.state not in (IDLE, FINISH, FAILED):
        gate.block("state_unknown", state=status.state or "UNKNOWN")


def _printer_blocks(gate: Gate, status: PrinterStatus) -> None:
    if _offline(status):
        gate.block("offline")
        return
    _idle_like(gate, status)
    blocking = status.blocking_hms
    if blocking:
        gate.block("hms", codes=_codes(blocking))
    ignored = [h for h in status.hms if h.ignorable]
    if ignored:
        gate.warn("hms_ignored", codes=_codes(ignored))


def _order(queue: list[QueueItem]) -> dict[int, tuple]:
    """Queue order key: Bambuddy ``position`` when both sides have one, else list order."""
    return {q.id: (q.position, i) for i, q in enumerate(queue)}


def _ahead(a: tuple, b: tuple) -> bool:
    (pa, ia), (pb, ib) = a, b
    if pa is not None and pb is not None and pa != pb:
        return pa < pb
    return ia < ib


def printer_blocks(status: PrinterStatus, action: str = "start") -> bool:
    """The printer alone already blocks ``action`` ("start" / "clear_plate"): offline or not idle-like (and, for a
    start, an active printer error). A camera check (chamber light, up to ~12 s) would then change nothing."""
    if _offline(status) or status.state not in (IDLE, FINISH, FAILED):
        return True
    return action == "start" and bool(status.blocking_hms)


def same_person(a: object, b: object, owner_name: str = "") -> bool:
    """Two requester names mean the same person (case-insensitive). An empty name is NOBODY's: it never equals
    another name, not even another empty one, so a job recorded without a requester (an unknown sender, before
    requesters were required) is never taken for the owner's or for the asking person's own. ``owner_name`` is
    accepted for older callers and no longer used."""
    ka, kb = str(a or "").strip().casefold(), str(b or "").strip().casefold()
    return bool(ka) and ka == kb


def start_gate(status: PrinterStatus, queue: list[QueueItem], item_id: int, *, plate: Optional[PlateCheck],
               in_cron: bool, own_item_ids: set[int], allow_jump: bool = False,
               voice_request: bool = False, plate_confirmed: bool = False, after_failure: bool = False,
               plate_skipped: bool = False, plate_deferred: bool = False,
               requesters: Optional[Mapping[int, str]] = None, owner_name: str = "") -> Gate:
    """May queue item ``item_id`` be started now? Approval is still required (``needs_owner``).

    ``own_item_ids``: queue ids of the workshop's ACTIVE jobs (queued or printing). ``requesters``: who asked for
    each of those jobs (queue id -> name; an empty name is nobody's, see ``same_person``). With it, a workshop job
    waits ahead "as ours" only when the SAME person asked for it: another household member's workshop job ahead
    blocks (``jump``, naming them) like a job queued elsewhere, unless ``allow_jump``. Without it (None) every
    workshop job counts as ours (older callers). ``plate_confirmed``: a
    person (the owner) confirmed the plate of the last job (``status.job_name``) is clear; after a FAILED
    job the camera alone is never enough. ``after_failure``: the store knows of a failed print nobody has
    confirmed since (``Store.unconfirmed_failure``): it blocks even when the printer no longer says FAILED
    (power cycle, cancel to IDLE). ``plate_skipped``: no plate check was made because the printer blocks.
    ``plate_deferred``: the hook's view: without a plate check the gate does not block on the plate (warning
    ``plate_deferred``); the handler's own check decides right before the start."""
    gate = Gate(ok=True, needs_owner=True, action="start")
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        pass
    if in_cron:
        gate.block("in_cron")
    _printer_blocks(gate, status)

    item = next((q for q in queue if q.id == item_id), None)
    if item is None:
        gate.block("item_missing", item=item_id)
    elif not item.is_pending:
        gate.block("item_not_pending", item=item_id, status=item.status)

    if status.awaiting_plate_clear is True:
        gate.block("awaiting_plate_clear")
    failed_unconfirmed = (status.state == FAILED and not plate_confirmed) or bool(after_failure)
    if failed_unconfirmed:
        gate.block("after_failure")
    empty = _check_plate(gate, plate, skipped=plate_skipped, person="confirmed" if plate_confirmed else "",
                         deferred="plate_deferred" if plate_deferred else "")
    if empty is False and status.state in (FINISH, FAILED) and not failed_unconfirmed:
        gate.block("after_job", state=status.state)
    elif empty is True and status.state == FINISH and not plate_confirmed:
        gate.warn("camera_only", pct=plate.difference_pct if plate else None, msg="")

    if item is not None:
        own = {int(i) for i in (own_item_ids or ()) if str(i).strip().isdigit()}
        if item.id not in own:
            gate.warn("not_ours", item=item.id)
        if not item.manual_start:
            gate.warn("not_manual", item=item.id)
        order = _order(queue)
        who_map = {int(k): str(v or "") for k, v in (requesters or {}).items() if str(k).strip().isdigit()}
        mine = who_map.get(item.id, "")
        for other in queue:  # anything ahead that may still print and is not ours blocks (any status case)
            if other.id == item.id or other.is_done:
                continue
            who = ""
            if other.id in own:
                if requesters is None or same_person(who_map.get(other.id, ""), mine, owner_name):
                    continue  # the same person's own earlier job (or no requester info: the workshop's)
                who = who_map.get(other.id, "").strip() or UNKNOWN_LABEL[0]
            if _ahead(order[other.id], order[item.id]):
                name = other.name or f"#{other.id}"
                if allow_jump:
                    gate.warn("jump_allowed", name=name, other=other.id, who=who)
                else:
                    gate.block("jump", name=name, other=other.id, who=who)
    if voice_request:
        gate.warn("voice")
    return gate


def clear_plate_gate(status: PrinterStatus, plate: Optional[PlateCheck], *, in_cron: bool,
                     cool_temp_c: float, auto_start_pending: list[QueueItem], person_confirms: bool = False,
                     plate_skipped: bool = False, plate_deferred: bool = False) -> Gate:
    """May we tell the printer manager the plate is clear (which lets it start the next job)?

    ``person_confirms``: the owner is confirming the plate themselves (``/home3d approve clear`` or an owner
    session's approved call): a band-only camera doubt then passes with a warning (see the module doc).
    ``plate_deferred``: as for ``start_gate`` (warning ``plate_deferred_clear``)."""
    gate = Gate(ok=True, needs_owner=True, action="clear_plate")
    if in_cron:
        gate.block("in_cron")
    if _offline(status):
        gate.block("offline")
    else:
        _idle_like(gate, status)
    if status.bed_temp is None:
        gate.block("bed_unknown")
    elif status.bed_temp > cool_temp_c:
        gate.block("bed_hot", bed=float(status.bed_temp), limit=float(cool_temp_c))
    _check_plate(gate, plate, skipped=plate_skipped, person="confirming" if person_confirms else "",
                 deferred="plate_deferred_clear" if plate_deferred else "")
    auto = [q for q in (auto_start_pending or []) if q.is_pending and not q.manual_start]
    if auto:
        gate.block("auto_start_pending", names=", ".join(q.name or f"#{q.id}" for q in auto[:3]))
    return gate


def resume_gate(status: PrinterStatus, *, in_cron: bool, hms_acknowledged: bool = False) -> Gate:
    """May a paused print be resumed? Only a PAUSE that a person is present for; an active printer error
    (blocking HMS) also needs the owner's explicit acknowledgement (``/home3d approve resume ack``)."""
    gate = Gate(ok=True, needs_owner=True, action="resume")
    if in_cron:
        gate.block("in_cron")
    if _offline(status):
        gate.block("offline")
    elif status.state != PAUSE:
        gate.block("not_paused", state=status.state or "UNKNOWN")
    blocking = status.blocking_hms
    if blocking:
        if hms_acknowledged:
            gate.warn("hms_acknowledged", codes=_codes(blocking))
        else:
            gate.block("hms_unacknowledged", codes=_codes(blocking))
    ignored = [h for h in status.hms if h.ignorable]
    if ignored:
        gate.warn("hms_ignored", codes=_codes(ignored))
    return gate


def describe(gate: Gate, lang: str) -> str:
    """One or two short sentences (``tr`` or ``en``) saying what the gate decided and why."""
    tr = lang == "tr"
    idx = 1 if tr else 0
    blocks = [i for i in gate.items if i.get("level") == "block"]
    warns = [i for i in gate.items if i.get("level") == "warn"]
    if gate.items:
        block_txt = [_render(i["code"], i.get("params", {}), lang) for i in blocks]
        warn_txt = [_render(i["code"], i.get("params", {}), lang) for i in warns]
    else:  # a Gate built by hand: only English text is available
        block_txt, warn_txt = list(gate.reasons), list(gate.warnings)
    if gate.ok:
        out = _OK_TEXT.get(gate.action, _OK_TEXT[""])[idx]
        if not gate.needs_owner:
            out = out.split(" (")[0].rstrip(".") + "."
    else:
        out = _BLOCK_TEXT.get(gate.action, _BLOCK_TEXT[""])[idx] + "; ".join(block_txt or ["?"]) + "."
    if warn_txt:
        out += (" Not: " if tr else " Note: ") + "; ".join(warn_txt) + "."
    return out
