/**
 * The three.js part viewer: one WebGLRenderer, orbit controls, soft lights, a 256 x 256 mm bed grid,
 * and an STL. Plain DOM + three (pattern from the official Meshy plugin's stage.ts, MIT): React mounts a
 * <div>, hands it to `createStage`, and calls `dispose()` on unmount, which frees the GPU context.
 *
 * - STL is Z-up, three.js is Y-up: the geometry is turned once at load.
 * - Render on demand: a frame is drawn only while something moves (orbit, damping, auto-rotate) or
 *   changed, and never while the canvas is off-screen or the window hidden.
 * - The renderer is transparent: the page's own theme background shows through, so no theme colour
 *   has to be converted for three.js except the part, grid and bed lines.
 */

import {
  AmbientLight,
  Box3,
  BufferGeometry,
  Color,
  DirectionalLight,
  DoubleSide,
  GridHelper,
  HemisphereLight,
  LineBasicMaterial,
  LineSegments,
  type Material,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer,
  EdgesGeometry
} from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'

/** Bambu A1 build plate. */
export const BED_MM = 256

export interface StageColors {
  part: string
  grid: string
  bed: string
}

export interface PartStats {
  triangles: number
  size: [number, number, number]
  fitsBed: boolean
}

export interface Stage {
  load: (bytes: ArrayBuffer) => PartStats
  setColors: (colors: Partial<StageColors>) => void
  setAutoRotate: (on: boolean) => void
  resetView: () => void
  dispose: () => void
}

/** A CSS colour as #rrggbb. Theme variables resolve to forms three.js cannot parse (color-mix(...)), so let
 *  the browser paint it on a 1px canvas and read the pixel back; an invalid value keeps the fallback. */
export function cssHex(value: string, fallback = '#888888'): string {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const g = canvas.getContext('2d', { willReadFrequently: true })
    if (!g || !value) return fallback
    g.fillStyle = fallback
    g.fillStyle = value
    g.fillRect(0, 0, 1, 1)
    const [r, gr, b] = g.getImageData(0, 0, 1, 1).data
    return `#${[r, gr, b].map(n => n.toString(16).padStart(2, '0')).join('')}`
  } catch {
    return fallback
  }
}

/** A filament colour as the 3D view paints it: black and white parts keep enough lightness for their shape
 *  to read under the lights (a #000000 part would be a flat silhouette). */
export function viewableColor(hex: string): string {
  const c = new Color(hex)
  const hsl = { h: 0, s: 0, l: 0 }
  c.getHSL(hsl)
  const l = Math.min(0.82, Math.max(0.2, hsl.l))
  if (l === hsl.l) return hex
  c.setHSL(hsl.h, hsl.s, l)
  return `#${c.getHexString()}`
}

/** Theme colours for the scene, read from the element's computed CSS variables. */
export function themeColors(el: Element, part: string | null): StageColors {
  const css = getComputedStyle(el)
  const v = (name: string, fb: string) => css.getPropertyValue(name).trim() || fb
  return {
    part: viewableColor(part || cssHex(v('--ui-accent', '#4f7cff'), '#4f7cff')),
    grid: cssHex(v('--ui-text-tertiary', '#8a8a8a'), '#8a8a8a'),
    bed: cssHex(v('--ui-text-primary', '#808080'), '#808080')
  }
}

