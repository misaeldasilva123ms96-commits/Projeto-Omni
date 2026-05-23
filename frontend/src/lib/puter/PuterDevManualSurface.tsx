import { useState } from 'react'
import {
  PUTER_BROWSER_ADAPTER_ID,
  PUTER_PROVIDER_FAMILY,
  isPuterFreeModeFlagEnabled,
} from './freeModePuterBrowserAdapter'
import {
  PUTER_MANUAL_HARNESS_VERSION,
  invokePuterFreeModeManualHarness,
  type PuterManualHarnessResult,
} from './freeModePuterManualHarness'

export const PUTER_DEV_SURFACE_VERSION = 'puter_dev_surface_v1'
export const PUTER_DEV_SURFACE_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE'

export type PuterDevSurfaceState = {
  surface_version: typeof PUTER_DEV_SURFACE_VERSION
  harness_version: typeof PUTER_MANUAL_HARNESS_VERSION
  active: boolean
  denied: boolean
  pending: boolean
  reason: string
  provider_family: typeof PUTER_PROVIDER_FAMILY
  adapter_id: typeof PUTER_BROWSER_ADAPTER_ID
  sanitized_text: string
  experimental: true
}

export type PuterDevManualSurfaceProps = {
  accessSnapshotEnvelope: unknown
  defaultPrompt?: string
  devSurfaceEnabled?: boolean
  experimentalFeatureEnabled?: boolean
  runtime?: unknown
}

export function isPuterDevSurfaceFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function createPuterDevSurfaceState(reason = 'not_invoked'): PuterDevSurfaceState {
  return {
    surface_version: PUTER_DEV_SURFACE_VERSION,
    harness_version: PUTER_MANUAL_HARNESS_VERSION,
    active: false,
    denied: true,
    pending: false,
    reason: safeReason(reason),
    provider_family: PUTER_PROVIDER_FAMILY,
    adapter_id: PUTER_BROWSER_ADAPTER_ID,
    sanitized_text: '',
    experimental: true,
  }
}

export function resultToPuterDevSurfaceState(result: PuterManualHarnessResult): PuterDevSurfaceState {
  return {
    surface_version: PUTER_DEV_SURFACE_VERSION,
    harness_version: result.harness_version,
    active: result.ok,
    denied: result.denied,
    pending: false,
    reason: safeReason(result.reason),
    provider_family: PUTER_PROVIDER_FAMILY,
    adapter_id: PUTER_BROWSER_ADAPTER_ID,
    sanitized_text: result.sanitized_text,
    experimental: true,
  }
}

export function PuterDevManualSurface({
  accessSnapshotEnvelope,
  defaultPrompt = '',
  devSurfaceEnabled = isPuterDevSurfaceFlagEnabled(),
  experimentalFeatureEnabled = isPuterFreeModeFlagEnabled(),
  runtime,
}: PuterDevManualSurfaceProps) {
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [state, setState] = useState<PuterDevSurfaceState>(createPuterDevSurfaceState())

  if (!devSurfaceEnabled || !experimentalFeatureEnabled) {
    return null
  }

  async function handleManualInvoke() {
    setState((current) => ({ ...current, pending: true, reason: 'pending' }))
    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope,
      experimentalFeatureEnabled,
      manualInvocation: true,
      prompt,
      runtime,
    })
    setState(resultToPuterDevSurfaceState(result))
  }

  const outputText = state.sanitized_text || state.reason

  return (
    <section aria-label="Puter manual dev surface" data-puter-dev-surface="manual-only">
      <label htmlFor="puter-dev-manual-prompt">Manual prompt</label>
      <textarea
        id="puter-dev-manual-prompt"
        aria-label="Manual Puter prompt"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
      />
      <button type="button" onClick={handleManualInvoke} disabled={state.pending}>
        Run manual Puter check
      </button>
      <output aria-label="Puter manual result">
        {outputText}
      </output>
    </section>
  )
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'puter_dev_surface_denied'
}
