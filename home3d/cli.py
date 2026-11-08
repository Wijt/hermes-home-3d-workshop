"""``hermes home3d ...`` terminal commands.

  setup     write the watcher settings snapshot, install the cron script, create the zero-token cron job
  watch     run the watcher in the foreground (``--once`` = one pass) and print the events
  status    printer, queue, plate and watcher state
  doctor    configuration, connectivity, presets (auto-eject marker), targets, watcher
  simulate  drive the simulated printer: scenario <name> | advance <min> | clear | reset | status
  demo      scripted end-to-end run on the simulator (no hardware, nothing is sent): the judge path
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

from .backends.base import ACTIVE_STATES, PREPARE, BackendError

PLUGIN_DIR = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "home3d_watch.py"
CRON_NAME = "home3d-watch"
_PLACEHOLDER = '"__PLUGIN_DIR__"'

_SUBCOMMAND_HELP = (
    ("setup", "Install the zero-token watcher (cron --no-agent script)"),
    ("watch", "Run the watcher in the foreground and print events"),
    ("status", "Printer, queue, plate and watcher state"),
    ("doctor", "Check configuration, connectivity, presets and targets"),
    ("simulate", "Drive the simulated printer (scenario/advance/clear/reset/status)"),
    ("demo", "Scripted end-to-end run on the simulator (no hardware, nothing sent)"),
)
SCENARIOS = ("ok", "fail", "pause_hms", "eject_miss", "busy", "offline")


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
    p["demo"].add_argument("--lang", choices=("tr", "en"), default=None, help="message language (default: config)")
    p["demo"].add_argument("--keep", action="store_true", help="keep the demo data dir (photos, outbox, db)")
    p["demo"].add_argument("--data-dir", default=None, help="use this data dir instead of a temporary one")
    subparser.set_defaults(func=handle)


def handle(args: argparse.Namespace, rt=None) -> int:
    sub = getattr(args, "home3d_command", None)
    if not sub:
        print("usage: hermes home3d {" + ",".join(n for n, _ in _SUBCOMMAND_HELP) + "}")
        return 2
    if rt is None:
        from .runtime import Runtime

        rt = Runtime(None)  # outside Hermes: the watcher snapshot or defaults
    try:
        return int(_DISPATCH[sub](rt, args) or 0)
    except KeyboardInterrupt:
        return 130
    except BackendError as e:
        print(f"home3d: {e}")
        return 1


# ---- setup --------------------------------------------------------------------------------------------
def hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home  # type: ignore

        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes").expanduser()


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


def _existing_cron(binary: str) -> bool:
    try:
        proc = subprocess.run([binary, "cron", "list"], capture_output=True, text=True, timeout=60,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return CRON_NAME in (proc.stdout or "")


def _cmd_setup(rt, args) -> int:
    from .config import write_snapshot
    from .notify import hermes_bin

    s = rt.settings
    print(f"settings snapshot : {write_snapshot(s)}")
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
    return 0 if proc.returncode == 0 else 1


# ---- watch / status -----------------------------------------------------------------------------------
def _indent(text: str, pad: str = "     ") -> str:
    return "\n".join(pad + line for line in str(text).splitlines())


def _print_results(results: list[dict], out: Callable[[str], None] = print) -> None:
    for r in results:
        out(f"  📣 {r.get('kind')}" + (f" · {r['job']}" if r.get("job") else ""))
        if r.get("owner_text"):
            out("   owner :\n" + _indent(r["owner_text"]) + (f"\n     [photo] {r['owner_media']}"
                                                            if r.get("owner_media") else ""))
        if r.get("family_text"):
            out("   family:\n" + _indent(r["family_text"]))


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
    add("ok" if s.owner_ids else "warn", "owner_ids",
        f"{len(s.owner_ids)} id(s)" if s.owner_ids else "empty: nobody can approve from a chat (only local CLI/TUI)")
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
        if args.plate:
            try:
                p = be.check_plate()
                add("ok" if p.is_empty else "warn", "plate check",
                    f"empty={p.is_empty} diff={p.difference_pct} {p.message}".strip())
            except BackendError as e:
                add("warn", "plate check", str(e))

    w = rt.store.kv_get("watcher") or {}
    upd = w.get("updated") if isinstance(w, dict) else None
    if isinstance(upd, (int, float)):
        age = time.time() - upd
        add("ok" if age < 10 * 60 else "warn", "watcher", f"last pass {round(age / 60)} min ago")
    else:
        add("warn", "watcher", "never ran: hermes home3d setup")
    script = hermes_home() / "scripts" / SCRIPT_NAME
    add("ok" if script.is_file() else "warn", "cron script", str(script) if script.is_file() else "not installed")
    from .plugin import SKILL_PATH as skill

    add("ok" if skill.is_file() else "FAIL", "skill", str(skill))

    width = max(len(r[1]) for r in rows)
    for level, label, detail in rows:
        print(f"[{level:>4}] {label:<{width}}  {detail}")
    fails = sum(1 for r in rows if r[0] == "FAIL")
    print("ready." if not fails else f"{fails} problem(s) to fix.")
    return 1 if fails else 0


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


class _Source:
    """What the gateway passes to a slash command (``SessionSource``), reduced to what /home3d reads."""

    def __init__(self, user_id: str, platform: str = "whatsapp"):
        self.user_id, self.platform, self.chat_id = user_id, platform, "<group>@g.us"


class _Demo:
    def __init__(self, lang: str, persona: str, owner_name: str, out: Callable[[str], None]):
        from .backends.simulator import SimulatorBackend
        from .commands import make_command
        from .config import Settings
        from .hooks import make_hooks
        from .runtime import Runtime
        from .store import Store
        from .tools import build_tools

        self.out, self.lang, self.tr = out, lang, lang == "tr"
        self.settings = Settings(
            backend="simulator", persona_name=persona, language=lang, owner_name=owner_name,
            owner_ids=[DEMO_OWNER],
            household=[{"id": DEMO_MUM, "name": "Mum", "address_as": "Anneciğim" if self.tr else "Mum"},
                       {"id": DEMO_DAD, "name": "Dad", "address_as": "Babacığım" if self.tr else "Dad"}],
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
        self.n = 0

    # -- output --
    def step(self, title: str) -> None:
        self.n += 1
        self.out(f"\n── {self.n}. {title} " + "─" * max(3, 70 - len(title)))

    def say(self, text: str) -> None:
        self.out(text)

    def mark(self, name: str) -> None:
        if name not in self.milestones:
            self.milestones.append(name)

    # -- Hermes emulation --
    def user_turn(self, session: str, sender: str, text: str, first: bool = True) -> None:
        self.say(f"  💬 {text}")
        r = self.hooks["pre_llm_call"](session_id=session, user_message=text, platform="whatsapp",
                                       sender_id=sender, is_first_turn=first)
        if r and r.get("context"):
            self.say("  pre_llm_call context:\n" + _indent(r["context"], "   │ "))

    def call(self, name: str, args: dict, session: str) -> dict:
        """What model_tools does: pre_tool_call -> (approval) -> handler -> post_tool_call."""
        d = self.hooks["pre_tool_call"](tool_name=name, args=args, task_id="demo", session_id=session)
        if d and d.get("action") == "block":
            self.hooks["post_tool_call"](tool_name=name, args=args, result=json.dumps({"error": d["message"]}),
                                         session_id=session, status="blocked")
            self.say(f"  ⛔ {name} blocked by pre_tool_call:\n" + _indent(d["message"], "     "))
            return {"ok": False, "blocked": True, "error": d["message"]}
        if d and d.get("action") == "approve":
            self.say(f"  🔐 Hermes approval prompt: {d['message']}\n     → the owner taps 'approve once'")
        raw = self.tools[name](args, session_id=session, task_id="demo")
        self.hooks["post_tool_call"](tool_name=name, args=args, result=raw, session_id=session)
        try:
            return json.loads(raw)
        except ValueError:
            return {"ok": False, "error": raw}

    def slash(self, text: str, user_id: Optional[str], session: str) -> str:
        self.say(f"  ⌨️  {text}" + (f"   (from {user_id})" if user_id else "   (local CLI)"))
        reply = self.cmd(text.replace("/home3d", "", 1).strip(),
                         source=_Source(user_id) if user_id else None, session_id=session, platform="whatsapp")
        self.say(_indent(reply, "     "))
        return reply

    def watch(self) -> list[dict]:
        from . import watcher

        res = watcher.run_once(self.settings, self.be, self.store, deliver=False)
        self.events += res
        _print_results(res, self.say)
        return res

    def advance(self, minutes: float) -> list[dict]:
        st = self.be.advance(minutes)
        self.say(f"  ⏩ +{minutes:g} min → {_status_line(st)}")
        return self.watch()

    def print_job(self) -> None:
        """Advance until the running job ends: big steps, then stop just before the end for the done photo."""
        for _ in range(40):
            st = self.be.status()
            if st.state not in ACTIVE_STATES:
                return
            rem = st.remaining_min if st.remaining_min is not None else 10
            if st.state == PREPARE:
                m = 3
            elif rem > 4:
                m = max(1, min(rem - 2, max(10, rem // 2)))
            else:
                m = rem + 1
            self.advance(m)

    def after_finish(self, until: set[str], step_min: float = 5, max_steps: int = 30) -> list[str]:
        seen: list[str] = []
        for _ in range(max_steps):
            kinds = [r["kind"] for r in self.advance(step_min)]
            seen += kinds
            if until & set(seen):
                break
        return seen

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
        self.print_job()
        seen = self.after_finish({"plate_not_clear", "eject_unverified"})
        self.be.human_clears_plate()
        seen += self.after_finish({"plate_clear"}, max_steps=6)
        return qid, seen

    # -- the script --
    def run(self) -> None:
        tr, persona = self.tr, self.settings.persona_name
        self.step("Baseline watcher pass (silent: it only records the printer state)")
        self.watch()

        self.step("Mum sends a voice note (transcribed by the Hermes gateway)")
        self.user_turn("demo-mum", DEMO_MUM,
                       f"{persona}, bana çiçekler için küçük bir hediye kutusu basabilir misin?" if tr
                       else f"{persona}, can you print me a little gift box for flowers?")
        self.mark("request")

        self.step("Agent finds MakerWorld options (web search → home3d_find_models)")
        found = self.call("home3d_find_models", {"urls": ["https://makerworld.com/en/models/1440000",
                                                          "https://makerworld.com/en/models/1440002",
                                                          "https://makerworld.com/en/models/1440004"]}, "demo-mum")
        for c in found.get("cards", []):
            prof = (c.get("a1_profiles") or [{}])[0]
            self.say(f"  🖼️  {c['title']} · {c['license']} · ♥{c.get('likes')} · A1 profile {prof.get('profile_id')}"
                     f" · ~{prof.get('print_time_min')} min · {prof.get('weight_g')} g")
        if found.get("cards"):
            self.mark("find")

        self.step("Mum picks the first one → home3d_import (records who asked, via voice)")
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

        self.step("Mum's chat asks the agent to start it: the code says no")
        blocked = self.call("home3d_start", {"queue_item_id": qid1}, "demo-mum")
        if blocked.get("blocked"):
            self.mark("non_owner_blocked")

        self.step("The owner approves with a slash command (no model call)")
        reply = self.slash(f"/home3d approve start {qid1}", DEMO_OWNER, "demo-owner")
        if reply.startswith("▶️"):
            self.mark("owner_approved_start")
        self.watch()

        self.step("Meanwhile Dad asks for a coaster (queued behind Mum's print)")
        self.user_turn("demo-dad", DEMO_DAD, "Bana bir bardak altlığı basar mısın?" if tr else "Could you print me a coaster?")
        imp2 = self.call("home3d_import", {"model_id": 1440007, "request_text": "bardak altlığı" if tr else "coaster"},
                         "demo-dad")
        sl2 = self.call("home3d_slice", {"library_file_id": imp2.get("library_file_id"), "material": "PLA",
                                         "colour": "black", "request_id": imp2.get("request_id")}, "demo-dad")
        q2 = self.call("home3d_queue", {"action": "add", "sliced_file_id": sl2.get("sliced_file_id"),
                                        "request_id": imp2.get("request_id")}, "demo-dad")
        qid2 = q2.get("queue_item_id")
        self.say(f"  Dad's coaster: sliced {sl2.get('sliced_file_id')} · {sl2.get('print_time_min')} min · "
                 f"auto-eject {'planned' if (sl2.get('eject') or {}).get('planned') else 'off'} · queue #{qid2}")

        self.step("Mum's print runs; the zero-token watcher reports (simulated time)")
        self.print_job()
        if "finished" in [e["kind"] for e in self.events]:
            self.mark("finished")

        self.step("Bed cools, the end G-code pushes the part off, the camera verifies the plate")
        seen = self.after_finish({"ready_next", "plate_not_clear", "eject_unverified"})
        if "finished_ejected" in seen:
            self.mark("auto_eject_verified")
        if "ready_next" in seen:
            self.mark("ready_next")

        self.step("Scenario eject_miss: the next part will stay on the plate")
        self.be.set_scenario("eject_miss")
        self.say("  simulator: the push will miss this time")
        self.user_turn("demo-owner", DEMO_OWNER, f"#{qid2} başlat" if tr else f"start #{qid2}")
        st2 = self.call("home3d_start", {"queue_item_id": qid2}, "demo-owner")
        self.say(f"  start → ok={st2.get('ok')} · {st2.get('name')} for {st2.get('requester')}")
        if st2.get("ok"):
            self.mark("owner_session_start")
        self.watch()
        self.print_job()
        seen = self.after_finish({"plate_not_clear", "eject_unverified"})
        moments = self.store.human_needed(kind="remove_part")
        if "plate_not_clear" in seen and moments:
            self.mark("human_needed_logged")

        self.step("The owner looks at what needed a person (and at upgrade proposals)")
        self.slash("/home3d moments", DEMO_OWNER, "demo-owner")
        self.slash("/home3d upgrades", DEMO_OWNER, "demo-owner")

        self.step("Someone takes the coaster off; the watcher sees an empty plate")
        self.be.human_clears_plate()
        seen = self.after_finish({"plate_clear"}, max_steps=6)
        if "plate_clear" in seen:
            self.mark("plate_clear_again")

        from .notify import read_outbox

        self.step("Fast-forward: the push misses on two more coasters this month (condensed)")
        mark = len(read_outbox(limit=0))
        for _ in range(2):
            before = len(self.events)
            qid, _seen = self.quietly(self.miss_round)
            n = len(self.store.human_needed(kind="remove_part"))
            flow = [r["kind"] for r in self.events[before:] if r["kind"] in (
                "finished", "plate_not_clear", "eject_unverified", "plate_clear", "upgrade_proposed")]
            self.say(f"  #{qid} Coaster: {' → '.join(flow) or 'nothing'} · remove_part moments: {n}")
            new = [r for r in self.events[before:] if r["kind"] == "upgrade_proposed"]
            if new:
                _print_results(new, self.say)
                self.mark("upgrade_proposed")

        self.step("The owner reviews the proposal and accepts it (printing the parts is a normal job)")
        self.slash("/home3d upgrades", DEMO_OWNER, "demo-owner")
        up = next((u for u in self.store.upgrades() if u.get("status") == "proposed"), None)
        if up:
            self.user_turn("demo-owner", DEMO_OWNER, f"{up['id']} numaralı öneriyi kabul et" if tr
                           else f"accept upgrade {up['id']}", first=False)
            acc = self.call("home3d_upgrades", {"action": "accept", "upgrade_id": up["id"]}, "demo-owner")
            self.say(f"  upgrade #{up['id']} → {acc.get('status')} · next: {acc.get('next')}")

        self.step("Outbox: every message that would have been sent (dry run)")
        recs = read_outbox(limit=0)
        shown = recs[:mark] + [r for r in recs[mark:] if "💡" in r.get("text", "")]
        for rec in shown:
            media = f"  [+photo {Path(rec['media']).name}]" if rec.get("media") else ""
            self.say(f"  → {rec['audience']:<6} {rec['target']}{media}\n" + _indent(rec["text"], "      "))
        if len(recs) > len(shown):
            self.say(f"  (+{len(recs) - len(shown)} messages from the condensed rounds not repeated here)")


DEMO_MILESTONES = ("request", "find", "import", "slice", "queue", "non_owner_blocked", "owner_approved_start",
                   "finished", "auto_eject_verified", "ready_next", "owner_session_start", "human_needed_logged",
                   "plate_clear_again", "upgrade_proposed")


def run_demo(*, lang: str = "en", persona: str = "Mıstık", owner_name: str = "Owner",
             data_dir: Optional[str] = None, keep: bool = False,
             out: Callable[[str], None] = print) -> dict:
    """Scripted simulator run of the whole loop. Returns {"ok", "milestones", "missing", "data_dir", "outbox"}."""
    saved = {k: os.environ.get(k) for k in _DEMO_ENV}
    tmp = Path(data_dir).expanduser() if data_dir else Path(tempfile.mkdtemp(prefix="home3d-demo-"))
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ.update(HOME3D_DATA_DIR=str(tmp), HOME3D_SIM_SPEED="0", HOME3D_DRY_RUN="1")
    result: dict[str, Any] = {"ok": False, "milestones": [], "missing": list(DEMO_MILESTONES), "data_dir": str(tmp),
                              "outbox": []}
    try:
        out(f"home-3d-workshop demo · persona {persona} · language {lang} · simulated printer · nothing is sent")
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
    res = run_demo(lang=args.lang or s.language, persona=s.persona_name or "Mıstık", owner_name=s.owner_name or "Owner",
                   data_dir=args.data_dir, keep=args.keep)
    return 0 if res["ok"] else 1


_DISPATCH: dict[str, Callable[[Any, Any], int]] = {
    "setup": _cmd_setup, "watch": _cmd_watch, "status": _cmd_status, "doctor": _cmd_doctor,
    "simulate": _cmd_simulate, "demo": _cmd_demo,
}

__all__ = ["setup_parser", "handle", "run_demo", "install_watch_script", "cron_command", "hermes_home"]
