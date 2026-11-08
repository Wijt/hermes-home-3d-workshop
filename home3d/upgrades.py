"""Human-needed moments -> upgrade proposals.

Every time a person had to step in (take a part off, swap filament, approve a start, ...) a moment is
logged. When one kind crosses its threshold inside its window, the workshop proposes the upgrade that
removes that step: for ``remove_part`` that is the printed tilt base + auto-eject preset the real system
built for itself. A kind with an open (non-rejected) proposal only gets its evidence count bumped; after
a rejection, a new proposal needs ``threshold`` fresh moments logged after the rejection.
Statuses (advanced by the ``home3d_upgrades`` tool): proposed -> accepted -> printing -> installed.
"""

from __future__ import annotations

from typing import Any

from .config import Settings
from .store import Store

STATUSES = ("proposed", "accepted", "printing", "installed", "rejected")
_EVIDENCE_LIMIT = 100_000

KINDS: dict[str, dict] = {
    "remove_part": {
        "label": "take a finished part off the plate", "label_tr": "biten parçayı tabladan alma",
        "threshold": 3, "window_days": 30,
        "title": "Auto-eject: tilted base + push-off preset",
        "title_tr": "Otomatik düşürme: eğik taban + itme ayarı",
        "proposal": ("Auto-eject: tilt the printer forward ~15° on a printed base and let the nozzle push cooled "
                     "parts off; slice sturdy PLA parts with the auto-eject preset. Recalibrate the camera plate "
                     "check on the tilted base."),
        "proposal_tr": ("Yazıcıyı basılı bir tabanla öne ~15° eğ, tabla soğuyunca nozul parçayı öne itip "
                        "düşürsün; sağlam PLA parçaları otomatik düşürme ayarıyla dilimle. Eğik tabanda kamera "
                        "tabla kontrolünü yeniden ayarla."),
        "model_ref": "https://makerworld.com/en/models/2335000",
    },
    "clean_plate": {
        "label": "clean the build plate", "label_tr": "tablayı temizleme",
        "threshold": 3, "window_days": 30,
        "title": "Plate care routine", "title_tr": "Tabla bakım düzeni",
        "proposal": ("Wash the textured PEI plate with dish soap and warm water on a schedule (IPA alone does not "
                     "degrease it), keep material bed temperatures, and add a brim gap for tiny parts."),
        "proposal_tr": ("Dokulu tablayı düzenli olarak bulaşık deterjanı ve ılık suyla yıka (sadece alkol yetmez), "
                        "malzemeye uygun tabla sıcaklığını koru, küçük parçalara kenar şeridi ekle."),
        "model_ref": "",
    },
    "filament_swap": {
        "label": "swap or refill filament", "label_tr": "filament değiştirme",
        "threshold": 3, "window_days": 30,
        "title": "Register spools and AMS slots", "title_tr": "Makaraları ve yuvaları kaydet",
        "proposal": ("Register every spool (material, colour, remaining) and keep a fixed AMS slot mapping for the "
                     "common colours; warn before a job when the tray it needs is low."),
        "proposal_tr": ("Her makarayı (malzeme, renk, kalan) kaydet, sık kullanılan renkler için sabit yuva düzeni "
                        "kullan; gereken makara azsa baskıdan önce uyar."),
        "model_ref": "",
    },
    "camera_check": {
        "label": "look at the plate because the camera was unsure", "label_tr": "kamera emin olamayınca tablaya bakma",
        "threshold": 2, "window_days": 30,
        "title": "Trustworthy plate detection", "title_tr": "Güvenilir tabla algılama",
        "proposal": ("Re-aim the camera or add an external one, light the plate for every check, and recalibrate "
                     "plate detection on the current setup (e.g. after tilting the printer)."),
        "proposal_tr": ("Kamerayı yeniden hizala ya da harici kamera ekle, her kontrolde ışığı aç ve tabla "
                        "algılamayı mevcut düzende (ör. eğik tabandan sonra) yeniden kalibre et."),
        "model_ref": "",
    },
    "failure_check": {
        "label": "check a failed print", "label_tr": "yarıda kalan baskıyı kontrol etme",
        "threshold": 2, "window_days": 30,
        "title": "Catch failures early", "title_tr": "Hataları erken yakala",
        "proposal": ("Enable the printer's failure (spaghetti) detection pause, slow the first layers of small "
                     "parts, add a brim for small footprints, and check the camera at layers 2-10."),
        "proposal_tr": ("Yazıcının hata algılama duraklatmasını aç, küçük parçaların ilk katmanlarını yavaşlat, "
                        "küçük tabanlara kenar şeridi ekle, 2-10. katmanlarda kameraya bak."),
        "model_ref": "",
    },
    "measure": {
        "label": "measure something by hand", "label_tr": "elle ölçü alma",
        "threshold": 3, "window_days": 60,
        "title": "Measure from photos", "title_tr": "Fotoğraftan ölçü",
        "proposal": ("Ask for a photo with a coin or ruler next to the object, and keep a printed calibration card "
                     "in the house for quick sizing."),
        "proposal_tr": ("Nesnenin yanına bozuk para ya da cetvel koyup fotoğraf iste; evde hızlı ölçü için basılı "
                        "bir ölçü kartı bulundur."),
        "model_ref": "",
    },
    "post_process": {
        "label": "clean supports or brims off a part", "label_tr": "destek veya kenar şeridi temizleme",
        "threshold": 5, "window_days": 30,
        "title": "Less post-processing", "title_tr": "Daha az temizlik işi",
        "proposal": ("Prefer orientations that need no support, use tree supports only where needed, and a brim "
                     "gap that peels off cleanly."),
        "proposal_tr": ("Destek gerektirmeyen yönü seç, ağaç desteği sadece gereken yere koy, kenar şeridini "
                        "kolay ayrılacak boşlukla bas."),
        "model_ref": "",
    },
    "approve_start": {
        "label": "wait for the owner to approve a start", "label_tr": "başlatma onayını bekleme",
        "threshold": 5, "window_days": 14,
        "title": "Standing approval window", "title_tr": "Süreli başlatma onayı",
        "proposal": ("Owner approval is the bottleneck: grant a standing approval window (e.g. this evening) for "
                     "jobs that pass every safety gate (empty plate, no errors, our job next)."),
        "proposal_tr": ("Onay beklemek darboğaz oldu: tüm güvenlik kontrollerinden geçen işler (boş tabla, hata "
                        "yok, sıra bizde) için süreli bir onay penceresi ver (ör. bu akşam)."),
        "model_ref": "",
    },
    "other": {
        "label": "step in by hand", "label_tr": "elle müdahale",
        "threshold": 5, "window_days": 30,
        "title": "Review manual steps", "title_tr": "Elle yapılan işleri gözden geçir",
        "proposal": "Review the logged moments and decide which step to automate next.",
        "proposal_tr": "Kaydedilen müdahaleleri gözden geçir ve sıradaki otomasyonu seç.",
        "model_ref": "",
    },
}


