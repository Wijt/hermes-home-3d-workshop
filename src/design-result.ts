/**
 * Reading a `home3d_design` tool call (home3d/tools.py `_design_out` for render, the `get` branch for get):
 * `{ ok, name, version, size_mm, volume_cm3, est_grams_max, triangles, fits_build_volume, warnings,
 *    previews: [png paths], media: ["MEDIA:<png>"], stl_path }`. A reopened chat can hand the result back
 * as a JSON string, and `args` can carry display keys: read everything defensively.
 */

import type { Design, DesignVersion } from './types.ts'

export interface DesignCall {
  slug: string
  version: number
  sizeMm: [number, number, number] | null
  grams: number | null
  volumeCm3: number | null
  triangles: number | null
  fitsBed: boolean | null
  warnings: string[]
  previews: string[]
}

const asObj = (v: unknown): Record<string, unknown> | null => {
  if (typeof v === 'string') {
    try {
      return asObj(JSON.parse(v))
    } catch {
      return null
    }
  }
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}
const n = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/** The call's design, or null when it is not a successful render/get (then the built-in player stays). */
export function readDesignCall(result: unknown, args: unknown): DesignCall | null {
  const r = asObj(result)
  if (!r || r.ok !== true) return null
  const a = asObj(args) ?? {}
  const slug = typeof r.name === 'string' && r.name ? r.name : typeof a.name === 'string' ? a.name : ''
  const version = n(r.version)
  if (!slug || version === null) return null
  const size = Array.isArray(r.size_mm) && r.size_mm.length === 3 && r.size_mm.every(x => typeof x === 'number') ? (r.size_mm as [number, number, number]) : null
  return {
    slug,
    version,
    sizeMm: size,
    grams: n(r.est_grams_max),
    volumeCm3: n(r.volume_cm3),
    triangles: n(r.triangles),
    fitsBed: typeof r.fits_build_volume === 'boolean' ? r.fits_build_volume : null,
    warnings: Array.isArray(r.warnings) ? r.warnings.filter((w): w is string => typeof w === 'string').slice(0, 3) : [],
    previews: Array.isArray(r.previews) ? r.previews.filter((p): p is string => typeof p === 'string') : []
  }
}

/** Draw the full card only once per call: for its first preview picture (or a file the result does not list). */
export function isLeadPicture(call: DesignCall, path: string): boolean {
  const i = call.previews.indexOf(path)
  return i <= 0
}

/** The overview's entry for this design version (its STL file ref lives there). */
export function findVersion(designs: Design[], slug: string, version: number): DesignVersion | null {
  const norm = (s: string) => s.trim().toLowerCase()
  const d = designs.find(x => norm(x.slug) === norm(slug))
  return d?.versions.find(v => v.version === version) ?? null
}

export function callFacts(c: DesignCall): string[] {
  const out: string[] = []
  if (c.sizeMm) out.push(`${c.sizeMm.map(x => Math.round(x * 10) / 10).join(' × ')} mm`)
  if (c.grams !== null) out.push(`about ${Math.round(c.grams)} g`)
  else if (c.volumeCm3 !== null) out.push(`${Math.round(c.volumeCm3 * 10) / 10} cm³`)
  if (c.fitsBed === false) out.push('too big for the bed')
  return out
}
