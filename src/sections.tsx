/** The sections under the top band, one per use case 4 to 10. Each has a plain-words empty state. */

import { useState } from 'react'

import type { Rest } from './data.ts'
import { Icon } from './icons.tsx'
import {
  designFacts,
  fmtAgo,
  fmtDuration,
  hexColor,
  noticeLine,
  noticeStatusLabel,
  noticeSummary,
  noticeTone,
  outcomeLabel,
  sentence,
  setupSummary,
  sortChecks,
  watcherLine
} from './model.ts'
import type { Design, Overview } from './types.ts'
import { Empty, FixText, PersonTag, RefImage, Reply, Section, Spinner, Tag, Thumb, useAction } from './ui.tsx'
import { PartViewer } from './viewer.tsx'

type P = { ov: Overview; rest: Rest; nowSec: number }

// ---- 4. Order ------------------------------------------------------------------------------------

const isPrinting = (status: string) => /^printing$|^running$/i.test(status.trim())

export function Queue({ ov, rest }: P) {
  const nextIndex = ov.queue.findIndex(q => !isPrinting(q.status))
  return (
    <Section id="queue" title="Up next" count={ov.queue.length}>
      {ov.queue.length ? (
        <ol className="w-rows" aria-label="Print queue">
          {ov.queue.map((q, i) => (
            <li key={q.id} className={`w-row${i === nextIndex ? ' next' : ''}`}>
              <span className="w-pos num" aria-label={`Position ${i + 1}`}>
                {i + 1}
              </span>
              <Thumb rest={rest} fileRef={q.model?.preview ?? null} alt={`Preview of ${q.name}`} />
              <div className="w-main">
                <span className="title">
                  <span className="ellipsis">{q.name || 'Untitled job'}</span>
                  {!isPrinting(q.status) ? null : ov.printer.state === 'printing' ? (
                    <Tag tone="accent">Printing now</Tag>
                  ) : ov.printer.state === 'paused' ? (
                    <Tag tone="warn">Paused</Tag>
                  ) : ov.printer.state === 'failed' ? (
                    <Tag tone="bad">Failed</Tag>
                  ) : null}
                </span>
                <span className="sub">
                  {q.for.name ? (
                    <span>
                      for <PersonTag p={q.for} groups={ov.groups} />
                    </span>
                  ) : (
                    <span>not asked in a chat</span>
                  )}
                  {fmtDuration(q.print_time_min) ? <span className="num">{fmtDuration(q.print_time_min)}</span> : null}
                  {q.eject_planned !== null ? <span>{q.eject_planned ? 'auto-eject' : 'stays on plate'}</span> : null}
                  {!q.ours ? <span>from elsewhere</span> : null}
                </span>
              </div>
              <div className="end">{q.status && !isPrinting(q.status) ? <span className="state">{sentence(q.status)}</span> : null}</div>
            </li>
          ))}
        </ol>
      ) : (
        <Empty>The queue is empty. New requests wait here after you approve them.</Empty>
      )}
    </Section>
  )
}

// ---- 5. Deliver ------------------------------------------------------------------------------------

