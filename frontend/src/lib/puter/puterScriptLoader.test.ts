import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  PUTER_SCRIPT_ID,
  PUTER_SCRIPT_LOADER_VERSION,
  PUTER_SCRIPT_SRC,
  createPuterScriptLoaderResult,
  loadPuterScriptRuntime,
} from './puterScriptLoader'

function clearPuterRuntime() {
  delete (window as Window & { puter?: unknown }).puter
  document.querySelectorAll('script').forEach((script) => script.remove())
}

function getPuterScript() {
  return document.getElementById(PUTER_SCRIPT_ID) as HTMLScriptElement | null
}

describe('Puter dev script loader', () => {
  beforeEach(() => {
    clearPuterRuntime()
  })

  it('is idle by default and exposes only safe status metadata', () => {
    const result = createPuterScriptLoaderResult()

    expect(result).toEqual({
      loader_version: PUTER_SCRIPT_LOADER_VERSION,
      status: 'idle',
      reason: 'not_started',
      script_src: PUTER_SCRIPT_SRC,
    })
  })

  it('does not inject a script on import', () => {
    expect(getPuterScript()).toBeNull()
  })

  it('requires both experimental flags before loading', async () => {
    for (const input of [
      { experimentalFeatureEnabled: false, devSurfaceEnabled: false },
      { experimentalFeatureEnabled: true, devSurfaceEnabled: false },
      { experimentalFeatureEnabled: false, devSurfaceEnabled: true },
    ]) {
      const result = await loadPuterScriptRuntime({ ...input, runtime: window })

      expect(result.status).toBe('unavailable')
      expect(result.reason).toBe('feature_disabled')
      expect(getPuterScript()).toBeNull()
    }
  })

  it('rejects non-browser runtime safely', async () => {
    const result = await loadPuterScriptRuntime({
      devSurfaceEnabled: true,
      experimentalFeatureEnabled: true,
      runtime: {},
    })

    expect(result.status).toBe('unavailable')
    expect(result.reason).toBe('non_browser_runtime')
  })

  it('injects only the fixed Puter script URL after explicit load', async () => {
    const chat = vi.fn()
    const pending = loadPuterScriptRuntime({
      devSurfaceEnabled: true,
      experimentalFeatureEnabled: true,
      runtime: window,
    })
    const script = getPuterScript()

    expect(script).not.toBeNull()
    expect(script?.src).toBe(PUTER_SCRIPT_SRC)
    expect(script?.async).toBe(true)
    expect(document.scripts).toHaveLength(1)

    ;(window as Window & { puter?: unknown }).puter = { ai: { chat } }
    script?.dispatchEvent(new Event('load'))

    const result = await pending
    expect(result.status).toBe('loaded')
    expect(result.reason).toBe('puter_available')
    expect(chat).not.toHaveBeenCalled()
  })

  it('prevents duplicate script injection', async () => {
    const script = document.createElement('script')
    script.id = PUTER_SCRIPT_ID
    script.src = PUTER_SCRIPT_SRC
    document.head.appendChild(script)

    const pending = loadPuterScriptRuntime({
      devSurfaceEnabled: true,
      experimentalFeatureEnabled: true,
      runtime: window,
    })

    expect(document.querySelectorAll(`script[src="${PUTER_SCRIPT_SRC}"]`)).toHaveLength(1)
    script.dispatchEvent(new Event('error'))

    const result = await pending
    expect(result.status).toBe('failed')
    expect(result.reason).toBe('script_load_failed')
  })

  it('fails closed when script loading fails', async () => {
    const pending = loadPuterScriptRuntime({
      devSurfaceEnabled: true,
      experimentalFeatureEnabled: true,
      runtime: window,
    })
    const script = getPuterScript()

    script?.dispatchEvent(new Event('error'))

    const result = await pending
    expect(result.status).toBe('failed')
    expect(result.reason).toBe('script_load_failed')
    expect(JSON.stringify(result).toLowerCase()).not.toContain('stack')
  })

  it('never calls puter.ai.chat when an existing runtime is already available', async () => {
    const chat = vi.fn()
    ;(window as Window & { puter?: unknown }).puter = { ai: { chat } }

    const result = await loadPuterScriptRuntime({
      devSurfaceEnabled: true,
      experimentalFeatureEnabled: true,
      runtime: window,
    })

    expect(result.status).toBe('loaded')
    expect(getPuterScript()).toBeNull()
    expect(chat).not.toHaveBeenCalled()
  })
})
