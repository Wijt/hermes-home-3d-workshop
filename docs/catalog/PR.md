<!--
DRAFT pull request for NousResearch/hermes-agent. Do NOT open it before the owner approves.
Title: plugin-catalog: add home-3d-workshop
Files: plugin-catalog/home-3d-workshop.yaml (copy docs/catalog/home-3d-workshop.yaml, drop its comment lines)
Before opening: replace <SHA40> everywhere, re-run validate at that commit, check that every CI job
(including the `openscad` job) is green on that commit, update "Status" with the real-printer result,
and attach the demo video link and screenshots. Remove this comment.
-->

# plugin-catalog: add home-3d-workshop

Adds one community entry: `plugin-catalog/home-3d-workshop.yaml`, pinned to
`Wijt/hermes-home-3d-workshop@<SHA40>` (version `0.1.0`, `requires_hermes: ">=0.22.5"`).

## What it does

A household 3D-printing workshop with a character. The persona is called Mıstık by default; the name
and the message language (`en` by default, or `tr`) are settings. Family members ask in plain words,
often by voice note. The agent finds MakerWorld models through Bambuddy, scales one, or designs a
part in OpenSCAD (it writes the code, renders it, looks at the preview pictures and keeps every
version), slices it and queues it with manual start. The owner approves the start; when a family member asks, the watcher
passes the request to the owner with the exact command. A zero-token cron watcher follows the print and tells
the owner (technical, with a photo) and the family (one plain line, by name) about finish, failure,
pause, HMS errors and the build plate. Each moment a person had to step in is logged. When one kind
repeats, the plugin proposes an upgrade, for example a printed tilted base for auto-eject.

It comes from a real home: a Bambu Lab A1 managed by Bambuddy, used every day by a family through a
Hermes agent in their WhatsApp group. That agent once printed a tilted base for its own printer so
that finished parts slide off by themselves. The plugin turns that setup's lessons into tools, safety
gates in code, a watcher and a skill. The README tells the story.

It works with a Bambu Lab printer managed by Bambuddy, or with a built-in simulated printer. After
`hermes plugins install Wijt/hermes-home-3d-workshop --enable`, `hermes home3d demo` runs the whole
loop in about 10 seconds and sends nothing.

## Hermes surfaces used

- **Tools (14):** `home3d_status`, `home3d_camera`, `home3d_find_models`, `home3d_import`,
  `home3d_customize`, `home3d_design`, `home3d_slice`, `home3d_queue`, `home3d_start`, `home3d_stop`,
  `home3d_clear_plate`, `home3d_household`, `home3d_human_needed`, `home3d_upgrades`.
- **Hooks:** `pre_tool_call` (safety gates and owner approval for start, resume and plate-clear
  confirm; bounded: status and queue only, 5 s per request, 12 s in all), `post_tool_call` (audit
  trail), `pre_llm_call` (who is speaking, short printer context).
- **Slash command:** `/home3d` (`status`, `approve start <id> [jump]`, `approve clear`,
  `approve resume [ack]`, `whoami`, `upgrades`, `moments`, `help`).
- **CLI command:** `hermes home3d` (`setup`, `teardown`, `watch`, `status`, `doctor`, `simulate`, `demo`).
- **Skills:** `home-3d-workshop:household-printing` and `home-3d-workshop:parametric-design`.
- **Config:** `config_schema` only; one optional secret `HOME3D_BAMBUDDY_API_KEY`, read with
  `agent.secret_scope.get_secret`. No `requires_env`. Python standard library only.
- **Storage:** `plugin_data_dir` (SQLite and files under `HERMES_HOME/plugin-data/home-3d-workshop`).
- **Cron:** `hermes cron create --no-agent --script`, created by `hermes home3d setup`.

## Disclosure (rule 13)

- **Network.** Only the Bambuddy URL the user sets, over HTTP on the LAN. When set,
  `HOME3D_BAMBUDDY_API_KEY` is sent as `X-API-Key`, unencrypted over plain HTTP. MakerWorld lookups and
  downloads go through Bambuddy; the plugin makes no other network calls.
