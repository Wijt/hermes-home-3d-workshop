/**
 * The top band: what the printer is doing and for whom (use case 1), the approval waiting for the owner
 * (2), and Stop / Pause (3). Everything else on the page sits below it.
 */

import { type ReactNode, useState } from 'react'

import type { Rest } from './data.ts'
import { Icon } from './icons.tsx'
import {
  approvalCopy,
  ejectLabel,
  failingChecks,
  filamentLine,
  fmtAgo,
  fmtDuration,
  heroMode,
  isActive,
  isReady,
  partColor,
  personLabel,
  progressPct,
  slotByNumber,
  slotLabel,
  stateLabel,
  stateTone,
  waitingAfterPrint,
  waitingCommand
} from './model.ts'
import type { Overview, Waiting } from './types.ts'
import { PersonTag, RefImage, Reply, Spinner, useAction } from './ui.tsx'
import { PartViewer } from './viewer.tsx'

export function Hero({ ov, rest, nowSec }: { ov: Overview; rest: Rest; nowSec: number }) {
  const mode = heroMode(ov)
  const printerAction = useAction()
  return (
    <section className="w-hero" aria-label="Printer now" data-workshop-hero={mode}>
      <StatusStrip ov={ov} action={printerAction} rest={rest} nowSec={nowSec} showCam={mode === 'approve'} />
      <Reply state={printerAction} />
      {mode === 'approve' ? (
        <Approvals ov={ov} rest={rest} nowSec={nowSec} action={printerAction} />
      ) : mode === 'running' ? (
        <NowPrinting ov={ov} rest={rest} nowSec={nowSec} />
      ) : mode === 'attention' ? (
        <Attention ov={ov} rest={rest} nowSec={nowSec} />
      ) : mode === 'offline' ? (
        <Offline ov={ov} />
      ) : (
        <Idle ov={ov} rest={rest} nowSec={nowSec} />
      )}
    </section>
  )
}

// ---- the strip: state, job, person, numbers, Stop and Pause -------------------------------------

