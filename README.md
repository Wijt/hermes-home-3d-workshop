# home-3d-workshop

A Hermes Agent plugin that gives a household a 3D-printing service with a character.

Family members ask in plain words, often by voice note. The agent finds or adapts a model, slices it and
queues it. The owner approves the start. A zero-token watcher follows the print, tells the owner and the
family what happened, and checks that the build plate is clear for the next job. Each time a person must
step in, the plugin records it. When the same need repeats, it proposes an upgrade to the workshop.

The character is called **Mıstık** by default. You can change the name (`persona_name`) and the language
of the messages (`language`: `tr` or `en`). The default language is Turkish, the language of the home
it comes from; set `language: en` for English.

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
unnoticed for about four hours. Of more than 300 runs of the old agent watch jobs, about nine in ten had
nothing to report. After it missed a failure, the agent changed its own rule: "Better to stop by
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
| Start, stop, pause, resume, mark plate clear | Planned | Verified |
| Watcher notices sent with `hermes send` | Planned | Verified (dry run, outbox only) |
| Auto-eject push on the tilted base | Real in the original setup; with this plugin: planned | Simulated |

`hermes plugins validate . --install-deps` passes on Hermes 0.22.5 (also in CI), and
`hermes plugins install Wijt/hermes-home-3d-workshop` installs it. The real-hardware loop with this
plugin is **planned, not done**. The family uses the printer every
day, so we test on it only when no family job waits.

## Install

Requires Hermes **0.22.5 or newer**. The plugin uses only the Python standard library.

```bash
hermes plugins install Wijt/hermes-home-3d-workshop --enable
```

Hermes shows a banner for a Git install, because nobody reviewed it yet. The plugin starts with the
simulated printer, so it does nothing to real hardware until you configure Bambuddy.

## Quick try: the simulator

```bash
hermes home3d demo              # under 10 seconds, English, nothing is sent
hermes home3d demo --lang tr    # the same run in Turkish
```

The demo runs the full loop on a simulated printer in a temporary folder: a request, model cards,
import, scale, slice, queue, a blocked start from a family member, the owner's approval, the print, the
messages to the owner and the family, auto-eject, a missed push, a failure, a filament-runout pause, and
an upgrade proposal. Scripted stand-ins (such as canned search results and the owner's tap on
"approve") are marked `[staged]`.

You can also talk to the agent while the simulator is active. Ask it to print a coaster. Then move the
simulated time forward and run one watcher pass:

```bash
hermes home3d simulate advance 60 --watch
hermes home3d simulate scenario eject_miss   # also: ok, fail, pause_hms, busy, offline
```

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
   in `owner_ids` or `household`.
4. Start the watcher: `hermes home3d setup`. Remove it again with `hermes home3d teardown`.

Other settings: `public_url` (links sent to people), `send_profile` (the profile that owns the messaging
adapters), `standard_printer_preset`, `process_presets`, `filament_presets`, `bed_type`,
`eject_cool_temp_c` (default 30), `watch_interval` (default `2m`), `local_is_owner` (default true) and
`inject_context` (`auto`, `always` or `never`).

**Auto-eject** needs a printer that is tilted forward and a Bambuddy printer preset whose end G-code
pushes the cooled part off. The plugin does not ship this G-code and never sends G-code itself. The
skill reference `skills/household-printing/references/auto-eject.md` explains the concept. Run the
first tests with a person present.

## Tools

