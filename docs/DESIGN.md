# home-3d-workshop — design contract

This file is the single contract between modules. Code against the signatures here. Already written (do
not change signatures without updating this file): `plugin.yaml`, `__init__.py`, `home3d/__init__.py`,
`home3d/config.py`, `home3d/backends/base.py`, `home3d/backends/__init__.py`, `home3d/store.py`,
`home3d/runtime.py`.

## Goals (what the jury must see)
A household 3D-printing service with a character ("Mıstık" by default). Family members ask in plain
language (often voice notes, transcribed by the Hermes gateway). Lifecycle:
request → find (MakerWorld via Bambuddy) or customise → slice (auto-eject preset when safe) → queue
(manual start) → owner-approved start → zero-token watch → failure handling → notify owner (technical +
photo) and family (one plain line, by name) → verify plate clear → next job; every moment a human had to
step in is logged and, past a threshold, becomes an **upgrade proposal** (e.g. the printed tilt-base
auto-eject mod). Safety lives in code (gates + pre_tool_call), not in prose.

## Hard rules for all code
- Python ≥3.11, **stdlib only** at import time. Optional: `PIL` (Pillow ships with Hermes) — import inside
  functions with a fallback. No new pip dependencies.
- Never import Hermes modules at module top level. Import inside functions, wrapped in `try/except`, so
  the package works in tests/CI without Hermes and inside the cron watcher script.
- Relative imports inside `home3d` (the plugin dir is loaded as `hermes_plugins.<slug>`; the watcher
  script loads it via `importlib` spec).
- Tool handlers: `def handler(args: dict, **kwargs) -> str` — always return a JSON string, never raise.
  Envelope: `{"ok": true, ...}` or `{"ok": false, "error": "...", ...}`.
- No personal data, IPs, serials, group ids or secrets in the repo. Examples use `192.168.1.50`,
  `whatsapp:<group>@g.us`, names like "Mum", "Dad", "Sam".
- English code/comments; user-facing strings via `messages.py` (tr + en).
- Secrets only via `config.get_api_key()` (wraps `agent.secret_scope.get_secret`).
- Real printer: implementers may only use **HTTP GET** against the owner's live Bambuddy (its LAN address is
  never written into the repo) to verify parsing. Never POST/PUT/PATCH/DELETE to it.

## Backend contract — `home3d/backends/base.py` (written)
See the file. Backends: `bambuddy.BambuddyBackend(base_url, printer_id=1, api_key="", public_url="")`
and `simulator.SimulatorBackend(state_path: Path | None = None)`.

### Bambuddy mapping (verified against Bambuddy's OpenAPI spec, `GET /api/v1/openapi.json`, and the slice-API
recipe of the system this plugin was distilled from)
- status: `GET /printers/{id}/status` → state, progress, remaining_time (min), layer_num/total_layers,
  temperatures.bed/bed_target/nozzle, hms_errors[] (`full_code` or code fields), ams[0].tray[] (id, tray_type,
  tray_color RRGGBBAA → `#RRGGBB`, remain, tray_sub_brands). `connected:false` → state OFFLINE.
- queue: `GET /queue/?printer_id={id}` (filter out completed/cancelled/failed/skipped unless include_done),
  name = `library_file_name` or `archive_name`.
- snapshot: `POST /printers/{id}/chamber-light?on=true`, wait ~12 s, `GET /printers/{id}/camera/snapshot`,
  then **always** `POST ...chamber-light?on=false` (try/finally). Re-encode with PIL to ≤1280 px JPEG q88
  (raw frames lack a JFIF header and WhatsApp shows them broken). Only turn the light on if it was off is not
  knowable → always restore to off.
- check_plate: `GET /printers/{id}/camera/check-plate` → is_empty, difference_percent, confidence,
  needs_calibration, message. Known false positives at 18–25 % on an empty plate → treat
  `difference_pct < 26 and not is_empty` as `is_empty=None` (uncertain), never as "empty".
- resolve_model: `POST /makerworld/resolve {url}` (a bare id → `https://makerworld.com/en/models/<id>`).
  Map design.id/title/coverUrl/designCreator.name/license/likeCount/downloadCount/printCount/summary,
  instances[] → profileId/title/compatibility.devProductName/prediction(print time s)/weight,
  already_imported_library_ids. URL fragment `#profileId-NNN` is an *instance id*, not a profileId.
- import_model: `GET /makerworld/status` (`can_download` must be true) then
  `POST /makerworld/import {model_id, profile_id}` → library_file_id.
- upload_file: `POST /library/files` multipart field `file`. download_file: `GET /library/files/{id}/download`.
- slice: `POST /library/files/{id}/slice` (SliceRequest; presets as `{"source":"local","id":"<id>"}` for numeric
  ids, `"<source>:<id>"` (e.g. `cloud:GP079`) for another source, else `{"source":"standard","id":"<name>"}` (the
  OpenAPI `PresetRef` requires `id`, not `name`); `export_3mf: true`), poll `GET /slice-jobs/{job_id}` until
  done (2 s → 5 s backoff, timeout) → `result.library_file_id`; then `library_gcode` for G-code text.
  Default `process_overrides` from the recipe (arachne, z_hop 0.4 Slope Lift, no prime tower, no brim).
- library_gcode: `GET /library/files/{id}/gcode` (plain text).
- queue_add: `POST /queue/` with `{library_file_id, printer_id, manual_start, ams_mapping, plate_id,
  bed_levelling:"off", flow_cali:"off", vibration_cali:false}` — always send the three calibration fields.
- queue_remove: `DELETE /queue/{id}`. start: `POST /queue/{id}/start`.
- stop/pause/resume: `POST /printers/{id}/print/stop|pause|resume`. mark_plate_cleared:
  `POST /printers/{id}/clear-plate`. recent_archives: `GET /archives/?limit=`.
- preview_url(file): `{public_url}/gcode-viewer?library_file={id}&plate=1`.
- HTTP: `urllib.request`, timeout 20 s (slice/import 60 s), header `X-API-Key` when set; on HTTP error raise
  `BackendError("<METHOD> <path>: <status> <short body>")`.

### Simulator (`backends/simulator.py`)
- State JSON at `data_dir()/simulator.json` (or `state_path`), shared by tools and the watcher process, with
  a file lock (`fcntl.flock`) around read-modify-write.
