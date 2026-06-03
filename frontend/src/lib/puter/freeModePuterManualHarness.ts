import {
  PUTER_BROWSER_ADAPTER_ID,
  PUTER_PROVIDER_FAMILY,
  selectPuterFreeModeBrowserAdapter,
  type PuterBrowserSelectionInput,
} from './freeModePuterBrowserAdapter'

export const PUTER_MANUAL_HARNESS_VERSION = 'puter_manual_harness_v1'

const SECRET_PATTERNS = [
  /\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b/g,
  /\bbearer\s+[A-Za-z0-9._~+/=-]{8,}/gi,
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
]

export type PuterManualHarnessResult = {
  ok: boolean
  denied: boolean
  reason: string
  provider_family: typeof PUTER_PROVIDER_FAMILY
  adapter_id: typeof PUTER_BROWSER_ADAPTER_ID
  sanitized_text: string
  experimental: true
  harness_version: typeof PUTER_MANUAL_HARNESS_VERSION
}

export type PuterManualHarnessInput = PuterBrowserSelectionInput & {
  manualInvocation?: boolean
  prompt?: unknown
}

export async function invokePuterFreeModeManualHarness(
  input: PuterManualHarnessInput,
): Promise<PuterManualHarnessResult> {
  if (input.manualInvocation !== true) {
    return denied('manual_invocation_required')
  }

  const prompt = sanitizePrompt(input.prompt)
  if (!prompt) {
    return denied('invalid_prompt')
  }

  const selection = selectPuterFreeModeBrowserAdapter(input)
  if (!selection.selection_allowed) {
    return denied(selection.reason)
  }

  const chat = getPuterChat(input.runtime)
  if (!chat) {
    return denied('puter_unavailable')
  }

  try {
    const response = await chat(prompt)
    return {
      ...baseResult(),
      ok: true,
      denied: false,
      reason: 'ok',
      sanitized_text: sanitizeProviderText(readProviderText(response)),
    }
  } catch {
    return denied('puter_call_failed')
  }
}

function denied(reason: string): PuterManualHarnessResult {
  return {
    ...baseResult(),
    ok: false,
    denied: true,
    reason: safeReason(reason),
  }
}

function baseResult(): Omit<PuterManualHarnessResult, 'ok' | 'denied' | 'reason'> {
  return {
    provider_family: PUTER_PROVIDER_FAMILY,
    adapter_id: PUTER_BROWSER_ADAPTER_ID,
    sanitized_text: '',
    experimental: true,
    harness_version: PUTER_MANUAL_HARNESS_VERSION,
  }
}

type PuterChat = (prompt: string) => Promise<unknown> | unknown

function getPuterChat(runtime: unknown): PuterChat | null {
  if (!runtime || typeof runtime !== 'object' || !('window' in runtime)) {
    return null
  }

  const windowRecord = (runtime as { window?: unknown }).window
  if (!windowRecord || typeof windowRecord !== 'object') {
    return null
  }

  const puter = (windowRecord as Record<string, unknown>).puter
  if (!puter || typeof puter !== 'object') {
    return null
  }

  const ai = (puter as Record<string, unknown>).ai
  if (!ai || typeof ai !== 'object') {
    return null
  }

  const chat = (ai as Record<string, unknown>).chat
  return typeof chat === 'function' ? chat as PuterChat : null
}

function sanitizePrompt(value: unknown): string {
  if (typeof value !== 'string') {
    return ''
  }

  const trimmed = value.trim()
  if (!trimmed || containsSecretMaterial(trimmed)) {
    return ''
  }

  return trimmed
}

function readProviderText(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return ''
  }

  const record = value as Record<string, unknown>
  for (const key of ['text', 'message', 'content']) {
    const candidate = record[key]
    if (typeof candidate === 'string') {
      return candidate
    }
  }

  return ''
}

function sanitizeProviderText(value: string): string {
  let sanitized = String(value || '')
  for (const pattern of SECRET_PATTERNS) {
    sanitized = sanitized.replace(pattern, '[redacted]')
  }
  return sanitized.trim()
}

function containsSecretMaterial(value: string): boolean {
  return SECRET_PATTERNS.some((pattern) => {
    pattern.lastIndex = 0
    return pattern.test(value)
  })
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'manual_harness_denied'
}
