/**
 * DEV ONLY: mounts the Workshop page, the status-bar chip and a transcript card in a fake app frame, fed by
 * the fixture overview. Query string: ?scenario=approve|printing|paused|idle|failed|offline|empty|checks|two|
 * notowner|off|down|stale|card, &theme=dark, &session=1 (a focused chat: actions run slash.exec),
 * &composer=1 (no chat, but a message box answers).
 */

import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

import { host, shimControl, themeAtom, toasts, useValue } from '@hermes/plugin-sdk'

import plugin from '../src/plugin.tsx'
import type { MediaProps } from '../src/design-card.tsx'

const params = new URLSearchParams(location.search)
const scenario = params.get('scenario') || 'approve'
const dark = params.get('theme') === 'dark'
document.documentElement.classList.toggle('dark', dark)
themeAtom.set(dark ? 'dark' : 'light')
if (params.get('session') === '1') host.state.focusedSessionId.set('sess-demo')
shimControl.composer(params.get('composer') === '1')

const ASSETS: Record<string, string> = {
  'designs/name-tag-sam/v1.stl': 'assets/name_tag_v1.stl',
  'designs/name-tag-sam/v2.stl': 'assets/name_tag_v2.stl',
  'designs/name-tag-sam/v1-iso.png': 'assets/name_tag_v1.png',
  'designs/name-tag-sam/v2-iso.png': 'assets/name_tag_v2.png',
  'designs/name-tag-sam/v2-top.png': 'assets/name_tag_v2_top.png',
  'designs/screw-box/v1.stl': 'assets/label_box.stl',
  'designs/screw-box/v1-iso.png': 'assets/label_box.png',
  'camera/latest.png': 'assets/camera_frame.png',
  'photos/job-9.png': 'assets/done_photo.png'
}

type Json = Record<string, any>

async function loadFixture(): Promise<Json> {
  // The backend's own fixture wins once it exists; until then the dev fixture (same contract).
  const urls = params.get('fixture') === 'dev' ? ['fixtures/workshop_overview.json'] : ['../tests/fixtures/workshop_overview.json', 'fixtures/workshop_overview.json']
  for (const url of urls) {
    const r = await fetch(url).catch(() => null)
    if (r?.ok) {
      console.info('[harness] fixture', url)
      return r.json()
    }
  }
  throw new Error('no fixture')
}

/** Shift every *_ts field so the fixture reads as "now". */
function rebase(v: any, shift: number): any {
  if (Array.isArray(v)) return v.map(x => rebase(x, shift))
  if (v && typeof v === 'object') {
    const out: Json = {}
    for (const [k, x] of Object.entries(v)) out[k] = /(^|_)ts$/.test(k) && typeof x === 'number' && x > 0 ? x + shift : rebase(x, shift)
    return out
  }
  return v
}

function applyScenario(base: Json, name: string): Json {
  const o: Json = structuredClone(base)
  const idle = () => {
    o.printer = { ...o.printer, state: 'idle', job_name: '', progress: 0, remaining_min: null, layer: null, total_layers: null, bed_temp: 24 }
    o.now = null
  }
  switch (name) {
    case 'printing':
    case 'card':
      o.waiting = []
      break
    case 'paused':
      o.waiting = []
      o.printer.state = 'paused'
      break
    case 'idle':
      o.waiting = []
      idle()
      break
    case 'failed':
      o.waiting = []
      o.printer = { ...o.printer, state: 'failed', errors: [{ code: '0300-4000-0002-0001', text: 'The nozzle may be clogged' }] }
      break
    case 'offline':
      o.waiting = []
      o.printer = { ...o.printer, state: 'offline' }
      o.now = null
      o.setup.checks[0] = { id: 'backend', label: 'Printer connection', status: 'error', detail: 'Bambuddy did not answer in 10 s', fix: 'Check the printer is on, then run `hermes home3d doctor`' }
      break
    case 'checks':
      o.waiting[0].checklist[0] = { id: 'plate', label: 'Plate is clear', ok: false, detail: 'camera sees something on the bed' }
      break
    case 'two':
      o.waiting.push({ ...structuredClone(o.waiting[0]), id: 16, queue_item_id: 16, name: 'Lens cap', asked_by: { name: 'Mum', group: 'Family' }, command: 'home3d approve start 16', model: { stl: 'designs/screw-box/v1.stl', preview: 'designs/screw-box/v1-iso.png' } })
      break
    case 'notowner':
      o.viewer = { is_owner: false, reason: 'This Hermes user is not the owner set in home3d settings.' }
      break
    case 'empty':
      idle()
      Object.assign(o, {
        waiting: [], queue: [], done_box: [], notices: { pending: 0, failed: 0, recent: [] }, filament: { slots: [] }, needs_human: [], upgrades: [], designs: [],
        setup: { checks: [] }, watcher: { fresh: false, last_pass_ts: null, interval: '2m', model_calls: 0 }, groups: [],
        camera: { available: false, frame: null, taken_ts: null, note: '' }
      })
      break
  }
  return o
}

