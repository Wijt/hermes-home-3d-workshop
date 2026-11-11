/** The Workshop page (route /workshop): the owner's back room. */

import { useState } from 'react'

import { type Rest, useNow, useOverview } from './data.ts'
import { Hero } from './hero.tsx'
import { Icon } from './icons.tsx'
import { errorInfo, staleness } from './model.ts'
import { DoneBox, Designs, Filament, Improve, Notices, Queue, Setup } from './sections.tsx'
import type { Overview } from './types.ts'
import { Styles } from './ui.tsx'

export interface PageProps {
  rest: Rest
  copy?: (text: string) => Promise<boolean>
}

export function WorkshopPage({ rest, copy }: PageProps) {
  const state = useOverview(rest)
  const nowMs = useNow(1_000)
  const nowSec = nowMs / 1000
  const { ov, error, failing, loading, updatedAt } = state

  let body
  if (loading) body = <Loading />
  else if (!ov) {
    const info = errorInfo(error)
    body = info.kind === 'not_enabled' ? <NotEnabled copy={copy} /> : <Unreachable text={info.text} onRetry={state.refetch} />
  } else {
    const fresh = staleness(updatedAt, nowMs, failing)
    body = <Content ov={ov} rest={rest} nowSec={nowSec} fresh={fresh} failing={failing} errorText={failing ? errorInfo(error).text : ''} onRefresh={state.refetch} />
  }
  return (
    <div className="h3w-scroll" data-workshop-page="">
      <div className="h3w w-page">
        <Styles />
        {body}
      </div>
    </div>
  )
}

function Header({ ov, fresh, onRefresh }: { ov: Overview | null; fresh?: { stale: boolean; text: string }; onRefresh?: () => void }) {
  const groups = ov?.groups.map(g => g.name) ?? []
  return (
    <header className="w-top">
      <div>
        <h1 className="w-title">Workshop</h1>
        {ov ? (
          <p className="w-sub">
            {ov.persona || 'The printer'} runs the printer
            {groups.length ? ` for ${groups.length === 1 ? groups[0] : `${groups.slice(0, -1).join(', ')} and ${groups[groups.length - 1]}`}` : ''}. People ask in
            chat; you approve here.
          </p>
        ) : null}
      </div>
      <div className="w-top-right">
        {ov?.simulated ? (
          <span className="w-sim" title="The simulator backend: nothing here moves real hardware." data-workshop-simulated="">
            <Icon name="cube" size={12} /> Simulated printer
          </span>
        ) : null}
        {fresh?.text ? (
          <span className={`w-fresh${fresh.stale ? ' stale' : ''}`} aria-live="polite">
            <span className="w-pulse" aria-hidden />
            {fresh.text}
          </span>
        ) : null}
        {onRefresh ? (
          <button type="button" className="w-btn ghost sm" onClick={onRefresh} aria-label="Refresh now" title="Refresh now">
            <Icon name="refresh" size={13} />
          </button>
        ) : null}
      </div>
    </header>
  )
}

function Content({
  ov,
  rest,
  nowSec,
  fresh,
  failing,
  errorText,
  onRefresh
}: {
  ov: Overview
  rest: Rest
  nowSec: number
  fresh: { stale: boolean; text: string; ago: string }
  failing: boolean
  errorText: string
  onRefresh: () => void
}) {
  const p = { ov, rest, nowSec }
  return (
    <>
      <Header ov={ov} fresh={fresh} onRefresh={onRefresh} />
      {failing ? (
        <div className="w-banner t-warn" role="status">
          <Icon name="alert" />
          <span>
            <b>The workshop backend stopped answering.</b>{' '}
            <span className="muted">
              Below is its last answer{fresh.ago ? `, from ${fresh.ago}` : ''}.{errorText ? ` (${errorText})` : ''}
            </span>
          </span>
        </div>
      ) : null}
      {!ov.viewer.is_owner ? (
        <div className="w-banner t-warn">
          <Icon name="hand" />
          <span>
            <b>You are not the printer owner here.</b> <span className="muted">{ov.viewer.reason || 'You can look, but the printer refuses actions from this account.'}</span>
          </span>
        </div>
      ) : null}
      <Hero ov={ov} rest={rest} nowSec={nowSec} />
      <div className="w-grid">
        <div className="w-col">
          <Queue {...p} />
          <DoneBox {...p} />
          <Improve {...p} />
          <Designs {...p} />
        </div>
        <div className="w-col">
          <Notices {...p} />
          <Filament {...p} />
          <Setup {...p} />
        </div>
      </div>
    </>
  )
}

function Loading() {
  return (
    <>
      <Header ov={null} />
      <div className="w-hero" aria-busy="true" aria-label="Loading the workshop">
        <div className="w-hero-body">
          <div className="w-skel" style={{ aspectRatio: '4 / 3' }} />
          <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
            <div className="w-skel" style={{ height: 14, width: '30%' }} />
            <div className="w-skel" style={{ height: 26, width: '70%' }} />
            <div className="w-skel" style={{ height: 90 }} />
            <div className="w-skel" style={{ height: 40, width: '40%' }} />
          </div>
        </div>
      </div>
    </>
  )
}

const ENABLE = 'hermes plugins enable home-3d-workshop'

function NotEnabled({ copy }: { copy?: (text: string) => Promise<boolean> }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="w-state-page" data-workshop-state-page="not-enabled">
      <h2>
        <Icon name="wrench" size={18} /> The workshop backend is off
      </h2>
      <p className="muted">
        This screen is on, but the plugin&apos;s Python half is not loaded in Hermes, so there is nothing to show yet. It runs the printer, the queue and
        the approvals.
      </p>
      <ol>
        <li>
          Enable the plugin:
          <div className="w-code" style={{ marginTop: 6 }}>
            <code>{ENABLE}</code>
            {copy ? (
              <button
                type="button"
                className="w-btn ghost sm"
                onClick={() => void copy(ENABLE).then(ok => setCopied(ok))}
                aria-label="Copy the command"
              >
                <Icon name={copied ? 'check' : 'copy'} size={12} /> {copied ? 'Copied' : 'Copy'}
              </button>
            ) : null}
          </div>
        </li>
        <li>Restart Hermes so the backend loads the plugin&apos;s routes.</li>
        <li>Come back here: the page checks again every few seconds.</li>
      </ol>
    </div>
  )
}

function Unreachable({ text, onRetry }: { text: string; onRetry: () => void }) {
  return (
    <div className="w-state-page" data-workshop-state-page="unreachable">
      <h2>
        <Icon name="alert" size={18} /> Can&apos;t reach the workshop
      </h2>
      <p className="muted">The Hermes backend did not answer for the workshop. It may be restarting.</p>
      <div className="w-code">
        <code>{text}</code>
      </div>
      <div>
        <button type="button" className="w-btn" onClick={onRetry}>
          <Icon name="refresh" size={12} /> Try again
        </button>
      </div>
    </div>
  )
}
