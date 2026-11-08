"""Pure safety decisions: may we start a queued job, may we mark the plate clear?

No I/O: callers pass the printer status, queue and the latest plate check. Every block carries a stable
code (``Gate.items``) so ``describe()`` can say it in Turkish or English without ``messages.py``.
Approval itself is enforced by the ``pre_tool_call`` hook; gates only decide whether it is even possible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional

from .backends.base import ACTIVE_STATES, FAILED, FINISH, IDLE, OFFLINE, PlateCheck, PrinterStatus, QueueItem

# code -> (en, tr); ``{x}`` placeholders are filled from the item params
_TEXT: dict[str, tuple[str, str]] = {
    "in_cron": ("never from a scheduled job, a person must be present",
                "zamanlanmış görevden asla, başında biri olmalı"),
    "offline": ("the printer is offline", "yazıcıya ulaşılamıyor"),
    "busy": ("the printer is busy ({state}{job_sfx})", "yazıcı şu an meşgul ({state}{job_sfx})"),
    "state_unknown": ("printer state '{state}' is not idle", "yazıcının durumu ({state}) boşta değil"),
    "hms": ("printer error {codes}", "yazıcıda hata var: {codes}"),
    "item_missing": ("queue item {item} not found", "{item} numaralı iş kuyrukta yok"),
    "item_not_pending": ("queue item {item} is {status}, not pending",
                         "{item} numaralı iş bekleyen değil ({status})"),
    "plate_unknown": ("no plate check yet: look at the camera first",
                      "tabla henüz kontrol edilmedi, önce kameraya bakmak lazım"),
    "plate_occupied": ("the plate is not empty ({detail})", "tabla boş değil ({detail})"),
    "plate_uncertain": ("the plate check is not sure the plate is empty ({detail})",
                        "kamera tablanın boş olduğundan emin değil ({detail})"),
    "after_job": ("the last job {state}: the plate must be cleared first",
                  "son iş {state}, önce tablanın temizlenmesi gerek"),
    "jump": ("{name} (#{other}) is waiting ahead and is not ours", "sırada önde başkasının işi var: {name} (#{other})"),
    "bed_hot": ("the bed is still hot ({bed:.0f} C > {limit:.0f} C)",
                "tabla hâlâ sıcak ({bed:.0f} °C, sınır {limit:.0f} °C)"),
    "auto_start_pending": ("auto-start items pending ({names}): marking the plate clear would start them",
                           "otomatik başlayacak işler var ({names}), tabla boş denirse hemen başlarlar"),
    # warnings
    "voice": ("voice request: a written confirmation is required", "sesli istek: yazılı onay gerekiyor"),
    "hms_ignored": ("ignored harmless HMS {codes}", "zararsız uyarı yok sayıldı: {codes}"),
    "jump_allowed": ("jumping ahead of {name} (#{other}) as allowed", "izinle {name} (#{other}) işinin önüne geçiliyor"),
    "not_ours": ("queue item {item} was not queued through the workshop",
                 "{item} numaralı iş atölye üzerinden eklenmedi"),
    "needs_calibration": ("plate detection needs calibration", "tabla algılamanın kalibrasyonu gerekiyor"),
    "bed_unknown": ("bed temperature unknown", "tabla sıcaklığı bilinmiyor"),
    "not_manual": ("queue item {item} starts automatically", "{item} numaralı iş kendiliğinden başlayacak şekilde"),
}

_OK_TEXT = {
    "start": ("Start possible (owner approval still needed).", "Başlatılabilir (sahibinin onayı gerekli)."),
    "clear_plate": ("The plate can be marked clear.", "Tabla boş olarak işaretlenebilir."),
    "": ("OK.", "Tamam."),
}
_BLOCK_TEXT = {
    "start": ("Cannot start: ", "Başlatamam: "),
    "clear_plate": ("Cannot mark the plate clear: ", "Tablayı boş işaretleyemem: "),
    "": ("Blocked: ", "Engellendi: "),
}


@dataclass
class Gate:
    ok: bool
    reasons: list[str] = field(default_factory=list)  # English, for logs / the agent
    warnings: list[str] = field(default_factory=list)
    needs_owner: bool = False
    action: str = ""  # "start" | "clear_plate"
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
                "FAILED": ("failed", "yarıda kaldı"), "IDLE": ("idle", "boşta")}


def _render(code: str, params: dict, lang: str) -> str:
    i = 1 if lang == "tr" else 0
    p = dict(params)
    if "state" in p:
        p["state"] = _STATE_WORDS.get(p["state"], (p["state"], p["state"]))[i]
    if "job" in p:
        p["job_sfx"] = f": {p['job']}" if p["job"] else ""
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


def _check_plate(gate: Gate, plate: Optional[PlateCheck]) -> bool:
    """Block unless the plate check explicitly says empty. Returns True when the plate is empty."""
    if plate is None:
        gate.block("plate_unknown")
        return False
    if plate.needs_calibration:
        gate.warn("needs_calibration")
    if plate.is_empty is True:
        return True
    gate.block("plate_occupied" if plate.is_empty is False else "plate_uncertain",
               pct=plate.difference_pct, msg=plate.message)
    return False


def _printer_blocks(gate: Gate, status: PrinterStatus) -> None:
    if status.state == OFFLINE or not status.connected:
        gate.block("offline")
        return
    if status.state in ACTIVE_STATES:
        gate.block("busy", state=status.state, job=status.job_name)
    elif status.state not in (IDLE, FINISH, FAILED):
        gate.block("state_unknown", state=status.state or "?")
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


def start_gate(status: PrinterStatus, queue: list[QueueItem], item_id: int, *, plate: Optional[PlateCheck],
               in_cron: bool, own_item_ids: set[int], allow_jump: bool = False,
               voice_request: bool = False) -> Gate:
    """May queue item ``item_id`` be started now? Approval is still required (``needs_owner``)."""
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

    empty = _check_plate(gate, plate)
    if not empty and status.state in (FINISH, FAILED):
        gate.block("after_job", state=status.state)

    if item is not None:
        own = {int(i) for i in (own_item_ids or ()) if str(i).strip().isdigit()}
        if item.id not in own:
            gate.warn("not_ours", item=item.id)
        if not item.manual_start:
            gate.warn("not_manual", item=item.id)
        order = _order(queue)
        for other in queue:
            if other.id == item.id or not other.is_pending or other.id in own:
                continue
            if _ahead(order[other.id], order[item.id]):
                name = other.name or f"#{other.id}"
                if allow_jump:
                    gate.warn("jump_allowed", name=name, other=other.id)
                else:
                    gate.block("jump", name=name, other=other.id)
    if voice_request:
        gate.warn("voice")
    return gate


def clear_plate_gate(status: PrinterStatus, plate: Optional[PlateCheck], *, in_cron: bool,
                     cool_temp_c: float, auto_start_pending: list[QueueItem]) -> Gate:
    """May we tell the printer manager the plate is clear (which lets it start the next job)?"""
    gate = Gate(ok=True, needs_owner=True, action="clear_plate")
    if in_cron:
        gate.block("in_cron")
    if status.state == OFFLINE or not status.connected:
        gate.block("offline")
    elif status.state in ACTIVE_STATES:
        gate.block("busy", state=status.state, job=status.job_name)
    if status.bed_temp is None:
        gate.warn("bed_unknown")
    elif status.bed_temp > cool_temp_c:
        gate.block("bed_hot", bed=float(status.bed_temp), limit=float(cool_temp_c))
    _check_plate(gate, plate)
    auto = [q for q in (auto_start_pending or []) if q.is_pending and not q.manual_start]
    if auto:
        gate.block("auto_start_pending", names=", ".join(q.name or f"#{q.id}" for q in auto[:3]))
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
