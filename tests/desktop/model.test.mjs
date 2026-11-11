// Pure-module tests for the Workshop screen (no app, no DOM):
//   node --experimental-strip-types --no-warnings --test tests/desktop/*.test.mjs
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { test } from 'node:test'

import {
  approvalCopy,
  chipText,
  designFacts,
  errorInfo,
  filamentLine,
  fmtAgo,
  fmtDuration,
  heroMode,
  hexColor,
  isReady,
  normalize,
  noticeLine,
  noticeStatusLabel,
  noticeSummary,
  noticeTone,
  outcomeLabel,
  partColor,
  personLabel,
  progressPct,
  setupSummary,
  sortChecks,
  staleness,
  waitingAfterPrint,
  waitingCommand,
  watcherLine
} from '../../src/model.ts'

const root = new URL('../../', import.meta.url)
const fixtures = ['tests/fixtures/workshop_overview.json', 'dev/fixtures/workshop_overview.json']
  .map(p => new URL(p, root))
  .filter(u => existsSync(u))
  .map(u => [u.pathname.split('/').slice(-3).join('/'), JSON.parse(readFileSync(u, 'utf8'))])

const base = () => normalize(JSON.parse(readFileSync(new URL('dev/fixtures/workshop_overview.json', root), 'utf8')))

test('every fixture normalizes into every section the page renders', () => {
  assert.ok(fixtures.length >= 1)
  for (const [name, raw] of fixtures) {
    const ov = normalize(raw)
    for (const key of ['printer', 'camera', 'notices', 'filament', 'setup', 'watcher', 'viewer']) assert.ok(ov[key], `${name}: ${key}`)
    for (const key of ['waiting', 'queue', 'done_box', 'needs_human', 'upgrades', 'designs', 'groups']) assert.ok(Array.isArray(ov[key]), `${name}: ${key}`)
    for (const w of ov.waiting) {
      assert.ok(waitingCommand(w).startsWith('home3d approve '), `${name}: waiting command`)
      assert.equal(typeof w.facts.slot_label, 'string')
    }
    for (const s of ov.filament.slots) assert.match(s.label, /^Slot \d+$/, `${name}: slot label`)
    for (const d of ov.designs) assert.deepEqual(d.versions.map(v => v.version), [...d.versions.map(v => v.version)].sort((a, b) => a - b))
    assert.ok(chipText(ov).text.length > 0)
  }
})

test('normalize survives an empty, partial or wrong answer', () => {
  for (const raw of [undefined, null, 42, 'x', [], {}, { printer: { state: 'weird' }, waiting: [{}], queue: 'no', filament: { slots: [{}] } }]) {
    const ov = normalize(raw)
    assert.equal(typeof ov.printer.state, 'string')
    assert.ok(Array.isArray(ov.waiting) && Array.isArray(ov.queue) && Array.isArray(ov.filament.slots))
    assert.equal(ov.viewer.is_owner, true) // the backend's owner check still guards every action
  }
  const odd = normalize({ printer: { state: 'weird' }, waiting: [{ action: 'explode' }] })
  assert.equal(odd.printer.state, 'offline')
  assert.equal(odd.waiting[0].action, 'start')
  assert.equal(odd.waiting[0].model, null)
  const upgrade = normalize({ upgrades: [{ id: 'a', model_ref: 'javascript:alert(1)' }, { id: 'b', model_ref: 'https://example.org/m/1' }] }).upgrades
  assert.deepEqual(upgrade.map(u => u.model_ref), ['', 'https://example.org/m/1'])
})

test('the status-bar chip says the one thing that matters', () => {
  const ov = base()
  ov.waiting[0].ready = false // the backend says it can only start after Mum's print
  // the chip says the print, and that one job waits
  assert.deepEqual(chipText(ov), { text: 'Printing 62% · for Mum · 41 min · 1 waiting', tone: 'neutral' })
  ov.printer.state = 'idle'
  assert.deepEqual(chipText(ov), { text: 'Waiting for you: 1', tone: 'accent' })
  ov.printer.state = 'printing'
  ov.waiting = []
  assert.equal(chipText(ov).text, 'Printing 62% · for Mum · 41 min')
  ov.printer.state = 'paused'
  assert.equal(chipText(ov).text, 'Paused 62% · for Mum')
  ov.printer.state = 'idle'
  ov.now = null
  assert.equal(chipText(ov).text, 'Idle')
  ov.printer.awaiting_plate_clear = true
  assert.equal(chipText(ov).text, 'Plate needs clearing')
  ov.printer.state = 'offline'
  assert.equal(chipText(ov).tone, 'bad')
})

