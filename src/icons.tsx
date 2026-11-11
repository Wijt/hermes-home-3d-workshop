/** Small line icons drawn in currentColor (16 px grid), so they follow the theme like text does. */

import type { ReactNode } from 'react'

const P: Record<string, ReactNode> = {
  play: <path d="M5 3.5v9l7-4.5z" fill="currentColor" stroke="none" />,
  pause: (
    <>
      <rect x="4" y="3.5" width="2.6" height="9" rx=".6" fill="currentColor" stroke="none" />
      <rect x="9.4" y="3.5" width="2.6" height="9" rx=".6" fill="currentColor" stroke="none" />
    </>
  ),
  stop: <rect x="4" y="4" width="8" height="8" rx="1.2" fill="currentColor" stroke="none" />,
  check: <path d="M3.5 8.5l3 3 6-7" />,
  x: <path d="M4.5 4.5l7 7m0-7l-7 7" />,
  alert: (
    <>
      <path d="M8 2.5l6 11H2z" />
      <path d="M8 7v3m0 1.8v.2" />
    </>
  ),
  dot: <circle cx="8" cy="8" r="3" fill="currentColor" stroke="none" />,
  ring: <circle cx="8" cy="8" r="3.2" />,
  clock: (
    <>
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 5v3.2l2 1.3" />
    </>
  ),
  cube: (
    <>
      <path d="M8 2l5.5 3v6L8 14l-5.5-3V5z" />
      <path d="M2.5 5L8 8l5.5-3M8 8v6" />
    </>
  ),
  camera: (
    <>
      <rect x="2" y="4.5" width="12" height="8.5" rx="1.5" />
      <path d="M5.5 4.5l1-2h3l1 2" />
      <circle cx="8" cy="8.7" r="2.3" />
    </>
  ),
  refresh: (
    <>
      <path d="M13 8a5 5 0 1 1-1.5-3.6" />
      <path d="M13 2.5v3h-3" />
    </>
  ),
  box: (
    <>
      <path d="M2.5 6h11v7.5h-11z" />
      <path d="M1.8 3.5h12.4V6H1.8zM6.5 8.5h3" />
    </>
  ),
  spool: (
    <>
      <circle cx="8" cy="8" r="5.5" />
      <circle cx="8" cy="8" r="1.6" />
    </>
  ),
  bell: (
    <>
      <path d="M4 11V7.5a4 4 0 0 1 8 0V11l1 1.2H3z" />
      <path d="M6.6 13.8a1.5 1.5 0 0 0 2.8 0" />
    </>
  ),
  hand: (
    <>
      <path d="M5 8V3.8a1 1 0 0 1 2 0V7.5m0-4.7a1 1 0 0 1 2 0v4.7m0-3.7a1 1 0 0 1 2 0V9" />
      <path d="M11 6.5a1 1 0 0 1 2 0V10a4.5 4.5 0 0 1-4.5 4.5h-.7A4 4 0 0 1 4.6 13L2.8 10a1 1 0 0 1 1.6-1.2L5 9.6" />
    </>
  ),
  spark: <path d="M8 2v3m0 6v3M2 8h3m6 0h3M4 4l2 2m4 4l2 2m0-8l-2 2M6 10l-2 2" />,
  layers: (
    <>
      <path d="M8 2.5l6 3-6 3-6-3z" />
      <path d="M2 8.5l6 3 6-3M2 11.2l6 3 6-3" />
    </>
  ),
  thermo: (
    <>
      <path d="M6.5 9.5V3.5a1.5 1.5 0 0 1 3 0v6a2.8 2.8 0 1 1-3 0z" />
    </>
  ),
  arrow: <path d="M3 8h9m-3.5-3.5L12 8l-3.5 3.5" />,
  link: <path d="M6.5 9.5l3-3M7 4.5l1-1a2.5 2.5 0 0 1 3.5 3.5l-1 1M9 11.5l-1 1A2.5 2.5 0 0 1 4.5 9l1-1" />,
  copy: (
    <>
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.3" />
      <path d="M10.5 3.5v-.3a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h.3" />
    </>
  ),
  wrench: <path d="M10.2 2.4a3.3 3.3 0 0 0-3.7 4.4L2.7 10.6a1.4 1.4 0 0 0 2 2l3.8-3.8a3.3 3.3 0 0 0 4.4-3.7l-2 2-2-.6-.6-2z" />,
  eject: (
    <>
      <path d="M3 9.5L8 4l5 5.5z" />
      <path d="M3 12.5h10" />
    </>
  ),
  reset: (
    <>
      <path d="M3.5 8a4.5 4.5 0 1 0 1.4-3.2" />
      <path d="M3 2.8v2.6h2.6" />
    </>
  )
}

export type IconName = keyof typeof P

export function Icon({ name, size = 14, title }: { name: IconName | string; size?: number; title?: string }) {
  return (
    <svg
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0 }}
    >
      {title ? <title>{title}</title> : null}
      {P[name] ?? P.dot}
    </svg>
  )
}
