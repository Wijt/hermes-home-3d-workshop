/** Small building blocks shared by the page, the transcript card and the chip. */

import { host } from '@hermes/plugin-sdk'
import { type ReactNode, type SyntheticEvent, useCallback, useRef, useState } from 'react'

import { type ActionOutcome, runCommand } from './actions.ts'
import { refreshOverview, type Rest, useFile } from './data.ts'
import { Icon, type IconName } from './icons.tsx'
import { groupTone, initial, personLabel, type Tone } from './model.ts'
import { CSS } from './styles.ts'
import type { Group, Person } from './types.ts'

export function Styles() {
  return <style>{CSS}</style>
}

export function Tag({ tone = 'neutral', children, outline }: { tone?: Tone; children: ReactNode; outline?: boolean }) {
  return <span className={`w-tag t-${tone}${outline ? ' outline' : ''}`}>{children}</span>
}

/** The round initial a chat shows beside a sender, in the colour of the group they asked from. */
export function Avatar({ p, groups, small }: { p: Person | null | undefined; groups: Group[]; small?: boolean }) {
  const group = p?.group?.trim() || ''
  return (
    <span className={`w-ava${small ? ' sm' : ''} g-${group ? groupTone(groups, group) : 'other'}`} aria-hidden>
      {initial(p?.name)}
    </span>
  )
}

/** "Mum", then the group with its colour dot; the title says both in words. */
export function PersonTag({ p, groups }: { p: Person | null | undefined; groups: Group[] }) {
  const name = p?.name?.trim() || 'someone'
  const group = p?.group?.trim() || ''
  return (
    <span className="w-person" title={personLabel(p)}>
      <b>{name}</b>
      {group ? (
        <span className={`grp g-${groupTone(groups, group)}`}>
          <span>{group}</span>
        </span>
      ) : null}
    </span>
  )
}

export function Section({
  id,
  title,
  count,
  aside,
  children
}: {
  id: string
  title: string
  count?: number | null
  aside?: ReactNode
  children: ReactNode
}) {
  return (
    <section aria-labelledby={`w-sec-${id}`} data-workshop-section={id}>
      <div className="w-sec-head">
        <h2 id={`w-sec-${id}`}>
          {title}
          {count ? <span className="count num">{count}</span> : null}
        </h2>
        {aside ? <div className="aside">{aside}</div> : null}
      </div>
      {children}
    </section>
  )
}

export function Empty({ icon = 'check', children }: { icon?: IconName; children: ReactNode }) {
  return (
    <p className="w-empty">
      <Icon name={icon} />
      <span>{children}</span>
    </p>
  )
}

/** An image from a file ref: a shimmer while it loads, nothing (or `fallback`) when it cannot load. */
export function RefImage({
  rest,
  fileRef,
  alt,
  className,
  fallback = null,
  onLoad
}: {
  rest: Rest
  fileRef: string | null
  alt: string
  className?: string
  fallback?: ReactNode
  onLoad?: (e: SyntheticEvent<HTMLImageElement>) => void
}) {
  const { file, loading } = useFile(rest, fileRef)
  if (loading) return <div className={`w-skel ${className ?? ''}`} style={{ width: '100%', height: '100%' }} aria-hidden />
  if (!file?.dataUrl || !/^data:image\//.test(file.dataUrl)) return <>{fallback}</>
  return <img className={className} src={file.dataUrl} alt={alt} draggable={false} onLoad={onLoad} />
}

export function Thumb({ rest, fileRef, alt, icon = 'cube' }: { rest: Rest; fileRef: string | null; alt: string; icon?: IconName }) {
  return (
    <span className="w-thumb">
      {fileRef ? <RefImage rest={rest} fileRef={fileRef} alt={alt} fallback={<Icon name={icon} size={18} />} /> : <Icon name={icon} size={18} />}
    </span>
  )
}

// ---- actions -------------------------------------------------------------------------------------

export interface ActionState {
  busy: string | null
  outcome: (ActionOutcome & { command: string }) | null
  run: (command: string) => Promise<void>
  clear: () => void
}

/** Runs a `home3d ...` command (see actions.ts), keeps its reply to show, refreshes the overview. */
export function useAction(): ActionState {
  const [busy, setBusy] = useState<string | null>(null)
  const [outcome, setOutcome] = useState<ActionState['outcome']>(null)
  const inflight = useRef(false)
  const run = useCallback(async (command: string) => {
    if (inflight.current) return
    inflight.current = true
    setBusy(command)
    setOutcome(null)
    try {
      const r = await runCommand(host, command)
      setOutcome({ ...r, command })
      if (r.kind === 'failed') host.notify({ kind: 'error', message: r.text })
    } finally {
      inflight.current = false
      setBusy(null)
      refreshOverview()
    }
  }, [])
  return { busy, outcome, run, clear: () => setOutcome(null) }
}

/** The command's reply, said plainly under the button that ran it. */
export function Reply({ state, inline }: { state: ActionState; inline?: boolean }) {
  const o = state.outcome
  if (!o) return null
  const tone: Tone = o.kind === 'ran' ? (o.ok ? 'good' : 'warn') : o.kind === 'seated' ? 'accent' : o.kind === 'manual' ? 'warn' : 'bad'
  const icon: IconName = o.kind === 'ran' && o.ok ? 'check' : o.kind === 'seated' ? 'arrow' : 'alert'
  return (
    <div className={`w-reply t-${tone}${inline ? ' w-reply-inline' : ''}`} role="status" aria-live="polite" data-workshop-reply="">
      <Icon name={icon} />
      <pre>{o.text}</pre>
      {o.kind === 'manual' ? <CopyButton text={`/${o.command.replace(/^\/+/, '')}`} /> : null}
      <button type="button" className="w-btn ghost sm" onClick={state.clear} aria-label="Dismiss the reply">
        <Icon name="x" size={12} />
      </button>
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  const copy = () => {
    try {
      void navigator.clipboard?.writeText(text).then(() => setDone(true), () => setDone(false))
    } catch {
      setDone(false)
    }
  }
  return (
    <button type="button" className="w-btn sm" onClick={copy} aria-label={`Copy ${text}`}>
      <Icon name={done ? 'check' : 'copy'} size={12} /> {done ? 'Copied' : 'Copy command'}
    </button>
  )
}

/** Show `backticked` parts of a line as code (a fix the owner may want to copy). */
export function FixText({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g)
  return (
    <span>
      {parts.map((p, i) => (p.startsWith('`') && p.endsWith('`') && p.length > 2 ? <code key={i}>{p.slice(1, -1)}</code> : <span key={i}>{p}</span>))}
    </span>
  )
}

export function Spinner() {
  return (
    <svg className="w-spin" width="14" height="14" viewBox="0 0 16 16" aria-hidden>
      <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeOpacity=".25" strokeWidth="2" />
      <path d="M14 8a6 6 0 0 0-6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
