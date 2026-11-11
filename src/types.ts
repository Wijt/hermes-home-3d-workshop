/**
 * The JSON contract of `GET overview` (dashboard/plugin_api.py), schema 1. Every field can be null or
 * missing on an older or half-wired backend: `normalize()` in model.ts fills the gaps, so views read
 * these types and never guard each field themselves.
 */

/** Opaque string the front end hands back to `GET file?ref=...`. */
export type FileRef = string

export interface Person {
  name: string
  group: string
}

export interface ModelRefs {
  stl: FileRef | null
  preview: FileRef | null
}

export type PrinterState = 'idle' | 'printing' | 'paused' | 'finished' | 'failed' | 'offline'

export interface PrinterError {
  code: string
  text: string
}

export interface Printer {
  state: PrinterState
  job_name: string
  progress: number
  remaining_min: number | null
  layer: number | null
  total_layers: number | null
  bed_temp: number | null
  errors: PrinterError[]
  awaiting_plate_clear: boolean
}

export interface NowJob {
  queue_item_id: number | null
  name: string
  for: Person
  eject_planned: boolean | null
  model: ModelRefs | null
}

export interface Camera {
  available: boolean
  frame: FileRef | null
  taken_ts: number | null
  note: string
}

export interface CheckItem {
  id: string
  label: string
  ok: boolean
  detail: string
}

export interface Facts {
  print_time_min: number | null
  grams: number | null
  material: string
  color: string
  slot: number | null
  /** "Slot 3": the backend numbers slots from 0 and sends the printed label. */
  slot_label: string
  eject_planned: boolean | null
  /** Why auto-eject is (not) planned, in the backend's words. */
  eject_reason: string
}

export type WaitingAction = 'start' | 'clear' | 'resume'

export interface Waiting {
  id: number
  action: WaitingAction
  queue_item_id: number | null
  name: string
  asked_by: Person
  asked_ts: number | null
  facts: Facts
  checklist: CheckItem[]
  /** The words of the request, when it came from a chat. */
  request_text: string
  /** True when every check passes; null when the backend does not say. */
  ready: boolean | null
  command: string
  /** A second way through, e.g. "Start ahead of the queue" when the only failing check is the turn order. */
  alt: { command: string; label: string } | null
  model: ModelRefs | null
}

export interface QueueItem {
  id: number
  name: string
  for: Person
  status: string
  ours: boolean
  print_time_min: number | null
  eject_planned: boolean | null
  model: ModelRefs | null
}

/** How the part left the plate (Store.done_box `left_plate`): pushed off, waiting on it, taken off by a person. */
export type Outcome = 'pushed' | 'on_plate' | 'taken_off' | 'unknown'

export interface DoneItem {
  /** The part id `/home3d collected <id>` takes. */
  id: number
  /** The queue item it was printed as. */
  job_id: number | null
  name: string
  for: Person
  finished_ts: number | null
  outcome: Outcome
  photo: FileRef | null
  collected: boolean
  collected_by: string
  detail: string
  command: string
}

/** The outbox states. `dry_run`: simulated, nothing was sent on purpose (not a failure). */
export type NoticeStatus = 'sent' | 'pending' | 'failed' | 'no_target' | 'dry_run'

export interface Notice {
  ts: number | null
  /** Who it was for, in words: a group's name, "owner chat", "family chat". */
  to: string
  group: string
  kind: string
  job: string
  status: NoticeStatus
  attempts: number
  /** Empty for a viewer who is not the owner. */
  error: string
  /** Empty for a viewer who is not the owner. */
  text: string
}

export interface Notices {
  pending: number
  sent: number
  failed: number
  no_target: number
  dry_run: number
  recent: Notice[]
}

export interface Slot {
  slot: number
  /** "Slot 1" (the printed label; `slot` itself may count from 0). */
  label: string
  material: string
  color: string
  name: string
  remain_pct: number | null
  loaded: boolean
}

export interface NeedsHuman {
  id: number
  kind: string
  text: string
  ts: number | null
  /** False once the event that resolves it happened (the plate was cleared, the start approved, ...). */
  open: boolean
  job: string
  who: string
  /** What resolved it, for a handled moment. */
  resolved_by: string
}

export interface Upgrade {
  id: string
  title: string
  why: string
  count: number
  status: string
  /** A link with more (a printable model page), when the proposal has one. */
  model_ref: string
}

export interface DesignVersion {
  version: number
  stl: FileRef | null
  previews: FileRef[]
  facts: Record<string, unknown>
  note: string
}

export interface Design {
  slug: string
  title: string
  versions: DesignVersion[]
}

export type CheckStatus = 'ok' | 'warn' | 'missing' | 'error'

export interface SetupCheck {
  id: string
  label: string
  status: CheckStatus
  detail: string
  fix: string
}

export interface Watcher {
  fresh: boolean
  last_pass_ts: number | null
  interval: string
  model_calls: number | null
}

export interface Group {
  name: string
  tone: 'family' | 'team' | string
  language: string
  /** How many sender ids the group lists. */
  members: number
}

export interface Overview {
  schema: number
  generated_ts: number
  backend: string
  persona: string
  simulated: boolean
  printer: Printer
  now: NowJob | null
  camera: Camera
  waiting: Waiting[]
  queue: QueueItem[]
  done_box: DoneItem[]
  notices: Notices
  filament: { slots: Slot[] }
  needs_human: NeedsHuman[]
  upgrades: Upgrade[]
  designs: Design[]
  /** `pending`: a check run is going on in the background; `checked_ts`: when the shown rows were made. */
  setup: { checks: SetupCheck[]; checked_ts: number | null; pending: boolean }
  watcher: Watcher
  groups: Group[]
  viewer: { is_owner: boolean; reason: string }
}

/** `GET file?ref=...` */
export interface FilePayload {
  name: string
  bytes: number
  mime: string
  dataUrl: string
}
