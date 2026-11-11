"""``hermes home3d ...`` terminal commands.

  setup     write the watcher settings snapshot, install the cron script, create the zero-token cron job
  teardown  remove what setup created: the home3d-watch cron job(s) and the installed watcher script
  watch     run the watcher in the foreground (``--once`` = one pass) and print the events
  status    printer, queue, plate and watcher state
  doctor    configuration, connectivity, presets (auto-eject marker), targets, watcher
  simulate  drive the simulated printer: scenario <name> | advance <min> | clear | reset | status
  demo      scripted end-to-end run on the simulator (no hardware, nothing is sent): the judge path.
            English by default (``--lang tr`` for the Turkish household); scripted stand-ins are marked [staged]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .backends.base import ACTIVE_STATES, PAUSE, PREPARE, RUNNING, BackendError

PLUGIN_DIR = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "home3d_watch.py"
CRON_NAME = "home3d-watch"
_PLACEHOLDER = '"__PLUGIN_DIR__"'

_SUBCOMMAND_HELP = (
    ("setup", "Install the zero-token watcher (cron --no-agent script)"),
    ("teardown", "Remove the watcher cron job(s) and script that setup installed"),
    ("watch", "Run the watcher in the foreground and print events"),
    ("status", "Printer, queue, plate and watcher state"),
    ("doctor", "Check configuration, connectivity, presets and targets"),
    ("simulate", "Drive the simulated printer (scenario/advance/clear/reset/status)"),
    ("demo", "Scripted end-to-end run on the simulator (no hardware, nothing sent)"),
)
_SUBCOMMAND_HELP_TR = {
    "setup": "Sıfır-token izleyiciyi kur (cron --no-agent betiği)",
    "teardown": "setup'ın kurduğu izleyici cron işini ve betiği kaldır",
    "watch": "İzleyiciyi ön planda çalıştır, olayları yaz",
    "status": "Yazıcı, kuyruk, tabla ve izleyici durumu",
    "doctor": "Ayarları, bağlantıyı, ön ayarları ve hedefleri kontrol et",
    "simulate": "Benzetilmiş yazıcıyı sür (scenario/advance/clear/reset/status)",
    "demo": "Benzetilmiş yazıcıda baştan sona senaryo (donanım yok, hiçbir şey gönderilmez)",
}


def cli_help(lang: str = "en") -> str:
    """``hermes home3d`` without a subcommand: one line per subcommand, in ``lang``, then the demo hint."""
    tr = lang == "tr"
    width = max(len(n) for n, _h in _SUBCOMMAND_HELP)
    lines = ["kullanım: hermes home3d <komut>" if tr else "usage: hermes home3d <command>", ""]
    lines += [f"  {n:<{width}}  {_SUBCOMMAND_HELP_TR.get(n, h) if tr else h}" for n, h in _SUBCOMMAND_HELP]
    lines += ["", "Donanımsız dene: hermes home3d demo" if tr else "Try it without hardware: hermes home3d demo"]
    return "\n".join(lines)


SCENARIOS = ("ok", "fail", "pause_hms", "eject_miss", "busy", "offline", "dispatch_fail")


# ---- argparse --------------------------------------------------------------------------------------------
def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Build the ``hermes home3d`` argparse tree."""
    subs = subparser.add_subparsers(dest="home3d_command")
    p = {name: subs.add_parser(name, help=help_, description=help_) for name, help_ in _SUBCOMMAND_HELP}
    p["setup"].add_argument("--interval", default=None, help="watcher interval, e.g. 2m (default: watch_interval)")
    p["setup"].add_argument("--print-only", action="store_true", help="print the cron command instead of running it")
    p["setup"].add_argument("--deliver", default="local",
                            help="cron delivery for the script output (default: local; the watcher sends itself)")
    p["setup"].add_argument("--force", action="store_true", help="create the cron job even if one exists")
    p["teardown"].add_argument("--print-only", action="store_true",
                               help="print what would be removed (and the commands) without changing anything")
    p["watch"].add_argument("--once", action="store_true", help="one pass, then exit")
    p["watch"].add_argument("--dry-run", action="store_true", help="never send; only write the outbox")
    p["watch"].add_argument("--every", type=float, default=60.0, help="seconds between passes (default 60)")
    p["status"].add_argument("--json", action="store_true", help="raw home3d_status JSON")
    p["doctor"].add_argument("--plate", action="store_true",
                             help="also run a camera plate check (may switch the chamber light)")
    sim = p["simulate"].add_subparsers(dest="sim_command")
    sc = sim.add_parser("scenario", help="next/current job behaviour")
    sc.add_argument("name", choices=SCENARIOS)
    adv = sim.add_parser("advance", help="move simulated time forward")
    adv.add_argument("minutes", type=float)
    adv.add_argument("--watch", action="store_true", help="run one watcher pass (dry run) afterwards")
    sim.add_parser("clear", help="a person takes the part off the plate")
    sim.add_parser("reset", help="fresh simulated printer")
    sim.add_parser("status", help="simulated printer status")
    p["demo"].add_argument("--lang", choices=("tr", "en"), default="en",
                           help="message language: en (default) or tr (the Turkish household version)")
    p["demo"].add_argument("--keep", action="store_true", help="keep the demo data dir (photos, outbox, db)")
    p["demo"].add_argument("--data-dir", default=None, help="use this data dir instead of a temporary one")
    subparser.set_defaults(func=handle)


def handle(args: argparse.Namespace, rt=None) -> int:
    sub = getattr(args, "home3d_command", None)
    if rt is None:
        from .runtime import Runtime

        rt = Runtime(None)  # outside Hermes: the live config.yaml settings, else the watcher snapshot, else defaults
    if not sub:
        try:
            lang = rt.settings.language
        except Exception:
            lang = "en"
        print(cli_help(lang))
        return 2
    try:
        return int(_DISPATCH[sub](rt, args) or 0)
    except KeyboardInterrupt:
        return 130
    except BackendError as e:
        print(f"home3d: {e}")
        return 1


# ---- setup --------------------------------------------------------------------------------------------
def hermes_home() -> Path:
    from .config import hermes_home as _home

    return _home()


def install_watch_script(home: Optional[Path] = None, plugin_dir: Path = PLUGIN_DIR) -> Path:
    """Copy ``scripts/home3d_watch.py`` to ``<HERMES_HOME>/scripts/`` with PLUGIN_DIR baked in."""
    template = (plugin_dir / "scripts" / SCRIPT_NAME).read_text(encoding="utf-8")
    if template.count(_PLACEHOLDER) != 1:
        raise RuntimeError(f"{SCRIPT_NAME}: expected one {_PLACEHOLDER} placeholder")
    dest_dir = (home or hermes_home()) / "scripts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / SCRIPT_NAME
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(template.replace(_PLACEHOLDER, repr(str(Path(plugin_dir).resolve()))), encoding="utf-8")
    tmp.chmod(0o755)
    tmp.replace(dest)
    return dest


def cron_schedule(interval: str) -> str:
    """'2m' -> 'every 2m' (Hermes also reads '2m' as recurring; being explicit is clearer)."""
    iv = (interval or "2m").strip()
    return f"every {iv}" if re.fullmatch(r"\d+\s*[smhd]", iv) else iv


def cron_command(interval: str, deliver: str = "local", binary: str = "hermes") -> list[str]:
    return [binary, "cron", "create", cron_schedule(interval), "--name", CRON_NAME, "--no-agent",
            "--script", SCRIPT_NAME, "--deliver", deliver or "local"]


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_CRON_HEAD = re.compile(r"^ {1,4}([A-Za-z0-9_-]{4,64}) \[[^\]]+\]\s*$")
_CRON_ROW = re.compile(r"^\s+(Name|Script):\s*(.*?)\s*$")


