/**
 * Pure helpers for the Workshop screen: turn the overview JSON into words a person reads at a glance.
 * No React, no DOM, no SDK: tests/desktop/model.test.mjs runs these under plain `node --test`.
 */

import type {
  CheckItem,
  CheckStatus,
  DoneItem,
  Facts,
  Group,
  ModelRefs,
  Notice,
  NoticeStatus,
  Outcome,
  Overview,
  Person,
  Printer,
  PrinterState,
  SetupCheck,
  Slot,
  Waiting,
  WaitingAction,
  Watcher
} from './types.ts'

// ---- defensive reading ---------------------------------------------------------------------------

type Loose = Record<string, unknown>

const obj = (v: unknown): Loose => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Loose) : {})
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const str = (v: unknown, d = ''): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : d)
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const int = (v: unknown, d = 0): number => num(v) ?? d
const bool = (v: unknown, d = false): boolean => (typeof v === 'boolean' ? v : d)
const boolOrNull = (v: unknown): boolean | null => (typeof v === 'boolean' ? v : null)
const refOrNull = (v: unknown): string | null => (typeof v === 'string' && v ? v : null)

const STATES: PrinterState[] = ['idle', 'printing', 'paused', 'finished', 'failed', 'offline']
const ACTIONS: WaitingAction[] = ['start', 'clear', 'resume']
const CHECKS: CheckStatus[] = ['ok', 'warn', 'missing', 'error']
const OUTCOMES: Outcome[] = ['pushed', 'on_plate', 'taken_off', 'unknown']
const NOTICE_STATUSES: NoticeStatus[] = ['sent', 'pending', 'failed', 'no_target', 'dry_run']

function person(v: unknown): Person {
  const o = obj(v)
  return { name: str(o.name), group: str(o.group) }
}

function model(v: unknown): ModelRefs | null {
  if (!v || typeof v !== 'object') return null
  const o = obj(v)
  const stl = refOrNull(o.stl)
  const preview = refOrNull(o.preview)
  return stl || preview ? { stl, preview } : null
}

function facts(v: unknown): Facts {
  const o = obj(v)
  return {
    print_time_min: num(o.print_time_min),
    grams: num(o.grams),
    material: str(o.material),
    color: str(o.color),
    slot: num(o.slot),
    slot_label: str(o.slot_label),
    eject_planned: boolOrNull(o.eject_planned),
    eject_reason: str(o.eject_reason)
  }
}

function checkItem(v: unknown): CheckItem {
  const o = obj(v)
  return { id: str(o.id), label: str(o.label), ok: bool(o.ok), detail: str(o.detail) }
}