export function DoneBox({ ov, rest, nowSec }: P) {
  const action = useAction()
  const waiting = ov.done_box.filter(d => !d.collected).length
  return (
    <Section
      id="done"
      title="Done box"
      count={ov.done_box.length}
      aside={waiting ? <span className="faint">{waiting} to pick up</span> : null}
    >
      <Reply state={action} inline />
      {ov.done_box.length ? (
        <ul className="w-rows">
          {ov.done_box.map((d, i) => {
            const out = outcomeLabel(d)
            const cmd = d.command || `home3d collected ${d.id}`
            return (
              <li key={d.id || `row-${i}`} className="w-row" data-workshop-part={d.id}>
                <span className="w-thumb" style={{ width: 64, height: 48 }}>
                  {d.photo ? (
                    <RefImage rest={rest} fileRef={d.photo} alt={`Photo of ${d.name} after printing`} fallback={<Icon name="camera" />} />
                  ) : (
                    <Icon name="camera" />
                  )}
                </span>
                <div className="w-main">
                  <span className="title">
                    <span className="ellipsis">{d.name || 'A print'}</span>
                    <Tag tone={out.tone}>{out.text}</Tag>
                  </span>
                  <span className="sub">
                    <span>
                      for <PersonTag p={d.for} groups={ov.groups} />
                    </span>
                    {fmtAgo(d.finished_ts, nowSec) ? <span>finished {fmtAgo(d.finished_ts, nowSec)}</span> : null}
                    {d.detail ? <span className="faint">{d.detail}</span> : null}
                  </span>
                </div>
                <div className="end">
                  {!d.collected ? (
                    <button
                      type="button"
                      className="w-btn sm"
                      disabled={!!action.busy}
                      onClick={() => void action.run(cmd)}
                      aria-label={`Picked up: ${d.name || 'a print'}`}
                      title={`Marks it as picked up (runs /${cmd})`}
                      data-workshop-action="collected"
                    >
                      {action.busy === cmd ? <Spinner /> : <Icon name="check" size={12} />} Picked up
                    </button>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      ) : (
        <Empty icon="box">Nothing has come off the printer yet. Finished parts are listed here with a photo.</Empty>
      )}
    </Section>
  )
}

// ---- 7. Stock ---------------------------------------------------------------------------------------

export function Filament({ ov }: P) {
  const slots = ov.filament.slots
  return (
    <Section id="filament" title="Filament">
      {slots.length ? (
        <div className="w-slots">
          {slots.map(s => {
            const hex = hexColor(s.color)
            const low = s.remain_pct !== null && s.remain_pct < 15
            if (!s.loaded) {
              return (
                <div key={s.slot} className="w-slot empty">
                  <Spool pct={null} empty />
                  <span className="mat faint">Empty</span>
                  <span className="sub ellipsis">{s.label}</span>
                </div>
              )
            }
            return (
              <div
                key={s.slot}
                className={`w-slot${low ? ' low' : ''}`}
                style={{ ['--sw' as string]: hex ?? undefined }}
                title={[s.name, hex].filter(Boolean).join(', ') || undefined}
              >
                <Spool pct={s.remain_pct} />
                <span className="mat ellipsis">{s.material || 'Unknown material'}</span>
                <span
                  className="sub num ellipsis"
                  role={s.remain_pct !== null ? 'meter' : undefined}
                  aria-label={s.remain_pct !== null ? `${s.label} remaining` : undefined}
                  aria-valuenow={s.remain_pct ?? undefined}
                  aria-valuemin={s.remain_pct !== null ? 0 : undefined}
                  aria-valuemax={s.remain_pct !== null ? 100 : undefined}
                >
                  {s.label}
                  {s.remain_pct !== null ? `, ${s.remain_pct}%${low ? ', low' : ''}` : ''}
                </span>
                {s.name ? <span className="brand">{s.name}</span> : null}
              </div>
            )
          })}
        </div>
      ) : (
        <Empty icon="spool">The printer has not reported its filament yet.</Empty>
      )}
    </Section>
  )
}

/** A spool seen from the side: the filament is wound as far out from the hub as the slot is full. */
function Spool({ pct, empty }: { pct: number | null; empty?: boolean }) {
  const hub = 7
  const rim = 23.5
  const level = pct === null ? 0.72 : Math.max(0, Math.min(100, pct)) / 100
  const wound = hub + (rim - hub) * level
  return (
    <svg width="60" height="60" viewBox="-27 -27 54 54" aria-hidden>
      <circle r="26" className="flange" />
      {empty || wound <= hub + 0.5 ? null : (
        <>
          <circle r={wound} className="wound" />
          {wound - hub > 6 ? <circle r={(wound + hub) / 2} className="turn" /> : null}
        </>
      )}
      {empty ? null : (
        <>
          <circle r={hub} className="hub" />
          <circle r="2.4" className="hole" />
        </>
      )}
    </svg>
  )
}

// ---- 6. Trust ---------------------------------------------------------------------------------------

export function Notices({ ov, nowSec }: P) {
  const n = ov.notices
  const sum = noticeSummary(n)
  const recent = n.recent.slice(0, 4)
  const older = n.recent.length - recent.length
  return (
    <Section id="notices" title="Messages">
      {sum.tone !== 'neutral' ? (
        <div className={`w-summary t-${sum.tone}`}>
          <Icon name={sum.tone === 'good' ? 'check' : 'alert'} />
          {sum.text}
        </div>
      ) : null}
      {recent.length ? (
        <ul className="w-rows">
          {recent.map((r, i) => {
            const tone = noticeTone(r.status)
            return (
              <li key={`${r.ts}-${i}`} className="w-row" style={{ alignItems: 'flex-start', padding: '9px 0' }}>
                <span className={`w-dot t-${tone}`} aria-hidden />
                <div className="w-main">
                  <span className="clamp2" title={r.text || undefined}>
                    {noticeLine(r)}
                  </span>
                  <span className="sub">
                    <span>to {r.to || 'someone'}</span>
                    <span>{fmtAgo(r.ts, nowSec)}</span>
                    <span className={`t-${tone} w-ink`}>{noticeStatusLabel(r.status)}</span>
                    {r.error ? <span className="faint">{r.error}</span> : null}
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      ) : null}
      {older > 0 ? <p className="faint" style={{ fontSize: 12, paddingTop: 4 }}>and {older} earlier</p> : null}
      {recent.length ? null : (
        <Empty icon="bell">No messages sent yet. When a print starts, finishes or fails, the people who asked are told, and it shows here.</Empty>
      )}
    </Section>
  )
}

// ---- 9. Improve -----------------------------------------------------------------------------------------

export function Improve({ ov, nowSec }: P) {
  const open = ov.needs_human.filter(h => h.open)
  const handled = ov.needs_human.filter(h => !h.open)
  const closed = handled.length
  // the open moments first; the space left shows the latest handled ones (what the upgrade proposals count)
  const shown = [...open.slice(0, 5), ...handled.slice(0, Math.max(0, 4 - open.length))]
  return (
    <Section
      id="improve"
      title="Where it needed you"
      count={open.length || null}
    >
      {open.length ? null : <Empty>Nothing needs a person right now{closed ? ` (${closed} handled before)` : ''}.</Empty>}
      {shown.length ? (
        <ul className="w-rows">
          {shown.map(h => (
            <li key={h.id} className="w-row" style={{ alignItems: 'flex-start' }} data-workshop-moment={h.open ? 'open' : 'handled'}>
              <span className={`lead${h.open ? ' t-warn' : ''}`}>
                <Icon name="hand" />
              </span>
              <div className="w-main">
                <span className={h.open ? undefined : 'muted'}>{h.text}</span>
                <span className="sub">
                  {h.open ? null : <span className="faint">Handled</span>}
                  {h.job ? <span>{h.job}</span> : null}
                  {h.who ? <span>for {h.who}</span> : null}
                  <span>{fmtAgo(h.ts, nowSec)}</span>
                </span>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      <div>
        <h3 className="w-subhead">Proposed upgrades</h3>
        {ov.upgrades.length ? (
          <ul className="w-rows">
            {ov.upgrades.map(u => (
              <li key={u.id} className="w-row" style={{ alignItems: 'flex-start' }}>
                <span className="lead t-accent">
                  <Icon name="spark" />
                </span>
                <div className="w-main">
                  <span className="title">
                    <span>{u.title}</span>
                  </span>
                  {u.why ? <span className="muted clamp3">{u.why}</span> : null}
                  <span className="sub">
                    {u.status ? <span className={u.status === 'done' ? 't-good w-ink' : 'faint'}>{sentence(u.status)}</span> : null}
                    {u.count ? <span className="num">came up {u.count}×</span> : null}
                    {u.model_ref ? (
                      <a className="w-link" href={u.model_ref} target="_blank" rel="noreferrer noopener">
                        <Icon name="link" size={12} /> The printable part
                      </a>
                    ) : null}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <Empty icon="spark">No upgrade proposals yet. They come from patterns in the moments above.</Empty>
        )}
      </div>
    </Section>
  )
}

// ---- 10. Iterate ------------------------------------------------------------------------------------------

export function Designs({ ov, rest }: P) {
  return (
    <Section id="designs" title="Design versions" count={ov.designs.length}>
      {ov.designs.length ? (
        <div>
          {ov.designs.map(d => (
            <DesignRow key={d.slug} d={d} rest={rest} />
          ))}
        </div>
      ) : (
        <Empty icon="cube">No designs yet. Ask the printer in a chat to design a part, and every version appears here.</Empty>
      )}
    </Section>
  )
}

function DesignRow({ d, rest }: { d: Design; rest: Rest }) {
  const [pick, setPick] = useState<number | null>(null)
  const [img, setImg] = useState(0)
  const latest = d.versions[d.versions.length - 1]
  const v = d.versions.find(x => x.version === pick) ?? latest
  if (!v) return null
  const facts = designFacts(v.facts)
  const preview = v.previews[Math.min(img, v.previews.length - 1)] ?? null
  return (
    <div className="w-design" data-workshop-design={d.slug}>
      <div className="w-design-head">
        <span style={{ fontWeight: 650 }}>{d.title}</span>
        <div className="w-vers" role="group" aria-label={`Versions of ${d.title}`}>
          {d.versions.map(x => (
            <button
              key={x.version}
              type="button"
              className="w-ver num"
              aria-pressed={x.version === v.version}
              onClick={() => {
                setPick(x.version)
                setImg(0)
              }}
            >
              v{x.version}
            </button>
          ))}
        </div>
        <span className="faint" style={{ marginLeft: 'auto', fontSize: 12 }}>
          {d.versions.length} version{d.versions.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="w-design-body">
        <PartViewer key={`${d.slug}-${v.version}`} rest={rest} stl={v.stl} preview={preview} color={null} label={`${d.title} v${v.version}`} className="short" />
        <div style={{ display: 'grid', gap: 8, minWidth: 0 }}>
          <div style={{ fontWeight: 600 }}>
            v{v.version}
            {v.version === latest.version ? <span className="faint" style={{ fontWeight: 400 }}>, latest</span> : null}
          </div>
          {facts.length ? (
            <div className="w-facts-line num">
              {facts.map(f => (
                <span key={f} className={f.includes('too big') ? 'bad' : undefined}>
                  {f}
                </span>
              ))}
            </div>
          ) : null}
          {v.note ? <p className="muted">{v.note}</p> : null}
          {v.previews.length > 1 ? (
            <div className="w-strip-thumbs" role="group" aria-label="Preview pictures">
              {v.previews.map((p, i) => (
                <button key={p} type="button" aria-pressed={i === img} aria-label={`Picture ${i + 1}`} onClick={() => setImg(i)}>
                  <RefImage rest={rest} fileRef={p} alt="" />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

// ---- 8. Health ------------------------------------------------------------------------------------------

export function Setup({ ov, nowSec }: P) {
  const checks = sortChecks(ov.setup.checks)
  const sum = setupSummary(checks)
  const w = watcherLine(ov.watcher, nowSec)
  const bad = checks.filter(c => c.status !== 'ok')
  const good = checks.filter(c => c.status === 'ok')
  const calls = ov.watcher.model_calls
  return (
    <Section id="setup" title="Health">
      {checks.length ? (
        <div className={`w-summary t-${sum.tone}`}>
          <Icon name={sum.tone === 'good' ? 'check' : 'alert'} />
          {sum.text}
        </div>
      ) : null}
      <div className="w-watch">
        <span className={`beat t-${w.tone}`}>{w.text}</span>
        {calls !== null ? (
          <span className={`w-zero num${calls === 0 ? '' : ' spent'}`} title="The watcher checks the printer with plain code: it spends no model calls.">
            <b>{calls}</b> model call{calls === 1 ? '' : 's'}
          </span>
        ) : null}
        {ov.setup.pending ? (
          <span className="faint" data-workshop-setup="checking">
            checking the setup now…
          </span>
        ) : fmtAgo(ov.setup.checked_ts, nowSec) ? (
          <span className="faint">setup checked {fmtAgo(ov.setup.checked_ts, nowSec)}</span>
        ) : null}
      </div>
      {bad.length ? (
        <ul className="w-rows">
          {bad.map(c => (
            <li key={c.id || c.label} className="w-row" style={{ alignItems: 'flex-start' }}>
              <span className={`lead t-${c.status === 'warn' ? 'warn' : 'bad'}`}>
                <Icon name={c.status === 'warn' ? 'alert' : 'x'} />
              </span>
              <div className="w-main">
                <span className="title">{c.label}</span>
                {c.detail ? <span className="sub">{c.detail}</span> : null}
                {c.fix ? (
                  <span className="w-fix">
                    <b>Fix:</b>
                    <FixText text={c.fix} />
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {good.length ? (
        <details className="w-more">
          <summary>
            {good.length} check{good.length === 1 ? '' : 's'} fine
          </summary>
          <ul className="w-rows">
            {good.map(c => (
              <li key={c.id || c.label} className="w-row" style={{ padding: '6px 0' }}>
                <span className="lead t-good">
                  <Icon name="check" />
                </span>
                <div className="w-main">
                  <span>{c.label}</span>
                  {c.detail ? <span className="sub">{c.detail}</span> : null}
                </div>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {!checks.length ? (
        <Empty icon="wrench">{ov.setup.pending ? 'The setup check is running; its results show here in a moment.' : 'The workshop has not run its setup check yet.'}</Empty>
      ) : null}
    </Section>
  )
}