- **Printer and library writes.** Import, scale, design upload, slice and queue add write to the
  Bambuddy library and queue without a prompt. Queue items are always manual start. Queue remove only removes the asking
  person's own waiting items: never a job queued outside the workshop or another household member's job,
  not even for the owner (who can remove anything by hand in Bambuddy). A tool photo or plate check switches
  the chamber light on for about 12 s, then restores its earlier state.
- **Chamber light from the cron job.** The watcher switches the light by itself for its plate checks
  and photos: at most once per pass (photo and check share one light cycle; twice when a camera request
  fails), one photo near the end of each print the workshop queued (other prints: one photo and plate
  check, in one light cycle, when they end), a check when a print ends, and re-checks that
  back off 15, 30, 60 and 120 min, at most 6, while a plate waits for a person or a job waits on an idle
  printer. The count starts again when the printer state, the job or the queue head changes.
- **Bambuddy settings.** Read with `GET /settings/`, never changed. With Bambuddy's
  `require_plate_clear` off, Bambuddy's own queue may start an auto-start item on a finished printer
  before the camera check. `hermes home3d doctor` warns about this when an auto-eject preset is set, and
  the README asks the user to turn the setting on.
- **Approvals (rule 12).** Start, resume and plate-clear confirm are blocked in cron and in runs with
  nobody present (kanban workers, `chat -q`, `-z`, `--source tool`; both checks fail closed), when a
  safety gate fails, and for unknown or non-owner senders. A household member's blocked request is
  stored, and the watcher tells the owner once, with the command; an unknown sender's is not passed on.
  Only an owner session gets the Hermes approve prompt. The handler also requires a single-use pass
  from that hook or from `/home3d approve`, so a dispatch that skips `pre_tool_call` is refused; it
  checks the plate with the camera right before the action. `/home3d approve` runs the gate and the
  action at once and stores nothing for later. The owner is any id in `owner_ids`, plus, while
  `local_is_owner` is true (the default), any local CLI, TUI or Desktop session and any slash command
  typed in the TUI, Desktop or web dashboard (these reach the plugin without a sender). The README asks
  users to turn `local_is_owner` off when others can reach the dashboard. On IRC and ntfy, where people
  choose their own ids, only an entry written with the platform (`irc:<nick>`) matches a sender. `yolo` and approvals off skip
  the prompt in an owner session. Each `rule_key` is unique, so "always" does not carry over; each
  "always" answer still adds one unused `command_allowlist` line. Stop and pause need no approval and
  pass no gate: anyone who can reach the agent can stop or pause a print.
- **Hook time (rule 12).** Hermes 0.22.5 runs a hook callback with a 30 s timeout, and a timed-out
  `pre_tool_call` blocks every tool call of the process for 60 s, stop included. So `pre_tool_call`
  never uses the camera or the chamber light. It reads only printer status and queue, at most 5 s per
  request and 12 s in all, and blocks the gated call when the printer does not answer in time. It never
  issues a pass after that deadline. With a lower `plugins.hook_callback_timeout` the deadline is 0.4 of
  it, and `hermes home3d doctor` warns below 15 s.
- **Hermes internals (rule 9).** The plugin registers only through public `ctx.register_*` surfaces and
  patches nothing. To find cron and unattended runs it uses `ctx.current_cron_execution()` and also
  reads non-public Hermes internals: `gateway.session_context.get_session_env`,
  `cron.execution_identity._CURRENT` and `gateway.session_finite` (`finite_turn_required`,
  `unattended_turn`), and `hermes_cli.plugins._resolve_hook_callback_timeout` to size the hook deadline.
  It takes them from `sys.modules`, never imports them, and never writes to them, so
  `hermes plugins validate` does not list them. A check that raises counts as cron or unattended (fail
  closed). If a later Hermes renames one, that extra check is skipped; the public cron check and Hermes'
  own approval gate stay. A public "unattended run" seam in Hermes would let the plugin drop these
  reads.