/** The overview as the views expect it: every section present, every field typed. */
export function normalize(raw: unknown): Overview {
  const o = obj(raw)
  const p = obj(o.printer)
  const state = STATES.includes(p.state as PrinterState) ? (p.state as PrinterState) : 'offline'
  const printer: Printer = {
    state,
    job_name: str(p.job_name),
    progress: int(p.progress),
    remaining_min: num(p.remaining_min),
    layer: num(p.layer),
    total_layers: num(p.total_layers),
    bed_temp: num(p.bed_temp),
    errors: arr(p.errors).map(e => ({ code: str(obj(e).code), text: str(obj(e).text) })).filter(e => e.code || e.text),
    awaiting_plate_clear: bool(p.awaiting_plate_clear)
  }
  const n = o.now && typeof o.now === 'object' ? obj(o.now) : null
  const cam = obj(o.camera)
  const notices = obj(o.notices)
  const watcher = obj(o.watcher)
  const viewer = obj(o.viewer)
  return {
    schema: int(o.schema, 1),
    generated_ts: int(o.generated_ts),
    backend: str(o.backend),
    persona: str(o.persona),
    simulated: bool(o.simulated),
    printer,
    now: n
      ? {
          queue_item_id: num(n.queue_item_id),
          name: str(n.name),
          for: person(n.for),
          eject_planned: boolOrNull(n.eject_planned),
          model: model(n.model)
        }
      : null,
    camera: {
      available: bool(cam.available),
      frame: refOrNull(cam.frame),
      taken_ts: num(cam.taken_ts),
      note: str(cam.note)
    },
    waiting: arr(o.waiting).map(v => {
      const w = obj(v)
      const action = ACTIONS.includes(w.action as WaitingAction) ? (w.action as WaitingAction) : 'start'
      return {
        id: int(w.id),
        action,
        queue_item_id: num(w.queue_item_id),
        name: str(w.name),
        asked_by: person(w.asked_by),
        asked_ts: num(w.asked_ts),
        facts: facts(w.facts),
        checklist: arr(w.checklist).map(checkItem),
        request_text: str(w.request_text),
        ready: boolOrNull(w.ready),
        command: str(w.command),
        alt: w.alt && typeof w.alt === 'object' && str(obj(w.alt).command) ? { command: str(obj(w.alt).command), label: str(obj(w.alt).label) || 'Other way' } : null,
        model: model(w.model)
      }
    }),
    queue: arr(o.queue).map(v => {
      const q = obj(v)
      return {
        id: int(q.id),
        name: str(q.name),
        for: person(q.for),
        status: str(q.status),
        ours: bool(q.ours, true),
        print_time_min: num(q.print_time_min),
        eject_planned: boolOrNull(q.eject_planned),
        model: model(q.model)
      }
    }),
    done_box: arr(o.done_box).map(v => {
      const d = obj(v)
      const outcome = OUTCOMES.includes(d.outcome as Outcome) ? (d.outcome as Outcome) : 'unknown'
      const id = int(d.id)
      return {
        id,
        job_id: num(d.job_id),
        name: str(d.name),
        for: person(d.for),
        finished_ts: num(d.finished_ts),
        outcome,
        photo: refOrNull(d.photo),
        collected: bool(d.collected),
        collected_by: str(d.collected_by),
        detail: str(d.detail),
        command: str(d.command) || `home3d collected ${id}`
      }
    }),
    notices: {
      pending: int(notices.pending),
      sent: int(notices.sent),
      failed: int(notices.failed),
      no_target: int(notices.no_target),
      dry_run: int(notices.dry_run),
      recent: arr(notices.recent).map(v => {
        const r = obj(v)
        const status = NOTICE_STATUSES.includes(r.status as NoticeStatus) ? (r.status as NoticeStatus) : 'pending'
        return {
          ts: num(r.ts),
          to: str(r.to),
          group: str(r.group),
          kind: str(r.kind),
          job: str(r.job),
          status,
          attempts: int(r.attempts),
          error: str(r.error),
          text: str(r.text)
        }
      })
    },
    filament: {
      slots: arr(obj(o.filament).slots).map(v => {
        const s = obj(v)
        return {
          slot: int(s.slot),
          label: str(s.label) || `Slot ${int(s.slot)}`,
          material: str(s.material),
          color: str(s.color),
          name: str(s.name),
          remain_pct: num(s.remain_pct),
          loaded: bool(s.loaded, true)
        }
      })
    },
    needs_human: arr(o.needs_human).map(v => {
      const h = obj(v)
      return {
        id: int(h.id),
        kind: str(h.kind),
        text: str(h.text),
        ts: num(h.ts),
        open: bool(h.open, true),
        job: str(h.job),
        who: str(h.who),
        resolved_by: str(h.resolved_by)
      }
    }),
    upgrades: arr(o.upgrades).map(v => {
      const u = obj(v)
      const ref = str(u.model_ref)
      return { id: str(u.id), title: str(u.title), why: str(u.why), count: int(u.count), status: str(u.status), model_ref: /^https:\/\//.test(ref) ? ref : '' }
    }),
    designs: arr(o.designs).map(v => {
      const d = obj(v)
      return {
        slug: str(d.slug),
        title: str(d.title) || str(d.slug),
        versions: arr(d.versions)
          .map(x => {
            const ver = obj(x)
            return {
              version: int(ver.version),
              stl: refOrNull(ver.stl),
              previews: arr(ver.previews).filter((r): r is string => typeof r === 'string' && !!r),
              facts: obj(ver.facts),
              note: str(ver.note)
            }
          })
          .sort((a, b) => a.version - b.version)
      }
    }),
    setup: {
      checked_ts: num(obj(o.setup).checked_ts),
      pending: bool(obj(o.setup).pending),
      checks: arr(obj(o.setup).checks).map(v => {
        const c = obj(v)
        const status = CHECKS.includes(c.status as CheckStatus) ? (c.status as CheckStatus) : 'warn'
        return { id: str(c.id), label: str(c.label), status, detail: str(c.detail), fix: str(c.fix) }
      })
    },
    watcher: {
      fresh: bool(watcher.fresh),
      last_pass_ts: num(watcher.last_pass_ts),
      interval: str(watcher.interval),
      model_calls: num(watcher.model_calls)
    },
    groups: arr(o.groups)
      .map(v => ({ name: str(obj(v).name), tone: str(obj(v).tone, 'family'), language: str(obj(v).language), members: int(obj(v).members) }))
      .filter(g => g.name),
    viewer: { is_owner: bool(viewer.is_owner, true), reason: str(viewer.reason) }
  }
}

// ---- words ---------------------------------------------------------------------------------------

/** "Mum · Family"; just "Mum" without a group; "someone" when nobody is named. */
export function personLabel(p: Person | null | undefined): string {
  const name = p?.name?.trim() || ''
  const group = p?.group?.trim() || ''
  if (!name) return group ? `someone · ${group}` : 'someone'
  return group ? `${name} · ${group}` : name
}

/** "41 min", "1 h 05 min", "2 h", "under a minute"; "" when unknown. */
export function fmtDuration(min: number | null | undefined): string {
  if (min === null || min === undefined || !Number.isFinite(min) || min < 0) return ''
  const m = Math.round(min)
  if (m < 1) return 'under a minute'
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h} h ${String(rest).padStart(2, '0')} min` : `${h} h`
}

/** Seconds since the epoch; a value in milliseconds is accepted too. */
export function toSeconds(ts: number | null | undefined): number | null {
  if (ts === null || ts === undefined || !Number.isFinite(ts) || ts <= 0) return null
  return ts > 1e12 ? ts / 1000 : ts
}

/** "just now", "40 s ago", "12 min ago", "3 h ago", "2 days ago"; "" when unknown. */
export function fmtAgo(ts: number | null | undefined, nowSec: number): string {
  const t = toSeconds(ts)
  if (t === null) return ''
  const d = Math.max(0, nowSec - t)
  if (d < 5) return 'just now'
  if (d < 60) return `${Math.floor(d)} s ago`
  if (d < 3600) return `${Math.floor(d / 60)} min ago`
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`
  const days = Math.floor(d / 86400)
  return days === 1 ? 'yesterday' : `${days} days ago`
}

