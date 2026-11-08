#!/usr/bin/env python3
"""home-3d-workshop zero-token watcher: one pass per Hermes cron tick (``--no-agent --script``).

``hermes home3d setup`` copies this file to ``$HERMES_HOME/scripts/home3d_watch.py`` with PLUGIN_DIR
baked in. No model calls: it reads the printer, sends owner/family notices through ``hermes send`` and
prints nothing on success when an owner target is configured (empty stdout = silent cron run).

The watcher reads the LIVE plugin settings from this profile's ``config.yaml`` (the snapshot in the data dir is
only the fallback): the installed copy points ``HERMES_HOME`` at the profile it lives in when the environment does
not name one.

The installed copy only runs while Hermes would load the plugin. When the plugin is switched off
(``plugins.disabled`` lists it, or ``plugins.enabled`` in ``config.yaml`` does not) or removed (its directory
is gone), a leftover cron job prints nothing and exits 0: it neither messages the family nor raises a cron
alert on every tick. ``hermes home3d teardown`` removes the job and this script. A plugin directory that is
there but does not load is a broken install: that exits 1, so cron reports it.
"""

import importlib
import importlib.util
import os
import re
import sys
from pathlib import Path

PLUGIN_DIR = "__PLUGIN_DIR__"  # replaced at setup time
PACKAGE = "home3d_ws"
PLUGIN_NAME = "home-3d-workshop"
ACTIVE, DISABLED, REMOVED, UNKNOWN = "active", "disabled", "removed", "unknown"


def _installed() -> bool:
    """True for the copy ``setup`` installed (PLUGIN_DIR baked in), False for the template run from the repo."""
    return bool(PLUGIN_DIR) and not PLUGIN_DIR.startswith("__")


