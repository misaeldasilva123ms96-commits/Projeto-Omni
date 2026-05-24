import { useState } from 'react'
import {
  isPuterChatBridgeFlagEnabled,
} from './freeModeChatBridgeContract'
import {
  isPuterChatBridgeDevRealFlagEnabled,
  runFreeModeChatBridgeDevReal,
  type FreeModeChatBridgeDevRealResult,
} from './freeModeChatBridgeDevReal'
import {
  PUTER_BROWSER_ADAPTER_ID,
  PUTER_PROVIDER_FAMILY,
  isPuterFreeModeFlagEnabled,
} from './freeModePuterBrowserAdapter'

export const PUTER_FREE_CHAT_DEV_TOGGLE_VERSION = 'puter_free_chat_dev_toggle_v1'
export const PUTER_FREE_CHAT_DEV_TOGGLE_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE'

export type PuterFreeChatDevToggleState = {
  toggle_version: typeof PUTER_FREE_CHAT_DEV_TOGGLE_VERSION
  active: boolean
  denied: boolean
  pending: boolean
  reason: string
  provider_family: typeof PUTER_PROVIDER_FAMILY
  adapter_id: typeof PUTER_BROWSER_ADAPTER_ID | ''
  sanitized_text: string
  experimental: true
}

export type PuterFreeChatDevToggleSurfaceProps = {
  accessSnapshotEnvelope: unknown
  chatBridgeFeatureEnabled?: boolean
  chatDevToggleEnabled?: boolean
  defaultPrompt?: string
  devRealFeatureEnabled?: boolean
  experimentalFeatureEnabled?: boolean
  runtime?: unknown
}

export function isPuterFreeChatDevToggleFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function createPuterFreeChatDevToggleState(reason = 'not_invoked'): PuterFreeChatDevToggleState {
  return {
    toggle_version: PUTER_FREE_CHAT_DEV_TOGGLE_VERSION,
    active: false,
    denied: true,
    pending: false,
    reason: safeReason(reason),
    provider_family: PUTER_PROVIDER_FAMILY,
    adapter_id: '',
    sanitized_text: '',
    experimental: true,
  }
}

export function resultToPuterFreeChatDevToggleState(
  result: FreeModeChatBridgeDevRealResult,
): PuterFreeChatDevToggleState {
  return {
    toggle_version: PUTER_FREE_CHAT_DEV_TOGGLE_VERSION,
    active: result.allowed,
    denied: result.denied,
    pending: false,
    reason: safeReason(result.reason),
    provider_family: PUTER_PROVIDER_FAMILY,
    adapter_id: result.adapter_id === PUTER_BROWSER_ADAPTER_ID ? PUTER_BROWSER_ADAPTER_ID : '',
    sanitized_text: sanitizeVisibleText(result.sanitized_output),
    experimental: true,
  }
}

export function PuterFreeChatDevToggleSurface({
  accessSnapshotEnvelope,
  chatBridgeFeatureEnabled = isPuterChatBridgeFlagEnabled(),
  chatDevToggleEnabled = isPuterFreeChatDevToggleFlagEnabled(),
  defaultPrompt = '',
  devRealFeatureEnabled = isPuterChatBridgeDevRealFlagEnabled(),
  experimentalFeatureEnabled = isPuterFreeModeFlagEnabled(),
  runtime,
}: PuterFreeChatDevToggleSurfaceProps) {
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [state, setState] = useState<PuterFreeChatDevToggleState>(createPuterFreeChatDevToggleState())

  if (
    experimentalFeatureEnabled !== true
    || chatBridgeFeatureEnabled !== true
    || devRealFeatureEnabled !== true
    || chatDevToggleEnabled !== true
  ) {
    return null
  }

  async function handleManualInvoke() {
    setState((current) => ({ ...current, pending: true, reason: 'pending' }))
    const result = await runFreeModeChatBridgeDevReal({
      accessSnapshotEnvelope,
      browserRuntimeAvailable: hasBrowserRuntime(runtime),
      chatBridgeFeatureEnabled,
      dailyTokenUsage: 125,
      devRealFeatureEnabled,
      experimentalFeatureEnabled,
      inputTokenEstimate: 100,
      outputTokenBudgetEstimate: 25,
      planMode: 'free',
      prompt,
      puterRuntimeAvailable: hasPuterRuntime(runtime),
      requestOptions: {},
      requestedCapabilities: {},
      runtime,
    })
    setState(resultToPuterFreeChatDevToggleState(result))
  }

  const outputText = state.sanitized_text || state.reason

  return (
    <section aria-label="Puter Free chat dev toggle" data-puter-free-chat-dev-toggle="manual-only">
      <label htmlFor="puter-free-chat-dev-prompt">Dev chat prompt</label>
      <textarea
        id="puter-free-chat-dev-prompt"
        aria-label="Puter Free chat dev prompt"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
      />
      <button type="button" onClick={handleManualInvoke} disabled={state.pending}>
        Run dev Free chat bridge
      </button>
      <output aria-label="Puter Free chat dev result">
        {outputText}
      </output>
    </section>
  )
}

function hasBrowserRuntime(runtime: unknown): boolean {
  return Boolean(runtime && typeof runtime === 'object' && 'window' in runtime)
}

function hasPuterRuntime(runtime: unknown): boolean {
  if (!hasBrowserRuntime(runtime)) {
    return false
  }

  const browserWindow = (runtime as { window?: unknown }).window
  if (!browserWindow || typeof browserWindow !== 'object') {
    return false
  }

  const puter = (browserWindow as Record<string, unknown>).puter
  if (!puter || typeof puter !== 'object') {
    return false
  }

  const ai = (puter as Record<string, unknown>).ai
  return Boolean(ai && typeof ai === 'object' && typeof (ai as Record<string, unknown>).chat === 'function')
}

function sanitizeVisibleText(value: string | null): string {
  return typeof value === 'string' ? value : ''
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'puter_free_chat_dev_toggle_denied'
}