export function stateLabel(state: PrinterState): string {
  return { idle: 'Idle', printing: 'Printing', paused: 'Paused', finished: 'Finished', failed: 'Failed', offline: 'Offline' }[state]
}

export type Tone = 'neutral' | 'accent' | 'good' | 'warn' | 'bad'

export function stateTone(state: PrinterState): Tone {
  return ({ idle: 'neutral', printing: 'accent', paused: 'warn', finished: 'good', failed: 'bad', offline: 'bad' } as const)[state]
}

/** Progress as a whole percent 0..100 (the backend reports percent). */
export function progressPct(p: Printer): number {
  const v = Number.isFinite(p.progress) ? p.progress : 0
  return Math.max(0, Math.min(100, Math.round(v)))
}

export const isActive = (state: PrinterState) => state === 'printing' || state === 'paused'

/** What the top band leads with. */
export type HeroMode = 'approve' | 'running' | 'attention' | 'idle' | 'offline'

/**
 * Does an approval lead the top band? Yes when one can go now (or is about the print on the printer: resume,
 * plate), or when nothing is printing. While a print runs, a start that has to wait for it does not cover the
 * running print: the band shows the print and names what waits (`waitingAfterPrint`).
 */
export function approvalLeads(ov: Overview): boolean {
  if (!ov.waiting.length) return false
  if (!isActive(ov.printer.state)) return true
  return ov.waiting.some(w => w.action !== 'start' || isReady(w))
}

/** Starts that wait for the running print to end (shown under the print, not over it). */
export function waitingAfterPrint(ov: Overview): Waiting[] {
  return approvalLeads(ov) ? [] : ov.waiting
}