def parse_cron_list(text: str) -> list[dict]:
    """``hermes cron list [--all]`` output -> ``[{"id", "name", "script"}]``.

    v0.22.5 prints one block per job: an ``  <id> [state]`` line, then indented ``Label: value`` rows (``Name:``,
    ``Script:``, ...). Colour codes are stripped; anything else (banner, warnings) is ignored."""
    jobs: list[dict] = []
    cur: Optional[dict] = None
    for raw in _ANSI.sub("", text or "").splitlines():
        head = _CRON_HEAD.match(raw)
        if head:
            cur = {"id": head.group(1), "name": "", "script": ""}
            jobs.append(cur)
            continue
        row = _CRON_ROW.match(raw) if cur is not None else None
        if row:
            cur[row.group(1).lower()] = row.group(2)  # type: ignore[index]
    return jobs


def watcher_cron_jobs(text: str) -> list[dict]:
    """The jobs ``setup`` creates: named ``home3d-watch`` or running the ``home3d_watch.py`` script."""
    return [j for j in parse_cron_list(text)
            if j["name"] == CRON_NAME or (j["script"] and Path(j["script"]).name == SCRIPT_NAME)]


def _cron_list(binary: str, all_jobs: bool = True) -> Optional[str]:
    """stdout of ``hermes cron list [--all]`` (``--all``: disabled and completed jobs too), or None when it could
    not run."""
    cmd = [binary, "cron", "list"] + (["--all"] if all_jobs else [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                              env={**os.environ, "NO_COLOR": "1"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (proc.stdout or "") if proc.returncode == 0 else None


def _existing_cron(binary: str) -> bool:
    """A live (active or paused) watcher job exists already."""
    out = _cron_list(binary, all_jobs=False) or ""
    return bool(watcher_cron_jobs(out)) or CRON_NAME in out


def _cmd_setup(rt, args) -> int:
    from .config import write_snapshot
    from .notify import hermes_bin

    s = rt.settings
    dry = bool(args.print_only)  # --print-only writes nothing: no snapshot, no script, no cron job
    if dry:
        print("settings snapshot : would be written to the data dir (fallback only)")
    else:
        print(f"settings snapshot : {write_snapshot(s)} (fallback only)")
    try:
        from .config import load_watcher_settings

        print(f"watcher settings  : {load_watcher_settings()[1]}")
    except Exception:
        pass
    if dry:
        print(f"watcher script    : would be installed at {hermes_home() / 'scripts' / SCRIPT_NAME}")
    else:
        print(f"watcher script    : {install_watch_script()}")
    if s.backend == "simulator":
        print("note              : backend is 'simulator' (the watcher watches the simulated printer)")
    if not s.owner_target:
        print("note              : owner_target is empty: owner notices only reach the cron output (--deliver)")
    binary = hermes_bin()
    cmd = cron_command(args.interval or s.watch_interval or "2m", args.deliver, binary or "hermes")
    if args.print_only or not binary:
        print("create the cron job with:" if args.print_only else "hermes binary not found; create the job yourself:")
        print("  " + shlex.join(cmd))
        return 0 if args.print_only else 1
    if _existing_cron(binary) and not args.force:
        print(f"cron job '{CRON_NAME}' already exists (hermes cron list); --force creates another one")
        return 0
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    out = (proc.stdout or proc.stderr or "").strip()
    if out:
        print(out)
    if proc.returncode == 0:
        print("note              : the job runs while the Hermes scheduler runs (`hermes gateway`); check with "
              "hermes home3d doctor")
        print("undo with         : hermes home3d teardown")
    return 0 if proc.returncode == 0 else 1


def _cmd_teardown(rt, args) -> int:
    """Undo ``setup``: remove the ``home3d-watch`` cron job(s), then the installed script. The data dir (photos,
    outbox, database) and the plugin itself stay; ``hermes plugins disable|remove`` is Hermes' own job."""
    from .config import data_dir
    from .notify import hermes_bin

    script = hermes_home() / "scripts" / SCRIPT_NAME
    binary = hermes_bin()
    failed = False
    if not binary:
        print("hermes binary not found: remove the job yourself (hermes cron list, then hermes cron remove <id>)")
        failed = True
    else:
        listing = _cron_list(binary)
        if listing is None:
            print("could not run 'hermes cron list --all': remove the job yourself (hermes cron remove <id>)")
            failed = True
        else:
            jobs = watcher_cron_jobs(listing)
            if not jobs:
                print(f"cron job          : none ('{CRON_NAME}' is not in hermes cron list --all)")
            for job in jobs:
                cmd = [binary, "cron", "remove", job["id"]]
                label = job["name"] or job["script"]
                if args.print_only:
                    print(f"would remove job  : {job['id']} ({label}): {shlex.join(cmd)}")
                    continue
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
                    ok, detail = proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()
                except (OSError, subprocess.TimeoutExpired) as e:
                    ok, detail = False, str(e)
                if ok:
                    print(f"cron job          : removed {job['id']} ({label})")
                else:
                    failed = True
                    last = detail.splitlines()[-1] if detail else "no output"
                    print(f"cron job          : could not remove {job['id']} ({label}): {last}")
    if script.exists() or script.is_symlink():
        if args.print_only:
            print(f"would remove      : {script}")
        elif failed:
            # a job that still points at a missing script fails on every tick: keep it until the job is gone
            print(f"watcher script    : kept {script} (remove the cron job first, then run teardown again)")
        else:
            script.unlink()
            print(f"watcher script    : removed {script}")
    else:
        print(f"watcher script    : not installed ({script})")
    tmp = script.with_suffix(".tmp")
    if tmp.exists() and not args.print_only:
        tmp.unlink()
    try:
        print(f"kept              : data dir {data_dir()} (photos, outbox, database); delete it yourself if you want")
    except OSError:
        pass
    print("plugin            : still installed; switch it off with: hermes plugins disable home-3d-workshop")
    return 1 if failed else 0


# ---- watch / status -----------------------------------------------------------------------------------
def _indent(text: str, pad: str = "     ") -> str:
    return "\n".join(pad + line for line in str(text).splitlines())


def _print_results(results: list[dict], out: Callable[[str], None] = print, persona: str = "",
                   owner: str = "") -> None:
    """Watcher notices as sent: the persona's technical note to the owner and its plain one to the family. With a
    ``persona`` (the demo) the lines name who speaks to whom and photos are shown by file name only."""
    to_owner = f"{persona} → {owner or 'owner'} (owner chat)" if persona else "owner"
    to_family = f"{persona} → family group" if persona else "family"

    def photo(path: Any) -> str:
        return f"\n     [photo] {Path(str(path)).name if persona else path}" if path else ""

    for r in results:
        out(f"  📣 watcher: {r.get('kind')}" + (f" · {r['job']}" if r.get("job") else ""))
        if r.get("owner_text"):
            out(f"   {to_owner}:\n" + _indent(r["owner_text"]) + photo(r.get("owner_media")))
        if r.get("family_text"):
            out(f"   {to_family}:\n" + _indent(r["family_text"]) + photo(r.get("family_media")))


def _cmd_watch(rt, args) -> int:
    from . import watcher

    while True:
        results = watcher.run_once(rt.settings, rt.backend, rt.store, deliver=not args.dry_run)
        stamp = time.strftime("%H:%M:%S")
        if results:
            print(f"[{stamp}] {len(results)} event(s)")
            _print_results(results)
        elif args.once:
            w = rt.store.kv_get(watcher.KV_KEY) or {}
            print(f"[{stamp}] no events (printer {w.get('state', '?')})")
        if args.once:
            return 0
        time.sleep(max(5.0, float(args.every)))


def _cmd_status(rt, args) -> int:
    from .commands import format_status, make_command

    data = make_command(rt).command.tool("home3d_status", {})
    print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else format_status(data, rt.settings.language))
    return 0 if data.get("ok", True) else 1


# ---- doctor -------------------------------------------------------------------------------------------
def _cmd_doctor(rt, args) -> int:
    from .config import data_dir
    from .notify import hermes_bin

    rows: list[tuple[str, str, str]] = []

    def add(level: str, label: str, detail: str = "") -> None:
        rows.append((level, label, detail))

    s = rt.settings
    add("ok", "backend", s.backend + (f" ({s.bambuddy_url}, printer {s.printer_id})" if s.backend == "bambuddy" else ""))
    add("ok", "persona", f"{s.persona_name} · language {s.language}")
    local = getattr(s, "local_is_owner", True)
    add("ok" if s.owner_ids or local else "FAIL", "owner_ids",
        f"{len(s.owner_ids)} id(s), compared exactly (check with /home3d whoami)" if s.owner_ids else
        ("empty: nobody can approve from a chat (only a local CLI/TUI session)" if local
         else "empty and local_is_owner is off: nobody can approve anything"))
    add("ok", "local sessions", "count as the owner (local_is_owner)" if local
        else "are not the owner (local_is_owner: false)")
    add("ok", "inject_context", str(getattr(s, "inject_context", "auto")))
    add("ok" if s.household else "warn", "household",
        f"{len(s.household)} person(s)" if s.household else "empty: family members are not recognised by name")
    add("ok" if s.owner_target else "warn", "owner_target", s.owner_target or "empty: owner notices stay in the outbox")
    add("ok" if s.family_target else "warn", "family_target",
        s.family_target or "empty: family notices stay in the outbox")
    try:
        d = data_dir()
        probe = d / ".doctor"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        add("ok", "data dir", str(d))
    except OSError as e:
        add("FAIL", "data dir", str(e))
    _doctor_watcher_settings(s, add)
    _doctor_hook_timeout(add)
    binary = hermes_bin()
    add("ok" if binary else "warn", "hermes binary", binary or "not found: notifications cannot be sent")

    try:
        be = rt.backend
        st = be.status()
        add("ok" if st.connected and st.state != "OFFLINE" else "FAIL", "printer",
            f"{st.state}" + (f" · {st.job_name}" if st.job_name else "") + (f" · {st.printer_name}" if st.printer_name else ""))
        if st.blocking_hms:
            add("warn", "HMS", ", ".join(h.code for h in st.blocking_hms))
        add("ok", "queue", f"{len(be.queue())} active item(s)")
    except BackendError as e:
        be = None
        add("FAIL", "printer", str(e))
    if be is not None:
        _doctor_presets(rt, be, add)
        _doctor_plate_clear_setting(rt, be, add)
        if args.plate:
            try:
                p = be.check_plate()
                add("ok" if p.is_empty else "warn", "plate check",
                    f"empty={p.is_empty} diff={p.difference_pct} {p.message}".strip())
            except BackendError as e:
                add("warn", "plate check", str(e))

    _doctor_watcher(rt, binary, add)
    _doctor_openscad(add)
    from .plugin import SKILLS

    for i, (name, path, _desc) in enumerate(SKILLS):
        add("ok" if path.is_file() else "FAIL", "skill" if i == 0 else f"skill {name}", str(path))

    width = max(len(r[1]) for r in rows)
    for level, label, detail in rows:
        print(f"[{level:>4}] {label:<{width}}  {detail}")
    fails = sum(1 for r in rows if r[0] == "FAIL")
    print("ready." if not fails else f"{fails} problem(s) to fix.")
    return 1 if fails else 0


OPENSCAD_MISSING = "not found: the agent cannot design new parts (install openscad, and xvfb for previews)"


def _doctor_openscad(add) -> None:
    """OpenSCAD for home3d_design (and the two templates); previews need a display or xvfb-run."""
    from . import design

    try:
        st = design.openscad_status()
    except Exception as e:  # doctor never dies on a probe
        add("warn", "openscad", f"cannot check: {e}")
        return
    if not st["openscad"]:
        add("warn", "openscad", OPENSCAD_MISSING)
        return
    version = st["version"] or "unknown version"
    if st["previews"]:
        how = " (xvfb-run)" if design._needs_xvfb() else ""
        add("ok", "openscad", f"{version} · {st['openscad']} · previews on{how}")
    else:
        add("warn", "openscad", f"{version} · previews off: install xvfb (xvfb-run) so the agent can look at its "
                                "designs")


SCHEDULER_DOWN = ("installed, but the Hermes scheduler is not running: start `hermes gateway` "
                  "(check `hermes cron status`)")


def _doctor_watcher(rt, binary: Optional[str], add) -> None:
    """The cron job, the script and the last pass. A job (or script) without any pass means no scheduler runs it."""
    script = hermes_home() / "scripts" / SCRIPT_NAME
    jobs: Optional[list[dict]] = None
    if binary:
        listing = _cron_list(binary, all_jobs=False)
        jobs = watcher_cron_jobs(listing) if listing is not None else None
    if jobs is None:
        add("warn", "cron job", "unknown (hermes cron list did not run)" if binary else "unknown (no hermes binary)")
    elif not jobs:
        add("warn", "cron job", f"none named {CRON_NAME}: hermes home3d setup")
    elif len(jobs) > 1:
        add("warn", "cron job", f"{len(jobs)} watcher jobs ({', '.join(j['id'] for j in jobs)}): remove the extra "
                                "one with hermes cron remove <id>")
    else:
        add("ok", "cron job", f"{jobs[0]['id']} ({jobs[0]['name'] or jobs[0]['script']})")
    add("ok" if script.is_file() else "warn", "cron script", str(script) if script.is_file() else "not installed")
    installed = bool(jobs) or (jobs is None and script.is_file())
    w = rt.store.kv_get("watcher") or {}
    upd = w.get("updated") if isinstance(w, dict) else None
    if isinstance(upd, (int, float)):
        age = time.time() - upd
        from .hooks import watcher_stale_s

        if age < watcher_stale_s(rt.settings):
            add("ok", "watcher", f"last pass {round(age / 60)} min ago")
        else:
            add("warn", "watcher", f"last pass {round(age / 60)} min ago: "
                + ("is the Hermes scheduler running? start `hermes gateway` (check `hermes cron status`)"
                   if installed else "hermes home3d setup"))
    else:
        add("warn", "watcher", SCHEDULER_DOWN if installed else "never ran: hermes home3d setup")


def _doctor_watcher_settings(s, add) -> None:
    """What the cron watcher will read (the live config.yaml, else the snapshot) against these settings, and whether
    the fallback snapshot is stale."""
    from .config import SOURCE_CONFIG, load_settings, load_watcher_settings, read_snapshot, settings_diff

    try:
        view, source = load_watcher_settings()
    except Exception as e:
        add("warn", "watcher settings", f"could not resolve them: {type(e).__name__}: {e}")
        return
    diff = settings_diff(view, s)
    live_read = source.startswith(SOURCE_CONFIG)
    if diff:
        add("warn", "watcher settings",
            f"the watcher reads {source}, which differs from these settings in {', '.join(diff[:8])}"
            + ("" if live_read else ": run `hermes home3d setup` inside Hermes to rewrite the snapshot"))
    else:
        add("ok", "watcher settings", f"the watcher reads {source}")
    snap = read_snapshot()
    if snap and live_read:  # (when the watcher reads the snapshot itself, the row above already compared it)
        stale = settings_diff(load_settings(overrides=snap), s)
        if stale:
            add("warn", "settings snapshot", f"differs from the live settings in {', '.join(stale[:8])} (only the "
                                             "fallback; it is rewritten on the next settings read inside Hermes)")


HOOK_TIMEOUT_MIN_S = 15.0  # below this Hermes hook timeout the printer gate before a start gets under 6 s


def _doctor_hook_timeout(add) -> None:
    """Hermes' ``plugins.hook_callback_timeout``: the printer gate in ``pre_tool_call`` gets 0.4 of it when it is
    below 30 s, so a low value makes starts fail on a slow printer manager (a block, never an unsafe start)."""
    from .config import hook_callback_timeout
    from .hooks import deadline_for

    try:
        limit, source = hook_callback_timeout()
    except Exception as e:
        add("warn", "hook timeout", f"could not read plugins.hook_callback_timeout: {type(e).__name__}: {e}")
        return
    gate = f"{deadline_for(limit):.3g}"
    if limit <= 0:
        add("ok", "hook timeout", f"plugins.hook_callback_timeout is off (no limit); the printer gate stops "
                                  f"after {gate} s")
    elif limit < HOOK_TIMEOUT_MIN_S:
        add("warn", "hook timeout", f"plugins.hook_callback_timeout is {limit:g} s ({source}): the printer check "
                                    f"before a start gets only {gate} s and may block starts; set it to "
                                    f"{HOOK_TIMEOUT_MIN_S:g} s or more (default 30)")
    else:
        add("ok", "hook timeout", f"{limit:g} s ({source}); the printer gate stops after {gate} s")


def _doctor_plate_clear_setting(rt, be, add) -> None:
    """Bambuddy's ``require_plate_clear``: off, its queue manager may start a queued auto-start item on a FINISH
    printer before the watcher's camera check (with auto-eject: on top of a part the push missed)."""
    fn = getattr(be, "settings", None)
    if not callable(fn):
        return
    try:
        d = fn() or {}
    except BackendError as e:
        add("warn", "require plate clear", f"Bambuddy settings not readable: {e}")
        return
    if not isinstance(d, dict) or "require_plate_clear" not in d:
        if getattr(be, "name", "") != "simulator":
            add("warn", "require plate clear", "unknown (not in the Bambuddy settings)")
        return
    s = rt.settings
    eject = bool(str(s.autoeject_printer_preset or "").strip()) or getattr(be, "name", "") == "simulator"
    if d.get("require_plate_clear") is True:
        add("ok", "require plate clear", "on: queued jobs wait until the plate is marked clear")
    elif eject:
        add("warn", "require plate clear", "off: Bambuddy may auto-start a queued auto-start item on a finished "
                                           "printer before the camera check: turn on 'Require plate clear'")
    else:
        add("ok", "require plate clear", "off (no auto-eject preset; turning it on is still safer)")


def _doctor_presets(rt, be, add) -> None:
    s = rt.settings
    if getattr(be, "name", "") == "simulator":
        add("ok", "auto-eject preset", s.autoeject_printer_preset or "sim-autoeject (built into the simulator)")
        return
    presets_fn = getattr(be, "presets", None)
    known: set[str] = set()
    if callable(presets_fn):
        try:
            tiers = presets_fn() or {}
            for tier in tiers.values():
                for items in (tier or {}).values():
                    known.update(str(p.get("id")) for p in items or [] if isinstance(p, dict))
            add("ok", "presets", f"{len(known)} slicer preset(s) visible")
        except BackendError as e:
            add("warn", "presets", str(e))
    marker_fn = getattr(be, "preset_has_eject_marker", None)
    for label, pid, want in (("auto-eject preset", s.autoeject_printer_preset, True),
                             ("standard preset", s.standard_printer_preset, False)):
        if not pid:
            add("warn" if want else "ok", label, "not set" + (": parts are never pushed off" if want else ""))
            continue
        if known and str(pid) not in known:
            add("FAIL", label, f"{pid} not found in Bambuddy presets")
            continue
        has = None
        if callable(marker_fn):
            try:
                has = marker_fn(str(pid))
            except BackendError as e:
                add("warn", label, f"{pid}: {e}")
                continue
        if has is None:
            add("warn", label, f"{pid}: eject marker unknown")
        elif has == want:
            add("ok", label, f"{pid}: " + ("has the AUTO-EJECT end block" if want else "no eject block"))
        else:
            add("FAIL", label, f"{pid}: " + ("no HOME3D/HERMES AUTO-EJECT marker in its end G-code" if want
                                             else "contains the AUTO-EJECT block (parts would be pushed)"))
    for q, name in sorted((s.process_presets or {}).items()):
        if known and str(name) not in known and not str(name).endswith("@BBL A1"):
            add("warn", f"process {q}", f"{name}: not a known preset id")


# ---- simulate -----------------------------------------------------------------------------------------
def _status_line(st) -> str:
    bits = [st.state]
    if st.job_name:
        bits.append(f"\"{st.job_name}\"")
    if st.state in ACTIVE_STATES:
        bits.append(f"{st.progress:.0f}%")
        if st.layer and st.total_layers:
            bits.append(f"layer {st.layer}/{st.total_layers}")
        if st.remaining_min is not None:
            bits.append(f"{st.remaining_min} min left")
    if st.bed_temp is not None:
        bits.append(f"bed {st.bed_temp:.0f}°C")
    if st.blocking_hms:
        bits.append("HMS " + ",".join(h.code for h in st.blocking_hms))
    return " · ".join(bits)


def _cmd_simulate(rt, args) -> int:
    if rt.settings.backend != "simulator":
        print("home3d simulate only works with backend: simulator (current: bambuddy)")
        return 2
    be = rt.backend
    sub = getattr(args, "sim_command", None)
    if sub == "scenario":
        be.set_scenario(args.name)
        print(f"scenario: {args.name}")
    elif sub == "advance":
        st = be.advance(float(args.minutes))
        print(f"+{args.minutes:g} min → {_status_line(st)}")
        if args.watch:
            from . import watcher

            _print_results(watcher.run_once(rt.settings, be, rt.store, deliver=False))
        return 0
    elif sub == "clear":
        be.human_clears_plate()
        print("plate cleared by a person")
    elif sub == "reset":
        be.reset()
        print("simulator reset")
    elif sub != "status":
        print("usage: hermes home3d simulate {scenario,advance,clear,reset,status}")
        return 2
    print(_status_line(be.status()))
    return 0


# ---- demo ---------------------------------------------------------------------------------------------
DEMO_OWNER, DEMO_MUM, DEMO_DAD = "owner@demo", "mum@demo", "dad@demo"
_DEMO_ENV = ("HOME3D_DATA_DIR", "HOME3D_SIM_SPEED", "HOME3D_DRY_RUN")
STAGED = "[staged]"
DEMO_LEGEND = (f"{STAGED} marks scripted stand-ins: what people say and do, the model's chat replies, the web search "
               "and approval taps. Everything else is the plugin's own code (hooks, tools, safety gates, watcher, "
               "messages) driving a simulated printer.")
DEMO_OWNER_NAME = "Sam"  # the demo's owner when the configured owner_name is the default "Owner"
# (English, Turkish) display names and how the persona addresses them
DEMO_PEOPLE = {DEMO_MUM: (("Mum", "Mum"), ("Annem", "Anneciğim")),
               DEMO_DAD: (("Dad", "Dad"), ("Babam", "Babacığım"))}
# (English, Turkish) lines of the script. Turkish is the household language of the original install.
_LINES = {
    "mum_voice": ("{p}, can you print me a little gift box for flowers?",
                  "{p}, bana çiçekler için küçük bir hediye kutusu basabilir misin?"),
    "mum_options": ("Mum, I found two (pictures below):\n1) {a}, about {ta}\n2) {b}, about {tb}\nWhich one?",
                    "Anneciğim, iki tane buldum (resimler aşağıda):\n1) çiçek kutusu, yaklaşık {ta}\n"
                    "2) saksı, yaklaşık {tb}\nHangisi olsun?"),
    "mum_pick": ("The first one, the white box.", "İlki olsun, beyaz kutu."),
    "mum_start": ("Lovely, print it please!", "Çok güzel, bas lütfen!"),
    "mum_waiting": ("It's in the queue (#{q}). I've passed it on to {o}: {o} decides when it starts.",
                    "Sıraya ekledim (#{q}). {o_dat} ilettim, ne zaman başlayacağına o karar verecek."),
    "dad_ask": ("Could you print me a coaster? Our mugs are wide, make it 11 cm.",
                "Bana bir bardak altlığı basar mısın? Kupalarımız geniş, 11 cm olsun."),
    "dad_ready": ("Dad, it's {w0} cm as designed; I made it {w} cm. About {t}, {g} g of black. It's in the queue "
                  "after the flower box (#{q}).",
                  "Babacığım, aslı {w0} cm; {w} cm yaptım. Yaklaşık {t}, {g} g siyah. Çiçek kutusundan sonra "
                  "sırada (#{q})."),
    "owner_start": ("start #{q}", "#{q} başlat"),
    "owner_resume": ("resume the coaster", "altlığa devam et"),
    "mum_clip": ("Could you print a cable clip for my charger?", "Şarj kablom için bir kablo klipsi basar mısın?"),
    "owner_again": ("print the clip again", "klipsi tekrar bas"),
    "owner_accept": ("accept upgrade {u}", "{u} numaralı öneriyi kabul et"),
}


def _l(key: str, tr: bool, **kw: Any) -> str:
    return _LINES[key][1 if tr else 0].format(**kw)


def _dur(minutes: Any, tr: bool) -> str:
    try:
        m = int(round(float(minutes)))
    except (TypeError, ValueError):
        return "?"
    h, m = divmod(m, 60)
    if tr:
        return f"{h} saat {m} dakika" if h else f"{m} dakika"
    return f"{h} h {m} min" if h else f"{m} min"


class _Source:
    """What the gateway passes to a slash command (``SessionSource``), reduced to what /home3d reads."""

    def __init__(self, user_id: str, platform: str = "whatsapp"):
        self.user_id, self.platform, self.chat_id = user_id, platform, "<group>@g.us"


class _Demo:
    """Drives the real hooks, tools, /home3d command and watcher the way Hermes would, on the simulator."""

    def __init__(self, lang: str, persona: str, owner_name: str, out: Callable[[str], None]):
        from .backends.simulator import SimulatorBackend
        from .commands import make_command
        from .config import Settings
        from .hooks import make_hooks
        from .runtime import Runtime
        from .store import Store
        from .tools import build_tools

        self.out, self.lang, self.tr = out, lang, lang == "tr"
        (mum, mum_addr), (dad, dad_addr) = (DEMO_PEOPLE[DEMO_MUM][1 if self.tr else 0],
                                            DEMO_PEOPLE[DEMO_DAD][1 if self.tr else 0])
        self.mum, self.dad = mum, dad
        self.settings = Settings(
            backend="simulator", persona_name=persona, language=lang, owner_name=owner_name,
            owner_ids=[DEMO_OWNER],
            household=[{"id": DEMO_MUM, "name": mum, "address_as": mum_addr},
                       {"id": DEMO_DAD, "name": dad, "address_as": dad_addr}],
            owner_target="whatsapp:<owner-chat>@g.us", family_target="whatsapp:<family-group>@g.us",
            eject_cool_temp_c=30.0)
        self.be = SimulatorBackend()
        self.be.reset()
        self.store = Store()
        self.rt = Runtime(None, settings=self.settings, store=self.store, backend=self.be)
        self.tools = {n: h for n, _schema, h in build_tools(self.rt)}
        self.hooks = make_hooks(self.rt)
        self.cmd = make_command(self.rt)
        self.events: list[dict] = []
        self.milestones: list[str] = []
        self.blocked: list[str] = []
        self.n = 0
        self._seen_context: dict[str, set] = {}
        self.names = {DEMO_OWNER: owner_name, DEMO_MUM: mum, DEMO_DAD: dad}

    # -- output --
    def step(self, title: str) -> None:
        self.n += 1
        self.out(f"\n── {self.n}. {title} " + "─" * max(3, 70 - len(title)))

    def say(self, text: str) -> None:
        self.out(text)

    def staged(self, text: str) -> None:
        self.say(f"  🎬 {STAGED} {text}")

    def mark(self, name: str) -> None:
        if name not in self.milestones:
            self.milestones.append(name)

    def reply(self, to: str, text: str) -> None:
        """The persona's chat reply. The model writes these in real use, so they are staged here."""
        self.say(f"  🤖 {self.settings.persona_name} → {to} {STAGED}:\n" + _indent(text, "     "))

    def results(self, res: list[dict]) -> None:
        _print_results(res, self.say, persona=self.settings.persona_name, owner=self.settings.owner_name)

    # -- Hermes emulation --
    def user_turn(self, session: str, sender: str, text: str, first: bool = True, voice: bool = False) -> None:
        who = self.names.get(sender, sender)
        self.say(f"  {'🎙️' if voice else '💬'} {who}{' (voice note, transcribed by the gateway)' if voice else ''}"
                 f" {STAGED}: {text}")
        r = self.hooks["pre_llm_call"](session_id=session, user_message=text, platform="whatsapp",
                                       sender_id=sender, is_first_turn=first)
        ctx = (r or {}).get("context") or ""
        seen = self._seen_context.setdefault(session, set())
        new = [ln for ln in ctx.splitlines() if ln.strip() and ln not in seen]
        seen.update(new)
        if new:
            self.say("  pre_llm_call context (new lines):\n" + _indent("\n".join(new), "   │ "))

    def call(self, name: str, args: dict, session: str) -> dict:
        """What model_tools does: pre_tool_call -> (Hermes approval prompt) -> handler -> post_tool_call."""
        d = self.hooks["pre_tool_call"](tool_name=name, args=args, task_id="demo", session_id=session,
                                        tool_call_id=f"demo-{self.n}", turn_id="demo")
        if d and d.get("action") == "block":
            self.hooks["post_tool_call"](tool_name=name, args=args, result=json.dumps({"error": d["message"]}),
                                         session_id=session, status="blocked")
            self.blocked.append(name)
            self.say(f"  ⛔ {name} blocked by pre_tool_call (real gate):\n" + _indent(d["message"], "     "))
            return {"ok": False, "blocked": True, "error": d["message"]}
        if d and d.get("action") == "approve":
            self.say(f"  🔐 Hermes asks {self.settings.owner_name} to approve: {d['message']}\n"
                     f"     {STAGED} {self.settings.owner_name} taps 'approve once' (the demo approves by itself)")
        raw = self.tools[name](args, session_id=session, task_id="demo")
        self.hooks["post_tool_call"](tool_name=name, args=args, result=raw, session_id=session)
        try:
            res = json.loads(raw)
        except ValueError:
            return {"ok": False, "error": raw}
        if res.get("blocked"):
            self.say(f"  ⛔ {name} refused by the tool:\n" + _indent(res.get("message") or res.get("error", ""), "     "))
        return res

    def slash(self, text: str, user_id: Optional[str], session: str) -> str:
        who = self.names.get(user_id or "", user_id) if user_id else f"{self.settings.owner_name} (local CLI)"
        self.say(f"  ⌨️  {who} {STAGED}: {text}")
        reply = self.cmd(text.replace("/home3d", "", 1).strip(),
                         source=_Source(user_id) if user_id else None, session_id=session, platform="whatsapp")
        self.say(_indent(reply, "     "))
        return reply

    def watch(self) -> list[dict]:
        from . import watcher

        res = watcher.run_once(self.settings, self.be, self.store, deliver=False)
        self.events += res
        self.results(res)
        return res

    def advance(self, minutes: float) -> list[dict]:
        st = self.be.advance(minutes)
        self.say(f"  ⏩ +{minutes:g} min → {_status_line(st)}")
        return self.watch()

    def print_job(self, until_pause: bool = False, stop_at_end_gcode: bool = False):
        """Advance through the running job in a few big steps: warm-up, half way, the last minute (the watcher takes
        the "done" photo there), the end G-code (with auto-eject the bed cools and the part is pushed off while the
        printer still says RUNNING at 100 %), the end. Stops early at a pause, or at the end G-code when asked."""
        for _ in range(24):
            st = self.be.status()
            if st.state not in ACTIVE_STATES or (until_pause and st.state == PAUSE):
                return st
            end_gcode = st.state == RUNNING and (st.progress or 0) >= 99.95
            if end_gcode and stop_at_end_gcode:
                return st
            rem = st.remaining_min if st.remaining_min is not None else 10
            if st.state == PREPARE:
                m = 3
            elif end_gcode:
                m = 5
            elif rem > 30 and (st.progress or 0) < 45:
                m = max(1, rem // 2)
            elif rem > 2:
                m = rem - 1
            else:
                m = rem + 1
            self.advance(m)
        return self.be.status()

    def kinds(self, since: int = 0) -> list[str]:
        return [r["kind"] for r in self.events[since:]]

    def after_finish(self, until: set[str], steps: tuple = (5, 5, 5, 5, 5, 10, 15, 15, 30),
                     since: Optional[int] = None) -> list[str]:
        """Simulated minutes after the end of a print (the end G-code, FINISH, the camera checks) until one of
        ``until`` was announced since event index ``since`` (default: now). Returns the kinds since then."""
        start = len(self.events) if since is None else since
        for m in steps:
            if until & set(self.kinds(start)):
                break
            self.advance(m)
        return self.kinds(start)

    def quietly(self, fn: Callable[[], Any]) -> Any:
        """Run ``fn`` without printing its steps (the condensed fast-forward)."""
        out, self.out = self.out, (lambda _text: None)
        try:
            return fn()
        finally:
            self.out = out

    def miss_round(self) -> tuple[Any, list[str]]:
        """Dad asks for another coaster, the owner starts it, the push misses, a person takes it off."""
        tr = self.tr
        imp = self.call("home3d_import", {"model_id": 1440007, "request_text": "bardak altlığı" if tr else "coaster"},
                        "demo-dad")
        sl = self.call("home3d_slice", {"library_file_id": imp.get("library_file_id"), "material": "PLA",
                                        "colour": "black", "request_id": imp.get("request_id")}, "demo-dad")
        q = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl.get("sliced_file_id"),
                                       "request_id": imp.get("request_id")}, "demo-dad")
        qid = q.get("queue_item_id")
        if not self.call("home3d_start", {"queue_item_id": qid}, "demo-owner").get("ok"):
            return qid, ["start blocked"]
        since = len(self.events)
        self.print_job()
        self.after_finish({"plate_not_clear", "eject_unverified"}, since=since)
        self.be.human_clears_plate()
        self.after_finish({"plate_clear"}, steps=(15, 15, 30, 60))
        return qid, self.kinds(since)

    # -- the script --
    def run(self) -> None:
        tr, persona, owner = self.tr, self.settings.persona_name, self.settings.owner_name
        mum, dad = self.mum, self.dad
        self.step("Baseline watcher pass (silent: it only records the printer state)")
        self.watch()

        # ---- request -> find -> import -> slice -> queue ----
        self.step("Mum sends a voice note")
        self.user_turn("demo-mum", DEMO_MUM, _l("mum_voice", tr, p=persona), voice=True)
        self.mark("request")

        self.step("The agent looks for ready models (web search → home3d_find_models)")
        self.staged("canned web search: the demo hands over two fixed MakerWorld links; the simulator makes up "
                    "the model cards (likes, times)")
        found = self.call("home3d_find_models", {"urls": ["https://makerworld.com/en/models/1440000",
                                                          "https://makerworld.com/en/models/1440004"]}, "demo-mum")
        cards = found.get("cards") or []
        for c in cards:
            prof = (c.get("a1_profiles") or [{}])[0]
            self.say(f"  🖼️  {c['title']} · {c['license']} · ♥{c.get('likes')} · A1 profile {prof.get('profile_id')}"
                     f" · ~{prof.get('print_time_min')} min · {prof.get('weight_g')} g")
        if len(cards) >= 2:
            self.mark("find")
            t = [_dur((c.get("a1_profiles") or [{}])[0].get("print_time_min"), tr) for c in cards[:2]]
            self.reply(mum, _l("mum_options", tr, a=cards[0]["title"], b=cards[1]["title"], ta=t[0], tb=t[1]))

        self.step("Mum picks the first one → home3d_import (records who asked, and that it was a voice note)")
        self.user_turn("demo-mum", DEMO_MUM, _l("mum_pick", tr), first=False)
        imp = self.call("home3d_import", {"model_id": 1440000, "request_text": "çiçek kutusu" if tr else "flower box",
                                          "channel": "voice"}, "demo-mum")
        self.say(f"  library file {imp.get('library_file_id')} · request #{imp.get('request_id')} · "
                 f"requester {imp.get('requester')!r}")
        if imp.get("ok"):
            self.mark("import")

        self.step("home3d_slice (auto-eject only when the part is safe to push off)")
        sl = self.call("home3d_slice", {"library_file_id": imp.get("library_file_id"), "quality": "standard",
                                        "material": "PLA", "colour": "white", "request_id": imp.get("request_id")},
                       "demo-mum")
        ej = sl.get("eject") or {}
        self.say(f"  sliced file {sl.get('sliced_file_id')} · {sl.get('print_time_min')} min · {sl.get('grams')} g · "
                 f"auto-eject {'planned' if ej.get('planned') else 'off'} ({'; '.join(ej.get('reasons') or [])})")
        if sl.get("warnings"):
            self.say("  warnings: " + "; ".join(sl["warnings"]))
        if sl.get("ok"):
            self.mark("slice")

        self.step("home3d_queue add (always manual start: nothing starts by itself)")
        q1 = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl.get("sliced_file_id"),
                                        "request_id": imp.get("request_id")}, "demo-mum")
        qid1 = q1.get("queue_item_id")
        self.say(f"  queue item #{qid1} · AMS {q1.get('ams_mapping')} · eject planned {q1.get('eject_planned')}")
        if q1.get("ok"):
            self.mark("queue")

        # ---- who may start ----
        self.step("Mum says \"print it\": her chat may not start a print (her ask becomes a request to the owner)")
        self.user_turn("demo-mum", DEMO_MUM, _l("mum_start", tr), first=False)
        blocked = self.call("home3d_start", {"queue_item_id": qid1}, "demo-mum")
        if blocked.get("blocked"):
            self.mark("non_owner_blocked")
            self.reply(mum, _l("mum_waiting", tr, q=qid1, o=owner, o_dat=_dative(owner)))

        self.step("The next watcher pass tells the owner, with the exact command")
        self.watch()
        asked = self.store.latest_approval_request("start", qid1, mum) or {}
        if asked.get("announced_ts") is not None:  # told once (on its own or inside the "next job ready" note)
            self.mark("owner_told_request")

        self.step("The owner approves with a slash command (no model call; it runs right away, nothing is stored)")
        reply = self.slash(f"/home3d approve start {qid1}", DEMO_OWNER, "demo-owner-chat")
        if reply.startswith("▶️"):
            self.mark("owner_approved_start")
        self.watch()

        # ---- customise ----
        self.step("Meanwhile Dad wants a bigger coaster → home3d_customize scales the model")
        self.user_turn("demo-dad", DEMO_DAD, _l("dad_ask", tr))
        imp2 = self.call("home3d_import", {"model_id": 1440007, "request_text": "bardak altlığı" if tr else "coaster"},
                         "demo-dad")
        cus = self.call("home3d_customize", {"library_file_id": imp2.get("library_file_id"), "target_size_mm": 110,
                                             "request_id": imp2.get("request_id")}, "demo-dad")
        size0 = " × ".join(f"{v:g}" for v in cus.get("size_before_mm") or [])
        size1 = " × ".join(f"{v:g}" for v in cus.get("size_mm") or [])
        self.say(f"  {imp2.get('name')} {size0} mm → {cus.get('name')} {size1} mm (×{cus.get('factor')}) · "
                 f"library file {cus.get('library_file_id')}")
        if cus.get("ok"):
            self.mark("customize")
        sl2 = self.call("home3d_slice", {"library_file_id": cus.get("library_file_id") or imp2.get("library_file_id"),
                                         "material": "PLA", "colour": "black", "request_id": imp2.get("request_id")},
                        "demo-dad")
        q2 = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl2.get("sliced_file_id"),
                                        "request_id": imp2.get("request_id")}, "demo-dad")
        qid2 = q2.get("queue_item_id")
        self.say(f"  sliced {sl2.get('sliced_file_id')} · {sl2.get('print_time_min')} min · {sl2.get('grams')} g · "
                 f"auto-eject {'planned' if (sl2.get('eject') or {}).get('planned') else 'off'} · queue #{qid2}")

        def cm(mm: Any) -> str:
            return f"{float(mm) / 10:.3g}".replace(".", "," if tr else ".")

        self.reply(dad, _l("dad_ready", tr, w0=cm((cus.get("size_before_mm") or [95])[0]),
                           w=cm((cus.get("size_mm") or [110])[0]),
                           t=_dur(sl2.get("print_time_min"), tr), g=f"{float(sl2.get('grams') or 0):.0f}", q=qid2))

        # ---- the happy path ----
        self.step("Mum's print runs; the zero-token watcher reports (simulated time)")
        since = len(self.events)
        self.print_job(stop_at_end_gcode=True)

        self.step("End G-code: the bed cools and the part is pushed off while the printer still says RUNNING; "
                  "at FINISH the camera looks at the plate")
        seen = self.after_finish({"ready_next", "plate_not_clear", "eject_unverified"}, since=since)
        if {"finished", "finished_ejected"} & set(seen):
            self.mark("finished")
        if "finished_ejected" in seen:
            self.mark("auto_eject_camera_ok")
        if "ready_next" in seen:
            self.mark("ready_next")

        # ---- filament runs out ----
        self.step("Filament run-out: the owner starts the coaster from his own chat")
        self.be.set_scenario("pause_hms")
        self.staged("simulator scenario pause_hms: the black spool runs out at 30 %")
        self.user_turn("demo-owner", DEMO_OWNER, _l("owner_start", tr, q=qid2))
        st2 = self.call("home3d_start", {"queue_item_id": qid2}, "demo-owner")
        self.say(f"  start → ok={st2.get('ok')} · {st2.get('name')} for {st2.get('requester')}")
        if st2.get("ok"):
            self.mark("owner_session_start")
        self.watch()
        st = self.print_job(until_pause=True)
        if st.state == PAUSE and "paused" in self.kinds():
            self.mark("paused")

        self.step("Resuming with a printer error active needs the owner to acknowledge it")
        self.user_turn("demo-owner", DEMO_OWNER, _l("owner_resume", tr), first=False)
        r = self.call("home3d_stop", {"action": "resume", "reason": "owner asked"}, "demo-owner")
        if r.get("blocked"):
            self.mark("resume_blocked_hms")
        self.staged("Dad loads a new spool")
        reply = self.slash("/home3d approve resume ack", DEMO_OWNER, "demo-owner-chat")
        if reply.startswith("▶️"):
            self.mark("resumed")
        self.be.set_scenario("eject_miss")
        self.staged("simulator scenario eject_miss: this time the push will not move the part")
        since = len(self.events)
        self.print_job()
        seen = self.after_finish({"plate_not_clear", "eject_unverified"}, since=since)
        if "plate_not_clear" in seen and self.store.human_needed(kind="remove_part"):
            self.mark("human_needed_logged")

        self.step("The owner looks at what needed a person (and at upgrade proposals)")
        self.slash("/home3d moments", DEMO_OWNER, "demo-owner-chat")
        self.slash("/home3d upgrades", DEMO_OWNER, "demo-owner-chat")

        self.step("Dad takes the coaster off; the watcher sees an empty plate")
        self.staged("Dad takes the coaster off the plate")
        self.be.human_clears_plate()
        seen = self.after_finish({"plate_clear"}, steps=(15, 15, 30, 60))
        if "plate_clear" in seen:
            self.mark("plate_clear_again")

        # ---- a failed print ----
        self.step("A failed print: Mum's cable clip comes loose")
        self.be.set_scenario("fail")
        self.staged("simulator scenario fail: the clip comes loose at 40 %")
        self.user_turn("demo-mum", DEMO_MUM, _l("mum_clip", tr), first=False)
        imp3 = self.call("home3d_import", {"model_id": 1440001, "request_text": "kablo klipsi" if tr else "cable clip"},
                         "demo-mum")
        sl3 = self.call("home3d_slice", {"library_file_id": imp3.get("library_file_id"), "material": "PLA",
                                         "colour": "white", "request_id": imp3.get("request_id")}, "demo-mum")
        q3 = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl3.get("sliced_file_id"),
                                        "request_id": imp3.get("request_id")}, "demo-mum")
        qid3 = q3.get("queue_item_id")
        self.say(f"  sliced {sl3.get('sliced_file_id')} · {sl3.get('print_time_min')} min · {sl3.get('grams')} g · "
                 f"auto-eject {'planned' if (sl3.get('eject') or {}).get('planned') else 'off'} · queue #{qid3}")
        self.slash(f"/home3d approve start {qid3}", DEMO_OWNER, "demo-owner-chat")
        self.print_job()
        if "failed" in self.kinds():
            self.mark("failed")

        self.step("After a failure nothing starts until a person has confirmed the plate")
        self.user_turn("demo-owner", DEMO_OWNER, _l("owner_again", tr), first=False)
        q4 = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl3.get("sliced_file_id"),
                                        "request_id": imp3.get("request_id")}, "demo-owner")
        qid4 = q4.get("queue_item_id")
        self.say(f"  queued again as #{qid4}")
        again = self.call("home3d_start", {"queue_item_id": qid4}, "demo-owner")
        if again.get("blocked"):
            self.mark("start_blocked_after_failure")
        self.staged(f"{owner} takes the loose clip off the plate")
        self.be.human_clears_plate()
        self.after_finish({"plate_clear"}, steps=(15, 15, 30, 60))
        reply = self.slash("/home3d approve clear", DEMO_OWNER, "demo-owner-chat")
        if reply.startswith("✅"):
            self.mark("plate_confirmed")
        self.be.set_scenario("eject_miss")
        self.staged("simulator scenario eject_miss: the small clip will not be pushed off either")
        reply = self.slash(f"/home3d approve start {qid4}", DEMO_OWNER, "demo-owner-chat")
        if reply.startswith("▶️"):
            self.mark("reprint_started")
        since = len(self.events)
        self.print_job()
        self.after_finish({"plate_not_clear", "eject_unverified"}, since=since)
        self.staged("Mum takes the clip off the plate")
        self.be.human_clears_plate()
        self.after_finish({"plate_clear"}, steps=(15, 15, 30, 60))

        # ---- self-upgrade ----
        from .notify import read_outbox

        self.step("Fast-forward: later that month another coaster stays on the plate (condensed)")
        self.staged("condensed: Dad asks for another coaster, the owner approves it, the push misses, Dad takes it "
                    "off (the same real calls as above, output hidden)")
        before = len(self.events)
        qid, _seen = self.quietly(self.miss_round)
        n = len(self.store.human_needed(kind="remove_part"))
        flow = [k for k in self.kinds(before) if k in (
            "finished", "finished_ejected", "plate_not_clear", "eject_unverified", "plate_clear", "upgrade_proposed")]
        self.say(f"  #{qid} Coaster: {' → '.join(flow) or 'nothing'} · remove_part moments: {n}")
        new = [r for r in self.events[before:] if r["kind"] == "upgrade_proposed"]
        if new:
            self.results(new)
            self.mark("upgrade_proposed")

        self.step("The owner reviews the proposal and accepts it (printing the parts is a normal job)")
        self.slash("/home3d upgrades", DEMO_OWNER, "demo-owner-chat")
        up = next((u for u in self.store.upgrades() if u.get("status") == "proposed"), None)
        if up:
            self.user_turn("demo-owner", DEMO_OWNER, _l("owner_accept", tr, u=up["id"]), first=False)
            acc = self.call("home3d_upgrades", {"action": "accept", "upgrade_id": up["id"]}, "demo-owner")
            self.say(f"  upgrade #{up['id']} → {acc.get('status')} · next: {acc.get('next')}")

        self.step("Outbox: what would have been sent (dry run; every message is shown above where it happened)")
        recs = read_outbox(limit=0)
        for rec in recs:
            media = " [+photo]" if rec.get("media") else ""
            first = (rec.get("text") or "").strip().splitlines()[0] if (rec.get("text") or "").strip() else ""
            self.say(f"  → {rec['audience']:<6}{media:<9} {first if len(first) <= 90 else first[:89] + '…'}")
        owners = sum(1 for r in recs if r["audience"] == "owner")
        self.say(f"  {len(recs)} messages: {owners} to the owner chat, {len(recs) - owners} to the family group")
        blocked = ", ".join(f"{k} ×{self.blocked.count(k)}" for k in dict.fromkeys(self.blocked))
        self.say(f"  blocked by the plugin's gates on the way: {blocked or 'nothing'}")


