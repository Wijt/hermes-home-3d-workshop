/**
 * Home 3D Workshop for Hermes Desktop: the printer owner's back room.
 *
 * - /workshop page (sidebar entry and ⌘K command): what the printer is doing and for whom, the approval
 *   waiting for the owner with the part in 3D, Stop and Pause, the queue, the done box, filament,
 *   messages, health, where it needed a human, and the versions of designed parts.
 * - Status-bar chip: "Printing 62% · for Mum · 41 min", "Waiting for you: 1", "Idle".
 * - Inline card for the pictures `home3d_design` returns, with the part in 3D on request.
 *
 * Data comes from this plugin's own backend (dashboard/plugin_api.py) through `ctx.rest`. Printer actions
 * run the plugin's slash commands as the local user (actions.ts), so the plugin's owner check applies.
 */

import type { HermesPlugin, PaletteContribution, PluginContribution } from '@hermes/plugin-sdk'
import * as sdk from '@hermes/plugin-sdk'
import { host, PALETTE_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA, STATUSBAR_AREAS } from '@hermes/plugin-sdk'

import { WorkshopChip } from './chip.tsx'
import { refreshOverview } from './data.ts'
import { DesignCard, type MediaProps } from './design-card.tsx'
import { WorkshopPage } from './page.tsx'

export const PLUGIN_ID = 'home-3d-workshop'
export const PATH = '/workshop'
export const DESIGN_TOOLS = ['home3d_design']

const plugin: HermesPlugin = {
  id: PLUGIN_ID,
  name: 'Workshop',
  description: 'The 3D printer’s back room: what is printing and for whom, approvals with the part in 3D, queue, done box, filament and health.',
  register(ctx) {
    const rest = ctx.rest
    const copy = ctx.os?.writeClipboard ? (text: string) => ctx.os.writeClipboard!(text) : undefined
    const contributions: PluginContribution[] = [
      { id: 'page', area: ROUTES_AREA, data: { path: PATH }, render: () => <WorkshopPage rest={rest} copy={copy} /> },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Workshop', codicon: 'tools' } },
      { id: 'chip', area: STATUSBAR_AREAS.right, order: 90, render: () => <WorkshopChip rest={rest} path={PATH} /> },
      {
        id: 'open',
        area: PALETTE_AREA,
        data: {
          id: `${PLUGIN_ID}.open`,
          label: 'Workshop: open the printer room',
          keywords: ['3d', 'printer', 'workshop', 'print', 'approve', 'queue', 'filament', 'bambu'],
          run: () => {
            refreshOverview()
            host.navigate(PATH)
          }
        } satisfies PaletteContribution
      }
    ]
    // Older Desktops do not export the area: they keep the built-in picture for the tool's files.
    const mediaArea = (sdk as { TOOL_MEDIA_RENDERER_AREA?: unknown }).TOOL_MEDIA_RENDERER_AREA
    if (typeof mediaArea === 'string') {
      contributions.push({
        id: 'design-card',
        area: mediaArea,
        data: { tools: DESIGN_TOOLS, render: (props: MediaProps) => <DesignCard props={props} rest={rest} path={PATH} /> }
      })
    }
    ctx.registerMany(contributions)
    // A workshop tool just ran in some chat (a request queued, a print started): refresh now, not at the next poll.
    ctx.onEvent('tool.complete', event => {
      const name = (event.payload as { name?: unknown } | undefined)?.name
      if (typeof name === 'string' && name.startsWith('home3d_')) refreshOverview()
    })
  }
}

export default plugin
