/**
 * The three.js part viewer: one WebGLRenderer, orbit controls, and an STL resting on the printer's own
 * build plate (a 256 x 256 mm textured sheet on its heatbed), lit like a product photo with a soft shadow. Plain DOM + three (pattern from the official Meshy plugin's stage.ts, MIT): React mounts a
 * <div>, hands it to `createStage`, and calls `dispose()` on unmount, which frees the GPU context.
 *
 * - STL is Z-up, three.js is Y-up: the geometry is turned once at load.
 * - Render on demand: a frame is drawn only while something moves (orbit, damping, auto-rotate) or
 *   changed, and never while the canvas is off-screen or the window hidden.
 * - The renderer is transparent: the page's own backdrop shows around the bed. The plate keeps its own
 *   colour in every theme (it is an object, not a surface of the app); only the part follows the filament.
 */

import {
  Box3,
  BoxGeometry,
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  ExtrudeGeometry,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  PCFSoftShadowMap,
  PerspectiveCamera,
  Scene,
  Shape,
  Spherical,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer
} from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'

/** Bambu A1 build plate. */
export const BED_MM = 256

/** Thickness of the steel sheet and of the heatbed under it, in mm. */
const SHEET_MM = 1.6
const HEATBED_MM = 6

export interface StageColors {
  part: string
  /** The textured build sheet. */
  plate: string
  /** The heatbed under the sheet (seen at its edges). */
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

/** A filament colour as the 3D view paints it: black and white parts keep enough range for their shape
 *  to read under the lights (a #000000 part would be a flat silhouette, a #ffffff one would burn out). */
export function viewableColor(hex: string): string {
  const c = new Color(hex)
  const hsl = { h: 0, s: 0, l: 0 }
  c.getHSL(hsl)
  const l = Math.min(0.82, Math.max(0.075, hsl.l))
  if (l === hsl.l) return hex
  c.setHSL(hsl.h, hsl.s, l)
  return `#${c.getHexString()}`
}

/** Colours for the scene, read from the element's computed CSS variables (styles.ts sets the plate's). */
export function themeColors(el: Element, part: string | null): StageColors {
  const css = getComputedStyle(el)
  const v = (name: string, fb: string) => css.getPropertyValue(name).trim() || fb
  return {
    part: viewableColor(part || cssHex(v('--ui-accent', '#4f7cff'), '#4f7cff')),
    plate: cssHex(v('--w-plate', '#75695a'), '#75695a'),
    bed: cssHex(v('--w-bed', '#26272b'), '#26272b')
  }
}

/**
 * The sheet's surface as one picture: fine grain (a textured PEI sheet is never flat colour), a 16 mm grid
 * with stronger lines every 64 mm, and an inset border. Drawn in light greys: the material's colour tints it.
 */
function plateTexture(): CanvasTexture {
  const px = 1024
  const perMm = px / BED_MM
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = px
  const g = canvas.getContext('2d')
  if (g) {
    // grain, drawn small and tiled
    const tile = document.createElement('canvas')
    tile.width = tile.height = 128
    const t = tile.getContext('2d')
    if (t) {
      const img = t.createImageData(128, 128)
      for (let i = 0; i < img.data.length; i += 4) {
        const n = 196 + Math.floor(Math.random() * 44)
        img.data[i] = img.data[i + 1] = img.data[i + 2] = n
        img.data[i + 3] = 255
      }
      t.putImageData(img, 0, 0)
      const pattern = g.createPattern(tile, 'repeat')
      if (pattern) {
        g.fillStyle = pattern
        g.fillRect(0, 0, px, px)
      }
    }
    const line = (mm: number, alpha: number, width: number) => {
      g.fillStyle = `rgba(255,255,255,${alpha})`
      const at = Math.round(mm * perMm - width / 2)
      g.fillRect(at, 0, width, px)
      g.fillRect(0, at, px, width)
    }
    for (let mm = 16; mm < BED_MM; mm += 16) line(mm, mm % 64 === 0 ? 0.5 : 0.24, mm % 64 === 0 ? 3 : 2)
    g.strokeStyle = 'rgba(255,255,255,0.42)'
    g.lineWidth = 3
    const inset = 4 * perMm
    g.strokeRect(inset, inset, px - inset * 2, px - inset * 2)
  }
  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 8
  // ExtrudeGeometry's cap UVs are the shape's own coordinates (mm, centred): map -128..128 to 0..1.
  texture.repeat.set(1 / BED_MM, 1 / BED_MM)
  texture.offset.set(0.5, 0.5)
  return texture
}

function roundedSquare(size: number, radius: number): Shape {
  const h = size / 2
  const s = new Shape()
  s.moveTo(-h + radius, -h)
  s.lineTo(h - radius, -h)
  s.quadraticCurveTo(h, -h, h, -h + radius)
  s.lineTo(h, h - radius)
  s.quadraticCurveTo(h, h, h - radius, h)
  s.lineTo(-h + radius, h)
  s.quadraticCurveTo(-h, h, -h, h - radius)
  s.lineTo(-h, -h + radius)
  s.quadraticCurveTo(-h, -h, -h + radius, -h)
  return s
}

/** True when the person asked the system for less motion: the part then waits still until they turn it. */
export function prefersStill(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

export function createStage(host: HTMLElement, colors: StageColors): Stage {
  const renderer = new WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = SRGBColorSpace
  renderer.setClearColor(0x000000, 0)
  const canvas = renderer.domElement
  Object.assign(canvas.style, { display: 'block', width: '100%', height: '100%', outline: 'none', touchAction: 'none' })
  canvas.setAttribute('aria-label', '3D view of the part. Drag or use the arrow keys to turn, scroll or use plus and minus to zoom.')
  canvas.setAttribute('role', 'img')
  canvas.tabIndex = 0
  host.appendChild(canvas)

  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = PCFSoftShadowMap

  const scene = new Scene()
  // Sky light with a warm bounce from the plate, a warm key that casts the shadow, a cool fill and a rim.
  scene.add(new HemisphereLight(0xffffff, 0x5a5146, 1.15))
  const key = new DirectionalLight(0xfff3e2, 2.3)
  key.castShadow = true
  key.shadow.mapSize.set(1024, 1024)
  key.shadow.bias = -0.0005
  key.shadow.normalBias = 0.4
  scene.add(key)
  scene.add(key.target)
  const fill = new DirectionalLight(0xdde7ff, 0.65)
  fill.position.set(220, 110, 160)
  scene.add(fill)
  const rim = new DirectionalLight(0xffffff, 0.85)
  rim.position.set(80, 150, -240)
  scene.add(rim)
  const KEY_DIR = new Vector3(-0.42, 1, 0.5).normalize()
  /** Point the key light at `target` and fit its shadow box around a part of this `radius`. */
  const aimKey = (target: Vector3, radius: number) => {
    const r = Math.max(radius * 1.8, 24)
    key.position.copy(target).addScaledVector(KEY_DIR, r * 4)
    key.target.position.copy(target)
    const cam = key.shadow.camera
    cam.left = cam.bottom = -r
    cam.right = cam.top = r
    cam.near = 1
    cam.far = r * 9
    cam.updateProjectionMatrix()
  }
  aimKey(new Vector3(), 60)

  // The bed: the textured sheet (top at y = 0, rounded corners) on a darker heatbed.
  const sheetTexture = plateTexture()
  const sheetGeometry = new ExtrudeGeometry(roundedSquare(BED_MM, 5), { depth: SHEET_MM, bevelEnabled: false, curveSegments: 6 })
  sheetGeometry.rotateX(-Math.PI / 2)
  sheetGeometry.translate(0, -SHEET_MM, 0)
  const sheetTop = new MeshStandardMaterial({ color: colors.plate, map: sheetTexture, bumpMap: sheetTexture, bumpScale: 0.35, roughness: 0.92, metalness: 0.12 })
  const sheetSide = new MeshStandardMaterial({ color: colors.plate, roughness: 0.6, metalness: 0.5 })
  const sheet = new Mesh(sheetGeometry, [sheetTop, sheetSide])
  sheet.receiveShadow = true
  scene.add(sheet)
  const heatbedMaterial = new MeshStandardMaterial({ color: colors.bed, roughness: 0.75, metalness: 0.2 })
  const heatbed = new Mesh(new BoxGeometry(BED_MM + 8, HEATBED_MM, BED_MM + 8), heatbedMaterial)
  heatbed.position.y = -SHEET_MM - HEATBED_MM / 2
  scene.add(heatbed)

  const camera = new PerspectiveCamera(30, 1, 0.5, 5000)
  camera.position.set(140, 190, 240)
  const controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.dampingFactor = 0.12
  controls.autoRotate = !prefersStill()
  controls.autoRotateSpeed = 0.8
  controls.maxPolarAngle = Math.PI * 0.495 // stay above the bed
  // Any touch from the person stops the slow spin for good: they are looking at something.
  const stopSpin = () => {
    controls.autoRotate = false
  }
  controls.addEventListener('start', stopSpin)
  // Arrow keys turn the part around its middle, plus and minus move closer and away.
  const onKey = (e: KeyboardEvent) => {
    const turn: Record<string, [number, number, number]> = {
      ArrowLeft: [-0.2, 0, 1],
      ArrowRight: [0.2, 0, 1],
      ArrowUp: [0, -0.12, 1],
      ArrowDown: [0, 0.12, 1],
      '+': [0, 0, 0.87],
      '=': [0, 0, 0.87],
      '-': [0, 0, 1.15]
    }
    const step = turn[e.key]
    if (!step || e.altKey || e.ctrlKey || e.metaKey) return
    e.preventDefault()
    controls.autoRotate = false
    const at = new Spherical().setFromVector3(camera.position.clone().sub(controls.target))
    at.theta += step[0]
    at.phi = Math.min(controls.maxPolarAngle, Math.max(0.08, at.phi + step[1]))
    at.radius = Math.min(controls.maxDistance, Math.max(controls.minDistance, at.radius * step[2]))
    camera.position.copy(controls.target).add(new Vector3().setFromSpherical(at))
    controls.update()
    dirty = true
  }
  canvas.addEventListener('keydown', onKey)

  const material = new MeshStandardMaterial({ color: colors.part, roughness: 0.5, metalness: 0.02 })
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
    const fit = (sphere / Math.sin(Math.min(vfov, hfov) / 2)) * 1.18
    const target = new Vector3(0, size.y / 2, 0)
    camera.near = Math.max(0.1, radius / 200)
    camera.far = Math.max(2000, radius * 40)
    camera.position.copy(target).add(new Vector3(0.5, 1.12, 1).normalize().multiplyScalar(fit))
    camera.updateProjectionMatrix()
    controls.target.copy(target)
    controls.minDistance = radius * 0.4
    controls.maxDistance = Math.max(BED_MM * 2.2, fit * 3)
    controls.update()
    aimKey(target, sphere)
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
      part.castShadow = true
      part.receiveShadow = true
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
      if (c.plate) {
        sheetTop.color = new Color(c.plate)
        sheetSide.color = new Color(c.plate)
      }
      if (c.bed) heatbedMaterial.color = new Color(c.bed)
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
      canvas.removeEventListener('keydown', onKey)
      controls.dispose()
      part?.geometry.dispose()
      material.dispose()
      sheetGeometry.dispose()
      sheetTexture.dispose()
      sheetTop.dispose()
      sheetSide.dispose()
      heatbed.geometry.dispose()
      heatbedMaterial.dispose()
      key.shadow.map?.dispose()
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
