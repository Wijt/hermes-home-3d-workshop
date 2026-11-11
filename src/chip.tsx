/** Status-bar chip: "Printing 62% for Mum, 41 min left", "Waiting for you: 1", "Idle". Click opens the page. */

import { host } from '@hermes/plugin-sdk'

import { type Rest, useOverview } from './data.ts'
import { Icon } from './icons.tsx'
import { chipText, errorInfo } from './model.ts'
import { Styles } from './ui.tsx'

export const CHIP_POLL_MS = 15_000

export function WorkshopChip({ rest, path }: { rest: Rest; path: string }) {
  const { ov, error, loading } = useOverview(rest, CHIP_POLL_MS)
  if (loading) return null
  let text: string
  let tone: string
  if (!ov) {
    // The Python half is off: say so quietly instead of vanishing (the page explains how to turn it on).
    if (errorInfo(error).kind !== 'not_enabled') return null
    text = 'Workshop off'
    tone = 'neutral'
  } else {
    const c = chipText(ov)
    text = c.text
    tone = c.tone
  }
  return (
    <>
      <Styles />
      <button
        type="button"
        className={`h3w w-chip t-${tone}`}
        onClick={() => host.navigate(path)}
        title={`Workshop: ${text}`}
        data-workshop-chip=""
      >
        {tone === 'neutral' ? <Icon name="cube" size={12} /> : <span className="d" aria-hidden />}
        <span className="num">{text}</span>
      </button>
    </>
  )
}