const b64 = (buf: ArrayBuffer) => {
  let s = ''
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return btoa(s)
}

async function main() {
  const fixture = await loadFixture()
  let ov = applyScenario(rebase(fixture, Math.round(Date.now() / 1000) - (fixture.generated_ts || 0)), scenario)
  let calls = 0
  const rest = async <T,>(path: string): Promise<T> => {
    await new Promise(r => setTimeout(r, 120))
    if (scenario === 'off') throw new Error('404: {"detail":"Not Found"}')
    if (path.startsWith('overview')) {
      calls += 1
      if (scenario === 'down' || (scenario === 'stale' && calls > 1)) throw new Error('503: {"detail":"gateway restarting"}')
      return { ...ov, generated_ts: Math.round(Date.now() / 1000) } as T
    }
    if (path.startsWith('file?ref=')) {
      const ref = decodeURIComponent(path.slice('file?ref='.length))
      // The backend fixture's refs are paths under tests/fixtures/workshop_files; the dev fixture's are mapped.
      const tries = [ASSETS[ref], /^[\w./-]+$/.test(ref) && !ref.includes('..') ? `../tests/fixtures/workshop_files/${ref}` : null].filter(Boolean) as string[]
      let local = ''
      let buf: ArrayBuffer | null = null
      for (const t of tries) {
        const r = await fetch(t).catch(() => null)
        if (r?.ok) {
          local = t
          buf = await r.arrayBuffer()
          break
        }
      }
      if (!buf) throw new Error('404: {"detail":"no such file"}')
      const mime = local.endsWith('.png') ? 'image/png' : 'model/stl'
      return { name: local.split('/').pop(), bytes: buf.byteLength, mime, dataUrl: `data:${mime};base64,${b64(buf)}` } as T
    }
    throw new Error(`404: {"detail":"no route ${path}"}`)
  }

  // slash.exec as the plugin would answer, and the overview moving on like the real backend.
  shimControl.onRequest(async (method, p: any) => {
    await new Promise(r => setTimeout(r, 700))
    if (method !== 'slash.exec') throw new Error(`unknown method ${method}`)
    const c: string = p.command
    if (c.startsWith('home3d approve start')) {
      const w = ov.waiting.find((x: Json) => c.endsWith(` ${x.queue_item_id}`))
      if (!w) return { output: 'Not done: Cannot start: queue item not found. Nothing was kept: send the command again when ready.' }
      ov = { ...ov, waiting: ov.waiting.filter((x: Json) => x !== w), queue: [{ id: w.queue_item_id, name: w.name, for: w.asked_by, status: 'approved', ours: true, print_time_min: w.facts.print_time_min, eject_planned: w.facts.eject_planned, model: w.model }, ...ov.queue] }
      return { output: `Approved: "${w.name}" for ${w.asked_by.name} (${w.asked_by.group}) is next in the queue. ${w.asked_by.name} will be told when it starts.` }
    }
    if (c === 'home3d pause') {
      ov = { ...ov, printer: { ...ov.printer, state: 'paused' } }
      return { output: 'Paused. The nozzle is parked; resume from the Workshop or with /home3d approve resume.' }
    }
    if (c.startsWith('home3d approve resume')) {
      ov = { ...ov, printer: { ...ov.printer, state: 'printing' } }
      return { output: 'Resumed.' }
    }
    if (c === 'home3d stop') {
      ov = { ...ov, printer: { ...ov.printer, state: 'idle', progress: 0 }, now: null }
      return { output: 'Stopped "Screw box". Mum (Family) was told.' }
    }
    if (c.startsWith('home3d collected')) {
      const id = Number(c.split(' ').pop())
      ov = { ...ov, done_box: ov.done_box.map((d: Json) => (d.job_id === id ? { ...d, collected: true } : d)) }
      return { output: `Marked job ${id} as picked up.` }
    }
    return { output: `Unknown command: ${c}` }
  })

  // Register the plugin against a fake context and keep what it contributed.
  const contributions: any[] = []
  plugin.register({
    source: 'plugin:home-3d-workshop',
    registerMany: cs => {
      contributions.push(...cs)
      return () => {}
    },
    onDispose: () => {},
    onEvent: () => () => {},
    setInterval: () => () => {},
    rest: rest as any,
    os: { writeClipboard: async () => true }
  } as any)
  const page = contributions.find(c => c.id === 'page')
  const chip = contributions.find(c => c.id === 'chip')
  const nav = contributions.find(c => c.id === 'nav')
  const card = contributions.find(c => c.id === 'design-card')

  // A home3d_design render result for the fixture's first design, latest version, as the tool returns it.
  const d0 = ov.designs?.[0]
  const v0 = d0?.versions?.[d0.versions.length - 1]
  const pic = v0?.previews?.[0] ?? ''
  const picUrl = ASSETS[pic] ?? `../tests/fixtures/workshop_files/${pic}`
  const props: MediaProps = {
    file: { path: `/data/${pic}`, name: pic.split('/').pop() || 'preview.png', kind: 'image', mime: 'image/png', resolveUrl: async () => picUrl },
    args: { action: 'render', name: d0?.title },
    result: JSON.stringify({ ok: true, name: d0?.slug, version: v0?.version, ...v0?.facts, previews: (v0?.previews ?? []).map((p: string) => `/data/${p}`), stl_path: `/data/${v0?.stl}`, warnings: [] }),
    sessionId: 'sess-demo',
    fallback: <img src={picUrl} alt="" />
  }

  function Toasts() {
    const list = useValue(toasts)
    return (
      <div className="toasts">
        {list.map(t => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.message}
          </div>
        ))}
      </div>
    )
  }

  function App() {
    const [, force] = useState(0)
    useEffect(() => {
      const t = setInterval(() => force(n => n + 1), 60_000)
      return () => clearInterval(t)
    }, [])
    return (
      <div className="frame">
        <aside className="side">
          <div className="side-row">New session</div>
          <div className="side-row">Capabilities</div>
          <div className="side-row">Messaging</div>
          <div className="side-row">Artifacts</div>
          <div className="side-row active">{nav?.data.label}</div>
        </aside>
        <main className="main">
          {scenario === 'card' ? (
            <div className="transcript">
              <div className="bubble">Here is the new version. Want me to send it to the printer?</div>
              {card ? card.data.render(props) : <p>no TOOL_MEDIA_RENDERER_AREA</p>}
            </div>
          ) : (
            page.render()
          )}
        </main>
        <footer className="status">
          <span>Backend ready</span>
          <span style={{ marginLeft: 'auto' }} />
          {chip.render()}
          <span>client v0.23.1</span>
        </footer>
        <Toasts />
      </div>
    )
  }
  createRoot(document.getElementById('root')!).render(<App />)
}

main().catch(e => {
  document.body.textContent = `Harness failed: ${e?.message || e}`
})
