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

export type Outcome = 'pushed' | 'on_plate' | 'failed'

export interface DoneItem {
  job_id: number
  name: string
  for: Person
  finished_ts: number | null
  outcome: Outcome
  photo: FileRef | null
  collected: boolean
  detail: string
  command: string
}

export type NoticeStatus = 'sent' | 'pending' | 'failed' | 'no_target'

export interface Notice {
  ts: number | null
  to: string
  kind: string
  status: NoticeStatus
  error: string
  text: string
}

export interface Notices {
  pending: number
  failed: number
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
  open: boolean
  job: string
  who: string
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
  setup: { checks: SetupCheck[] }
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
