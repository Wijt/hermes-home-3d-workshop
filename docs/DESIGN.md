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
