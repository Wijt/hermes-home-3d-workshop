"""Settings and data-dir resolution.

Settings come from (highest first): an explicit mapping (tests, watcher snapshot), the Hermes plugin
settings (``ctx.get_config``), then defaults. The zero-token watcher runs outside the agent, so
``hermes home3d setup`` writes a non-secret snapshot (``watcher-config.json``) into the data dir.
Secrets are only read through ``agent.secret_scope.get_secret`` (catalog rule 11).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping, Optional

from . import PLUGIN_NAME

SNAPSHOT_FILE = "watcher-config.json"
API_KEY_ENV = "HOME3D_BAMBUDDY_API_KEY"
# The recorded "sender" of a local CLI/TUI/desktop session (no messaging identity). ``Settings.is_owner(LOCAL_SENDER)``
# is ``local_is_owner``. A messaging user whose id happens to be "local" is never recorded as this value (hooks.py).
LOCAL_SENDER = "local"
INJECT_MODES = ("auto", "always", "never")

_WA_ID = re.compile(r"^\+?(\d+)(?::\d+)?@(?:s\.whatsapp\.net|c\.us)$")
_LID_ID = re.compile(r"^\+?(\d+)(?::\d+)?@lid$")
_PHONE_ID = re.compile(r"^\+?(\d+)$")


def norm_id(sender_id: object) -> str:
    """Canonical form of a sender id for EXACT comparison (never compare only the part before "@").

    strip + lower; WhatsApp phone ids (``+90555...@s.whatsapp.net``, ``...:12@s.whatsapp.net``, ``...@c.us``) and bare
    phone numbers become their digits; ``@lid`` ids become ``<digits>@lid`` (a separate id space: never equal to a
    phone number); everything else (Matrix ``@sam:matrix.org``, e-mail, Telegram numeric ids, ``uid:3``) is compared
    as is, case-insensitively.
    """
    s = str(sender_id if sender_id is not None else "").strip().lower()
    m = _WA_ID.match(s) or _PHONE_ID.match(s)
    if m:
        return m.group(1)
    m = _LID_ID.match(s)
    if m:
        return f"{m.group(1)}@lid"
    return s


_norm = norm_id


@dataclass
class Person:
    id: str  # messaging sender id (e.g. WhatsApp user id); "" for unknown
    name: str
    role: str = "family"  # "owner" | "family"
    address_as: str = ""  # how the persona addresses them ("Anneciğim")

    @property
    def greeting_name(self) -> str:
        return self.address_as or self.name


@dataclass
class Settings:
    backend: str = "simulator"
    bambuddy_url: str = ""
    public_url: str = ""
    printer_id: int = 1
    persona_name: str = "Mıstık"
    language: str = "tr"
    owner_name: str = "Owner"
    owner_ids: list = field(default_factory=list)
    household: list = field(default_factory=list)
    owner_target: str = ""
    family_target: str = ""
    send_profile: str = ""
    autoeject_printer_preset: str = ""
    standard_printer_preset: str = ""
    process_presets: dict = field(default_factory=dict)
    filament_presets: dict = field(default_factory=dict)
    bed_type: str = "Textured PEI Plate"
    eject_cool_temp_c: float = 30.0
    watch_interval: str = "2m"
    local_is_owner: bool = True  # a local CLI/TUI/desktop session is the owner
    inject_context: str = "auto"  # auto | always | never (pre_llm_call context)

    # ---- derived helpers -------------------------------------------------------------------
    @property
    def link_base(self) -> str:
        return (self.public_url or self.bambuddy_url).rstrip("/")

    def people(self) -> list[Person]:
        out: list[Person] = []
        for oid in self.owner_ids or []:
            out.append(Person(id=str(oid), name=self.owner_name, role="owner"))
        for raw in self.household or []:
            if isinstance(raw, Mapping) and raw.get("name"):
                out.append(Person(id=str(raw.get("id", "")), name=str(raw["name"]),
                                  role=str(raw.get("role", "family")),
                                  address_as=str(raw.get("address_as", ""))))
        return out

    def person_for(self, sender_id: Optional[str]) -> Optional[Person]:
        """The household person with EXACTLY this id (after ``norm_id``), or None.

        ``LOCAL_SENDER`` is the owner when ``local_is_owner`` (and nobody otherwise); it never matches a configured id.
        """
        sid = norm_id(sender_id)
        if not sid:
            return None
        if sid == LOCAL_SENDER:
            return Person(id=LOCAL_SENDER, name=self.owner_name, role="owner") if self.local_is_owner else None
        for p in self.people():
            pid = norm_id(p.id)
            if pid and pid != LOCAL_SENDER and pid == sid:
                return p
        return None

    def is_owner(self, sender_id: Optional[str]) -> bool:
        p = self.person_for(sender_id)
        return bool(p and p.role == "owner")

    def to_snapshot(self) -> dict:
        return asdict(self)


_FIELD_NAMES = {f.name for f in fields(Settings)}


def _coerce(name: str, value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        if isinstance(default, bool):
            return value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
        if isinstance(default, int) and not isinstance(default, bool):
            return int(value)
        if isinstance(default, float):
            return float(value)
        if isinstance(default, list):
            if isinstance(value, str):
                value = json.loads(value) if value.strip().startswith("[") else [v.strip() for v in value.split(",") if v.strip()]
            return list(value)
        if isinstance(default, dict):
            if isinstance(value, str):
                value = json.loads(value) if value.strip() else {}
            return dict(value)
        return str(value)
    except (TypeError, ValueError):
        return default


def load_settings(ctx: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> Settings:
    """Resolve settings. ``ctx`` is a Hermes PluginContext (or None outside Hermes)."""
    base = Settings()
    values: dict[str, Any] = {}
    if ctx is None and overrides is None:
        snap = read_snapshot()
        if snap:
            values.update({k: v for k, v in snap.items() if k in _FIELD_NAMES})
    if ctx is not None and hasattr(ctx, "get_config"):
        for name in _FIELD_NAMES:
            try:
                v = ctx.get_config(name, None)
            except Exception:
                v = None
            if v is not None:
                values[name] = v
    if overrides:
        values.update({k: v for k, v in overrides.items() if k in _FIELD_NAMES})
    for name, raw in values.items():
        setattr(base, name, _coerce(name, raw, getattr(base, name)))
    if base.backend not in {"simulator", "bambuddy"}:
        base.backend = "simulator"
    if base.language not in {"tr", "en"}:
        base.language = "en"
    base.inject_context = str(base.inject_context or "").strip().lower()
    if base.inject_context not in INJECT_MODES:
        base.inject_context = "auto"
    return base


def get_api_key() -> str:
    """Bambuddy API key via the Hermes secret scope; '' when unset or outside Hermes."""
    try:
        from agent.secret_scope import get_secret  # type: ignore
    except Exception:
        return ""
    try:
        return get_secret(API_KEY_ENV, "") or ""
    except Exception:
        return ""


def data_dir() -> Path:
    """``<HERMES_HOME>/plugin-data/home-3d-workshop`` (or ``$HOME3D_DATA_DIR`` for tests/CI)."""
    override = os.environ.get("HOME3D_DATA_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    try:
        from plugins.plugin_storage import plugin_data_dir  # type: ignore

        return plugin_data_dir(PLUGIN_NAME)
    except Exception:
        home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
        p = home / "plugin-data" / PLUGIN_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p


def write_snapshot(settings: Settings) -> Path:
    path = data_dir() / SNAPSHOT_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings.to_snapshot(), ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


def read_snapshot() -> dict:
    path = data_dir() / SNAPSHOT_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
