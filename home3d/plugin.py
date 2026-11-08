"""Plugin wiring: one Runtime shared by the tools, hooks, ``/home3d``, ``hermes home3d`` and the skill.

``register_all`` only builds closures and registers them: no network, no threads, no store access.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import TOOLSET
from .runtime import Runtime

logger = logging.getLogger(__name__)

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "household-printing"
SKILL_PATH = PLUGIN_ROOT / "skills" / SKILL_NAME / "SKILL.md"  # folder name = skill name (Hermes skill lint)
SKILL_DESCRIPTION = ("Household 3D printing with a persona: family requests, MakerWorld options, slicing, "
                     "owner-approved starts, auto-eject, failure handling and upgrade proposals.")
TOOL_EMOJI = "🧰"
COMMAND_NAME = "home3d"
COMMAND_DESCRIPTION = "3D workshop: printer status, owner approvals, human-needed moments, upgrades"
COMMAND_ARGS_HINT = ("status | approve start <id> [jump] | approve clear | approve resume [ack] | whoami | upgrades | "
                     "moments | help")
CLI_HELP = "Household 3D workshop (watcher setup, status, doctor, simulator, demo)"
CLI_DESCRIPTION = ("home-3d-workshop: a household 3D-printing service with a character.\n"
                   "Try it without hardware: hermes home3d demo")


def register_all(ctx) -> None:
    from . import cli
    from .commands import make_command
    from .hooks import make_hooks
    from .tools import build_tools

    rt = Runtime(ctx)
    for name, schema, handler in build_tools(rt):
        ctx.register_tool(name=name, toolset=TOOLSET, schema=schema, handler=handler, emoji=TOOL_EMOJI)
    for hook_name, callback in make_hooks(rt).items():
        ctx.register_hook(hook_name, callback)
    if hasattr(ctx, "register_command"):
        ctx.register_command(COMMAND_NAME, make_command(rt), description=COMMAND_DESCRIPTION,
                             args_hint=COMMAND_ARGS_HINT)
    if hasattr(ctx, "register_cli_command"):
        def _handle(args) -> int:
            return cli.handle(args, rt)

        ctx.register_cli_command(name=COMMAND_NAME, help=CLI_HELP, setup_fn=cli.setup_parser, handler_fn=_handle,
                                 description=CLI_DESCRIPTION)
    if hasattr(ctx, "register_skill"):
        try:
            ctx.register_skill(SKILL_NAME, SKILL_PATH, description=SKILL_DESCRIPTION)
        except (FileNotFoundError, ValueError) as e:  # a missing skill must not take the tools down
            logger.warning("home-3d-workshop: skill not registered: %s", e)


__all__ = ["register_all", "SKILL_NAME", "SKILL_PATH"]