test('the top band leads with an approval that can go now, else the running print', () => {
  const ov = base()
  ov.waiting[0].ready = false // the backend says: printer busy, it waits for the print
  assert.equal(heroMode(ov), 'running')
  assert.deepEqual(waitingAfterPrint(ov), ov.waiting)
  ov.waiting[0].ready = true
  assert.equal(heroMode(ov), 'approve')
  assert.deepEqual(waitingAfterPrint(ov), [])
  ov.waiting[0].ready = false
  ov.waiting[0].action = 'resume' // about the print on the printer: always leads
  assert.equal(heroMode(ov), 'approve')
  ov.waiting[0].action = 'start'
  ov.printer.state = 'idle' // nothing printing: the card leads, with its failing checks
  assert.equal(heroMode(ov), 'approve')
  ov.printer.state = 'printing'
  ov.waiting = []
  assert.equal(heroMode(ov), 'running')
  ov.printer.state = 'failed'
  assert.equal(heroMode(ov), 'attention')
  ov.printer.state = 'offline'
  assert.equal(heroMode(ov), 'offline')
  ov.printer.state = 'idle'
  assert.equal(heroMode(ov), 'idle')
})

test('people are named with their group', () => {
  assert.equal(personLabel({ name: 'Mum', group: 'Family' }), 'Mum · Family')
  assert.equal(personLabel({ name: 'Sam', group: '' }), 'Sam')
  assert.equal(personLabel({ name: '', group: '' }), 'someone')
  assert.equal(personLabel(null), 'someone')
})

test('durations, ages and percentages read naturally', () => {
  assert.equal(fmtDuration(41), '41 min')
  assert.equal(fmtDuration(65), '1 h 05 min')
  assert.equal(fmtDuration(120), '2 h')
  assert.equal(fmtDuration(0.2), 'under a minute')
  assert.equal(fmtDuration(null), '')
  const now = 1_800_000_000
  assert.equal(fmtAgo(now - 2, now), 'just now')
  assert.equal(fmtAgo(now - 40, now), '40 s ago')
  assert.equal(fmtAgo(now - 12 * 60, now), '12 min ago')
  assert.equal(fmtAgo((now - 3 * 3600) * 1000, now), '3 h ago') // milliseconds accepted
  assert.equal(fmtAgo(now - 86400 * 1.5, now), 'yesterday')
  assert.equal(fmtAgo(0, now), '')
  assert.equal(progressPct({ progress: 40.6 }), 41)
  assert.equal(progressPct({ progress: 140 }), 100)
})

test('filament colours and lines use the printed slot label', () => {
  assert.equal(hexColor('#C12E1FFF'), '#c12e1f')
  assert.equal(hexColor('fff'), '#ffffff')
  assert.equal(hexColor('teal'), null)
  const slots = [{ slot: 2, label: 'Slot 3', material: 'PLA', color: '#000000', name: 'Bambu PLA Matte', remain_pct: 40, loaded: true }]
  const facts = { print_time_min: 30, grams: 14.2, material: 'PLA', color: '', slot: 2, slot_label: '', eject_planned: true, eject_reason: '' }
  assert.equal(filamentLine(facts, slots), 'PLA · Bambu PLA Matte · Slot 3')
  assert.equal(partColor(facts, slots), '#000000')
  assert.equal(partColor({ ...facts, slot: null }, slots), null)
})

test('approval: ready, command and the sentence under the button', () => {
  const w = base().waiting[0]
  assert.equal(isReady(w), true)
  assert.equal(isReady({ ...w, ready: null, checklist: [{ id: 'p', label: 'Plate', ok: false, detail: '' }] }), false)
  assert.equal(isReady({ ...w, ready: false }), false)
  assert.equal(waitingCommand({ ...w, command: '/home3d approve start 12' }), 'home3d approve start 12')
  assert.equal(waitingCommand({ ...w, command: '', queue_item_id: 7 }), 'home3d approve start 7')
  assert.equal(waitingCommand({ ...w, command: '', action: 'clear' }), 'home3d approve clear')
  assert.equal(approvalCopy(w).button, 'Start print')
  assert.match(approvalCopy(w).explain, /done box/)
  assert.match(approvalCopy({ ...w, facts: { ...w.facts, eject_planned: false } }).explain, /stays on the plate/)
  assert.equal(approvalCopy({ ...w, action: 'resume' }).button, 'Resume print')
})