- Virtual clock: `sim_now = real_now * 0 + base + (real_elapsed * speed) + offset`; speed from env
  `HOME3D_SIM_SPEED` (default 60: one real second = one simulated minute). `advance(minutes)` adds offset.
- Scenarios (`set_scenario(name)`): `ok` (default), `fail` (FAILED at 40 %), `pause_hms` (PAUSE with HMS
  `0700-2000-0002-0001` filament runout at 30 %), `eject_miss` (finishes, but the plate is still occupied
  afterwards), `busy` (a family job already queued ahead).
- Library seeded with two demo models; `resolve_model` returns a deterministic card for any MakerWorld URL/id
  (title from a small built-in list, license "Standard Digital File License" or "CC BY", two instances, one
  A1-compatible). `slice()` produces synthetic G-code with Bambu-style header comments
  (`; total estimated time`, `; total filament weight [g]`, `; printer_model = Bambu Lab A1`, `; max_z_height`),
  `; Z_HEIGHT:` layer markers, a first-layer footprint, and — if the printer preset equals the configured
  auto-eject preset id or `"sim-autoeject"` — an end block containing `; HOME3D AUTO-EJECT`.
- Print progression: start → PREPARE (2 sim-min) → RUNNING (duration from the slice) → FINISH;
  bed cools from 65 °C to room temp over ~20 sim-min after FINISH. If the job had the eject marker and the
  scenario is not `eject_miss`, the plate becomes empty ~15 sim-min after FINISH; otherwise occupied until
  `mark_plate_cleared()`/`human_clears_plate()`.
- snapshot: writes a PNG (pure-python zlib PNG writer, 320×240) showing an empty plate or a plate with a
  part; returns `Snapshot(path, lit=True, note="simulated")`.
- Extra simulator-only helpers: `advance(minutes)`, `set_scenario(name)`, `human_clears_plate()`, `reset()`.

## Pure logic
### `home3d/gcode.py`
```python
EJECT_MARKERS = ("HOME3D AUTO-EJECT", "HERMES AUTO-EJECT")
@dataclass class GcodeInfo:
    printer_model: str; print_time_s: int|None; filament_g: float|None; filament_types: list[str]
    nozzle_temps: list[float]; bed_temps: list[float]; max_z: float|None; layer_count: int
    first_layer_bbox: tuple[float,float,float,float]|None  # xmin,xmax,ymin,ymax of extrusion moves at the first Z
    has_eject_marker: bool; prime_tower: bool; warnings: list[str]
def inspect_gcode(text: str) -> GcodeInfo
def footprint_at(text: str, z: float) -> tuple[float,float,float,float]|None
@dataclass class EjectAssessment: eligible: bool; reasons: list[str]; push_z: float|None
def assess_eject(info: GcodeInfo, material: str = "PLA", *, min_height_mm=3.0,
                 min_footprint_mm=15.0, max_aspect=2.5) -> EjectAssessment
```
Eject rules (from the real system): only sturdy flat PLA-like parts; refuse PETG/TPU/flexible; refuse
height < 3 mm (push misses thin parts) unless footprint large; refuse tall-narrow (height / min footprint
side > max_aspect); refuse tiny footprint (< 15 mm side → rolls/falls wrong); refuse round small parts is
not detectable → note "check shape". Warnings: printer model not A1 (e.g. A1 mini file), prime tower on,
bed temp mismatch with material, nozzle temp outside material range (PLA 190–230, PETG 220–260).

### `home3d/gates.py`
```python
@dataclass class Gate: ok: bool; reasons: list[str] = []; warnings: list[str] = []; needs_owner: bool = False
def start_gate(status: PrinterStatus, queue: list[QueueItem], item_id: int, *, plate: PlateCheck|None,
               in_cron: bool, own_item_ids: set[int], allow_jump: bool = False,
               voice_request: bool = False) -> Gate
def clear_plate_gate(status: PrinterStatus, plate: PlateCheck|None, *, in_cron: bool,
                     cool_temp_c: float, auto_start_pending: list[QueueItem]) -> Gate
def describe(gate: Gate, lang: str) -> str
```
start_gate blocks (ok=False) when: in_cron; printer OFFLINE / not connected; printer active
(PREPARE/RUNNING/PAUSE); any blocking HMS; item not found or not pending; plate check not explicitly empty
(`is_empty is not True`) — state FAILED/FINISH needs a cleared plate first; another *pending* item that is
not ours (`own_item_ids`) sits ahead of it and `allow_jump` is False ("never jump someone else's job").
`needs_owner` is always True for start (approval is enforced by hooks). `voice_request` adds a warning that
a written confirmation is required (enforced in hooks).
clear_plate_gate blocks when: in_cron; printer active; bed hotter than cool_temp_c; plate check says not
empty or unknown; and when non-manual pending items exist (marking the plate clear would let the manager
auto-start them) → reason "auto-start items pending".