export function heroMode(ov: Overview): HeroMode {
  if (approvalLeads(ov)) return 'approve'
  if (isActive(ov.printer.state)) return 'running'
  if (ov.printer.state === 'offline') return 'offline'
  if (ov.printer.state === 'failed' || ov.printer.errors.length || ov.printer.awaiting_plate_clear) return 'attention'
  return 'idle'
}

/** Who the running job is for: the `now` block, else nobody known. */
export function nowFor(ov: Overview): string {
  return ov.now ? personLabel(ov.now.for) : ''
}

/** The status-bar chip: "Printing 62% · for Mum · 41 min", "Waiting for you: 1", "Idle". */
export function chipText(ov: Overview): { text: string; tone: Tone } {
  const p = ov.printer
  const who = ov.now?.for?.name?.trim()
  if (approvalLeads(ov)) return { text: `Waiting for you: ${ov.waiting.length}`, tone: 'accent' }
  if (p.state === 'printing') {
    const parts = [`Printing ${progressPct(p)}%`]
    if (who) parts.push(`for ${who}`)
    const left = fmtDuration(p.remaining_min)
    if (left) parts.push(left)
    if (ov.waiting.length) parts.push(`${ov.waiting.length} waiting`)
    return { text: parts.join(' · '), tone: 'neutral' }
  }
  if (p.state === 'paused') return { text: `Paused ${progressPct(p)}%${who ? ` · for ${who}` : ''}`, tone: 'warn' }
  if (p.state === 'failed') return { text: 'Print failed', tone: 'bad' }
  if (p.state === 'offline') return { text: 'Printer offline', tone: 'bad' }
  if (p.awaiting_plate_clear) return { text: 'Plate needs clearing', tone: 'warn' }
  if (p.state === 'finished') return { text: who ? `Finished · for ${who}` : 'Finished', tone: 'good' }
  return { text: 'Idle', tone: 'neutral' }
}

/** The button and the sentence that says what it will do. */
export function approvalCopy(w: Waiting): { button: string; explain: string } {
  if (w.action === 'clear') {
    return {
      button: 'Plate is clear, continue',
      explain: 'Tells the printer the bed is empty so the next job in the queue can start.'
    }
  }
  if (w.action === 'resume') {
    return { button: 'Resume print', explain: 'Continues the paused print from the layer where it stopped.' }
  }
  const after =
    w.facts.eject_planned === true
      ? 'When it is done the printer pushes it off into the done box.'
      : w.facts.eject_planned === false
        ? 'It stays on the plate until someone takes it off.'
        : ''
  return { button: 'Start print', explain: `Starts "${w.name || 'this job'}" on the printer now. ${after}`.trim() }
}

/** The slash command for a waiting item (the backend sends it; rebuilt only when missing). */
export function waitingCommand(w: Waiting): string {
  const given = w.command.trim().replace(/^\/+/, '')
  if (given) return given
  if (w.action === 'start') return w.queue_item_id !== null ? `home3d approve start ${w.queue_item_id}` : ''
  return `home3d approve ${w.action}`
}

export const failingChecks = (items: CheckItem[]) => items.filter(c => !c.ok)

export function ejectLabel(planned: boolean | null): string {
  return planned === true ? 'Pushed off into the done box' : planned === false ? 'Stays on the plate' : 'Not decided'
}

export function outcomeLabel(d: DoneItem): { text: string; tone: Tone } {
  if (d.collected) return { text: d.collected_by ? `Collected by ${d.collected_by}` : 'Collected', tone: 'neutral' }
  if (d.outcome === 'pushed') return { text: 'In the done box', tone: 'good' }
  if (d.outcome === 'taken_off') return { text: 'Taken off the plate', tone: 'good' }
  if (d.outcome === 'on_plate') return { text: 'Still on the plate', tone: 'warn' }
  return { text: 'Finished', tone: 'neutral' }
}

