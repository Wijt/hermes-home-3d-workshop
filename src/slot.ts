/**
 * One live 3D view at a time across the whole plugin (the Workshop page and transcript cards). A view
 * claims the slot when the person asks to see a part; whichever view held it falls back to its still
 * picture and frees its WebGL context. Chromium caps live contexts at about 16 per window, and the app
 * itself needs some.
 */

export interface ViewSlot {
  claim: (id: string) => void
  release: (id: string) => void
  holder: () => string | null
  subscribe: (fn: (holder: string | null) => void) => () => void
}

export function createViewSlot(): ViewSlot {
  let holder: string | null = null
  const listeners = new Set<(h: string | null) => void>()
  const emit = () => listeners.forEach(fn => fn(holder))
  return {
    claim(id) {
      if (holder === id) return
      holder = id
      emit()
    },
    release(id) {
      if (holder !== id) return
      holder = null
      emit()
    },
    holder: () => holder,
    subscribe(fn) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    }
  }
}

/** The plugin's one slot (module state: reset by `viewSlot.release` on dispose of its holder). */
export const viewSlot = createViewSlot()
