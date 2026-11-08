"""Settings and data-dir resolution.

Settings come from (highest first): an explicit mapping (tests), the Hermes plugin settings (``ctx.get_config``),
then defaults. The zero-token watcher runs outside the agent (``load_settings()`` without a ctx): it reads the LIVE
plugin settings from ``<HERMES_HOME>/config.yaml`` (``plugins.entries.home-3d-workshop.settings``, the same place
``ctx.get_config`` reads) with whatever YAML parser the interpreter has (PyYAML, or ruamel.yaml, which Hermes 0.22.5
ships). Only when that cannot be read does it fall back to the non-secret
snapshot (``watcher-config.json`` in the data dir), which ``hermes home3d setup`` writes and every in-process
settings read rewrites when the settings changed (``sync_snapshot``). ``hermes home3d doctor`` warns when the two
differ. Secrets are only read through ``agent.secret_scope.get_secret`` (catalog rule 11).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping, Optional

from . import PLUGIN_NAME

SNAPSHOT_FILE = "watcher-config.json"
API_KEY_ENV = "HOME3D_BAMBUDDY_API_KEY"
# An explicit Hermes config.yaml for the live settings read ("" switches the live read off). Without it, a set
# HOME3D_DATA_DIR (tests, CI, the demo) also switches it off, so a test never reads the real profile's config.
CONFIG_ENV = "HOME3D_HERMES_CONFIG"
PLUGIN_DIR_NAME = Path(__file__).resolve().parents[1].name
WATCH_SCRIPT = "home3d_watch.py"
# where the watcher's settings came from (``load_watcher_settings``)
SOURCE_CONFIG, SOURCE_SNAPSHOT, SOURCE_DEFAULTS = "config.yaml", "snapshot", "defaults"
# The recorded "sender" of a local CLI/TUI/desktop session (no messaging identity). ``Settings.is_owner(LOCAL_SENDER)``
# is ``local_is_owner``. A messaging user whose id happens to be "local" is never recorded as this value (hooks.py).
LOCAL_SENDER = "local"
INJECT_MODES = ("auto", "always", "never")
# Hermes platforms whose user id the sender chooses freely (an IRC nick, an ntfy topic). A sender from there is
# recorded as "<platform>:<id>" (``scoped_sender``), so only a household entry written the same way ("irc:<nick>")
# matches it: a bare id (e.g. the owner's Slack or WhatsApp id) never makes an IRC user the owner.
USER_CHOSEN_ID_PLATFORMS = frozenset({"irc", "ntfy"})
HERMES_HOOK_TIMEOUT_S = 30.0  # Hermes 0.22.5's default plugins.hook_callback_timeout

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


def scoped_sender(sender_id: object, platform: object) -> str:
    """The sender id to record for a MESSAGING platform: ``"<platform>:<id>"`` on a platform whose ids the sender
    chooses (``USER_CHOSEN_ID_PLATFORMS``), else the raw id. A raw id from any other platform that already looks like
    such a scoped id (``"irc:..."``) is quarantined as ``"<platform>:<id>"`` so it can never pass for one."""
    raw = str(sender_id if sender_id is not None else "").strip()
    plat = str(getattr(platform, "value", platform) or "").strip().lower()
    if not raw:
        return ""
    if plat in USER_CHOSEN_ID_PLATFORMS:
        return f"{plat}:{raw}"
    low = raw.lower()
    if any(low.startswith(p + ":") for p in USER_CHOSEN_ID_PLATFORMS):
        return f"{plat or 'unknown'}:{raw}"
    return raw


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
    language: str = "en"  # English first; a Turkish household sets "tr"
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


def _values_from(raw: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    return {k: v for k, v in (raw or {}).items() if k in _FIELD_NAMES}


def load_settings(ctx: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> Settings:
    """Resolve settings. ``ctx`` is a Hermes PluginContext (or None outside Hermes).

    Without ``ctx`` and ``overrides`` (the cron watcher, ``hermes home3d`` outside Hermes) the live
    ``config.yaml`` plugin settings are used, else the snapshot (``load_watcher_settings``)."""
    if ctx is None and overrides is None:
        return load_watcher_settings()[0]
    values: dict[str, Any] = {}
    if ctx is not None and hasattr(ctx, "get_config"):
        for name in _FIELD_NAMES:
            try:
                v = ctx.get_config(name, None)
            except Exception:
                v = None
            if v is not None:
                values[name] = v
    if overrides:
        values.update(_values_from(overrides))
    return _build(values)


def _build(values: Mapping[str, Any]) -> Settings:
    base = Settings()
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


def load_watcher_settings() -> tuple[Settings, str]:
    """``(settings, source)`` as the zero-token watcher sees them. ``source`` names where they came from:
    ``"config.yaml (<parser>)"`` (the live plugin settings), ``"snapshot (<why>)"`` or ``"defaults (<why>)"``."""
    live, why = read_live_settings()
    if live is not None:
        return _build(_values_from(live)), f"{SOURCE_CONFIG} ({why})"
    snap = read_snapshot()
    if snap:
        return _build(_values_from(snap)), f"{SOURCE_SNAPSHOT} ({why})"
    return _build({}), f"{SOURCE_DEFAULTS} ({why}; no snapshot either)"


# ---- the live Hermes config.yaml (what ctx.get_config reads) ---------------------------------------------------
def hermes_home() -> Path:
    """The Hermes profile home (``hermes_constants.get_hermes_home`` inside Hermes, else ``$HERMES_HOME`` or
    ``~/.hermes``)."""
    try:
        from hermes_constants import get_hermes_home  # type: ignore

        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes").expanduser()


def watch_script_path() -> Path:
    """Where ``hermes home3d setup`` installs the cron watcher script."""
    return hermes_home() / "scripts" / WATCH_SCRIPT


def live_config_path() -> Optional[Path]:
    """The ``config.yaml`` the live settings are read from; None when the live read is switched off."""
    if CONFIG_ENV in os.environ:
        explicit = os.environ.get(CONFIG_ENV, "").strip()
        return Path(explicit).expanduser() if explicit else None
    if os.environ.get("HOME3D_DATA_DIR"):
        return None  # tests / CI / the demo: never the real profile's settings
    return hermes_home() / "config.yaml"


def _yaml_load(text: str) -> tuple[Any, str]:
    """(parsed document, parser name). Raises LookupError when no YAML parser is importable. PyYAML first, then
    ruamel.yaml (what Hermes 0.22.5 itself ships), read as YAML 1.1 like Hermes reads its config (yes/no booleans)."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text), "PyYAML"
    except ImportError:
        pass
    try:
        from ruamel.yaml import YAML  # type: ignore
    except ImportError:
        raise LookupError("no YAML library") from None
    loader = YAML(typ="safe", pure=True)
    loader.version = (1, 1)
    return loader.load(text), "ruamel.yaml"


