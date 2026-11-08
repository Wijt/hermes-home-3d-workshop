# home-3d-workshop

[![CI](https://github.com/Wijt/hermes-home-3d-workshop/actions/workflows/ci.yml/badge.svg)](https://github.com/Wijt/hermes-home-3d-workshop/actions/workflows/ci.yml)

A Hermes Agent plugin that gives a household a 3D-printing service with a character.

Family members ask in plain words, often by voice note. The agent finds, adapts or designs a model,
slices it and queues it. The owner approves the start. A zero-token watcher follows the print, tells the owner and the
family what happened, and checks that the build plate is clear for the next job. Each time a person must
step in, the plugin records it. When the same need repeats, it proposes an upgrade to the workshop.

## Quick start

```bash
hermes plugins install Wijt/hermes-home-3d-workshop --enable
hermes home3d demo
```

The demo runs the whole loop on a simulated printer in a temporary folder, in about 10 seconds. It sends
nothing. Keep `--enable`. Without it, Hermes asks whether to enable the plugin (the default is no), and
`hermes home3d` is not found until the plugin is enabled.

![A condensed, real run of hermes home3d demo: a blocked start, the owner's approval, watcher notices and an upgrade proposal](docs/demo-terminal.svg)

## Why a plugin, not a skill

A skill can only ask the model to behave. This plugin puts the parts that must not fail into code.

| Need | With a skill only | In this plugin | Code |
|---|---|---|---|
| Safety gates | Rules in a prompt. The model can skip them. | Printer state, HMS errors, plate, queue order and "after a failure" are checked in code before a start, a resume or a plate clear. | [`gates.py`](home3d/gates.py) |
| Owner approval | The model decides who may start. | `pre_tool_call` refuses non-owners. An owner session gets a single-use pass, bound to the tool, the target and the session. The tool refuses without it. | [`hooks.py`](home3d/hooks.py) |
| Watching a print | An agent cron job that spends tokens on every run. In the original setup, about 9 in 10 of 323 runs had nothing to say. | A `--no-agent` cron script. No model, zero tokens. It writes only when something happens. | [`watcher.py`](home3d/watcher.py) |
| Household memory | Chat history. | SQLite: who asked for what, in their own words; jobs, failures, approval requests and moments. | [`store.py`](home3d/store.py) |
| Getting better | Notes, if somebody writes them. | Each time a person has to step in, the plugin logs it. Repeats become an upgrade proposal, for example a tilted base for auto-eject. | [`upgrades.py`](home3d/upgrades.py) |
| Two audiences | One voice for everyone. | The owner gets a technical note with a photo. The family gets one plain line, by name. | [`notify.py`](home3d/notify.py), [`messages.py`](home3d/messages.py) |
| Designing a part | The model runs OpenSCAD in a terminal. Nothing limits the time or the files it reads, and a new try overwrites the old one. | `home3d_design` renders one design at a time with time, CPU, memory and file-size limits. It refuses a version when OpenSCAD's own list of the files it read names one outside the design's folder. It keeps every version, measures the STL, flags code that OpenSCAD ignored and draws the previews. | [`design.py`](home3d/design.py) |

The skills still do what a skill does well. `skills/household-printing` holds the persona, the tone and
the workflow; `skills/parametric-design` holds the design know-how.

The character is called **Mıstık** by default. You can change the name (`persona_name`) and the language
of the messages (`language`: `en` or `tr`). The default language is English. The home it comes from sets
`language: tr`.

It works with a Bambu Lab printer that [Bambuddy](https://github.com/maziggy/bambuddy) manages, or with
the built-in simulated printer.

## The real story

This plugin comes from a real home. One household has a Bambu Lab A1 with an AMS lite, managed by
Bambuddy. In October 2026 the owner put a Hermes agent called Mıstık into the family WhatsApp group.
Mum, Dad and a sibling talked to it every day. Mum asked for rose gift boxes, a
make-up brush holder, a pill box and a toy car track split into parts that fit the bed. She mostly sent
voice notes. The household shaped the character. The owner told it: "keep your messages short, my
family does not read them".

The key episode started with one message from the owner after a print:

> "Can you clear the build plate after printing? If you drop the part in front, I just add the next
> print to the queue, and we remove the human bottleneck."

The agent tried it on the real printer. It waited for the bed to cool and pushed the part forward with
the nozzle, at reduced motor current. The part came loose but stopped at the front edge. The agent saw a
hazard: on the A1, a part pushed off the front lands in the path of the bed. It stopped and wrote the
lesson into its skill. The owner asked how other people solve this. The agent looked at the known
solutions and suggested to tilt the printer forward. The owner agreed. The agent picked a free tilted
A1 base on MakerWorld, sliced the parts and queued them. **It printed an upgrade for its own body.**
With the base installed at about 15 degrees and a box in front, the owner wrote: "it fell in by
itself". Auto-eject became the default for parts that are safe to push. The agent also refused to push
a tall rose box, and the owner agreed it was right.

Not everything went well, and the agent said so: "the part was not pushed at all". A pause went
unnoticed for about four hours. Of 323 runs of the old agent watch jobs, about nine in ten had nothing
to report. After it missed a failure, the agent changed its own rule: "Better to stop by
mistake than waste filament."

That setup used a Hermes profile with skills and shell scripts. This plugin turns what it learned into
tools, safety gates in code, a watcher that uses no tokens, and a skill that any Hermes user can install.

## Status: what is verified, and where

The plugin is new. This table shows what is verified, and where.

| Part | Real printer (Bambuddy 1.3.0 + A1) | Simulator and tests |
|---|---|---|
| Read printer status, queue and plate check (HTTP GET only) | Verified | Verified |
| Lit photo + plate check in one light cycle, light restored to its earlier state | Verified (a part on the plate read as occupied) | Verified (fake HTTP) |
| MakerWorld cards, import, slice with the auto-eject preset (G-code check: height, footprint, eject block) | Verified | Verified |
| Scale a model (upload + slice the scaled file), add to queue with manual start, remove | Verified | Verified |
| Read Bambuddy's `require_plate_clear` setting and the queue history (start errors) | Verified (GET only) | Verified |
| Start, stop, pause, resume, mark plate clear | Planned | Verified |
| Watcher on a real print (dry run: outbox only, nothing sent) | Verified on a family print it did not queue: no light or camera during the print, FINISH caught, one light cycle for photo + plate check, one owner notice | Verified |
| Watcher notices sent with `hermes send` | Planned | Verified (dry run, outbox only) |
| Design a part in OpenSCAD (render, measure, previews, versions), and the name-tag and label-box templates | Upload and slice of a designed part: planned | Verified with OpenSCAD 2021.01 (the real-OpenSCAD tests, also a CI job); upload and slice on the simulator |
| Auto-eject push on the tilted base | Real in the original setup. The A1 order the watcher expects (RUNNING through the 15 min cool-down and the push, then FINISH) was seen on a family print. A push of the plugin's own job: planned | Simulated |

`hermes plugins validate . --install-deps` passes on Hermes 0.22.5, and
`hermes plugins install Wijt/hermes-home-3d-workshop --enable` installs it. CI runs validate and the test
suite (more than 600 tests, no Hermes needed), plus a job that renders the templates and a sample
design with a real OpenSCAD. The real-hardware loop with this plugin is **planned, not
done**. The family uses the printer every day, so we test on it only when no family job waits.

## Install

Requires Hermes **0.22.5 or newer**. The plugin uses only the Python standard library. Designing new
parts also needs `openscad` (and `xvfb-run` for the preview pictures); see "The agent can design
parts".

```bash
hermes plugins install Wijt/hermes-home-3d-workshop --enable
```

Hermes shows a banner for a Git install, because nobody reviewed it yet. The plugin starts with the
simulated printer, so it does nothing to real hardware until you configure Bambuddy.

Upgrading: `language` now defaults to `en`; early versions defaulted to `tr`. A household that relied on the
old default sets `language: tr` under `plugins.entries.home-3d-workshop.settings`.

## More with the simulator

```bash
hermes home3d demo              # about 10 seconds, English, nothing is sent
hermes home3d demo --lang tr    # the same run in Turkish
```

The demo runs the full loop on a simulated printer in a temporary folder: a request, model cards,
import, scale, slice, queue, a blocked start from a family member, the request passed on to the owner,
the owner's approval, the print, the messages to the owner and the family, auto-eject, a missed push, a
failure, a filament-runout pause, and an upgrade proposal. Scripted stand-ins (what people say, the
model's chat replies, canned search results and the owner's tap on "approve") are marked `[staged]`.

You can also talk to the agent while the simulator is active. Ask it to print a coaster. Then move the
simulated time forward and run one watcher pass (simulated time runs 60 times faster than real time, so a
coaster may be done before you type the command; the watcher's first pass still reports a workshop print
that already ended):

```bash
hermes home3d simulate advance 60 --watch
hermes home3d simulate scenario eject_miss   # also: ok, fail, pause_hms, busy, offline, dispatch_fail
```

## The agent can design parts

Ready models come first. When nothing fits, or the part must fit something the household owns (a
phone with its case, a tube, a shelf edge, a broken piece), the agent designs it. It writes
parametric OpenSCAD code. `home3d_design` renders the code to an STL, measures it (size, volume, an
upper bound for the weight, separate bodies, fits the bed) and draws preview pictures. The agent
looks at the pictures itself, then sends the person one picture, the size in cm and a short
question. Every change is a new version, so "the first one was right" is one call away. After an
OK, the design is uploaded and goes through the normal slice, queue and owner-approved start.

The skill `home-3d-workshop:parametric-design` holds what a real household's prints taught:
parameters with units, asserts, text that lies flat until you rotate it, press-fit pockets instead of
print pauses, a closed underside so that tall parts do not warp, cable exits on all four sides of a
phone dock, and how to ask when feedback is vague. Its worked example is a phone dock with a
short fit-test ring ([`phone-dock.scad`](skills/parametric-design/templates/phone-dock.scad)).

Designing needs OpenSCAD on the machine that runs Hermes, and `xvfb-run` for the pictures on a
machine without a display:

```bash
sudo apt install openscad xvfb      # Debian and Ubuntu
hermes home3d doctor                # the "openscad" row: version, and whether pictures work
```

Renders run one at a time, with a time limit (180 seconds by default), a memory cap and a cap on the
STL size. The code may read files only from its own design folder (and OpenSCAD's own libraries):
the source is checked before the render, and OpenSCAD's list of the files it really read is checked
after it, so a file name hidden in a parameter is caught too. A render that OpenSCAD finished but
with part of the code ignored (a typo, an unknown name) is flagged, and the agent fixes it before it
shows anything. Without OpenSCAD, the agent says so and keeps to ready models.

## Set up with Bambuddy

1. Set the plugin settings in `config.yaml` under `plugins.entries.home-3d-workshop.settings`, with
   `hermes config set` or the Desktop plugin settings. Example (all values are placeholders):

   ```yaml
   backend: bambuddy
   bambuddy_url: http://192.168.1.50:8000
   printer_id: 1
   persona_name: Mıstık
   language: en
   owner_name: Sam
   owner_ids: ["<owner sender id>"]
   household:
     - {id: "<mum sender id>", name: Mum, address_as: Mum, role: family}
     - {id: "<dad sender id>", name: Dad, address_as: Dad, role: family}
   owner_target: "whatsapp:<owner chat>@g.us"
   family_target: "whatsapp:<family group>@g.us"
   autoeject_printer_preset: "<Bambuddy preset id>"   # optional, see "Auto-eject" below
   ```

   Example: `hermes config set plugins.entries.home-3d-workshop.settings.backend bambuddy`.
2. If Bambuddy API auth is on, put `HOME3D_BAMBUDDY_API_KEY=...` in the profile's `.env` file
   (`hermes config env-path` prints its path).
3. Check the setup: `hermes home3d doctor`. Use `/home3d whoami` in a chat to see the sender id to put
   in `owner_ids` or `household`. On IRC (and ntfy) people choose their own id, so write such an id with
   its platform, for example `irc:<nick>`: a bare id never matches a sender from those platforms.
4. Start the watcher: `hermes home3d setup`. The cron job runs only while the Hermes scheduler runs, and
   `hermes gateway` runs it (check with `hermes cron status`). If the job exists but no pass ran,
   `hermes home3d doctor` says so. Remove the watcher with `hermes home3d teardown`.
5. If you use auto-eject, turn on **Require plate clear** in Bambuddy's settings. `hermes home3d doctor`
   warns when it is off. See "Bambuddy's own queue" under "Safety model". With it on, Bambuddy waits after
   each print until the plate is marked clear, so the owner sends `/home3d approve clear` before
   `/home3d approve start <id>`; the "next job ready" message says so.

The watcher reads the plugin settings from `config.yaml` on each pass, so a change needs no new setup,
except `watch_interval`: setup writes it into the cron schedule, so after a change run
`hermes home3d teardown` and `hermes home3d setup` again.

Other settings: `public_url` (links sent to people), `send_profile` (the profile that owns the messaging
adapters), `standard_printer_preset`, `process_presets`, `filament_presets`, `bed_type`,
`eject_cool_temp_c` (default 30), `watch_interval` (default `2m`; the watcher counts as running for three
intervals after a pass, at least 10 minutes), `local_is_owner` (default true) and `inject_context`
(`auto`, `always` or `never`).

**Auto-eject** needs a printer that is tilted forward and a Bambuddy printer preset whose end G-code
pushes the cooled part off. The plugin does not ship this G-code and never sends G-code itself. The push
happens at the end of the print, inside the end G-code: the A1 still reports RUNNING at 100 % while the
bed cools and the nozzle pushes, and reports FINISH after the push. At FINISH the watcher checks the plate
with the camera at once. The skill reference `skills/household-printing/references/auto-eject.md`
explains the concept. Run the first tests with a person present.

## Tools

| Tool | What it does | Owner approval |
|---|---|---|
| `home3d_status` | Printer, queue, household jobs, plate state, watcher freshness | No |
| `home3d_camera` | Lit photo from the printer camera; optional plate check | No |
| `home3d_find_models` | MakerWorld cards (licence, print time, grams) from links or ids | No |
| `home3d_import` | Import a MakerWorld model into the Bambuddy library; records who asked | No |
| `home3d_customize` | Scale a model, or render a name tag or label box (OpenSCAD) | No |
| `home3d_design` | Design a part in OpenSCAD: render the agent's code to an STL with preview pictures, keep versions, upload for slicing | No |
| `home3d_slice` | Slice with the right presets; auto-eject only when the part is safe to push | No |
| `home3d_queue` | Add (always manual start), list, or remove a waiting workshop item: your own, or (the owner, present) someone else's. Never a job queued outside the workshop | No |
| `home3d_start` | Start a queued print after the safety gate | **Yes** |
| `home3d_stop` | Stop or pause: anyone, always. Resume: owner | Resume only |
| `home3d_clear_plate` | Check the plate, or confirm that it is clear | Confirm only |
| `home3d_household` | Who asked for what; remember facts and notes | No |
| `home3d_human_needed` | Log a moment when a person had to step in | No |
| `home3d_upgrades` | List and manage upgrade proposals | No |

Also: the `/home3d` slash command (`status`, `approve start <id> [jump]`, `approve clear`,
`approve resume [ack]`, `whoami`, `upgrades`, `moments`, `help`), the `hermes home3d` terminal command
(`setup`, `teardown`, `watch`, `status`, `doctor`, `simulate`, `demo`), the hooks `pre_tool_call`,
`post_tool_call` and `pre_llm_call`, and the skills `home-3d-workshop:household-printing` and
`home-3d-workshop:parametric-design`.

## Safety model

The rules are in code, not only in the prompt.

- **Gates.** Before a start, the code checks: the printer is online and idle, no active HMS error, the
  camera thinks the plate is empty (with the chamber light on), and no other person's job waits ahead: a
  job queued outside the workshop, or another household member's workshop job (unless the owner adds
  `jump`). The tool checks the plate with the camera right before the action, and so does
  `/home3d approve`. After a failed print, the owner must confirm that the plate is clear
  (`/home3d approve clear`). The confirmation counts only for the failed print it was made on (same job,
  layer and progress), so a later failure of the same file needs a new one. The watcher remembers the
  failure, so this holds even when the printer is restarted or the print was cancelled to idle (if the
  watcher saw the failure). A plate clear needs a cool bed. If the code is not sure, it blocks.
- **Camera doubt.** Bambuddy reads an empty plate at 18-25 %. The code calls that "not sure", never
  "empty". The owner can overrule exactly this doubt with `/home3d approve clear` after looking at the
  plate; the next start then accepts it. A plate the camera sees as occupied, or a check in the dark,
  is never overruled.
- **Owner approval.** Start, resume and "plate is clear" need the owner. In the owner's own session,
  Hermes shows its approval prompt. A family member or an unknown sender is blocked before any printer
  call. The block message gives the owner's command, for example `/home3d approve start <id>`. This
  command runs the gate again and runs the action at once. Nothing is stored for later.
- **Requests reach the owner.** When a household member is blocked, the plugin records the request. The
  watcher tells the owner on its next pass, once, with the exact command. If the watcher is not running,
  or no owner chat (`owner_target`) is set, the block says so, and the person must ask the owner directly.
  Once the owner has acted on a request, a new ask is a new request. A request from an unknown sender is not
  passed on.
- **No shortcut around the hook.** The tool itself refuses a start, resume or plate confirm without a
  single-use pass from that approval. A call that skips the hook does nothing.
- **A bounded hook.** Hermes gives each hook callback 30 seconds. If `pre_tool_call` times out, Hermes
  blocks every tool call of the process for 60 seconds, stop included. So the hook never uses the camera
  or the chamber light. It reads only the printer status and the queue, at most 5 seconds per request and
  12 seconds in all. If the printer does not answer in time, the hook blocks the call. If you set Hermes'
  `plugins.hook_callback_timeout` below 30 seconds, the hook allows itself 0.4 of it instead, and
  `hermes home3d doctor` warns below 15 seconds.
- **Never from cron, never unattended.** Scheduled runs cannot start, resume or clear. Neither can runs
  with nobody present: kanban workers, `hermes chat -q`, `hermes -z` and `--source tool` integrations.
  Both checks fail closed.
- **Resume after an error.** With an active HMS error, resume also needs an explicit acknowledgement
  (`/home3d approve resume ack`). The acknowledgement covers only the error codes the owner was shown;
  a new error blocks the resume.
- **Stop always works.** Anyone can stop or pause a print. No approval, no gate.
- **Queue is safe.** The plugin always adds items with manual start. Nothing it queues starts by itself.
  It never removes, postpones or reorders another person's job: not one queued outside the workshop, and
  not another household member's workshop job, even when the owner asks. People remove their own waiting
  items; the owner can remove any item by hand in Bambuddy.
- **Bambuddy's own queue.** Bambuddy can start its own auto-start items when a print ends. With its
  "Require plate clear" setting off, it may start one on a finished printer before the camera check,
  for example on top of a part that the push missed. Turn the setting on. `hermes home3d doctor` warns
  when it is off and an auto-eject preset is set.

Choose "approve once". Every printer action asks again; "always" does not carry over.

## Zero-token watcher

`hermes home3d setup` creates one Hermes cron job:

```bash
hermes cron create "every 2m" --name home3d-watch --no-agent --script home3d_watch.py --deliver local
```

Each run is a short Python process. It calls no model and costs no tokens. It reads the printer and the
queue, and it uses the camera only when it needs to. It speaks only when something happens: finish
(with the photo taken before the push), failure, pause, a new HMS error, plate not clear, plate clear,
next job ready, a household member's request for the owner's approval, a start that did not happen
(with Bambuddy's error), a job queued outside the workshop (once per item), printer offline and back
again, a print someone stopped (owner only: not a failure), a chamber light it could not switch off
again, or a new upgrade proposal. If the owner's message cannot be sent, a household member's request
stays pending and the next pass tries again. The owner gets the technical note with
a photo. The family gets one plain line that names the person who asked, and the thing they asked for
in their own words. Empty output sends nothing.

The job runs only while the Hermes scheduler runs (`hermes gateway`). Each pass reads the plugin
settings from `config.yaml`; the snapshot that setup writes is only a fallback.

The watcher switches the chamber light itself for its camera checks. One pass switches it at most once
(the photo and the plate check share one light cycle), or twice when a camera request fails and the plate
check is tried again. It takes one "done" photo near the end of each print the workshop queued. Other
prints get no near-end photo, only one photo and plate check (one light cycle) when they end: their eject
plan is unknown, so the camera says whether the part is still there. While a plate waits for a person, or a job waits
on an idle printer, the re-checks back off: 15, 30, 60, then 120 minutes, at most 6 times. The count
starts again when the printer state, the job or the first queued item changes.

## Human-needed moments become upgrades

Each time a person must act, the plugin logs a moment: remove a part, clean the plate, swap filament,
check the camera, check a failure, measure, post-process, or approve a start. When one kind repeats
(for example, 3 part removals in 30 days), it creates an upgrade proposal for the owner. "Approve a
start" is only logged: it never becomes a proposal, because the owner's approval is a safety step on
purpose. For part
removal, the proposal is the one from the story: a tilted base (MakerWorld model 2335000) plus an
auto-eject preset. The owner accepts it, the parts print through the normal flow, and the proposal
moves to "installed".

## Disclosure

- **Network.** The plugin talks only to the Bambuddy URL you set, over HTTP on your LAN. If you set
  `HOME3D_BAMBUDDY_API_KEY`, it goes in the `X-API-Key` header, unencrypted over plain HTTP. MakerWorld
  lookups and downloads go through Bambuddy; Bambuddy contacts makerworld.com, the plugin does not.
- **Printer writes.** Import, scale, design upload, slice and queue add write to the Bambuddy library
  and queue without an approval prompt. A photo or a plate check switches the chamber light on for about 12
  seconds and then sets it back to its earlier state.
- **Chamber light from the background job.** The cron watcher switches the light by itself for its plate
  checks and photos: at most once per pass (twice when a camera request fails), one photo near the end of
  each workshop print, a check when a print ends, and re-checks that back off from 15 to 120 minutes (at
  most 6) while a plate or a job waits. See "Zero-token watcher".
- **Bambuddy setting.** The plugin reads Bambuddy's settings (`GET /settings/`) and changes none. Turn
  on "Require plate clear" when you use auto-eject. With it off, Bambuddy may start a queued auto-start
  item on a finished printer before the camera check. `hermes home3d doctor` warns about this.
- **Approvals.** In an owner session, Hermes `yolo` or `approvals.mode: off` skips the prompt. An answer
  of "always" adds one `command_allowlist` line to `config.yaml` that never matches again. The owner is
  whoever is in `owner_ids`, plus anyone in a local CLI, TUI or Desktop session while `local_is_owner`
  is true. Slash commands typed in the TUI, Desktop or the web dashboard reach the plugin without a
  sender, so whoever can use those surfaces counts as the owner for `/home3d approve`. Turn
  `local_is_owner` off if your dashboard is shared or reachable from outside. Runs with nobody present
  (cron, kanban workers, `chat -q`, `-z`, `--source tool`) are never treated as the owner for a printer
  action.
- **Hook time.** `pre_tool_call` reads only the printer status and the queue (at most 5 seconds per
  request, 12 seconds in all) and never the camera, so it stays inside Hermes' 30-second hook limit. With
  a lower `plugins.hook_callback_timeout` it allows itself 0.4 of that limit.
- **Hermes internals.** To find cron and unattended runs, the plugin uses the public
  `ctx.current_cron_execution()`. It also reads Hermes internals that are not public API:
  `gateway.session_context.get_session_env`, `cron.execution_identity._CURRENT` and
  `gateway.session_finite`. It takes them from `sys.modules` and never imports or changes them. A check
  that raises counts as cron or unattended (fail closed). If a later Hermes renames one of them, that
  extra check is skipped; the public cron check and Hermes' own approval prompt stay. To size its hook
  deadline it also reads `hermes_cli.plugins._resolve_hook_callback_timeout` the same way (missing or
  failing: Hermes' default of 30 seconds is assumed).
- **Subprocesses.** `hermes send` (owner and family notices, with `-p <send_profile>` when set),
  `hermes cron create`, `hermes cron list` and `hermes cron remove` (setup and teardown), `openscad`
  (the templates and the agent's designs, when installed: one render at a time, with a wall-clock and a
  CPU-time limit, a memory cap and a file-size cap, without `OPENSCADPATH`) and `xvfb-run` (the design
  preview pictures on a machine without a display; its X cookie file lives in the design folder and is
  deleted afterwards).
- **Background job.** One cron job, every 2 minutes by default (720 runs a day). `hermes home3d setup`
  creates it, and `hermes home3d teardown` removes it with its script. Run teardown before you remove
  the plugin; after removal, use `hermes cron remove` and delete the script yourself. While the plugin
  is disabled or removed, the script reads `config.yaml`, prints nothing and exits.
- **Files written.** `$HERMES_HOME/plugin-data/home-3d-workshop/` (database, `outbox.jsonl` with every
  message, camera photos, model files, watcher log, and a settings snapshot without secrets that the
  watcher uses only when it cannot read `config.yaml`), its `designs/` folder (each design's OpenSCAD
  source, STL, preview pictures and facts, one set per version, kept until you delete them) and
  `$HERMES_HOME/scripts/home3d_watch.py`. The demo uses a temporary folder and deletes it.
- **Personal data, kept locally.** Household sender ids and names, who asked for what, who asked the
  owner to approve what, the messages sent, camera photos of the plate, and names written into
  designs. Nothing is sent anywhere except Bambuddy and your own chats.
- **Context.** The `pre_llm_call` hook adds a short context (persona, speaker, printer state; at most
  900 characters, no network). For household members and the local owner it comes on the first turn,
  on printing turns and when the printer state changes; other turns get one "Speaking: ..." line. Other
  senders get it only on printing turns. `inject_context: never` turns it off.
- **Always on.** The tools are on for every surface, including messaging gateways (turn a surface off
  with `hermes tools`). While the plugin is enabled, its two skills add one line each to the skills
  index of every session.

## Limitations

- Bambu Lab printers through Bambuddy only. The backend interface is small, but OctoPrint and Moonraker
  backends do not exist yet.
- MakerWorld has no search here. The agent finds links with web search, and the plugin reads the cards.
  Downloads depend on your Bambuddy version and its MakerWorld login.
- The plate check is a camera estimate. Thin parts and first layers can look empty. Look at the photo.
- Auto-eject needs your own tilted base and end G-code. The code refuses PETG, TPU, thin, small and
  tall-narrow parts. It cannot see shape: the agent must turn eject off for round or fragile parts.
- Orientation and supports come from the chosen MakerWorld profile or the owner's presets. The tools do
  not rotate models or switch supports on; the skill helps choose a profile.
- Designing, and the name-tag and label-box templates, need `openscad` (and `xvfb-run` for pictures) on
  the machine that runs Hermes. The templates, a sample design and the file-access probes are tested
  with OpenSCAD 2021.01 (locally and in the CI `openscad` job). The agent's own designs are checked by the render, the numbers and the pictures, not by an
  engineer: print a small fit test before a part that must fit, and do not design parts whose failure
  can hurt someone. Scaling an existing model needs no OpenSCAD.
- A design is one STL in one colour. A two-colour part is rendered as two parts, and the owner
  combines them in a slicer.
- Voice notes depend on the Hermes gateway's transcription.
- Messages are in English and Turkish only. Tested on Linux only.
- The sender id comes from the messaging platform. Check it with `/home3d whoami` before you trust it.

## License

MIT. See [LICENSE](LICENSE).
