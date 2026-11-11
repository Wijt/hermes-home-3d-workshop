// Minimal ambient types for the parts of `@hermes/plugin-sdk` the Workshop uses (typecheck only; the host
// supplies the real module at runtime). Shapes follow website/docs/developer-guide/desktop-plugin-sdk.md.
import type { ReactNode } from 'react'

export interface PluginRestOptions {
  method?: string
  body?: unknown
  timeoutMs?: number
}
export interface GatewayEvent {
  type: string
  payload?: unknown
  session_id?: string
}
export interface ReadableAtom<T> {
  get: () => T
  subscribe: (fn: (value: T) => void) => () => void
}
export interface PluginContribution {
  id: string
  area: string
  order?: number
  title?: string
  data?: unknown
  render?: () => ReactNode
}
export interface PluginContext {
  readonly source: string
  registerMany: (cs: PluginContribution[]) => () => void
  onDispose: (fn: () => void) => void
  onEvent: (type: string, listener: (event: GatewayEvent) => void) => () => void
  setInterval: (fn: () => void, ms: number) => () => void
  rest: <T>(path: string, opts?: PluginRestOptions) => Promise<T>
  os: { writeClipboard?: (text: string) => Promise<boolean> }
}
export interface HermesPlugin {
  id: string
  name?: string
  description?: string
  defaultEnabled?: boolean
  register: (ctx: PluginContext) => void
}
export interface PaletteContribution {
  id: string
  label: string
  keywords?: string[]
  run: () => void
}
/** Props a TOOL_MEDIA_RENDERER_AREA `render` receives. */
export interface ToolMediaProps {
  file: { path: string; name: string; kind: string; mime: string; resolveUrl: () => Promise<string> }
  toolName?: string
  toolCallId?: string
  args: unknown
  result: unknown
  sessionId: string | null
  fallback: ReactNode
}

export const ROUTES_AREA: string
export const SIDEBAR_NAV_AREA: string
export const PALETTE_AREA: string
export const STATUSBAR_AREAS: { left: string; right: string }
/** Newer Desktops only: feature-detect through a namespace import. */
export const TOOL_MEDIA_RENDERER_AREA: string | undefined

export const host: {
  request: <T>(method: string, params?: unknown) => Promise<T>
  navigate: (path: string) => void
  notify: (input: { kind: 'error' | 'info' | 'success' | 'warning'; message: string; title?: string }) => string
  state: { focusedSessionId: ReadableAtom<string | null> }
  composer?: {
    insertText?: (sessionId: null | string, text: string, opts?: { mode?: 'block' | 'inline' | 'prefix' }) => Promise<boolean>
  }
}

export interface QueryResult<T> {
  data: T | undefined
  error: unknown
  isError: boolean
  isPending: boolean
  isFetching: boolean
  dataUpdatedAt: number
  errorUpdatedAt: number
  refetch: () => Promise<unknown>
}
export function useQuery<T>(options: {
  queryKey: readonly unknown[]
  queryFn: () => Promise<T>
  refetchInterval?: number | false
  staleTime?: number
  gcTime?: number
  retry?: number | boolean
  enabled?: boolean
}): QueryResult<T>
export const queryClient: {
  invalidateQueries: (filters: { queryKey: readonly unknown[] }) => Promise<void>
}
/** Newer Desktops only. */
export const useTheme: (() => unknown) | undefined
