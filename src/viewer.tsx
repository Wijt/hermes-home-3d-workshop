/**
 * A part in 3D, or its still picture until the person asks for 3D. Holds the plugin's single WebGL view
 * (slot.ts): asking for 3D here returns any other view to its picture.
 */

import * as sdk from '@hermes/plugin-sdk'
import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react'

import { type Rest, useFile } from './data.ts'
import { Icon } from './icons.tsx'
import { viewSlot } from './slot.ts'
import { createStage, dataUrlToBuffer, type PartStats, type Stage, themeColors } from './stage.ts'
import { RefImage, Spinner } from './ui.tsx'

// Older Desktops have no useTheme: then the scene reads the theme once per load.
const useThemeSafe: () => unknown = typeof sdk.useTheme === 'function' ? sdk.useTheme : () => null

const fmtSize = (s: PartStats['size']) => s.map(n => (n >= 100 ? Math.round(n) : Math.round(n * 10) / 10)).join(' × ') + ' mm'

export function PartViewer({
  rest,
  stl,
  preview,
  still = null,
  color,
  label,
  autoMount = false,
  className = ''
}: {
  rest: Rest
  stl: string | null
  preview: string | null
  /** A picture URL the host already resolved (transcript cards), used instead of `preview`. */
  still?: string | null
  /** #rrggbb filament colour, or null for the theme accent. */
  color: string | null
  label: string
  /** Claim the 3D view on mount (the approval card): the part is the point of that card. */
  autoMount?: boolean
  className?: string
}) {
  const id = useId()
  const holder = useSyncExternalStore(viewSlot.subscribe, viewSlot.holder, viewSlot.holder)
  const live = holder === id && !!stl

  useEffect(() => {
    if (autoMount && stl) viewSlot.claim(id)
  }, [autoMount, stl, id])
  useEffect(() => () => viewSlot.release(id), [id])

  return (
    <div className={`w-media ${className}`} data-workshop-viewer={live ? 'live' : 'still'}>
      {live && stl ? (
        <LiveStage rest={rest} stl={stl} color={color} label={label} onClose={() => viewSlot.release(id)} />
      ) : (
        <>
          {still ? (
            <img className="fill" src={still} alt={`Preview of ${label}`} draggable={false} />
          ) : preview ? (
            <RefImage rest={rest} fileRef={preview} alt={`Preview of ${label}`} className="fill" fallback={<NoPicture />} />
          ) : (
            <NoPicture />
          )}
          {stl ? (
            <div className="over br">
              <button type="button" className="w-view3d" onClick={() => viewSlot.claim(id)} data-workshop-view3d="">
                <Icon name="cube" /> View in 3D
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

function NoPicture() {
  return (
    <div className="center">
      <Icon name="cube" size={28} />
      <span>No picture of this part</span>
    </div>
  )
}

function LiveStage({ rest, stl, color, label, onClose }: { rest: Rest; stl: string; color: string | null; label: string; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null)
  const stage = useRef<Stage | null>(null)
  const [glError, setGlError] = useState<string | null>(null)
  const [stats, setStats] = useState<PartStats | null>(null)
  const [spinning, setSpinning] = useState(true)
  const { file, error, loading } = useFile(rest, stl)
  const theme = useThemeSafe()

  // One renderer for the life of this view.
  useEffect(() => {
    const el = box.current
    if (!el) return
    try {
      stage.current = createStage(el, themeColors(el, color))
    } catch {
      setGlError('3D is not available in this window (no WebGL).')
      return
    }
    const s = stage.current
    const stop = () => setSpinning(false)
    el.addEventListener('pointerdown', stop)
    el.addEventListener('wheel', stop, { passive: true })
    return () => {
      el.removeEventListener('pointerdown', stop)
      el.removeEventListener('wheel', stop)
      s.dispose()
      stage.current = null
    }
  }, [])

  // The model, once its bytes arrive.
  useEffect(() => {
    if (!file?.dataUrl || !stage.current) return
    try {
      setStats(stage.current.load(dataUrlToBuffer(file.dataUrl)))
    } catch {
      setGlError('This file is not a readable STL.')
    }
  }, [file])

  // Theme or filament colour changed: repaint without reloading.
  useEffect(() => {
    if (box.current && stage.current) stage.current.setColors(themeColors(box.current, color))
  }, [theme, color])

  const problem = glError || (error ? 'Could not load the model from the workshop.' : null)
  return (
    <>
      <div ref={box} className="stage" tabIndex={-1} />
      {problem ? (
        <div className="center">
          <Icon name="alert" size={22} />
          <span>{problem}</span>
        </div>
      ) : loading || !stats ? (
        <div className="center">
          <Spinner />
          <span>Loading the part…</span>
        </div>
      ) : null}
      {stats ? (
        <div className="over bl">
          <span className="w-glass num" title={`${stats.triangles.toLocaleString()} triangles`}>
            {fmtSize(stats.size)}
            {stats.fitsBed ? '' : ' · too big for the bed'}
          </span>
        </div>
      ) : null}
      <div className="over tr">
        {stats ? (
          <button
            type="button"
            className="w-glass"
            onClick={() => {
              stage.current?.resetView()
              stage.current?.setAutoRotate(!spinning)
              setSpinning(!spinning)
            }}
            aria-label={spinning ? 'Stop turning' : 'Reset the view and turn slowly'}
            title={spinning ? 'Stop turning' : 'Reset view'}
          >
            <Icon name={spinning ? 'pause' : 'reset'} size={12} />
          </button>
        ) : null}
        <button type="button" className="w-glass" onClick={onClose} aria-label={`Close the 3D view of ${label}`} title="Back to the picture">
          <Icon name="x" size={12} />
        </button>
      </div>
    </>
  )
}