def plugin_entry(config: Any) -> Optional[Mapping]:
    """``plugins.entries.<key>`` of this plugin: the manifest name, or ``<category>/<dir>`` for a plugin installed one
    level down in ``<HERMES_HOME>/plugins`` (Hermes' ``manifest_key``)."""
    plugins = config.get("plugins") if isinstance(config, Mapping) else None
    entries = plugins.get("entries") if isinstance(plugins, Mapping) else None
    if not isinstance(entries, Mapping):
        return None
    entry = entries.get(PLUGIN_NAME)
    if isinstance(entry, Mapping):
        return entry
    for key, value in entries.items():
        if isinstance(value, Mapping) and str(key).count("/") == 1 and \
                str(key).rsplit("/", 1)[1] in (PLUGIN_NAME, PLUGIN_DIR_NAME):
            return value
    return None


def read_live_settings() -> tuple[Optional[dict], str]:
    """``(plugin settings from config.yaml, how)``; ``(None, why not)`` when they cannot be read for sure.

    Like ``ctx.get_config``: ``settings`` wins, the legacy ``config`` subtree fills the rest. A config without an
    entry for this plugin is "unknown" (None), not "defaults": the snapshot is the safer guess then."""
    path = live_config_path()
    if path is None:
        return None, "live config read is off (HOME3D_DATA_DIR / HOME3D_HERMES_CONFIG)"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as e:
        return None, f"{path} not readable ({e.strerror or e})"
    try:
        data, parser = _yaml_load(text)
    except LookupError:
        return None, "no YAML library to read config.yaml"
    except Exception as e:
        return None, f"{path} is not valid YAML ({type(e).__name__})"
    entry = plugin_entry(data)
    if entry is None:
        return None, f"no plugins.entries.{PLUGIN_NAME} in {path}"
    out: dict[str, Any] = {}
    for sub in ("config", "settings"):
        raw = entry.get(sub)
        if isinstance(raw, Mapping):
            out.update({str(k): v for k, v in raw.items()})
    return out, parser


def hook_callback_timeout(read_config: bool = True) -> tuple[float, str]:
    """``(seconds, source)``: how long Hermes lets one hook callback run (``plugins.hook_callback_timeout``; 0 or
    less = no limit). Inside Hermes its own resolver (``hermes_cli.plugins._resolve_hook_callback_timeout``, looked
    up in ``sys.modules``, never imported); else, with ``read_config``, ``config.yaml``; else Hermes' default."""
    import sys

    mod = sys.modules.get("hermes_cli.plugins")
    fn = getattr(mod, "_resolve_hook_callback_timeout", None) if mod is not None else None
    if callable(fn):
        try:
            return float(fn()), "Hermes"
        except Exception:
            pass
    path = live_config_path() if read_config else None
    if path is not None:
        try:
            data, _ = _yaml_load(path.read_text(encoding="utf-8-sig"))
            plugins = data.get("plugins") if isinstance(data, Mapping) else None
            raw = plugins.get("hook_callback_timeout") if isinstance(plugins, Mapping) else None
            if raw is not None and not isinstance(raw, bool) and float(raw) >= 0:  # negative: Hermes' default
                return float(raw), "config.yaml"
        except Exception:
            pass
    return HERMES_HOOK_TIMEOUT_S, "default"


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
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def settings_hash(settings: Settings) -> str:
    return hashlib.sha256(json.dumps(settings.to_snapshot(), ensure_ascii=False, sort_keys=True,
                                     default=str).encode("utf-8")).hexdigest()


def sync_snapshot(settings: Settings) -> bool:
    """Rewrite the snapshot when it differs from ``settings``; True when it was written."""
    if read_snapshot() == json.loads(json.dumps(settings.to_snapshot(), ensure_ascii=False, default=str)):
        return False
    write_snapshot(settings)
    return True


def settings_diff(a: Settings, b: Settings) -> list[str]:
    """Names of the fields whose values differ (compared after a JSON round trip)."""
    da = json.loads(json.dumps(a.to_snapshot(), default=str))
    db = json.loads(json.dumps(b.to_snapshot(), default=str))
    return sorted(k for k in set(da) | set(db) if da.get(k) != db.get(k))
