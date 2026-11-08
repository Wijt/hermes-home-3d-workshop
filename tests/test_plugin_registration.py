"""register(ctx) wiring: exactly the tools / hooks plugin.yaml declares, /home3d, ``hermes home3d`` and the
bundled skill, through the public PluginContext API with the kwargs Hermes v0.22.5 accepts. No Hermes needed."""

from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

from home3d_ws.home3d import TOOLSET
from home3d_ws.home3d import plugin as plugin_mod

ROOT = Path(__file__).resolve().parents[1]


def manifest_list(key: str) -> list[str]:
    """Items of a top-level ``key:`` list in plugin.yaml (stdlib only: CI has no PyYAML)."""
    out, inside = [], False
    for line in (ROOT / "plugin.yaml").read_text(encoding="utf-8").splitlines():
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            inside = True
            continue
        if inside:
            m = re.match(r"^\s+-\s+([\w.-]+)\s*$", line)
            if m:
                out.append(m.group(1))
            elif line.strip() and not line.startswith((" ", "\t")):
                break
    return out


class RecordingCtx:
    """Minimal stand-in for ``hermes_cli.plugins.PluginContext`` that records the public registration calls
    (keyword names mirror the v0.22.5 signatures)."""

    def __init__(self):
        self.tools, self.hooks, self.commands, self.cli_commands, self.skills = [], [], [], [], []

    def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None, is_async=False,
                      description="", emoji="", override=False):
        self.tools.append(dict(name=name, toolset=toolset, schema=schema, handler=handler, emoji=emoji,
                               check_fn=check_fn, is_async=is_async, override=override))

    def register_hook(self, hook_name, callback):
        self.hooks.append((hook_name, callback))

    def register_command(self, name, handler, description="", args_hint="", argument_mode=None):
        self.commands.append(dict(name=name, handler=handler, description=description, args_hint=args_hint))

    def register_cli_command(self, name, help, setup_fn, handler_fn=None, description=""):
        self.cli_commands.append(dict(name=name, help=help, setup_fn=setup_fn, handler_fn=handler_fn,
                                      description=description))

    def register_skill(self, name, path, description="", frontmatter=None):
        self.skills.append(dict(name=name, path=Path(path), description=description))

    def get_config(self, key, default=None):
        return default

    def current_cron_execution(self):
        return None


@pytest.fixture
def ctx():
    c = RecordingCtx()
    sys.modules["home3d_ws"].register(c)  # the plugin's own entry point
    return c


def test_tools_match_manifest(ctx):
    declared = manifest_list("provides_tools")
    names = [t["name"] for t in ctx.tools]
    assert declared and names == declared
    for t in ctx.tools:
        assert t["toolset"] == TOOLSET == "home_3d_workshop"
        assert t["schema"]["name"] == t["name"] and t["schema"]["parameters"]["type"] == "object"
        assert t["emoji"] == "🧰" and callable(t["handler"]) and not t["override"] and not t["is_async"]


def test_hooks_match_manifest(ctx):
    declared = manifest_list("provides_hooks")
    assert sorted(h for h, _ in ctx.hooks) == sorted(declared) == ["post_tool_call", "pre_llm_call", "pre_tool_call"]
    assert all(callable(cb) for _, cb in ctx.hooks)


def test_slash_command(ctx):
    (cmd,) = ctx.commands
    assert cmd["name"] == "home3d" and cmd["description"] and "approve start" in cmd["args_hint"]
    params = inspect.signature(cmd["handler"]).parameters
    assert {"source", "session_id", "platform"} <= set(params)
    assert "approve start" in cmd["handler"]("help")


def test_cli_command(ctx):
    (c,) = ctx.cli_commands
    assert c["name"] == "home3d" and c["help"] and callable(c["handler_fn"])
    parser = argparse.ArgumentParser(prog="hermes home3d")
    c["setup_fn"](parser)
    parser.set_defaults(func=c["handler_fn"])  # what hermes_cli.main does
    for sub in ("setup", "watch", "status", "doctor", "simulate", "demo"):
        assert parser.parse_args([sub] if sub != "simulate" else [sub, "status"]).home3d_command == sub
    args = parser.parse_args([])
    assert args.func(args) == 2  # no subcommand: usage


def test_skill_registered_with_existing_file(ctx):
    (skill,) = ctx.skills
    assert skill["name"] == "household-printing" and skill["description"]
    assert skill["path"] == ROOT / "skills" / "household-printing" / "SKILL.md"
    assert skill["path"].is_file(), "bundled SKILL.md is missing"


def test_descriptions_first_sentence_is_short(ctx):
    for t in ctx.tools:
        desc = t["schema"]["description"]
        first = re.split(r"(?<=[.!?])\s", desc.strip(), maxsplit=1)[0]
        assert len(first) <= 60, f"{t['name']}: {first!r} ({len(first)} chars)"


def test_register_is_side_effect_free(data_dir):
    c = RecordingCtx()
    plugin_mod.register_all(c)
    assert list(data_dir.iterdir()) == []  # no store, no simulator state, no network


def test_handlers_and_hooks_accept_hermes_kwargs(ctx):
    """The exact keyword sets hermes_cli.plugins / model_tools / agent.turn_context pass in v0.22.5."""
    handlers = {t["name"]: t["handler"] for t in ctx.tools}
    out = json.loads(handlers["home3d_status"]({}, task_id="t1", session_id="s1", tool_call_id="c1"))
    assert out["ok"] is True
    assert json.loads(handlers["home3d_start"]("not a dict"))["ok"] is False
    hooks = dict(ctx.hooks)
    assert hooks["pre_tool_call"](tool_name="home3d_status", args={}, task_id="t", session_id="s", tool_call_id="c",
                                  turn_id="u", api_request_id="a", middleware_trace=[]) is None
    r = hooks["pre_llm_call"](session_id="s", task_id="t", turn_id="u", user_message="3d print a box",
                              conversation_history=[], is_first_turn=True, model="m", platform="cli",
                              parent_session_id="", sender_id="")
    assert "home3d" in r["context"] or "home-3d-workshop" in r["context"]
    assert hooks["post_tool_call"](tool_name="home3d_status", args={}, result='{"ok": true}', task_id="t",
                                   session_id="s", tool_call_id="c", turn_id="u", api_request_id="a",
                                   duration_ms=3, status="ok", error_type=None, error_message=None,
                                   middleware_trace=[]) is None