### `home3d/eject.py` — plate-clear state machine
```python
PHASES = ("idle", "printing", "finished", "cooling", "ejecting", "verifying", "clear", "needs_human")
@dataclass class PlateState: phase: str; job_name: str = ""; eject_planned: bool = False;
    finished_ts: float|None = None; checks: int = 0; last_check: dict|None = None; reason: str = ""
def step(prev: PlateState, status: PrinterStatus, now: float, *, eject_planned: bool,
         plate: PlateCheck|None, cool_temp_c: float = 30.0, eject_window_s: float = 20*60,
         max_checks: int = 3) -> tuple[PlateState, list[str]]   # returns new state + emitted event kinds
def needs_plate_check(state: PlateState, status: PrinterStatus, now: float, cool_temp_c=30.0) -> bool
```
Events emitted: `finished`, `failed`, `plate_clear`, `plate_not_clear` (→ needs_human), `eject_unverified`.
When eject is planned the baked end-G-code pushes the part; the machine waits for the bed to cool and the
eject window to pass, then asks for a plate check (camera + check-plate); empty → `clear`; not empty after
`max_checks` → `needs_human`. Without an eject plan, FINISH goes straight to `needs_human` ("please take the
part off") unless a check says empty.

## Notifications
### `home3d/messages.py`
```python
def render(kind: str, audience: str, lang: str, **ctx) -> str   # audience: "owner" | "family"
```
Kinds: `started, finished, finished_ejected, plate_not_clear, failed, paused, hms, offline, ready_next,
upgrade_proposed, eject_skipped`. ctx keys: persona, job, requester, address_as, progress, layer, total_layers,
duration_min, grams, hms_code, hms_message, wiki_url, reason, next_job, upgrade_title, preview_url.
Family tone: one or two short lines, warm, plain words, no jargon, addresses the requester (`address_as`)
when known, never English inside Turkish. Owner tone: technical (state, layer, temps, HMS, links), still short.
Examples (tr, family): `✅ Anneciğim, "Gül kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin.`
`⚠️ Yazıcı durdu, "X" yarıda kaldı (%40). Sam'a haber verdim.` (owner name from ctx, never hardcoded)

### `home3d/notify.py`
```python
@dataclass class Delivery: target: str; ok: bool; error: str = ""; dry_run: bool = False
def send(settings: Settings, target: str, text: str, media: Path|None = None) -> Delivery
def notify(settings: Settings, *, owner_text: str|None, family_text: str|None,
           media: Path|None = None, owner_media_only: bool = True) -> list[Delivery]
```
Uses `hermes [-p <send_profile>] send -t <target> --json "<text>\nMEDIA:<abs path>"` via `subprocess.run`
(timeout 60 s), parses `{"success": true}`, retries once. Hermes binary: `shutil.which("hermes")`, else
`Path(sys.executable).parent / "hermes"`. Every message is also appended to `data_dir()/outbox.jsonl`
(ts, audience, target, text, media, ok) — the simulator/demo shows it. Empty target → dry_run=True (outbox only).
Family messages get no photo unless the event is `finished*` (a photo of the finished part is nice).

## Watcher — `home3d/watcher.py`
```python
def run_once(settings: Settings, backend: Backend, store: Store, *, now: float|None = None,
             deliver: bool = True, out_dir: Path|None = None) -> list[dict]
def main(argv: list[str]|None = None) -> int     # cron --no-agent entry point
```
Zero tokens: no model calls. Keeps `store.kv('watcher')` = {state, job_name, hms_codes, plate_state,
photo_for_job, offline_since, ready_notified_for}. Each run:
1. `status = backend.status()` (on BackendError → offline handling: notify owner once after 10 min).
2. Detect transitions: →RUNNING (record job start; no message), last layer reached and no photo yet → take
   snapshot for the "done" photo (before the eject push), →FINISH, →FAILED, →PAUSE, new blocking HMS.
3. Feed `eject.step()`; when it wants a plate check, call `backend.check_plate()` (+ snapshot for owner).
4. For each event: `store.add_event`, compose owner + family texts (`messages.render`), resolve requester
   from `store.job_by_name(job)` / request, deliver via `notify.notify` (if deliver), record notified flags.
5. Human-needed: `plate_not_clear` → `store.add_human_needed("remove_part", ...)`; `failed` →
   `("failure_check")`; `paused` with filament HMS → `("filament_swap")`; then `upgrades.evaluate(store,
   settings)` and announce new proposals to the owner once.
6. Idle + plate clear + pending items → `ready_next` to owner once per item (never auto-start).
`main()`: loads settings from the snapshot (`config.load_settings()`), builds the backend, runs once,
prints owner texts to stdout only when `settings.owner_target` is empty (so a cron `--deliver` target still
works), otherwise prints nothing (empty stdout = silent cron). Exit 0 even on backend errors (logged to
`data_dir()/watcher.log`).
`scripts/home3d_watch.py` is the template the CLI copies to `$HERMES_HOME/scripts/`: it has `PLUGIN_DIR`
baked in at setup time, loads the package with `importlib.util.spec_from_file_location("home3d_ws",
PLUGIN_DIR/"__init__.py", submodule_search_locations=[PLUGIN_DIR])`, then `home3d_ws.home3d.watcher.main()`.

## Upgrades — `home3d/upgrades.py`
```python
KINDS: dict[str, dict]   # kind -> {"label", "threshold", "window_days", "title", "proposal", "model_ref"}
def log_moment(store, kind, detail="", *, job_name="", who="", source="agent") -> int
def evaluate(store: Store, settings: Settings) -> list[dict]   # newly created proposals
```
Kinds: `remove_part` (threshold 3 / 30 days → "Auto-eject: tilt the printer forward ~15° on a printed base and
let the nozzle push cooled parts off; slice sturdy PLA parts with the auto-eject preset", model_ref
"https://makerworld.com/en/models/2335000"), `clean_plate`, `filament_swap` (register spools / AMS slot
mapping), `camera_check` (re-aim / external camera / recalibrate plate detection), `failure_check`
(enable failure detection pause), `measure` (ask for a photo with a coin / ruler), `post_process`,
`approve_start` (owner approval friction → standing approval window), `other`. A kind with an existing
non-rejected proposal only gets its evidence count bumped. Proposal statuses advance through the tool:
proposed → accepted → printing (parts queued through the normal flow) → installed.

## Customise — `home3d/customize.py`
```python
def scale_model(src: Path, factor: float, out: Path) -> Path      # .stl (ascii/binary) and .3mf
def model_bbox(src: Path) -> tuple[float,float,float]             # size x,y,z in mm
def openscad_available() -> bool
TEMPLATES: dict[str, dict]   # name -> {"file": "name_tag.scad", "params": {...defaults}, "description"}
def render_template(name: str, params: dict, out: Path) -> Path    # needs openscad
```
3MF scaling multiplies each `<build><item transform>` (or adds one) and rewrites the archive; never scales
mechanism parts automatically — the tool warns when the name contains lid/snap/hinge/thread.

## Hermes surfaces
### Tools — `home3d/tools.py`
```python
def build_tools(rt: Runtime) -> list[tuple[str, dict, Callable]]   # (name, schema, handler)
```
Descriptions: first sentence ≤ 60 chars and searchable (Tool Search defers plugin tools). All names
`home3d_*`:
| tool | args | does |
|---|---|---|
| home3d_status | — | printer + queue + jobs of this household + plate state + watcher freshness |
| home3d_camera | check_plate?:bool | lit snapshot (path + `MEDIA:` line for the reply) [+ plate check] |
| home3d_find_models | urls:[str] (MakerWorld links/ids found via web search) | cards: title, license, likes, A1 instances (profile_id, time, grams), cover; tells the agent to show 2–4 options |
| home3d_import | model_id:int, profile_id?:int, requester?:str, request_text?:str, channel?:str | import to library; records the request |
| home3d_customize | library_file_id:int, scale?:float, target_size_mm?:float, template?:str, params?:obj | scaled copy / template render, uploaded; returns new library_file_id + size |
| home3d_slice | library_file_id:int, quality?:draft/standard/fine, material?:str, colour?:str, eject?:auto/on/off, request_id?:int | slice with the right preset, inspect G-code, eject assessment, time/grams/preview link/warnings |
| home3d_queue | action: add/list/remove, sliced_file_id?, ams_slot?:int, request_id?, requester?, queue_item_id? | add always manual_start; records job + eject plan |
| home3d_start | queue_item_id:int, allow_jump?:bool | gated start (see hooks); re-checks start_gate in the handler |
| home3d_stop | action: stop/pause/resume, reason:str | stop/pause allowed for anyone ("dur" = stop now); resume gated |
| home3d_clear_plate | action: check/confirm | check = camera + plate check + temps; confirm = clear_plate_gate then mark_plate_cleared |
| home3d_household | action: who/history/remember/note, person?:str, text?:str | memory of who asked what |
| home3d_human_needed | action: log/list, kind?, detail?, who? | log a moment a person had to act |
| home3d_upgrades | action: list/evaluate/accept/reject/printing/installed, upgrade_id? | proposals derived from moments |

### Hooks — `home3d/hooks.py`
```python
def make_hooks(rt: Runtime) -> dict[str, Callable]   # {"pre_tool_call": f, "post_tool_call": g, "pre_llm_call": h}
```
- `pre_tool_call(tool_name, args, task_id="", session_id="", **kw)`: only for `home3d_start`,
  `home3d_clear_plate` (action confirm) and `home3d_stop` (action resume):
  - in cron → `{"action": "block", "message": ...}` (never start / clear / resume unattended);
  - gate fails → block with reasons;
  - a valid owner approval in the store (`/home3d approve ...`) → consume it, allow (return None);
  - sender is a known non-owner → block: "owner approval needed: owner sends `/home3d approve start <id>`";
  - else → `{"action": "approve", "message": <human summary>, "rule_key": f"home3d:{tool}:{target}:{int(time)}"}`
    (unique rule_key so "always" never sticks). Must never raise (wrap everything; on internal error → block).
- `pre_llm_call(session_id, user_message, platform, sender_id, is_first_turn, **kw)`: store
  session→sender; return `{"context": ...}` (≤ 900 chars): persona name + language + who is speaking (name,
  role, address_as) + one-line printer state from the last watcher snapshot (`store.kv_get("watcher")`, no
  network) + that person's open requests + reminder to load skill `home-3d-workshop:household-printing`
  for printing requests. Never raise.
- `post_tool_call(tool_name, args, result, session_id, **kw)`: for `home3d_*` tools parse the JSON result
  and append an audit event (`store.add_event("tool", ...)`); when a start/clear was blocked for lack of owner
  approval, log human_needed `approve_start`. Never raise.

### Slash command — `home3d/commands.py`
```python
def make_command(rt: Runtime) -> Callable   # handler(raw_args: str, source=None, session_id=None, platform=None) -> str
```
`/home3d` subcommands: `status`, `approve start <queue_id>`, `approve clear`, `whoami`, `upgrades`,
`moments`, `help`. `approve` only works when `source.user_id` (or `source.chat_id` fallback is NOT
accepted) is an owner id, or when there is no source (local CLI/TUI owner session). Grants a 15-minute
single-use approval in the store.

### CLI — `home3d/cli.py`
```python
def setup_parser(subparser) -> None; def handle(args) -> int
```
`hermes home3d setup [--interval 2m] [--print-only]` — writes the watcher snapshot, copies
`scripts/home3d_watch.py` to `$HERMES_HOME/scripts/home3d_watch.py` (PLUGIN_DIR baked), then runs (or prints)
`hermes cron create <interval> --name home3d-watch --no-agent --script home3d_watch.py --deliver local`.
`hermes home3d watch --once` (run the watcher in the foreground and print events), `status`, `doctor`
(config + connectivity + presets + eject marker in preset + targets), `simulate scenario <name> | advance
<min> | clear | reset` (simulator only), `demo` (scripted simulator run of the full loop, printing each step
and the outbox — the judge path).

### Plugin wiring — `home3d/plugin.py`
```python
def register_all(ctx) -> None
```
Creates `Runtime(ctx)`, registers every tool (`ctx.register_tool(name=..., toolset=TOOLSET, schema=...,
handler=..., emoji="🧰")`), the three hooks, `/home3d`, the `home3d` CLI command, and the bundled skill
(`ctx.register_skill("household-printing", <dir>/skills/household-printing/SKILL.md, description=...)`).
No network or threads in register().

## Skill — `skills/household-printing/SKILL.md` (+ `references/`)
English-first, generic, distilled from the real system: persona rules (short replies, language, answer only
when addressed in group chats, offer 2–4 MakerWorld options with pictures, let the family choose, one
question at a time), the request → print workflow mapped to the tools, orientation/slicing rules, auto-eject
eligibility, failure handling ("when in doubt, stop"), notification etiquette, human-needed logging and
upgrade proposals. Registered as `home-3d-workshop:household-printing`.

## Tests — `tests/`
pytest, no Hermes needed. `conftest.py` loads the plugin dir as package `home3d_ws` (like the homeassistant
example) and sets `HOME3D_DATA_DIR` to a tmp dir per test. One test file per module + an end-to-end
simulator test (request → import → slice → queue → approve → start → advance → finish → eject → plate clear →
outbox has owner + family messages; and the `eject_miss` scenario creates a human-needed moment and, on the
third one, an upgrade proposal).

## Contract changes
- simulator (additive): `SimulatorBackend(state_path=None, *, autoeject_presets=())`; extra helper `now()` (simulated
  timestamp — use it instead of `time.time()` when comparing with simulated time, e.g. the watcher's eject window);
  `advance()` returns the new `PrinterStatus`; extra scenario `offline` (status OFFLINE, printer actions raise).
  Auto-eject preset ids: `"sim-autoeject"`, `$HOME3D_SIM_AUTOEJECT_PRESET`, the snapshot's `autoeject_printer_preset`,
  or `autoeject_presets`. `start()` refuses while the simulated plate is occupied; non-manual queue items auto-start
  once idle with a clear plate (like Bambuddy's queue manager).
- gcode/gates/eject (additive, defaults only): `GcodeInfo` fields all have defaults, plus `footprint_mm` (w, d)
  and `to_dict()`; `first_layer_bbox` excludes skirt/brim/prime-tower moves. `EjectAssessment.push_z` = the
  baked push height (`PRESET_PUSH_Z_MM` 2.5) when eligible. Helper `material_family()`. `Gate` gains
  `action` ("start"|"clear_plate"), `items` ([{code, level, params}] used by `describe()`), `codes` property and
  `to_dict()`. `PlateState` gains `verify_after_ts` (end of the eject window, set by `step()`) and
  `to_dict()`/`from_dict()` for the watcher kv; `eject.EVENTS` lists the event kinds. Watcher loop:
  `needs_plate_check(state, status, now)` → `check_plate()` → `step(..., plate=...)`; pass the simulator's
  `now()` as `now` with the simulator backend.
- messages/notify/watcher/upgrades (additive): `messages` kinds also include `eject_unverified` (owner + family)
  and `plate_clear` (owner only); `render()` returns `""` when that audience gets nothing (family for `hms`,
  `offline`, `ready_next`, `upgrade_proposed`, `plate_clear`). Extra ctx keys: `owner`, `queue_item_id`,
  `bed_temp`, `nozzle_temp`, `filament`, `eject_planned`, `plate_diff`, `next_id`, `upgrade_id`, `upgrade_label`,
  `evidence`, `window_days`, `model_ref`, `offline_min`. `notify.Delivery` gains `audience`; `send(...,
  *, audience="", dry_run=False)`, `notify(..., dry_run=False)`; `HOME3D_DRY_RUN=1` forces outbox-only; the
  command is `hermes [-p P] send -t T --json -- "<text>"`; helpers `read_outbox()`, `outbox_path()`.
  `watcher.run_once(deliver=False)` = dry run (outbox only, nothing sent); one merged owner message (+ one family
  message) per pass; family hears only about jobs with a known non-owner requester; with an eject plan the
  family is told once, on the eject outcome. First pass is a silent baseline (an already FINISH/FAILED
  printer starts as `needs_human`). Extra kv keys: `initialized, online, offline_notified, started_ts,
  started_job, photo_path, hms_codes, pending, idle_check_ts, progress, layer, total_layers, bed_temp, now,
  updated`. `main()` flags `--dry-run`, `--verbose`; the cron script honours `$HOME3D_PLUGIN_DIR` and exits 1
  (cron alert) only when the plugin cannot be loaded. `upgrades.KINDS` entries also carry `label_tr`,
  `title_tr`, `proposal_tr` (proposal text follows `settings.language`); helpers `normalize_kind()`, `text_for()`.
- tools/customize (additive): `home3d_slice` stores `store.kv("slice:<sliced_file_id>")` = {name, source_file_id,
  request_id, requester, material, colour, eject_planned, eject_reasons, max_z, print_time_min, grams,
  filament_slots, used_slots, suggested_ams_slot, printer_preset}; `home3d_queue add` reads it (else inspects the
  G-code). With the simulator backend and no `autoeject_printer_preset`, the tools use `"sim-autoeject"`. Extra
  optional tool args: `request_id` (import/customize/slice), `confirm_mechanism`/`name` (customize),
  `include_done` (queue list), `note`/`status` (upgrades). Audit event kinds written by tools: `start_requested`,
  `stop_request`, `pause_request`, `resume_request`, `queue_removed`, `plate_clear_confirmed` (payload `who`,
  `sender`, `reason`). `customize.model_bbox()` of a multi-plate 3MF = the largest plate per axis (each plate
  prints alone); scaling is about each plate's bottom-centre. Extra helpers: `CustomizeError`, `model_bounds()`,
  `template_values()`, `factor_for_size()`, `mechanism_words()`, `fits_build_volume()`, `BUILD_VOLUME_MM`.
- hooks/commands/cli (additive): `/home3d approve start <id> [jump] | clear | resume` grants the 15-min single-use
  approval **and immediately runs the gated tool handler** (`home3d_start` / `home3d_clear_plate confirm` /
  `home3d_stop resume`); on success the approval is consumed, otherwise it stays for a later agent call. Approval
  store actions: `start` (target `"<id>"`, or `"<id>+jump"` when `allow_jump`), `clear_plate` (target `""`),
  `resume` (target `""`). Block messages for missing approval contain `hooks.APPROVAL_MARKER`
  ("owner approval needed"); `post_tool_call` logs those as `approve_start` moments (deduped 10 min).
  `pre_llm_call` sends the full context on the first turn / printing-related turns / printer state changes, else one
  "Speaking: ..." line. `cli.handle(args, rt=None)`; `cli.run_demo(lang, ...) -> {"ok", "milestones", "missing",
  "events", "outbox", "data_dir"}`; `commands.format_status(data, lang)`.
- integration (additive): the skill folder is `skills/household-printing/` (folder name = skill name, as Hermes'
  skill lint expects; `plugin.SKILL_PATH` is the one place that names it). `cli.run_demo` adds a condensed
  fast-forward (two more eject misses → the third `remove_part` moment → `upgrade_proposed` → the owner accepts
  it); `DEMO_MILESTONES` ends with `upgrade_proposed`. The `upgrade_proposed` owner text and `/home3d upgrades`
  tell the owner what to say to the persona ("accept upgrade N"), never a tool name. CI's personal-data scan
  holds no private values itself: generic patterns (real-looking group/user ids, keys, tokens, any private
  IPv4 except `192.168.1.50`) plus an optional `PRIVATE_SCAN_PATTERNS` repo secret for names / the real address.
  `tests/test_end_to_end.py` drives the whole loop through hooks → handlers → `watcher.run_once`.

## Fix round 1 (review r0: safety, hermes-api, e2e)
The review found that approvals could linger and be used by someone else, that some paths failed open, and that
the demo hid too much. These decisions supersede the "approval" paragraphs above where they disagree.

- **Identity (D1, `config.py`).** `Settings.person_for()` compares ids EXACTLY after `norm_id()`: strip + lower;
  WhatsApp phone ids (`@s.whatsapp.net`, `@c.us`, device suffix `:N`) and bare phone numbers become their digits;
  `@lid` ids become `<digits>@lid` (another id space, never equal to a phone number); everything else (Matrix,
  e-mail, Telegram, `uid:N`) as is. Never the part before "@". New settings `local_is_owner` (default true) and
  `inject_context` (`auto` | `always` | `never`); `LOCAL_SENDER = "local"` is the recorded sender of a local
  session and is the owner exactly when `local_is_owner`.
- **Session identity (D2, `hooks.pre_llm_call`, `store`).** An empty `sender_id` on a local platform, or a
  `uid:<n>` sender on one (the gateway-hosted classic CLI), records `LOCAL_SENDER`; a child session with a
  `parent_session_id` inherits the parent's sender. With `inject_context: auto` only household members and the
  local owner get the persona/printer context (first turn, printer change, printing-related message, or the
  persona's name); other chats get nothing.
- **Approvals (D3/D4, `hooks`, `commands`, `store`, `tools`).** For start, clear-plate confirm and resume the
  hook decides in this order: cron (fails closed: `current_cron_execution` raising, or Hermes' cron markers in the
  environment, count as cron) → safety gate → sender. Unknown sender and family members are blocked with the
  owner's command; the owner gets Hermes' approval prompt with a per-call `rule_key` ("always" can never carry
  over). On approve the hook issues a single-use **handler pass** bound to (tool, target, session); the handler
  consumes it first and refuses without one, so `ctx.dispatch_tool` (which skips hooks) cannot bypass the check.
  `Store.consume_pass` is atomic across processes (`BEGIN IMMEDIATE` + `UPDATE ... WHERE used=0`). Stop and pause
  are never gated. `/home3d approve start <id> [jump] | clear | resume [ack]` (owner only) runs the same
  `hooks.evaluate()` and, on success, issues a pass for its own one-off session and calls the handler directly;
  on any failure nothing is kept and the owner sends the command again. No stored approval authorises a later
  call any more. Resume with a blocking HMS needs the owner's acknowledgement (`resume ack` / `ack_hms=true` from
  an owner session).
- **Plate truth (D5, `gates`, `backends`).** Status parsing fails closed (missing/unknown state = `UNKNOWN`,
  `connected` must be literally true, string/int HMS codes are parsed). A light warning or a failed lit re-check
  makes the plate *uncertain* (blocks); the chamber light is restored to its previous state. After a FAILED print
  a start needs the owner's plate confirmation (`/home3d approve clear` → `store.confirm_plate`); after FINISH a
  camera-only "empty" is allowed with a warning. The jump check counts every not-done item that is not one of
  our active jobs (case-insensitive). Clearing with an unknown bed temperature is blocked. Messages say "the
  camera thinks the plate is empty", never "verified".
- **Store and watcher (D6/D7).** `job_by_name` matches exact normalised names (no `LIKE`), preferring queued or
  printing jobs; the watcher attributes a print to the backend queue item that is printing first. `ready_next`
  announces our first pending job and names foreign items ahead. Family texts name the job by the request text.
- **CLI, script, CI (D8, `cli.py`, `scripts/home3d_watch.py`, `.github/workflows/ci.yml`).**
  - `hermes home3d demo` is English unless `--lang tr`, prints a one-line `--lang` hint and a legend: every
    scripted stand-in (what people say and do, the model's chat replies, the canned web search, approval taps,
    simulator scenarios) is labelled `[staged]`; everything else is the real hooks, tools, gates, watcher and
    messages. The run now also shows a customise step (scale to a target size), a filament run-out pause (the
    owner's agent is refused a resume without `ack`, then `/home3d approve resume ack`), a failed print (the next
    start is refused until `/home3d approve clear`), the persona's owner and family notices at each step, and a
    recap of everything that was blocked. `DEMO_MILESTONES` grew accordingly; `run_demo()` also returns
    `seconds` (about 3-4 s in-process, deterministic: simulated time only moves through `advance()`).
  - The installed cron script checks `$HERMES_HOME/config.yaml` the way the plugin loader does
    (`plugins.enabled` must list the plugin's manifest name or `<category>/<dir>` key, `plugins.disabled` wins;
    no config = nothing enabled). Disabled or removed (plugin directory gone) → prints nothing, exits 0; a
    present but broken plugin still exits 1. It reads YAML with PyYAML or ruamel.yaml when the interpreter has
    one, else a small stdlib parser that refuses (and then keeps watching) anything it cannot read for sure.
  - `hermes home3d teardown [--print-only]` removes every `home3d-watch` cron job (parsed from
    `hermes cron list --all`, by name or by script) and then the installed script; the data dir is kept.
    If a job cannot be removed the script stays, so the job does not fail on every tick.
  - CI gains `hermes-validate`: clone Hermes `v0.22.5`, `uv sync --frozen --python 3.14`, then
    `hermes plugins validate . --install-deps` with `HERMES_HOME=$(mktemp -d)`. The demo step runs both languages.
- **Details the bullets above leave out.**
  - Bambuddy reports `is_empty: true` together with `failure_reason` or `light_warning` so that a print is not
    blocked; the backend reads either one as *uncertain* (`is_empty=None`, `light_ok=False`). A chamber light that
    cannot be switched off again adds `light_left_on` to `Snapshot.note` / `PlateCheck.message`; the watcher
    tells the owner (owner only, at most every 6 h, message kind `light_left_on`).
  - A 4xx on start becomes a readable `BackendError` (`BambuddyHTTPError` with `.status`/`.detail`), for example
    "not enough filament: PLA in AMS A slot 2 needs 31 g, 12 g left (HTTP 409)"; the agent and the owner see it as is.
  - Gate codes added: `after_failure` (FAILED and no plate confirmation), `camera_only` (warning after FINISH),
    `plate_dark`, `bed_unknown`; `resume_gate` blocks when not paused, offline, in cron, or on a blocking HMS
    without the owner's ack. A plate confirmation counts for that job name only, until the next start, at most 24 h.
  - `Runtime.plate_check()` caches only a confident "empty" for 90 s (keyed by printer state and job), so the hook
    and the handler of one call share one camera check and an "occupied" answer is always re-checked.
  - `post_tool_call` drops a pass the handler did not use (a denied prompt, another plugin's veto), so a pass
    never outlives the call it was issued for.

## Fix round 2 (re-verification of round 1)
The re-check found no regression, but three gaps where the household could still be misled or stuck.

- **A failure the printer forgets (`store`, `gates`, `watcher`, `hooks`, `tools`).** A print that ends RUNNING →
  IDLE (cancel, power loss), or a FAILED printer that is power-cycled to IDLE, no longer reports FAILED, so the
  camera alone decided again. The watcher now records every `failed` event (and a FAILED printer on its first pass)
  with `Store.record_failure`; `Store.unconfirmed_failure()` stays set until a person confirms the plate
  (`confirm_plate`, i.e. `/home3d approve clear`) or a new print starts (watcher). `start_gate(after_failure=...)`
  blocks with `after_failure` whatever the printer says now; the watcher's plate / "next job" notices ask for the
  confirmation the same way.
- **The false-positive dead end (`backends`, `gates`).** Bambuddy reads an empty plate at 18-25 %. That stays
  *uncertain* for the camera alone, but `PlateCheck.uncertain_band` now marks a check whose only doubt is that band
  (lit, calibrated, the check ran). The owner's `/home3d approve clear` (or an approved owner-session confirm) accepts
  it with a warning, and a start accepts it once that confirmation is recorded for the last job. "Occupied"
  (≥ 26 %), a dark check, a check that could not run and a missing calibration are never overruled. The approval
  prompt says "the camera is NOT sure ... you confirm it yourself". The clear reply names the next workshop job.
- **HMS ack bound to what the owner saw (`hooks`, `commands`, `store`, `tools`).** A resume pass carries a
  `detail` (`hms_ack:<sorted codes>`, new `passes.detail` column, migrated in place); the handler accepts the ack
  only when the printer's current blocking codes are a subset of those. A new error that appears while the prompt
  waits blocks the resume.
- **Nobody present (`runtime.unattended_markers`, `hooks`).** Kanban workers, `chat -q`, `-z` and `--source tool`
  runs are local `cli` sessions with a `uid:<n>` sender, i.e. the local owner. The hook now blocks every gated call
  when one of Hermes' markers is set (`HERMES_KANBAN_TASK`, `HERMES_SINGLE_QUERY_SESSION`,
  `HERMES_SESSION_SOURCE` in {kanban, tool}, `gateway.session_finite.finite_turn_required() is True` or
  `unattended_turn()`); like the cron check it reads modules only from `sys.modules` and fails closed.
- **Smaller fixes.** No camera check (and no chamber-light switching) when the printer alone already blocks
  (`gates.printer_blocks`; `plate_skipped` can never open a gate). The backend never switches a light whose state
  it cannot read. A light left on by a hook/handler check is handed to the watcher (`light_left_on:pending`) and
  named in the approval prompt / handler warnings. Workshop jobs whose queue item was cancelled, or removed on two
  passes in a row, in the printer manager become `cancelled` (no longer "ours"). `awaiting_plate_clear` from
  Bambuddy blocks a start until `/home3d approve clear`. `home3d_import` needs `request_text` (2-3 words in the
  requester's language) for a new request, so family texts never fall back to the English MakerWorld title.

## Fix round 2 (review of the public repo: hardware, judge, catalog)
A second review read the public repo at 34e355a with three lenses: the real printer, a hackathon judge
and a catalog reviewer. Decisions R2-1 to R2-9. Each item names the finding ids.

- **R2-1 Live settings for the watcher (hw/F1).** The cron watcher read only `watcher-config.json`, which
  `hermes home3d setup` wrote once. A later settings change did not reach it. Now `load_settings()` without a
  ctx reads `<HERMES_HOME>/config.yaml` → `plugins.entries.home-3d-workshop.settings` (PyYAML or ruamel.yaml
  when importable). The snapshot is only the fallback. Inside Hermes, `Runtime.settings` rewrites the snapshot
  when its content changed (hash in memory). `doctor` says where the watcher reads its settings and warns
  when the snapshot differs from the live settings.
- **R2-2 Jobs by queue item id (hw/F2, hw/F3).** When a queue item is `printing`, its id decides which
  workshop job prints. No store row means not ours: no family message, no guess by name. The name match is
  used only when no item is printing, and only among jobs that are still queued or printing. A job never
  goes back to `printing` once it left the active states. Jobs in `printing` are reconciled with
  `queue(include_done=True)`: an item that completed or failed while the printer is idle or on another job
  gets its finished or failed notice (with the stored photo) and is closed. A failed item without
  `started_at` is a start that did not happen: the owner gets "the start did not happen: <error_message>",
  and the job and the request close as `start_failed`. `QueueItem` has `error_message` and `started_at`.
- **R2-3 The push comes before FINISH (hw/F6).** On the real A1 the end G-code waits 15 min (`M400 S900`)
  and pushes while the printer still reports RUNNING at 100 %. FINISH comes after the push.
  `Backend.eject_in_gcode` (False by default; Bambuddy and the simulator set True) tells the plate state
  machine. With it, the watcher checks the plate at FINISH at once, with no cool-down gate. Empty →
  `finished_ejected` (the family gets the photo from before the push). Not empty or unsure → one re-check
  about 3 min later, then `plate_not_clear` or `eject_unverified`. The simulator now runs in the real order.
  `eject_in_gcode` False keeps the old flow.
- **R2-4 Light discipline (hw/F7, cat/F5).** A pass switches the chamber light at most once:
  `snapshot_and_check()` gives the photo and the plate check in one light cycle. No near-end photo for
  prints the workshop did not queue. Plate re-checks while a person is needed, and on an idle printer with
  a job waiting, back off 15 → 30 → 60 → 120 min, at most 6 per (printer state, job, queue head). The
  count starts again when one of them changes.
- **R2-5 Bambuddy's `require_plate_clear` (hw/F4).** The live Bambuddy has it off, so its queue may start an
  auto-start item on a FINISH printer before any camera check. `BambuddyBackend.settings()` reads
  `GET /settings/`. `doctor` warns when the setting is off and an auto-eject preset is set. The simulator
  has the same flag (default True; a test covers False). README, catalog, PR and skill say so.
- **R2-6 A bounded hook (cat/F1).** Hermes 0.22.5 runs a hook callback with a 30 s timeout. A timed-out
  `pre_tool_call` blocks every tool call of the process for 60 s, `home3d_stop` included. The hook now uses
  no camera, no chamber light and no slicing. It reads status and queue through `backend.with_timeout(5)`,
  under a 12 s deadline in a worker thread, and blocks when the printer does not answer in time. A late
  result is dropped, so no pass is issued after the deadline. `start_gate(..., plate_deferred=True)` does not
  block on the plate and warns `plate_deferred`. A plate check of this process from the last 120 s that said
  occupied or unsure still blocks. The handler checks the plate right before the action (the authoritative
  check), and so does `/home3d approve`. The approval prompt says so.
- **R2-7 Family requests reach the owner (cat/F2, cat/F3, cat/F4).** When the hook refuses a household
  member's start, resume or plate clear, it calls `Store.add_approval_request()` (one per action, item and
  person per 24 h). The watcher tells the owner each pending request once (`approval_request`, tr and en,
  with the exact `/home3d approve` command) and marks it announced. When the same pass already says "next
  job ready" for that item, the request goes into that message. The block text is true: watcher fresh →
  "the owner gets this request on the next watcher pass"; watcher off → "ask the owner directly". An unknown
  sender's request is not recorded. `approve_start` stays a logged moment but never becomes an upgrade
  proposal. Skill examples never promise a start.
- **R2-8 English first (judge/F3).** The default `language` is `en` in `plugin.yaml` and `config.py`. The
  household that the plugin comes from sets `tr`.
- **R2-9 Polish (judge/F4, F5, F9, F10, cat/F7).** `doctor` and `/home3d status` name the real cause when
  the cron job exists but no pass ran: the Hermes scheduler is not running, start `hermes gateway`.
  `/home3d help` and a bare `hermes home3d` print one line per subcommand with a description, in the
  configured language. The Turkish demo uses Turkish names (Annem, Babam) and Turkish moment and upgrade
  labels. `request_text` is named in the `home3d_import` description and in `home3d_find_models`' `next`.
  The simulator takes a model's title from the URL slug and picks its size by keyword.
- **Docs (judge/F1, F2, F6, F7, F8, F11, cat/F6, F8, F9, F10).** The README starts with a quick start
  (install with `--enable`, then `hermes home3d demo`), a terminal picture of a real demo run
  (`docs/demo-terminal.svg`) and a "why a plugin, not a skill" table that points at the code. The status
  table stays honest: the full real-printer loop is still planned (judge/F1 needs a free printer and the
  owner). The disclosure now covers the watcher's own light switching, the web dashboard as the local
  owner, `require_plate_clear`, the bounded hook and the read-only use of non-public Hermes internals for
  cron and unattended detection (fail closed when a marker raises; skipped when it is renamed). The
  catalog entry and the PR draft match the README. `docs/DEMO.md` and the subtitles use `--enable`, follow
  the current demo text, never promise a start, show the push at the end of the print and keep every cue
  at 17 characters per second or slower. The skill describes the real hook order: a family member's block
  says only that the owner must approve, so the agent checks `home3d_status` before it says anything about
  readiness.
- **Not changed.** judge/F12 (personal name and email in commit metadata) is the owner's decision. hw/F5
  (no `--failure-deliver` on the cron job) is left for a later round.

### Fix round 2, closing pass (verifier findings)

- **R2-6 follow-up: the deadline follows Hermes' hook timeout.** With `plugins.hook_callback_timeout` set
  below 30 s, the 12 s gate could outlast it, and Hermes then blocked every tool call (stop included) for
  60 s. The gate's deadline is now `min(12 s, 0.4 × hook_callback_timeout)` (`hooks.hook_deadline_s`; no
  limit when the timeout is 0 or less). The timeout comes from Hermes' own
  `hermes_cli.plugins._resolve_hook_callback_timeout` (read from `sys.modules`, never imported; missing or
  failing → 30 s). `doctor` shows the value and warns below 15 s (it falls back to `config.yaml` outside
  Hermes).
- **R2-1 follow-up: a printer switch starts the watcher over.** The watcher state carries
  `backend_key` = [backend name, printer manager URL, printer id]. When it changes (config.yaml switched to
  the simulator or to another printer), the state is dropped and the next pass is a first pass. Before, the
  new camera "cleared" the old printer's job and could send `finished_ejected` to the family. A state
  written before the key existed is kept and gets the key.
- **R2-2 follow-up: name matches never beat the queue.** The name fallback is used only when the queue was
  read, and never for a job whose own queue item is still pending or failed without `started_at` (the
  print came from the printer screen, a phone app or an archive reprint). A pass that could not read the
  queue decides nothing and remembers nothing; the next pass decides. Before, Mum's waiting "kutu" got a
  "done" message for a print from elsewhere, and a failed dispatch next to a FINISH of the same file was
  told as "done" instead of `start_failed`.
- **R2-7 follow-up: truthful request texts.** The dedupe and "already got this request" look only at
  requests that are still open, so a new ask after the owner acted is a new request that the watcher
  passes on. Without `owner_target` the watcher's owner notices reach only the cron output, so the block
  says "No owner chat is set (owner_target), so the owner may not be told automatically: ask them
  directly" (the skill treats it like "the watcher is off").
- **"Require plate clear" on.** Bambuddy then reports `awaiting_plate_clear` after every print and blocks
  starts until the plate is marked clear. The "next job ready" text names `/home3d approve clear` before the
  start command (once; a failed print's confirm line already names it).
- **Docs.** A pass switches the light twice when a camera request fails (the plate check is tried again);
  prints the workshop did not queue get one photo when they end; after a push the owner gets a fresh photo
  of the empty plate and the requester the photo from before the push.
- **Not changed (open).** A family auto-start item waiting while Bambuddy waits for "plate clear" still
  blocks `/home3d approve clear` (`auto_start_pending`): the owner clears it in Bambuddy. A failed queue
  item without `started_at` is taken as "the start did not happen" even when the printer did start (an
  MQTT verification error after a real start): the owner then sees that print as not the workshop's.
