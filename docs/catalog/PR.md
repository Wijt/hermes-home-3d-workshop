<!--
DRAFT pull request for NousResearch/hermes-agent. Do NOT open it before the owner approves.
Title: plugin-catalog: add home-3d-workshop
Files: plugin-catalog/home-3d-workshop.yaml (copy docs/catalog/home-3d-workshop.yaml, drop its comment lines)
Before opening: replace <SHA40> everywhere, re-run validate at that commit, update "Status" with the
real-printer result, and attach the demo video link and screenshots. Remove this comment.
-->

# plugin-catalog: add home-3d-workshop

Adds one community entry: `plugin-catalog/home-3d-workshop.yaml`, pinned to
`Wijt/hermes-home-3d-workshop@<SHA40>` (version `0.1.0`, `requires_hermes: ">=0.22.5"`).

## What it does

A household 3D-printing workshop with a character. The persona is called Mıstık by default; the name
and the message language (`tr` or `en`) are settings. Family members ask in plain words, often by
voice note. The agent finds MakerWorld models through Bambuddy or scales one, slices it and queues it
with manual start. The owner approves the start. A zero-token cron watcher follows the print and tells
the owner (technical, with a photo) and the family (one plain line, by name) about finish, failure,
pause, HMS errors and the build plate. Each moment a person had to step in is logged. When one kind
repeats, the plugin proposes an upgrade, for example a printed tilted base for auto-eject.

It comes from a real home: a Bambu Lab A1 managed by Bambuddy, used every day by a family through a
Hermes agent in their WhatsApp group. That agent once printed a tilted base for its own printer so
that finished parts slide off by themselves. The plugin turns that setup's lessons into tools, safety
gates in code, a watcher and a skill. The README tells the story.

It works with a Bambu Lab printer managed by Bambuddy, or with a built-in simulated printer:
`hermes home3d demo` runs the whole loop in under 10 seconds and sends nothing.

## Hermes surfaces used

- **Tools (13):** `home3d_status`, `home3d_camera`, `home3d_find_models`, `home3d_import`,
  `home3d_customize`, `home3d_slice`, `home3d_queue`, `home3d_start`, `home3d_stop`,
  `home3d_clear_plate`, `home3d_household`, `home3d_human_needed`, `home3d_upgrades`.
- **Hooks:** `pre_tool_call` (safety gates and owner approval for start, resume and plate-clear
  confirm), `post_tool_call` (audit trail), `pre_llm_call` (who is speaking, short printer context).
- **Slash command:** `/home3d` (`status`, `approve start <id> [jump]`, `approve clear`,
  `approve resume [ack]`, `whoami`, `upgrades`, `moments`).
- **CLI command:** `hermes home3d` (`setup`, `teardown`, `watch`, `status`, `doctor`, `simulate`, `demo`).
- **Skill:** `home-3d-workshop:household-printing`.
- **Config:** `config_schema` only; one optional secret `HOME3D_BAMBUDDY_API_KEY`, read with
  `agent.secret_scope.get_secret`. No `requires_env`. Python standard library only.
- **Storage:** `plugin_data_dir` (SQLite and files under `HERMES_HOME/plugin-data/home-3d-workshop`).
- **Cron:** `hermes cron create --no-agent --script`, created by `hermes home3d setup`.

## Disclosure (rule 13)

- **Network.** Only the Bambuddy URL the user sets, over HTTP on the LAN. When set,
  `HOME3D_BAMBUDDY_API_KEY` is sent as `X-API-Key`, unencrypted over plain HTTP. MakerWorld lookups and
  downloads go through Bambuddy; the plugin makes no other network calls.
- **Printer and library writes.** Import, scale, slice and queue add write to the Bambuddy library and
  queue without a prompt. Queue items are always manual start. A camera photo switches the chamber
  light on for about 12 s, then restores its earlier state.
- **Approvals (rule 12).** Start, resume and plate-clear confirm are blocked in cron (the check fails
  closed), when a safety gate fails, and for unknown or non-owner senders. Only an owner session gets
  the Hermes approve prompt. The handler also requires a single-use pass from that hook or from
  `/home3d approve`, so a dispatch that skips `pre_tool_call` is refused. `/home3d approve` runs the
  gate and the action at once and stores nothing for later. The owner is any id in `owner_ids`, plus any
  local CLI, TUI or Desktop session while `local_is_owner` is true (the default). `yolo` and
  approvals off skip the prompt in an owner session. Each `rule_key` is unique, so "always" does not
  carry over; each "always" answer still adds one unused `command_allowlist` line. Stop and pause are
  never blocked: anyone who can reach the agent can stop or pause a print.
- **Subprocesses.** `hermes send` (notices; `-p <send_profile>` when set), `hermes cron create`, `list`
  and `remove` (setup and teardown), `openscad` (templates, only when installed).
- **Background job.** One `--no-agent --script` cron job, every 2 minutes by default (720 runs a day).
  No model calls; empty output sends nothing. The script lives at
  `HERMES_HOME/scripts/home3d_watch.py`. It reads `HERMES_HOME/config.yaml` and stays silent while the
  plugin is disabled or removed. `hermes home3d teardown` removes the job and the script.
- **Files and personal data.** Kept locally under `HERMES_HOME/plugin-data/home-3d-workshop`: SQLite
  (requests, jobs, household sender ids and names, audit events), `outbox.jsonl` (every message), camera
  photos, model files, a watcher log and a settings snapshot without secrets.
- **Prompt context.** `pre_llm_call` adds up to 900 characters: for household members and the local
  owner on the first turn, on printing turns and on printer state changes, else one speaker line; for
  other senders only on printing turns. `inject_context: never` turns it off. While the plugin is
  enabled, its skill adds one line to the skills index of every session.

## Validation and testing

- `HERMES_HOME=$(mktemp -d) hermes plugins validate <checkout at <SHA40>> --install-deps` on Hermes
  0.22.5: passes. <!-- paste the final output -->
- The pytest suite (no Hermes needed) runs in the repo CI, plus a job that runs `hermes plugins
  validate` against Hermes 0.22.5.
- `hermes home3d demo` runs the full loop on the simulator. Scripted stand-ins are marked `[staged]`.

## Status on real hardware

- Verified on a real Bambuddy 1.3.0 with an A1: read-only calls (printer status, queue, plate check).
- Planned: the plate check that switches the chamber light on and back (a `chamber-light` POST, tested
  against a fake HTTP layer only), start, auto-eject verification and notices with this plugin on the
  real printer.
  <!-- update before opening -->

## Links

- Repo and README: https://github.com/Wijt/hermes-home-3d-workshop/tree/<SHA40>
- Demo video (under 90 s): <!-- X post link -->

## Checklist

- [x] One file, `plugin-catalog/home-3d-workshop.yaml`
- [x] `sha` is a full 40-character commit; `version` is quoted and matches `plugin.yaml`
- [x] `requires_hermes` is `">=0.22.5"` in the entry and in `plugin.yaml`
- [x] Declared tools and hooks match what the plugin registers
- [x] Secrets only through `get_secret`; no `.env` reads; no binaries or `.pyc` files
- [x] No self-updating code; no monkey-patching; public `ctx.register_*` surfaces only
- [x] Disclosures are in the README and in the entry description
- [x] I am the plugin's author and maintainer

🤖 Generated with [Claude Code](https://claude.com/claude-code)