def _plugin_dir() -> Path:
    override = os.environ.get("HOME3D_PLUGIN_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if _installed():
        return Path(PLUGIN_DIR).expanduser()
    return Path(__file__).resolve().parents[1]  # running the template from the repo itself


def _hermes_home() -> Path:
    """The profile home that owns this job: cron runs ``<HERMES_HOME>/scripts/<script>`` of that profile."""
    here = Path(__file__).resolve().parent
    if here.name == "scripts":
        return here.parent
    env = os.environ.get("HERMES_HOME", "").strip()
    return Path(env).expanduser() if env else Path.home() / ".hermes"


# ---- is the plugin switched on? (Hermes' rule: listed in plugins.enabled and not in plugins.disabled) ------------
def _unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.strip()


def _flow_list(value: str) -> list:
    if not value.endswith("]"):
        raise ValueError("multi-line flow list")
    return [_unquote(v) for v in value[1:-1].split(",") if _unquote(v)]


def parse_plugin_lists(text: str):
    """``(enabled, disabled)`` from the ``plugins:`` block of a Hermes ``config.yaml``, without a YAML library.

    ``enabled`` is None when the key is missing or not a list (Hermes then loads no user plugin). Handles the block
    style Hermes writes (``enabled:`` then ``- name`` lines, indented or not) and one-line flow lists (``[a, b]``);
    raises ValueError on anything else it cannot read for sure (flow mappings, anchors, multi-line lists)."""
    in_plugins, child_indent, key = False, None, None
    found: dict = {}
    for raw in text.splitlines():
        line = re.sub(r"\s+#.*$", "", raw.rstrip("\r\n")).rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            head, _, rest = stripped.partition(":")
            in_plugins, child_indent, key = head.strip() == "plugins", None, None
            if in_plugins and rest.strip() and rest.strip() not in ("{}", "null", "~"):
                raise ValueError("inline plugins mapping")
            continue
        if not in_plugins:
            continue
        if stripped.startswith("-") and key is not None and indent >= (child_indent or 0):
            item = _unquote(stripped[1:])
            if item:
                found[key].append(item)
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", stripped)
        if not m:
            continue
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue
        name, rest = m.group(1), m.group(2).strip()
        key = None
        if name not in ("enabled", "disabled"):
            continue
        if rest[:1] in ("&", "*", "!", "{", "|", ">"):
            raise ValueError(f"unsupported YAML in plugins.{name}")
        if rest.startswith("["):
            found[name] = _flow_list(rest)
        elif rest == "":
            found[name], key = [], name
        else:
            found[name] = None  # null or a scalar: not a list
    enabled = found["enabled"] if isinstance(found.get("enabled"), list) else None
    disabled = found["disabled"] if isinstance(found.get("disabled"), list) else []
    return enabled, disabled


def _yaml_load(text: str):
    """A real YAML parser when the interpreter has one (optional: PyYAML, or ruamel.yaml as in Hermes' own venv)."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        pass
    try:
        from ruamel.yaml import YAML  # type: ignore

        return YAML(typ="safe", pure=True).load(text)
    except ImportError:
        raise LookupError("no YAML library") from None


def _plugin_lists(config: Path):
    text = config.read_text(encoding="utf-8-sig")
    try:
        data = _yaml_load(text) or {}
    except LookupError:
        return parse_plugin_lists(text)
    plugins = data.get("plugins") if isinstance(data, dict) else None
    plugins = plugins if isinstance(plugins, dict) else {}
    enabled, disabled = plugins.get("enabled"), plugins.get("disabled")
    return ([str(x) for x in enabled] if isinstance(enabled, list) else None,
            [str(x) for x in disabled] if isinstance(disabled, list) else [])


def _plugin_keys(plugin_dir: Path, home: Path) -> set:
    """Names Hermes matches against plugins.enabled/disabled: the manifest name, plus ``<category>/<dir>`` for a
    plugin installed one level down in ``<HERMES_HOME>/plugins``."""
    names = set()
    try:
        text = (plugin_dir / "plugin.yaml").read_text(encoding="utf-8-sig")
        m = re.search(r"(?m)^name:\s*[\"']?([^\"'\s#]+)", text)
        names.add(m.group(1) if m else PLUGIN_NAME)
    except OSError:
        names.add(PLUGIN_NAME)
    try:
        rel = plugin_dir.resolve().relative_to((home / "plugins").resolve())
        if len(rel.parts) == 2:
            names.add("/".join(rel.parts))
    except (OSError, ValueError):
        pass
    return names


def plugin_state(plugin_dir: Path, home: Path) -> str:
    """ACTIVE | DISABLED | REMOVED | UNKNOWN (config unreadable: keep watching, the watcher only reads the printer)."""
    if not (plugin_dir / "plugin.yaml").is_file():
        return REMOVED
    config = home / "config.yaml"
    if not config.is_file():
        return DISABLED  # no plugins.enabled at all: Hermes loads no user plugin
    try:
        enabled, disabled = _plugin_lists(config)
    except Exception:
        return UNKNOWN
    names = _plugin_keys(plugin_dir, home)
    if names & {str(x) for x in disabled}:
        return DISABLED
    if enabled is None or not names & {str(x) for x in enabled}:
        return DISABLED
    return ACTIVE


# ---- run ---------------------------------------------------------------------------------------------------------
def _load(plugin_dir: Path):
    if PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(PACKAGE, plugin_dir / "__init__.py",
                                                      submodule_search_locations=[str(plugin_dir)])
        if spec is None or spec.loader is None:
            raise ImportError(f"no plugin at {plugin_dir}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[PACKAGE] = mod
        spec.loader.exec_module(mod)
    return importlib.import_module(f"{PACKAGE}.home3d.watcher")


def main() -> int:
    plugin_dir = _plugin_dir()
    if _installed() and plugin_state(plugin_dir, _hermes_home()) in (DISABLED, REMOVED):
        return 0  # switched off or removed: stay silent (hermes home3d teardown removes this job)
    if _installed() and not os.environ.get("HERMES_HOME", "").strip():
        os.environ["HERMES_HOME"] = str(_hermes_home())  # the live settings: <this profile>/config.yaml
    try:
        watcher = _load(plugin_dir)
    except Exception as exc:  # a broken install must not stay silent: non-zero exit -> cron alert
        print(f"home3d watcher: cannot load the plugin from {plugin_dir}: {exc}", file=sys.stderr)
        return 1
    return int(watcher.main(sys.argv[1:]) or 0)


if __name__ == "__main__":
    sys.exit(main())
