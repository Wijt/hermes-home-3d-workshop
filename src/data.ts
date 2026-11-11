/**
 * Reading the backend: the overview poll and file fetches, through the app's shared React Query client
 * (dedupes the page and the status-bar chip, keeps the last good answer while a poll fails).
 */

import { queryClient, useQuery } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'

import { normalize } from './model.ts'
import type { FilePayload, Overview } from './types.ts'

export type Rest = <T>(path: string, opts?: { method?: string; body?: unknown; timeoutMs?: number }) => Promise<T>

export const OVERVIEW_KEY = ['home-3d-workshop', 'overview'] as const
export const POLL_MS = 5_000

export interface OverviewState {
  ov: Overview | null
  error: unknown
  failing: boolean
  loading: boolean
  updatedAt: number
  refetch: () => void
}

export function useOverview(rest: Rest, pollMs: number | false = POLL_MS): OverviewState {
  const q = useQuery<Overview>({
    queryKey: OVERVIEW_KEY,
    queryFn: async () => normalize(await rest<unknown>('overview', { timeoutMs: 20_000 })),
    refetchInterval: pollMs,
    retry: 1
  })
  return {
    ov: q.data ?? null,
    error: q.error,
    // React Query keeps `data` from the last good answer when a refetch fails: show it, with its age.
    failing: q.isError,
    loading: q.isPending && !q.data,
    updatedAt: q.dataUpdatedAt || 0,
    refetch: () => void q.refetch()
  }
}

export function refreshOverview(): void {
  void queryClient.invalidateQueries({ queryKey: OVERVIEW_KEY })
}

/** A file ref's payload. Refs name a file version, so an answer is kept for the session. */
export function useFile(rest: Rest, ref: string | null, enabled = true) {
  const q = useQuery<FilePayload>({
    queryKey: ['home-3d-workshop', 'file', ref ?? ''],
    queryFn: () => rest<FilePayload>(`file?ref=${encodeURIComponent(ref ?? '')}`, { timeoutMs: 60_000 }),
    enabled: enabled && !!ref,
    staleTime: Infinity,
    gcTime: 10 * 60_000,
    retry: 1
  })
  return { file: q.data ?? null, error: q.isError ? q.error : null, loading: !!ref && enabled && q.isPending }
}

/** Wall clock in ms that ticks every `ms`, for "12 s ago" lines (component-scoped timer). */
export function useNow(ms = 1_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(t)
  }, [ms])
  return now
}
