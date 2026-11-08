#!/usr/bin/env python3
"""home-3d-workshop zero-token watcher: one pass per Hermes cron tick (``--no-agent --script``).

``hermes home3d setup`` copies this file to ``$HERMES_HOME/scripts/home3d_watch.py`` with PLUGIN_DIR
baked in. No model calls: it reads the printer, sends owner/family notices through ``hermes send`` and
prints nothing on success when an owner target is configured (empty stdout = silent cron run).
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path

PLUGIN_DIR = "__PLUGIN_DIR__"  # replaced at setup time
PACKAGE = "home3d_ws"


def _plugin_dir() -> Path:
    override = os.environ.get("HOME3D_PLUGIN_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if PLUGIN_DIR and not PLUGIN_DIR.startswith("__"):
        return Path(PLUGIN_DIR).expanduser()
    return Path(__file__).resolve().parents[1]  # running the template from the repo itself


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
    try:
        watcher = _load(plugin_dir)
    except Exception as exc:  # a broken install must not stay silent: non-zero exit -> cron alert
        print(f"home3d watcher: cannot load the plugin from {plugin_dir}: {exc}", file=sys.stderr)
        return 1
    return int(watcher.main(sys.argv[1:]) or 0)


if __name__ == "__main__":
    sys.exit(main())