| Tool | What it does | Owner approval |
|---|---|---|
| `home3d_status` | Printer, queue, household jobs, plate state, watcher freshness | No |
| `home3d_camera` | Lit photo from the printer camera; optional plate check | No |
| `home3d_find_models` | MakerWorld cards (licence, print time, grams) from links or ids | No |
| `home3d_import` | Import a MakerWorld model into the Bambuddy library; records who asked | No |
| `home3d_customize` | Scale a model, or render a name tag or label box (OpenSCAD) | No |
| `home3d_slice` | Slice with the right presets; auto-eject only when the part is safe to push | No |
| `home3d_queue` | Add (always manual start), list, or remove your own waiting items | No |
| `home3d_start` | Start a queued print after the safety gate | **Yes** |
| `home3d_stop` | Stop or pause: anyone, always. Resume: owner | Resume only |
| `home3d_clear_plate` | Check the plate, or confirm that it is clear | Confirm only |
| `home3d_household` | Who asked for what; remember facts and notes | No |
| `home3d_human_needed` | Log a moment when a person had to step in | No |
| `home3d_upgrades` | List and manage upgrade proposals | No |

Also: the `/home3d` slash command (`status`, `approve start <id> [jump]`, `approve clear`,
`approve resume [ack]`, `whoami`, `upgrades`, `moments`), the `hermes home3d` terminal command (`setup`,
`teardown`, `watch`, `status`, `doctor`, `simulate`, `demo`), the hooks `pre_tool_call`,
`post_tool_call` and `pre_llm_call`, and the skill `home-3d-workshop:household-printing`.

## Safety model

The rules are in code, not only in the prompt.

- **Gates.** Before a start, the code checks: the printer is online and idle, no active HMS error, the
  camera thinks the plate is empty (with the chamber light on), and no other person's job waits ahead
  (unless the owner adds `jump`). After a failed print, the owner must confirm that the plate is clear
  (`/home3d approve clear`). The watcher remembers the failure, so this holds even when the printer is
  restarted or the print was cancelled to idle (if the watcher saw the failure). A plate clear needs a
  cool bed. If the code is not sure, it blocks.
- **Camera doubt.** Bambuddy reads an empty plate at 18-25 %. The code calls that "not sure", never
  "empty". The owner can overrule exactly this doubt with `/home3d approve clear` after looking at the
  plate; the next start then accepts it. A plate the camera sees as occupied, or a check in the dark,
  is never overruled.
- **Owner approval.** Start, resume and "plate is clear" need the owner. In the owner's own session,
  Hermes shows its approval prompt. A family member or an unknown sender is blocked. The block message
  gives the owner's command, for example `/home3d approve start <id>`. This command runs the gate again
  and runs the action at once. Nothing is stored for later.
- **No shortcut around the hook.** The tool itself refuses a start, resume or plate confirm without a
  single-use pass from that approval. A call that skips the hook does nothing.
- **Never from cron, never unattended.** Scheduled runs cannot start, resume or clear. Neither can runs
  with nobody present: kanban workers, `hermes chat -q`, `hermes -z` and `--source tool` integrations.
  Both checks fail closed.
- **Resume after an error.** With an active HMS error, resume also needs an explicit acknowledgement
  (`/home3d approve resume ack`). The acknowledgement covers only the error codes the owner was shown;
  a new error blocks the resume.
- **Stop always works.** Anyone can stop or pause a print. No approval, no gate.
- **Queue is safe.** Items are always added with manual start. Nothing starts by itself.

Choose "approve once". Every printer action asks again; "always" does not carry over.

## Zero-token watcher

`hermes home3d setup` creates one Hermes cron job:

```bash
hermes cron create "every 2m" --name home3d-watch --no-agent --script home3d_watch.py --deliver local
```

Each run is a short Python process. It calls no model and costs no tokens. It reads the printer and the
queue, and it uses the camera only when it needs to. It speaks only when something happens: finish
(with the photo taken before the push), failure, pause, a new HMS error, plate not clear, plate clear,
next job ready, a job queued outside the workshop (once per item), printer offline, a chamber light it
could not switch off again, or a new upgrade proposal. The owner gets the technical note with a
photo. The family gets one plain line that names the person who asked, and the thing they asked for in
their own words. Empty output sends nothing.

## Human-needed moments become upgrades