test('notices: failures first, then pending, then messages with nowhere to go', () => {
  assert.equal(noticeSummary({ pending: 1, failed: 2, recent: [] }).tone, 'bad')
  assert.equal(noticeSummary({ pending: 1, failed: 0, recent: [] }).text, '1 waiting to send')
  const nowhere = { ts: 1, to: 'owner', kind: '', status: 'no_target', error: '', text: '✅ Finished: "Coaster" (#1)' }
  assert.equal(noticeSummary({ pending: 0, failed: 0, recent: [nowhere] }).tone, 'warn')
  assert.equal(noticeSummary({ pending: 0, failed: 0, recent: [{ ...nowhere, status: 'sent' }] }).text, 'Everyone was told')
  assert.equal(noticeLine(nowhere), 'Finished: "Coaster" (#1)')
  // a viewer who is not the owner gets no text: the kind in words and the job
  assert.equal(noticeLine({ ...nowhere, text: '', kind: 'started', job: 'Coaster' }), 'Print started: Coaster')
  assert.equal(noticeLine({ ...nowhere, text: '', kind: 'some_new_kind', job: '' }), 'Some new kind')
  // dry_run: simulated, not sent; neutral, never counted as a failure
  const dry = { ...nowhere, status: 'dry_run' }
  assert.equal(noticeStatusLabel('dry_run'), 'Simulated, not sent')
  assert.equal(noticeTone('dry_run'), 'neutral')
  assert.equal(noticeTone('failed'), 'bad')
  assert.deepEqual(noticeSummary({ pending: 0, failed: 0, dry_run: 1, recent: [dry] }), { text: 'Simulated: messages are written, not sent', tone: 'neutral' })
})

test('done box: real part ids, the collected flag and how the part left the plate', () => {
  const ov = normalize({ done_box: [
    { id: 4, job_id: 9, name: 'a coaster', outcome: 'taken_off', collected: false },
    { id: 3, job_id: 7, name: 'key tag', outcome: 'pushed', collected: true, collected_by: 'Mum' },
    { id: 2, job_id: null, name: 'clip', outcome: 'something_new' }
  ] })
  const [a, b, c] = ov.done_box
  assert.equal(a.command, 'home3d collected 4')
  assert.equal(a.job_id, 9)
  assert.deepEqual(outcomeLabel(a), { text: 'Taken off the plate', tone: 'good' })
  assert.deepEqual(outcomeLabel(b), { text: 'Collected by Mum', tone: 'neutral' })
  assert.equal(c.outcome, 'unknown')
  assert.equal(c.job_id, null)
})

test('groups and setup state come through normalize', () => {
  const ov = normalize({ groups: [{ name: 'Lab', tone: 'team', language: 'en', members: 2 }, { tone: 'x' }], setup: { checks: [], pending: true, checked_ts: null } })
  assert.deepEqual(ov.groups, [{ name: 'Lab', tone: 'team', language: 'en', members: 2 }])
  assert.equal(ov.setup.pending, true)
  assert.equal(ov.setup.checked_ts, null)
})

test('health: worst checks first, watcher line, model calls', () => {
  const checks = [
    { id: 'a', label: 'A', status: 'ok', detail: '', fix: '' },
    { id: 'b', label: 'B', status: 'warn', detail: '', fix: '' },
    { id: 'c', label: 'C', status: 'missing', detail: '', fix: '' }
  ]
  assert.deepEqual(sortChecks(checks).map(c => c.id), ['c', 'b', 'a'])
  assert.equal(setupSummary(checks).tone, 'bad')
  assert.equal(setupSummary([checks[0]]).text, 'All 1 checks pass')
  assert.equal(watcherLine({ fresh: true, last_pass_ts: 960, interval: '2m', model_calls: 0 }, 1000).text, 'Watcher checked 40 s ago (every 2m)')
  assert.equal(watcherLine({ fresh: false, last_pass_ts: null, interval: '', model_calls: 0 }, 1000).tone, 'warn')
})

test('design facts in plain words', () => {
  assert.deepEqual(designFacts({ size_mm: [40, 30, 35], est_grams_max: 11.9, fits_build_volume: true }), ['40 × 30 × 35 mm', 'about 12 g'])
  assert.deepEqual(designFacts({ size_mm: [300, 10, 10], volume_cm3: 5.94, fits_build_volume: false }), ['300 × 10 × 10 mm', '5.9 cm³', 'too big for the bed'])
  assert.deepEqual(designFacts({}), [])
})

test('backend errors: 404 means the Python half is off, the rest is "unreachable" or an error', () => {
  assert.equal(errorInfo(new Error('404: {"detail":"Not Found"}')).kind, 'not_enabled')
  assert.equal(errorInfo(new Error('503: {"detail":"gateway restarting"}')).text, 'gateway restarting')
  assert.equal(errorInfo(new Error('503: x')).kind, 'unreachable')
  assert.equal(errorInfo(new Error('Failed to fetch')).kind, 'unreachable')
  assert.equal(errorInfo(new Error('403: {"detail":"forbidden"}')).kind, 'error')
})

test('stale data says how old it is', () => {
  const now = 1_800_000_000_000
  assert.deepEqual(staleness(now - 3000, now, false), { stale: false, text: 'Updated just now', ago: 'just now' })
  assert.equal(staleness(now - 40_000, now, false).text, 'Last update 40 s ago')
  assert.equal(staleness(now - 3000, now, true).stale, true)
  assert.equal(staleness(0, now, true).text, 'No data yet')
})