export function createStage(host: HTMLElement, colors: StageColors): Stage {
  const renderer = new WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = SRGBColorSpace
  renderer.setClearColor(0x000000, 0)
  const canvas = renderer.domElement
  Object.assign(canvas.style, { display: 'block', width: '100%', height: '100%', outline: 'none', touchAction: 'none' })
  canvas.setAttribute('aria-label', '3D view of the part. Drag to turn, scroll to zoom.')
  canvas.setAttribute('role', 'img')
  host.appendChild(canvas)

  const scene = new Scene()
  scene.add(new HemisphereLight(0xffffff, 0x8a8a8a, 1.6))
  scene.add(new AmbientLight(0xffffff, 0.35))
  const key = new DirectionalLight(0xffffff, 1.5)
  key.position.set(-120, 260, 180)
  scene.add(key)
  const rim = new DirectionalLight(0xffffff, 0.6)
  rim.position.set(200, 120, -220)
  scene.add(rim)

  // The bed: a faint plate, a 16 mm grid and a crisp outline, all at y = 0.
  const bedPlate = new Mesh(
    new PlaneGeometry(BED_MM, BED_MM),
    new MeshBasicMaterial({ color: colors.bed, transparent: true, opacity: 0.035, side: DoubleSide, depthWrite: false })
  )
  bedPlate.rotation.x = -Math.PI / 2
  scene.add(bedPlate)
  const grid = new GridHelper(BED_MM, BED_MM / 16, colors.grid, colors.grid)
  const gridMat = grid.material as Material
  gridMat.transparent = true
  gridMat.opacity = 0.22
  gridMat.depthWrite = false
  scene.add(grid)
  const outline = new LineSegments(
    new EdgesGeometry(new PlaneGeometry(BED_MM, BED_MM)),
    new LineBasicMaterial({ color: colors.grid, transparent: true, opacity: 0.55 })
  )
  outline.rotation.x = -Math.PI / 2
  outline.position.y = 0.05
  scene.add(outline)

  const camera = new PerspectiveCamera(35, 1, 0.5, 5000)
  camera.position.set(160, 140, 220)
  const controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.dampingFactor = 0.12
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.9
  controls.maxPolarAngle = Math.PI * 0.495 // stay above the bed
  // Any touch from the person stops the slow spin for good: they are looking at something.
  const stopSpin = () => {
    controls.autoRotate = false
  }
  controls.addEventListener('start', stopSpin)

  const material = new MeshStandardMaterial({ color: colors.part, roughness: 0.55, metalness: 0.02 })
  let part: Mesh | null = null
  let home = { pos: camera.position.clone(), target: new Vector3() }
  let dirty = true
  let frame = 0
  let disposed = false
  let onScreen = true

  const resize = () => {
    const w = Math.max(1, host.clientWidth)
    const h = Math.max(1, host.clientHeight)
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
    dirty = true
  }
  const observer = new ResizeObserver(resize)
  observer.observe(host)
  resize()
  const visibility = new IntersectionObserver(entries => {
    onScreen = entries.some(e => e.isIntersecting)
    dirty = true
  })
  visibility.observe(host)
  const invalidate = () => {
    dirty = true
  }
  controls.addEventListener('change', invalidate)

  const tick = () => {
    if (disposed) return
    frame = requestAnimationFrame(tick)
    if (!onScreen || document.hidden) return
    const moved = controls.update()
    if (moved || dirty) {
      dirty = false
      renderer.render(scene, camera)
    }
  }
  tick()

  const frameAll = (size: Vector3) => {
    // Fit the part's bounding sphere in the narrower of the two fields of view, with a little air.
    const radius = Math.max(size.x, size.y, size.z, 10)
    const sphere = Math.max(size.length() / 2, 5)
    const vfov = (camera.fov * Math.PI) / 180
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect)
    const fit = (sphere / Math.sin(Math.min(vfov, hfov) / 2)) * 1.08
    const target = new Vector3(0, size.y / 2, 0)
    camera.near = Math.max(0.1, radius / 200)
    camera.far = Math.max(2000, radius * 40)
    camera.position.copy(target).add(new Vector3(0.62, 0.6, 1).normalize().multiplyScalar(fit))
    camera.updateProjectionMatrix()
    controls.target.copy(target)
    controls.minDistance = radius * 0.4
    controls.maxDistance = Math.max(BED_MM * 2.2, fit * 3)
    controls.update()
    home = { pos: camera.position.clone(), target: target.clone() }
  }

  return {
    load(bytes) {
      const geometry: BufferGeometry = new STLLoader().parse(bytes)
      geometry.rotateX(-Math.PI / 2) // Z-up (STL, the slicer) to Y-up (three.js)
      geometry.computeBoundingBox()
      const box = geometry.boundingBox ?? new Box3()
      const size = box.getSize(new Vector3())
      const center = box.getCenter(new Vector3())
      geometry.translate(-center.x, -box.min.y, -center.z) // centred on the bed, resting on it
      if (!geometry.getAttribute('normal')) geometry.computeVertexNormals()
      if (part) {
        scene.remove(part)
        part.geometry.dispose()
      }
      part = new Mesh(geometry, material)
      scene.add(part)
      frameAll(size)
      dirty = true
      const triangles = (geometry.index ? geometry.index.count : geometry.getAttribute('position').count) / 3
      // size in slicer terms: X, Y (depth) and Z (height)
      const sz: [number, number, number] = [size.x, size.z, size.y]
      return { triangles, size: sz, fitsBed: sz[0] <= BED_MM && sz[1] <= BED_MM && sz[2] <= BED_MM }
    },
    setColors(c) {
      if (c.part) material.color = new Color(c.part)
      if (c.grid) {
        const g = new Color(c.grid)
        for (const m of [grid.material, outline.material].flat() as Array<Material & { color?: Color }>) m.color?.copy(g)
        const lines = grid.geometry.getAttribute('color')
        if (lines) {
          for (let i = 0; i < lines.count; i += 1) lines.setXYZ(i, g.r, g.g, g.b)
          lines.needsUpdate = true
        }
      }
      if (c.bed) (bedPlate.material as MeshBasicMaterial).color = new Color(c.bed)
      dirty = true
    },
    setAutoRotate(on) {
      controls.autoRotate = on
      dirty = true
    },
    resetView() {
      camera.position.copy(home.pos)
      controls.target.copy(home.target)
      controls.update()
      dirty = true
    },
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      visibility.disconnect()
      controls.removeEventListener('change', invalidate)
      controls.removeEventListener('start', stopSpin)
      controls.dispose()
      part?.geometry.dispose()
      material.dispose()
      bedPlate.geometry.dispose()
      ;(bedPlate.material as Material).dispose()
      grid.geometry.dispose()
      ;(grid.material as Material).dispose()
      outline.geometry.dispose()
      ;(outline.material as Material).dispose()
      renderer.dispose()
      renderer.forceContextLoss()
      canvas.remove()
    }
  }
}

export function dataUrlToBuffer(dataUrl: string): ArrayBuffer {
  const comma = dataUrl.indexOf(',')
  const bin = atob(dataUrl.slice(comma + 1))
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i)
  return out.buffer
}