def normalize_kind(kind: Any) -> str:
    k = str(kind or "").strip().lower().replace("-", "_").replace(" ", "_")
    return k if k in KINDS else "other"


def text_for(kind: str, lang: str) -> dict:
    """Label / title / proposal of ``kind`` in ``lang`` (tr falls back to en)."""
    spec = KINDS[normalize_kind(kind)]
    tr = lang == "tr"
    return {"label": spec.get("label_tr" if tr else "label") or spec["label"],
            "title": spec.get("title_tr" if tr else "title") or spec["title"],
            "proposal": spec.get("proposal_tr" if tr else "proposal") or spec["proposal"],
            "model_ref": spec.get("model_ref", "")}


def log_moment(store: Store, kind: str, detail: str = "", *, job_name: str = "", who: str = "",
               source: str = "agent") -> int:
    """Record that a person had to act. Unknown kinds are stored as ``other`` (detail keeps the original)."""
    k = normalize_kind(kind)
    if k == "other" and str(kind or "").strip() and str(kind).strip().lower() != "other":
        detail = f"[{kind}] {detail}".strip()
    return store.add_human_needed(k, detail, job_name=job_name, who=who, source=source)


def _last_rejected(store: Store, kind: str) -> dict | None:
    rows = [u for u in store.upgrades(status="rejected") if u.get("kind") == kind]
    return max(rows, key=lambda u: u.get("updated") or 0) if rows else None


def evaluate(store: Store, settings: Settings) -> list[dict]:
    """Create proposals for kinds that crossed their threshold; bump evidence on open ones.
    Returns only the newly created proposals (dicts with id, kind, title, proposal, model_ref, evidence,
    label, window_days, threshold)."""
    lang = getattr(settings, "language", "en") or "en"
    created: list[dict] = []
    for kind, spec in KINDS.items():
        all_moments = store.human_needed(kind, limit=_EVIDENCE_LIMIT)
        if not all_moments:
            continue
        window_s = float(spec["window_days"]) * 86400
        rejected = _last_rejected(store, kind)
        cutoff = float(rejected.get("updated") or 0) if rejected is not None else 0.0
        existing = store.upgrade_for_kind(kind)
        if existing is not None:
            # evidence = the moments that triggered it (its window) + everything logged since
            since = max(cutoff, float(existing.get("created") or 0) - window_s)
            n = sum(1 for m in all_moments if float(m.get("ts") or 0) >= since)
            if n > int(existing.get("evidence") or 0):
                store.update_upgrade(int(existing["id"]), evidence=n)
            continue
        recent = store.human_needed(kind, since_days=float(spec["window_days"]), limit=_EVIDENCE_LIMIT)
        recent = [m for m in recent if float(m.get("ts") or 0) > cutoff]
        if len(recent) < int(spec["threshold"]):
            continue
        t = text_for(kind, lang)
        uid = store.add_upgrade(kind=kind, title=t["title"], proposal=t["proposal"], model_ref=t["model_ref"],
                                evidence=len(recent))
        created.append({"id": uid, "kind": kind, "title": t["title"], "proposal": t["proposal"],
                        "model_ref": t["model_ref"], "evidence": len(recent), "label": t["label"],
                        "window_days": int(spec["window_days"]), "threshold": int(spec["threshold"]),
                        "status": "proposed"})
    return created