function StatusStrip({
  ov,
  action,
  rest,
  nowSec,
  showCam
}: {
  ov: Overview
  action: ReturnType<typeof useAction>
  rest: Rest
  nowSec: number
  /** The body shows something else (an approval): keep the camera one click away. */
  showCam: boolean
}) {
  const p = ov.printer
  const [confirmStop, setConfirmStop] = useState(false)
  const [bigCam, setBigCam] = useState(false)
  const cam = showCam && ov.camera.available && ov.camera.frame ? ov.camera.frame : null
  const camAgo = fmtAgo(ov.camera.taken_ts, nowSec)
  const active = isActive(p.state)
  const pct = progressPct(p)
  const job = ov.now?.name || p.job_name
  const owner = ov.viewer.is_owner
  const notOwner = owner ? undefined : ov.viewer.reason || 'Only the printer owner can do this.'
  const resumeWaiting = ov.waiting.some(w => w.action === 'resume')
  return (
    <>
      <div className="w-strip">
        {cam ? (
          <button
            type="button"
            className="w-camthumb"
            onClick={() => setBigCam(v => !v)}
            aria-expanded={bigCam}
            aria-label={`Camera picture${camAgo ? `, ${camAgo}` : ''}: ${bigCam ? 'hide' : 'show larger'}`}
            title={`Camera${camAgo ? ` · ${camAgo}` : ''}`}
            data-workshop-camthumb=""
          >
            <RefImage rest={rest} fileRef={cam} alt="" fallback={<Icon name="camera" />} />
          </button>
        ) : null}
        <span className={`w-state t-${stateTone(p.state)}${p.state === 'printing' ? ' live' : ''}`} data-workshop-state={p.state}>
          <span className="dot" aria-hidden />
          {stateLabel(p.state)}
        </span>
        {job ? (
          <span className="w-strip-job">
            <span className="name ellipsis">{job}</span>
            {ov.now ? (
              <span className="faint">
                for <PersonTag p={ov.now.for} groups={ov.groups} />
              </span>
            ) : null}
          </span>
        ) : (
          <span className="w-strip-job" />
        )}
        {active ? (
          <span className="w-strip-meta num">
            <span>{pct}%</span>
            {fmtDuration(p.remaining_min) ? (
              <span>
                <Icon name="clock" size={12} />
                {fmtDuration(p.remaining_min)} left
              </span>
            ) : null}
            {p.layer !== null && p.total_layers ? (
              <span>
                <Icon name="layers" size={12} />
                {p.layer}/{p.total_layers}
              </span>
            ) : null}
          </span>
        ) : p.bed_temp !== null ? (
          <span className="w-strip-meta num">
            <span title="Bed temperature">
              <Icon name="thermo" size={12} />
              {Math.round(p.bed_temp)} °C
            </span>
          </span>
        ) : null}
        {active ? (
          <span className="w-strip-actions">
            {p.state === 'printing' ? (
              <button
                type="button"
                className="w-btn"
                disabled={!!action.busy || !owner}
                title={notOwner ?? 'Pause: the printer holds where it is; you can resume from here.'}
                onClick={() => void action.run('home3d pause')}
                data-workshop-action="pause"
              >
                {action.busy === 'home3d pause' ? <Spinner /> : <Icon name="pause" size={12} />} Pause
              </button>
            ) : !resumeWaiting ? (
              <button
                type="button"
                className="w-btn"
                disabled={!!action.busy || !owner}
                title={notOwner ?? 'Resume the print from where it stopped.'}
                onClick={() => void action.run('home3d approve resume')}
                data-workshop-action="resume"
              >
                {action.busy === 'home3d approve resume' ? <Spinner /> : <Icon name="play" size={12} />} Resume
              </button>
            ) : null}
            <button
              type="button"
              className="w-btn danger"
              disabled={!!action.busy || !owner}
              title={notOwner ?? 'Stop the print (asks first)'}
              aria-expanded={confirmStop}
              onClick={() => setConfirmStop(v => !v)}
              data-workshop-action="stop"
            >
              <Icon name="stop" size={12} /> Stop
            </button>
          </span>
        ) : null}
      </div>
      {active ? (
        <div
          className="w-strip-bar"
          role="progressbar"
          aria-label="Print progress"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <i style={{ width: `${pct}%` }} />
        </div>
      ) : null}
      {cam && bigCam ? (
        <div style={{ padding: '0 16px 14px', maxWidth: 560 }}>
          <CameraFrame ov={ov} rest={rest} nowSec={nowSec} fallback={null} />
        </div>
      ) : null}
      {confirmStop && active ? (
        <div style={{ padding: '0 16px 14px' }}>
          <div className="w-confirm" role="alertdialog" aria-labelledby="w-stop-q">
            <p id="w-stop-q">
              <b>Stop “{job || 'this print'}” now?</b>{' '}
              <span className="muted">
                The printer cancels the job{ov.now ? ` for ${personLabel(ov.now.for)}` : ''}. The unfinished part stays on the plate, and the
                job cannot be resumed.
              </span>
            </p>
            <div className="row">
              <button
                type="button"
                className="w-btn danger-solid"
                autoFocus
                disabled={!!action.busy}
                onClick={() => {
                  setConfirmStop(false)
                  void action.run('home3d stop')
                }}
                data-workshop-action="stop-confirm"
              >
                <Icon name="stop" size={12} /> Yes, stop the print
              </button>
              <button type="button" className="w-btn" onClick={() => setConfirmStop(false)}>
                Keep printing
              </button>
              <span className="w-cmd" style={{ alignSelf: 'center' }}>
                runs /home3d stop
              </span>
            </div>
          </div>
        </div>
      ) : null}
      {p.errors.length ? (
        <div style={{ padding: '0 16px 12px' }}>
          {p.errors.map((e, i) => (
            <div key={`${e.code}-${i}`} className="w-banner t-bad" style={{ marginBottom: 6 }}>
              <Icon name="alert" />
              <span>
                <b>{e.text || 'Printer error'}</b> {e.code ? <span className="w-cmd">{e.code}</span> : null}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </>
  )
}

// ---- approvals ------------------------------------------------------------------------------------

type Action = ReturnType<typeof useAction>

function Approvals({ ov, rest, nowSec, action }: { ov: Overview; rest: Rest; nowSec: number; action: Action }) {
  const [pick, setPick] = useState(0)
  const index = Math.min(pick, ov.waiting.length - 1)
  const w = ov.waiting[index]
  return (
    <>
      {ov.waiting.length > 1 ? (
        <div className="w-tabs" role="tablist" aria-label="Waiting for you">
          {ov.waiting.map((x, i) => (
            <button
              key={`${x.action}-${x.queue_item_id ?? 'x'}-${x.id}`}
              type="button"
              role="tab"
              className="w-tab"
              aria-selected={i === index}
              onClick={() => setPick(i)}
            >
              {i + 1}. {x.name || 'Job'} · {x.asked_by.name || 'someone'}
            </button>
          ))}
        </div>
      ) : null}
      <ApprovalCard key={`${w.action}-${w.queue_item_id ?? 'x'}-${w.id}`} w={w} ov={ov} rest={rest} nowSec={nowSec} action={action} />
    </>
  )
}

// The action state lives in the Hero: an approved item leaves `waiting` on the next refresh, and the
// command's reply must stay on screen after its card is gone.
function ApprovalCard({ w, ov, rest, nowSec, action }: { w: Waiting; ov: Overview; rest: Rest; nowSec: number; action: Action }) {
  const copy = approvalCopy(w)
  const failing = failingChecks(w.checklist)
  const ready = isReady(w)
  const command = waitingCommand(w)
  const slot = slotByNumber(ov.filament.slots, w.facts.slot)
  const swatch = partColor(w.facts, ov.filament.slots)
  const busyMain = action.busy === command
  const busyAlt = !!w.alt && action.busy === w.alt.command
  const done = action.outcome?.kind === 'ran' && action.outcome.ok && (action.outcome.command === command || action.outcome.command === w.alt?.command)
  const owner = ov.viewer.is_owner
  const kicker = w.action === 'start' ? 'Waiting for your OK' : w.action === 'clear' ? 'Plate check' : 'Paused, waiting for you'
  const notReady = failing.length
    ? `${failing.length} check${failing.length > 1 ? 's' : ''} not passed yet: the printer refuses until ${failing.length > 1 ? 'they are' : 'it is'} fixed.`
    : 'Not ready yet: the printer refuses for now.'
  return (
    <div className="w-hero-body" data-workshop-approval={w.id}>
      <PartViewer
        rest={rest}
        stl={w.model?.stl ?? null}
        preview={w.model?.preview ?? null}
        color={swatch}
        label={w.name || 'the part'}
        autoMount
      />
      <div style={{ minWidth: 0 }}>
        <span className="w-kicker t-accent">
          <Icon name="hand" size={13} /> {kicker}
        </span>
        <h3 className="w-big">{w.name || 'A print job'}</h3>
        <p className="w-asked">
          <span>asked by</span> <PersonTag p={w.asked_by} groups={ov.groups} />
          {fmtAgo(w.asked_ts, nowSec) ? <span className="faint">· {fmtAgo(w.asked_ts, nowSec)}</span> : null}
        </p>
        {w.request_text ? <blockquote className="w-quote">“{w.request_text}”</blockquote> : null}
        {w.action === 'start' ? (
          <dl className="w-facts">
            <div className="w-fact">
              <dt>Print time</dt>
              <dd className="num">{fmtDuration(w.facts.print_time_min) || 'Unknown'}</dd>
            </div>
            <div className="w-fact">
              <dt>Filament</dt>
              <dd className="num">{w.facts.grams !== null ? `${Math.round(w.facts.grams * 10) / 10} g` : 'Unknown'}</dd>
            </div>
            <div className="w-fact">
              <dt>Material</dt>
              <dd>
                {swatch ? <span className="w-swatch" style={{ ['--sw' as string]: swatch }} aria-hidden /> : null}
                <span>{filamentLine(w.facts, ov.filament.slots)}</span>
              </dd>
            </div>
            <div className="w-fact" title={w.facts.eject_reason || undefined}>
              <dt>When done</dt>
              <dd>
                <Icon name={w.facts.eject_planned ? 'eject' : 'box'} size={13} />
                <span>{ejectLabel(w.facts.eject_planned)}</span>
              </dd>
            </div>
          </dl>
        ) : (
          <div style={{ height: 14 }} />
        )}
        {slot && slot.remain_pct !== null && w.facts.grams !== null && slot.remain_pct < 15 ? (
          <div className="w-banner t-warn">
            <Icon name="spool" />
            <span>
              {slotLabel(w.facts, ov.filament.slots)} is down to {slot.remain_pct}%: check there is enough for {Math.round(w.facts.grams)} g.
            </span>
          </div>
        ) : null}
        {w.checklist.length ? (
          <ul className="w-checks" aria-label="Safety checklist">
            {w.checklist.map(c => (
              <li key={c.id || c.label} className={c.ok ? 'ok' : 'no'}>
                <Icon name={c.ok ? 'check' : 'x'} title={c.ok ? 'passed' : 'not passed'} />
                <span>
                  {c.label}
                  {c.detail ? <span className="detail"> · {c.detail}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        <div className="w-go">
          <button
            type="button"
            className={`w-btn primary${ready ? '' : ' muted-primary'}`}
            disabled={!!action.busy || !command || done || !owner}
            onClick={() => void action.run(command)}
            data-workshop-action={`approve-${w.action}`}
          >
            {busyMain ? <Spinner /> : <Icon name={w.action === 'clear' ? 'check' : 'play'} size={13} />}
            {busyMain ? 'Sending…' : done ? 'Sent' : copy.button}
          </button>
          {w.alt ? (
            <button
              type="button"
              className="w-btn"
              disabled={!!action.busy || done || !owner}
              onClick={() => void action.run(w.alt!.command)}
              title={`runs /${w.alt.command}`}
              data-workshop-action="approve-alt"
            >
              {busyAlt ? <Spinner /> : null}
              {w.alt.label}
            </button>
          ) : null}
          <span className="w-go-explain">
            {!owner ? ov.viewer.reason || 'Only the printer owner can approve.' : ready ? copy.explain : notReady}
            <br />
            <span className="w-cmd">runs /{command}</span>
          </span>
        </div>
      </div>
    </div>
  )
}

// ---- running ---------------------------------------------------------------------------------------

function CameraFrame({ ov, rest, nowSec, fallback }: { ov: Overview; rest: Rest; nowSec: number; fallback: ReactNode }) {
  const cam = ov.camera
  if (!cam.available || !cam.frame) return <>{fallback}</>
  const ago = fmtAgo(cam.taken_ts, nowSec)
  return (
    <div className="w-media wide" data-workshop-camera="">
      <RefImage rest={rest} fileRef={cam.frame} alt="Latest picture from the printer camera" className="fill cover" fallback={fallback} />
      <div className="over bl">
        <span className="w-photo-cap">
          <Icon name="camera" size={12} /> Camera{ago ? ` · ${ago}` : ''}
        </span>
      </div>
    </div>
  )
}

function NoCamera({ ov }: { ov: Overview }) {
  return (
    <div className="w-media wide">
      <div className="center">
        <Icon name="camera" size={26} />
        <span>{ov.camera.note || (ov.camera.available ? 'No camera picture yet' : 'No camera on this printer')}</span>
      </div>
    </div>
  )
}

function NowPrinting({ ov, rest, nowSec }: { ov: Overview; rest: Rest; nowSec: number }) {
  const p = ov.printer
  const pct = progressPct(p)
  const left = fmtDuration(p.remaining_min)
  const endsAt =
    p.remaining_min !== null && p.state === 'printing'
      ? new Date((nowSec + p.remaining_min * 60) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : ''
  const after = waitingAfterPrint(ov)
  const model = ov.now?.model
  const fallback = model ? (
    <PartViewer rest={rest} stl={model.stl} preview={model.preview} color={null} label={ov.now?.name || 'the part'} className="wide" />
  ) : (
    <NoCamera ov={ov} />
  )
  return (
    <div className="w-hero-body">
      <CameraFrame ov={ov} rest={rest} nowSec={nowSec} fallback={fallback} />
      <div style={{ minWidth: 0, alignSelf: 'center' }}>
        <span className={`w-kicker t-${stateTone(p.state)}`}>{p.state === 'paused' ? 'Paused' : 'Printing now'}</span>
        <h3 className="w-big">{ov.now?.name || p.job_name || 'A print job'}</h3>
        {ov.now ? (
          <p className="w-asked">
            <span>for</span> <PersonTag p={ov.now.for} groups={ov.groups} />
          </p>
        ) : null}
        <div className="w-pct num" style={{ marginTop: 16 }}>
          {pct}
          <small>%</small>
        </div>
        <div className="w-bigbar" aria-hidden>
          <i style={{ width: `${pct}%` }} />
        </div>
        <div className="w-lines num">
          {left ? (
            <div>
              <Icon name="clock" />
              <span>
                <b>{left}</b> left{endsAt ? ` · done around ${endsAt}` : ''}
              </span>
            </div>
          ) : null}
          {p.layer !== null && p.total_layers ? (
            <div>
              <Icon name="layers" />
              <span>
                Layer <b>{p.layer}</b> of {p.total_layers}
              </span>
            </div>
          ) : null}
          {ov.now ? (
            <div>
              <Icon name={ov.now.eject_planned ? 'eject' : 'box'} />
              <span>{ejectLabel(ov.now.eject_planned)}</span>
            </div>
          ) : null}
          {p.bed_temp !== null ? (
            <div>
              <Icon name="thermo" />
              <span>Bed {Math.round(p.bed_temp)} °C</span>
            </div>
          ) : null}
        </div>
        {after.length ? (
          <div className="w-banner t-accent" style={{ marginTop: 16, marginBottom: 0 }} data-workshop-after-print="">
            <Icon name="hand" />
            <span>
              <b>Waiting for your OK after this print:</b>{' '}
              {after.map((w, i) => (
                <span key={`${w.action}-${w.queue_item_id ?? i}`}>
                  {i ? ', ' : ''}
                  {w.name || 'a job'}
                  {w.asked_by.name ? <span className="muted"> for {personLabel(w.asked_by)}</span> : null}
                </span>
              ))}
            </span>
          </div>
        ) : null}
      </div>
    </div>
  )
}

// ---- nothing running ---------------------------------------------------------------------------------

function Idle({ ov, rest, nowSec }: { ov: Overview; rest: Rest; nowSec: number }) {
  const next = ov.queue[0]
  const finished = ov.printer.state === 'finished'
  return (
    <div className="w-idle">
      <div>
        {finished ? <span className="w-kicker t-good">Finished</span> : null}
        <h3 className="w-big">
          {finished ? `${ov.now?.name || ov.printer.job_name || 'The last job'} is done.` : 'Nothing is printing, and nothing is waiting for you.'}
        </h3>
        <p className="muted" style={{ marginTop: 6 }}>
          {next ? (
            <>
              Next in line: <b>{next.name}</b> for <PersonTag p={next.for} groups={ov.groups} />
              {next.status ? <span className="faint"> · {next.status}</span> : null}
            </>
          ) : (
            <>When someone asks {ov.persona || 'the printer'} for a part in a chat, it shows up here for your OK.</>
          )}
        </p>
      </div>
      {ov.camera.available && ov.camera.frame ? <CameraFrame ov={ov} rest={rest} nowSec={nowSec} fallback={null} /> : null}
    </div>
  )
}

function Attention({ ov, rest, nowSec }: { ov: Overview; rest: Rest; nowSec: number }) {
  const p = ov.printer
  const title =
    p.state === 'failed'
      ? `${ov.now?.name || p.job_name || 'The print'} failed.`
      : p.awaiting_plate_clear
        ? 'The plate needs clearing before the next print.'
        : 'The printer reports a problem.'
  return (
    <div className="w-idle">
      <div>
        <span className="w-kicker t-bad">
          <Icon name="alert" size={13} /> Needs a look
        </span>
        <h3 className="w-big">{title}</h3>
        <p className="muted" style={{ marginTop: 6 }}>
          {p.awaiting_plate_clear
            ? 'Take the part off the bed. When the plate is empty, the request to continue shows up here.'
            : 'Check the printer and the camera picture. The people who asked have been told what happened.'}
        </p>
      </div>
      <CameraFrame ov={ov} rest={rest} nowSec={nowSec} fallback={null} />
    </div>
  )
}

function Offline({ ov }: { ov: Overview }) {
  const firstBad = ov.setup.checks.find(c => c.status === 'error' || c.status === 'missing')
  return (
    <div className="w-idle">
      <div>
        <span className="w-kicker t-bad">
          <Icon name="alert" size={13} /> Offline
        </span>
        <h3 className="w-big">The printer is not answering.</h3>
        <p className="muted" style={{ marginTop: 6 }}>
          {firstBad ? (
            <>
              {firstBad.label}: {firstBad.detail}
              {firstBad.fix ? (
                <>
                  {' '}
                  <b>Fix:</b> {firstBad.fix}
                </>
              ) : null}
            </>
          ) : (
            'Check that the printer is on and on the network. The Health list below shows what the workshop can reach.'
          )}
        </p>
      </div>
    </div>
  )
}
