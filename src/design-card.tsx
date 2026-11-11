/**
 * The inline card for a picture `home3d_design` produced (TOOL_MEDIA_RENDERER_AREA). The tool returns PNG
 * previews as MEDIA lines and the STL as `stl_path`; the card shows the picture at once and, when the
 * workshop backend lists that version, turns the part in 3D on request (the STL comes through the
 * backend's `file?ref=`, never by path from the renderer).
 */

import { host } from '@hermes/plugin-sdk'
import { type ReactNode, useEffect, useState } from 'react'

import { type Rest, useOverview } from './data.ts'
import { callFacts, findVersion, isLeadPicture, readDesignCall } from './design-result.ts'
import { Icon } from './icons.tsx'
import { Styles, Tag } from './ui.tsx'
import { PartViewer } from './viewer.tsx'

export interface MediaProps {
  file: { path: string; name: string; kind: string; mime: string; resolveUrl: () => Promise<string> }
  args: unknown
  result: unknown
  sessionId: string | null
  fallback: ReactNode
}

export function DesignCard({ props, rest, path }: { props: MediaProps; rest: Rest; path: string }) {
  const { file, args, result, fallback } = props
  const call = readDesignCall(result, args)
  const isImage = file?.kind === 'image' || /^image\//.test(file?.mime || '') || /\.png$/i.test(file?.path || '')
  if (!call || !isImage || !isLeadPicture(call, file.path)) return <>{fallback}</>
  return <Card call={call} file={file} rest={rest} path={path} fallback={fallback} />
}

function Card({
  call,
  file,
  rest,
  path,
  fallback
}: {
  call: NonNullable<ReturnType<typeof readDesignCall>>
  file: MediaProps['file']
  rest: Rest
  path: string
  fallback: ReactNode
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let live = true
    file.resolveUrl().then(
      url => live && setSrc(url),
      () => live && setFailed(true)
    )
    return () => {
      live = false
    }
  }, [file])
  // No polling here: one read of the overview finds this version's STL ref (if the backend is on).
  const { ov } = useOverview(rest, false)
  const version = ov ? findVersion(ov.designs, call.slug, call.version) : null
  if (failed) return <>{fallback}</>
  const facts = callFacts(call)
  const title = ov?.designs.find(d => d.slug === call.slug)?.title || call.slug.replace(/[_-]+/g, ' ')
  return (
    <div className="h3w w-card" data-workshop-design-card="">
      <Styles />
      <div className="head">
        <Icon name="cube" />
        <span className="name">{title}</span>
        <Tag tone="accent">v{call.version}</Tag>
        <button type="button" className="w-link" style={{ marginLeft: 'auto', fontSize: 12 }} onClick={() => host.navigate(path)}>
          All versions <Icon name="arrow" size={12} />
        </button>
      </div>
      <PartViewer rest={rest} stl={version?.stl ?? null} preview={null} still={src} color={null} label={`${title} v${call.version}`} />
      {facts.length || call.warnings.length ? (
        <div className="w-facts-line num">
          {facts.map(f => (
            <span key={f} className={f.includes('too big') ? 'bad' : undefined}>
              {f}
            </span>
          ))}
          {call.warnings.map(w => (
            <span key={w} className="warn" title={w}>
              {w.length > 60 ? `${w.slice(0, 57)}…` : w}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
