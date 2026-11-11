/**
 * DEV ONLY: a stand-in for `@hermes/plugin-sdk` so the Workshop page runs in a plain browser (dev/harness.html).
 * Never part of desktop/plugin.js: the harness build aliases the SDK to this file. Same idea as the
 * memory-wiki plugin's tests/desktop-sdk-shim.mjs, with just enough React Query behaviour (polling, keeping
 * the last good data on a failed refetch, invalidation) to show what the app does.
 */

import { useEffect, useState, useSyncExternalStore } from 'react'

export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar.nav'
export const PALETTE_AREA = 'palette'
export const STATUSBAR_AREAS = { left: 'statusbar.left', right: 'statusbar.right' }
export const TOOL_MEDIA_RENDERER_AREA = 'transcript.toolMedia'

// ---- atoms ------------------------------------------------------------------------------------------------
export function atom<T>(value: T) {
  const listeners = new Set<(v: T) => void>()
  return {
    get: () => value,
    set(next: T) {
      value = next
      listeners.forEach(fn => fn(value))
    },
    subscribe(fn: (v: T) => void) {
      listeners.add(fn)
      fn(value)
      return () => listeners.delete(fn)
    },
    listen(fn: (v: T) => void) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    }
  }
}
export const useValue = <T,>(a: ReturnType<typeof atom<T>>) => useSyncExternalStore(a.listen, a.get, a.get)

// ---- host -------------------------------------------------------------------------------------------------
type Handler = (method: string, params: unknown) => Promise<unknown>
let requestHandler: Handler = async () => {
  throw new Error('no handler')
}
let composerAnswers = false
export const toasts = atom<Array<{ id: number; kind: string; message: string }>>([])
let toastId = 0

export const host = {
  state: { focusedSessionId: atom<string | null>(null), profile: atom('default') },
  request: <T,>(method: string, params?: unknown) => requestHandler(method, params) as Promise<T>,
  navigate: (path: string) => console.info('[shim] navigate', path),
  notify: (input: { kind: string; message: string }) => {
    const id = ++toastId
    toasts.set([...toasts.get(), { id, ...input }])
    setTimeout(() => toasts.set(toasts.get().filter(t => t.id !== id)), 4000)
    return String(id)
  },
  composer: {
    insertText: async (_sid: string | null, text: string) => {
      console.info('[shim] composer.insertText', text)
      return composerAnswers
    }
  }
}
export const shimControl = {
  onRequest(fn: Handler) {
    requestHandler = fn
  },
  composer(on: boolean) {
    composerAnswers = on
  }
}

// ---- theme ------------------------------------------------------------------------------------------------
export const themeAtom = atom<string>('light')
export const useTheme = () => useValue(themeAtom)

// ---- a small React Query ------------------------------------------------------------------------------------
interface Entry {
  key: unknown[]
  data: unknown
  error: unknown
  isError: boolean
  dataUpdatedAt: number
  errorUpdatedAt: number
  fetching: Promise<void> | null
  version: number
  listeners: Set<() => void>
  fn: () => Promise<unknown>
}
const cache = new Map<string, Entry>()

function entryFor(key: unknown[], fn: () => Promise<unknown>): Entry {
  const k = JSON.stringify(key)
  let e = cache.get(k)
  if (!e) {
    e = { key, data: undefined, error: null, isError: false, dataUpdatedAt: 0, errorUpdatedAt: 0, fetching: null, version: 0, listeners: new Set(), fn }
    cache.set(k, e)
  }
  e.fn = fn
  return e
}
const bump = (e: Entry) => {
  e.version += 1
  e.listeners.forEach(fn => fn())
}
function fetchEntry(e: Entry): Promise<void> {
  if (e.fetching) return e.fetching
  bump(e)
  e.fetching = Promise.resolve()
    .then(e.fn)
    .then(
      data => {
        Object.assign(e, { data, error: null, isError: false, dataUpdatedAt: Date.now() })
      },
      error => {
        Object.assign(e, { error, isError: true, errorUpdatedAt: Date.now() })
      }
    )
    .finally(() => {
      e.fetching = null
      bump(e)
    })
  return e.fetching
}

export function useQuery<T>(o: {
  queryKey: readonly unknown[]
  queryFn: () => Promise<T>
  refetchInterval?: number | false
  staleTime?: number
  enabled?: boolean
}) {
  const e = entryFor([...o.queryKey], o.queryFn)
  useSyncExternalStore(
    fn => {
      e.listeners.add(fn)
      return () => e.listeners.delete(fn)
    },
    () => e.version
  )
  const enabled = o.enabled !== false
  useEffect(() => {
    if (!enabled) return
    const stale = !e.dataUpdatedAt || (o.staleTime !== Infinity && Date.now() - e.dataUpdatedAt > (o.staleTime ?? 0))
    if (stale && !e.isError) void fetchEntry(e)
    else if (!e.dataUpdatedAt) void fetchEntry(e)
    if (typeof o.refetchInterval === 'number' && o.refetchInterval > 0) {
      const t = setInterval(() => void fetchEntry(e), o.refetchInterval)
      return () => clearInterval(t)
    }
  }, [JSON.stringify(o.queryKey), enabled, o.refetchInterval])
  return {
    data: e.data as T | undefined,
    error: e.error,
    isError: e.isError,
    isPending: e.data === undefined && !e.isError,
    isFetching: !!e.fetching,
    dataUpdatedAt: e.dataUpdatedAt,
    errorUpdatedAt: e.errorUpdatedAt,
    refetch: () => fetchEntry(e)
  }
}

export const queryClient = {
  invalidateQueries({ queryKey }: { queryKey: readonly unknown[] }) {
    const prefix = JSON.stringify([...queryKey]).slice(0, -1)
    const jobs: Promise<void>[] = []
    for (const [k, e] of cache) if (k.startsWith(prefix) && e.listeners.size) jobs.push(fetchEntry(e))
    return Promise.all(jobs).then(() => undefined)
  },
  clear() {
    cache.clear()
  }
}

/** Not used by the Workshop; here so a stray import fails loudly in dev rather than at runtime. */
export function useForceRender() {
  const [, set] = useState(0)
  return () => set(n => n + 1)
}