- **Subprocesses.** `hermes send` (notices; `-p <send_profile>` when set), `hermes cron create`, `list`
  and `remove` (setup and teardown), `openscad` (the templates and the agent's designs) and `xvfb-run`
  (design preview pictures without a display), only when installed. Renders run one at a time, with a
  180 s default time limit (at most 600 s) that stops the process group, a CPU-time limit (an orphaned
  OpenSCAD still stops), a memory cap and an STL size cap, without `OPENSCADPATH`. A design may read
  files only from its own folder and OpenSCAD's own libraries: the source is checked before the render,
  and OpenSCAD's `-d` list of the files it read is checked after it (a version that read anything else
  is refused: no STL, no pictures, no echo).
- **Background job.** One `--no-agent --script` cron job, every 2 minutes by default (720 runs a day).
  It runs while the Hermes scheduler runs (`hermes gateway`). No model calls; empty output sends
  nothing. The script lives at `HERMES_HOME/scripts/home3d_watch.py`. It reads the plugin settings
  from `HERMES_HOME/config.yaml` on each pass and stays silent while the plugin is disabled or removed.
  `hermes home3d teardown` removes the job and the script.
- **Files and personal data.** Kept locally under `HERMES_HOME/plugin-data/home-3d-workshop`: SQLite
  (requests, jobs, household sender ids and names, approval requests, audit events), `outbox.jsonl`
  (every message), camera photos, model files, `designs/` (OpenSCAD source, STL, preview pictures and
  facts for every version), a watcher log and a settings snapshot without secrets (the watcher's
  fallback when it cannot read `config.yaml`).
- **Prompt context.** `pre_llm_call` adds up to 900 characters: for household members and the local
  owner on the first turn, on printing turns and on printer state changes, else one speaker line; for
  other senders only on printing turns. `inject_context: never` turns it off. While the plugin is
  enabled, its two skills add one line each to the skills index of every session.

## Validation and testing

- `HERMES_HOME=$(mktemp -d) hermes plugins validate <checkout at <SHA40>> --install-deps` on Hermes
  0.22.5: passes. <!-- paste the final output -->
- The pytest suite (no Hermes needed) runs in the repo CI, plus a job that runs `hermes plugins
  validate` against Hermes 0.22.5, and a job that installs `openscad` and `xvfb` on ubuntu-24.04 and
  runs the real-OpenSCAD tests with OpenSCAD 2021.01: the templates, a sample design and the
  file-access probes (each refused). <!-- confirm this job is green on <SHA40> -->
- `hermes home3d demo` runs the full loop on the simulator. Scripted stand-ins are marked `[staged]`.

## Status on real hardware

This matches the README's status table at the same commit.

- Verified on a real Bambuddy 1.3.0 with an A1: printer status, queue, plate check, the lit photo with
  plate check in one light cycle (light restored to its earlier state), MakerWorld cards and import,
  slice with the auto-eject preset (G-code check), scale, queue add with manual start and remove, and
  reading `require_plate_clear` and the queue history (GET only).
- The watcher in dry run (outbox only) on a real family print it did not queue: no light or camera
  during the print, FINISH caught, one light cycle for the photo and plate check, one owner notice. The
  A1's auto-eject order (RUNNING through the cool-down and the push, then FINISH) was seen on that print.
- Designing: the templates, a sample design and the file-access probes are tested with OpenSCAD
  2021.01 (locally and in the CI `openscad` job); a design upload and slice are tested on the
  simulator.
- Planned on the real printer: start, stop, pause, resume and plate-clear confirm, watcher notices
  sent with `hermes send`, the auto-eject push with this plugin (the push itself is real in the
  original setup), and the upload and slice of a designed part.
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
- [x] No self-updating code; no monkey-patching; registers only through public `ctx.register_*`
  surfaces (the read-only use of non-public Hermes internals is disclosed above)
- [x] Disclosures are in the README and in the entry description
- [x] I am the plugin's author and maintainer

🤖 Generated with [Claude Code](https://claude.com/claude-code)