Each time a person must act, the plugin logs a moment: remove a part, clean the plate, swap filament,
check the camera, check a failure, measure, post-process, or approve a start. When one kind repeats
(for example, 3 part removals in 30 days), it creates an upgrade proposal for the owner. For part
removal, the proposal is the one from the story: a tilted base (MakerWorld model 2335000) plus an
auto-eject preset. The owner accepts it, the parts print through the normal flow, and the proposal
moves to "installed".

## Disclosure

- **Network.** The plugin talks only to the Bambuddy URL you set, over HTTP on your LAN. If you set
  `HOME3D_BAMBUDDY_API_KEY`, it goes in the `X-API-Key` header, unencrypted over plain HTTP. MakerWorld
  lookups and downloads go through Bambuddy; Bambuddy contacts makerworld.com, the plugin does not.
- **Printer writes.** Import, scale, slice and queue add write to the Bambuddy library and queue
  without an approval prompt. A photo switches the chamber light on for about 12 seconds and then sets
  it back to its earlier state.
- **Approvals.** In an owner session, Hermes `yolo` or `approvals.mode: off` skips the prompt. An answer
  of "always" adds one `command_allowlist` line to `config.yaml` that never matches again. The owner is
  whoever is in `owner_ids`, plus anyone in a local CLI, TUI or Desktop session while `local_is_owner`
  is true. Slash commands typed in the TUI, Desktop or the web dashboard reach the plugin without a
  sender, so whoever can use those surfaces counts as the owner for `/home3d approve`. Turn
  `local_is_owner` off if your dashboard is shared or reachable from outside. Runs with nobody present
  (cron, kanban workers, `chat -q`, `-z`, `--source tool`) are never treated as the owner for a printer
  action.
- **Subprocesses.** `hermes send` (owner and family notices, with `-p <send_profile>` when set),
  `hermes cron create`, `hermes cron list` and `hermes cron remove` (setup and teardown), and `openscad`
  (templates only, when installed).
- **Background job.** One cron job, every 2 minutes by default (720 runs a day). `hermes home3d setup`
  creates it, and `hermes home3d teardown` removes it with its script. Run teardown before you remove
  the plugin; after removal, use `hermes cron remove` and delete the script yourself. While the plugin
  is disabled or removed, the script reads `config.yaml`, prints nothing and exits.
- **Files written.** `$HERMES_HOME/plugin-data/home-3d-workshop/` (database, `outbox.jsonl` with every
  message, camera photos, model files, watcher log, a settings snapshot without secrets) and
  `$HERMES_HOME/scripts/home3d_watch.py`. The demo uses a temporary folder and deletes it.
- **Personal data, kept locally.** Household sender ids and names, who asked for what, the messages
  sent, and camera photos of the plate. Nothing is sent anywhere except Bambuddy and your own chats.
- **Context.** The `pre_llm_call` hook adds a short context (persona, speaker, printer state; at most
  900 characters, no network). For household members and the local owner it comes on the first turn,
  on printing turns and when the printer state changes; other turns get one "Speaking: ..." line. Other
  senders get it only on printing turns. `inject_context: never` turns it off.
- **Always on.** The tools are on for every surface, including messaging gateways (turn a surface off
  with `hermes tools`). While the plugin is enabled, its skill adds one line to the skills index of
  every session.

## Limitations

- Bambu Lab printers through Bambuddy only. The backend interface is small, but OctoPrint and Moonraker
  backends do not exist yet.
- MakerWorld has no search here. The agent finds links with web search, and the plugin reads the cards.
  Downloads depend on your Bambuddy version and its MakerWorld login.
- The plate check is a camera estimate. Thin parts and first layers can look empty. Look at the photo.
- Auto-eject needs your own tilted base and end G-code. The code refuses PETG, TPU, thin, small and
  tall-narrow parts. It cannot see shape: the agent must turn eject off for round or fragile parts.
- Voice notes depend on the Hermes gateway's transcription.
- Messages are in Turkish and English only. Tested on Linux only.
- The sender id comes from the messaging platform. Check it with `/home3d whoami` before you trust it.

## License

MIT. See [LICENSE](LICENSE).