/** "#rrggbb" or null: accepts "rrggbb", "#rgb" and "#rrggbbaa" (Bambu reports RRGGBBAA). */
export function hexColor(value: string | null | undefined): string | null {
  const v = (value || '').trim().replace(/^#/, '')
  if (/^[0-9a-f]{3}$/i.test(v)) return `#${v.split('').map(c => c + c).join('')}`.toLowerCase()
  if (/^[0-9a-f]{6}([0-9a-f]{2})?$/i.test(v)) return `#${v.slice(0, 6)}`.toLowerCase()
  return null
}

export function slotByNumber(slots: Slot[], n: number | null): Slot | null {
  return n === null ? null : slots.find(s => s.slot === n) ?? null
}

/** The colour to paint a part: the job's filament colour, else the slot's, else null (theme accent). */
export function partColor(f: Facts | null, slots: Slot[]): string | null {
  return hexColor(f?.color) ?? hexColor(slotByNumber(slots, f?.slot ?? null)?.color) ?? null
}

/** "PLA · Bambu PLA Matte · Slot 3" */
export function filamentLine(f: Facts, slots: Slot[]): string {
  const slot = slotByNumber(slots, f.slot)
  const material = f.material || slot?.material || ''
  const colour = slot?.name || (hexColor(f.color) ? '' : f.color)
  const where = f.slot_label || slot?.label || (f.slot !== null ? `Slot ${f.slot}` : '')
  return [material, colour, where].filter(Boolean).join(' · ') || 'Not chosen yet'
}

export function slotLabel(f: Facts, slots: Slot[]): string {
  return f.slot_label || slotByNumber(slots, f.slot)?.label || (f.slot !== null ? `Slot ${f.slot}` : 'its slot')
}

/** Is the waiting item clear to go? The backend's `ready` wins; else every check must pass. */
export function isReady(w: Waiting): boolean {
  return w.ready ?? w.checklist.every(c => c.ok)
}

const KIND_WORDS: Record<string, string> = {
  started: 'Print started',
  finished: 'Print finished',
  finished_ejected: 'Finished and pushed off',
  failed: 'Print failed',
  stopped: 'Print stopped',
  paused: 'Print paused',
  approval_request: 'Asked you to approve',
  plate_clear: 'Plate is clear',
  plate_not_clear: 'Plate is not clear',
  ready_next: 'Ready for the next job',
  delivery_failed: 'Some messages were not delivered'
}

/** The line a notice shows: the start of its text (emoji trimmed), else its kind in words (a viewer who is not
 * the owner gets no text). */
export function noticeLine(n: Notice): string {
  const t = n.text.replace(/^[^\p{L}\p{N}"“]+/u, '').trim()
  if (t) return t.length > 90 ? `${t.slice(0, 88).trimEnd()}…` : t
  const kinds = n.kind.split(',').filter(Boolean)
  const words = kinds.map(k => KIND_WORDS[k] ?? k.replace(/_/g, ' ')).join(', ')
  const line = words ? words[0].toUpperCase() + words.slice(1) : 'Message'
  return n.job ? `${line}: ${n.job}` : line
}

export function noticeSummary(n: Overview['notices']): { text: string; tone: Tone } {
  if (n.failed) return { text: `${n.failed} not delivered${n.pending ? `, ${n.pending} waiting to send` : ''}`, tone: 'bad' }
  if (n.pending) return { text: `${n.pending} waiting to send`, tone: 'warn' }
  const nowhere = n.recent.filter(r => r.status === 'no_target').length
  if (nowhere) return { text: `${nowhere} of the last ${n.recent.length} had no chat to go to`, tone: 'warn' }
  if (n.recent.length && n.recent.every(r => r.status === 'dry_run'))
    return { text: 'Simulated: messages are written, not sent', tone: 'neutral' }
  return { text: n.recent.length ? 'Everyone was told' : 'Nothing to tell yet', tone: n.recent.length ? 'good' : 'neutral' }
}

export function noticeStatusLabel(s: Notice['status']): string {
  return { sent: 'Sent', pending: 'Waiting', failed: 'Failed', no_target: 'No chat to send to', dry_run: 'Simulated, not sent' }[s]
}

/** The colour of a notice's status: a simulated notice is neutral, not a failure. */
export function noticeTone(s: Notice['status']): Tone {
  return s === 'sent' ? 'good' : s === 'failed' ? 'bad' : s === 'dry_run' ? 'neutral' : 'warn'
}

export function setupSummary(checks: SetupCheck[]): { text: string; tone: Tone } {
  if (!checks.length) return { text: 'No checks reported', tone: 'neutral' }
  const bad = checks.filter(c => c.status === 'error' || c.status === 'missing').length
  const warn = checks.filter(c => c.status === 'warn').length
  const ok = checks.length - bad - warn
  if (bad) return { text: `${bad} need fixing, ${ok} of ${checks.length} fine`, tone: 'bad' }
  if (warn) return { text: `${warn} to look at, ${ok} of ${checks.length} fine`, tone: 'warn' }
  return { text: `All ${checks.length} checks pass`, tone: 'good' }
}

/** Order setup checks worst first, keeping the backend's order inside each band. */
export function sortChecks(checks: SetupCheck[]): SetupCheck[] {
  const rank: Record<CheckStatus, number> = { error: 0, missing: 1, warn: 2, ok: 3 }
  return checks.map((c, i) => ({ c, i })).sort((a, b) => rank[a.c.status] - rank[b.c.status] || a.i - b.i).map(x => x.c)
}

export function watcherLine(w: Watcher, nowSec: number): { text: string; tone: Tone } {
  const ago = fmtAgo(w.last_pass_ts, nowSec)
  const every = w.interval ? ` (every ${w.interval})` : ''
  if (!ago) return { text: 'Watcher has not run yet', tone: 'warn' }
  return { text: `Watcher ${w.fresh ? 'checked' : 'last checked'} ${ago}${every}`, tone: w.fresh ? 'good' : 'warn' }
}

export function groupTone(groups: Group[], name: string): 'family' | 'team' | 'other' {
  const tone = groups.find(g => g.name.toLowerCase() === name.trim().toLowerCase())?.tone
  return tone === 'family' || tone === 'team' ? tone : 'other'
}

/** Readable lines from a design version's free-form facts. */
export function designFacts(f: Record<string, unknown>): string[] {
  const out: string[] = []
  const size = Array.isArray(f.size_mm) ? f.size_mm.filter((x): x is number => typeof x === 'number') : []
  if (size.length === 3) out.push(`${size.map(n => (Math.round(n * 10) / 10).toString()).join(' × ')} mm`)
  const grams = num(f.est_grams_max) ?? num(f.grams)
  if (grams !== null) out.push(`about ${Math.round(grams)} g`)
  const time = num(f.print_time_min)
  if (time !== null) out.push(fmtDuration(time))
  const vol = num(f.volume_cm3)
  if (vol !== null && grams === null) out.push(`${Math.round(vol * 10) / 10} cm³`)
  if (f.fits_build_volume === false) out.push('too big for the bed')
  return out
}

// ---- errors and freshness ------------------------------------------------------------------------

export type ErrorKind = 'not_enabled' | 'unreachable' | 'error'

/** `ctx.rest` rejects with "<status>: <body>". 404 means the plugin's Python half is not mounted. */
export function errorInfo(err: unknown): { kind: ErrorKind; status: number | null; text: string } {
  const raw = err instanceof Error ? err.message : typeof err === 'string' ? err : String(err ?? '')
  const m = /^\s*(\d{3})\b/.exec(raw)
  const status = m ? Number(m[1]) : null
  const detail = /"detail"\s*:\s*"([^"]+)"/.exec(raw)?.[1]
  const text = detail || raw || 'No answer'
  if (status === 404) return { kind: 'not_enabled', status, text }
  if (status === null || status >= 500 || /fetch|network|timed? ?out|ECONN|abort/i.test(raw)) return { kind: 'unreachable', status, text }
  return { kind: 'error', status, text }
}

/** Data older than three polls is stale: say how old it is. */
export const STALE_AFTER_MS = 15_000

export function staleness(updatedAtMs: number, nowMs: number, failing: boolean): { stale: boolean; text: string; ago: string } {
  if (!updatedAtMs) return { stale: failing, text: failing ? 'No data yet' : '', ago: '' }
  const age = Math.max(0, nowMs - updatedAtMs)
  const ago = fmtAgo(updatedAtMs / 1000, nowMs / 1000)
  const stale = failing || age > STALE_AFTER_MS
  return { stale, text: stale ? `Last update ${ago}` : `Updated ${ago}`, ago }
}