def _dative(name: str) -> str:
    from .messages import dative

    return dative(name)


DEMO_MILESTONES = ("request", "find", "import", "slice", "queue", "non_owner_blocked", "owner_told_request",
                   "owner_approved_start", "customize", "finished", "auto_eject_camera_ok", "ready_next",
                   "owner_session_start", "paused", "resume_blocked_hms", "resumed", "human_needed_logged",
                   "plate_clear_again", "failed", "start_blocked_after_failure", "plate_confirmed", "reprint_started",
                   "upgrade_proposed")


def run_demo(*, lang: str = "en", persona: str = "Mıstık", owner_name: str = DEMO_OWNER_NAME,
             data_dir: Optional[str] = None, keep: bool = False,
             out: Callable[[str], None] = print) -> dict:
    """Scripted simulator run of the whole loop. Returns {"ok", "milestones", "missing", "data_dir", "outbox",
    "events", "seconds"}. Deterministic: simulated time only moves through ``advance()``. The owner is called
    ``DEMO_OWNER_NAME`` unless a real name is given (the settings default "Owner" counts as none)."""
    t0 = time.monotonic()
    lang = lang if lang in ("tr", "en") else "en"
    owner_name = owner_name if owner_name and owner_name.strip() not in ("", "Owner") else DEMO_OWNER_NAME
    saved = {k: os.environ.get(k) for k in _DEMO_ENV}
    tmp = Path(data_dir).expanduser() if data_dir else Path(tempfile.mkdtemp(prefix="home3d-demo-"))
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ.update(HOME3D_DATA_DIR=str(tmp), HOME3D_SIM_SPEED="0", HOME3D_DRY_RUN="1")
    result: dict[str, Any] = {"ok": False, "milestones": [], "missing": list(DEMO_MILESTONES), "data_dir": str(tmp),
                              "outbox": [], "events": []}
    try:
        out(f"home-3d-workshop demo · persona {persona} · language {lang} · simulated printer · nothing is sent")
        out("(--lang tr runs the same demo in Turkish, the household language)" if lang == "en"
            else "(--lang en runs the same demo in English)")
        out(DEMO_LEGEND)
        out(f"data dir: {tmp}")
        demo = _Demo(lang, persona, owner_name, out)
        try:
            demo.run()
        finally:
            from .notify import read_outbox

            result["milestones"] = list(demo.milestones)
            result["missing"] = [m for m in DEMO_MILESTONES if m not in demo.milestones]
            result["outbox"] = read_outbox(limit=0)
            result["events"] = [e.get("kind") for e in demo.events]
        result["ok"] = not result["missing"]
        result["seconds"] = round(time.monotonic() - t0, 2)
        out("\n" + ("✅ demo complete: " if result["ok"] else "⚠️ demo incomplete: ")
            + " → ".join(result["milestones"])
            + (f"\n   missing: {', '.join(result['missing'])}" if result["missing"] else ""))
        if not keep and not data_dir:
            out("(temporary data removed; --keep keeps the photos, outbox and database)")
        return result
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if not keep and not data_dir:
            shutil.rmtree(tmp, ignore_errors=True)


def _cmd_demo(rt, args) -> int:
    s = rt.settings
    res = run_demo(lang=getattr(args, "lang", None) or "en", persona=s.persona_name or "Mıstık",
                   owner_name=s.owner_name or DEMO_OWNER_NAME, data_dir=args.data_dir, keep=args.keep)
    return 0 if res["ok"] else 1


_DISPATCH: dict[str, Callable[[Any, Any], int]] = {
    "setup": _cmd_setup, "teardown": _cmd_teardown, "watch": _cmd_watch, "status": _cmd_status,
    "doctor": _cmd_doctor, "simulate": _cmd_simulate, "demo": _cmd_demo,
}

__all__ = ["setup_parser", "handle", "run_demo", "install_watch_script", "cron_command", "hermes_home",
           "parse_cron_list", "watcher_cron_jobs", "DEMO_MILESTONES", "cli_help", "SCHEDULER_DOWN"]
