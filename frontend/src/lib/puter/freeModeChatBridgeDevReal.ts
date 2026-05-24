import {
  decideFreeModeChatBridge,
  type FreeModeChatBridgeDecision,
  type FreeModeChatBridgeInput,
} from './freeModeChatBridgeContract'
import {
  invokePuterFreeModeManualHarness,
  type PuterManualHarnessResult,
} from './freeModePuterManualHarness'

export const FREE_MODE_CHAT_BRIDGE_DEV_REAL_VERSION = 'free_mode_chat_bridge_dev_real_v1'
export const PUTER_CHAT_BRIDGE_DEV_REAL_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL'

const APPROVED_DEV_REAL_RESULT_KEYS = new Set([
  'dev_real_bridge_version',
  'allowed',
  'denied',
  'reason',
  'dev_real_enabled',
  'provider_family',
  'adapter_id',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'access_layer_plan_mode',
  'provider_family',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'fallback_triggered',
  'quota_allowed',
  'quota_exceeded',
  'routing_allowed',
  'selected_adapter_id',
  'boundary_version',
  'snapshot_version',
  'sanitized_output',
])

const SECRET_PATTERNS = [
  /\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b/g,
  /\bbearer\s+[A-Za-z0-9._~+/=-]{8,}/gi,
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
]

export type FreeModeChatBridgeDevRealInput = FreeModeChatBridgeInput & {
  devRealFeatureEnabled?: boolean
  prompt?: unknown
  runtime?: unknown
}

export type FreeModeChatBridgeDevRealRuntimeTruth = {
  access_layer_plan_mode: string
  provider_family: string
  provider_attempted: boolean
  provider_succeeded: boolean
  provider_failed_reason: string
  fallback_triggered: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  selected_adapter_id: string
  boundary_version: string
  snapshot_version: string
  sanitized_output: string | null
}

export type FreeModeChatBridgeDevRealResult = {
  dev_real_bridge_version: typeof FREE_MODE_CHAT_BRIDGE_DEV_REAL_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  dev_real_enabled: boolean
  provider_family: string
  adapter_id: string
  fallback_required: boolean
  sanitized_output: string | null
  runtime_truth: FreeModeChatBridgeDevRealRuntimeTruth
}

export function isPuterChatBridgeDevRealFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export async function runFreeModeChatBridgeDevReal(
  input: FreeModeChatBridgeDevRealInput,
): Promise<FreeModeChatBridgeDevRealResult> {
  const decision = decideFreeModeChatBridge(input)
  const devRealEnabled = input.devRealFeatureEnabled === true

  if (!devRealEnabled) {
    return denied('dev_real_bridge_disabled', decision, devRealEnabled)
  }

  if (!decision.allowed) {
    return denied(decision.reason, decision, devRealEnabled)
  }

  const harnessResult = await invokePuterFreeModeManualHarness({
    accessSnapshotEnvelope: input.accessSnapshotEnvelope,
    experimentalFeatureEnabled: input.experimentalFeatureEnabled,
    manualInvocation: true,
    prompt: input.prompt,
    requestOptions: input.requestOptions,
    runtime: input.runtime,
  })

  if (!harnessResult.ok) {
    return providerFailed(harnessResult.reason, decision, devRealEnabled)
  }

  return providerSucceeded(harnessResult, decision, devRealEnabled)
}

function denied(
  reason: string,
  decision: FreeModeChatBridgeDecision,
  devRealEnabled: boolean,
): FreeModeChatBridgeDevRealResult {
  return {
    ...baseResult(reason, decision, devRealEnabled),
    allowed: false,
    denied: true,
    fallback_required: true,
    sanitized_output: null,
    runtime_truth: {
      ...baseRuntimeTruth(reason, decision),
      provider_attempted: false,
      provider_succeeded: false,
      fallback_triggered: true,
      sanitized_output: null,
    },
  }
}

function providerFailed(
  reason: string,
  decision: FreeModeChatBridgeDecision,
  devRealEnabled: boolean,
): FreeModeChatBridgeDevRealResult {
  const providerAttempted = safeReason(reason) === 'puter_call_failed'
  return {
    ...baseResult(reason, decision, devRealEnabled),
    allowed: false,
    denied: true,
    fallback_required: true,
    sanitized_output: null,
    runtime_truth: {
      ...baseRuntimeTruth(reason, decision),
      provider_attempted: providerAttempted,
      provider_succeeded: false,
      fallback_triggered: true,
      sanitized_output: null,
    },
  }
}

function providerSucceeded(
  harnessResult: PuterManualHarnessResult,
  decision: FreeModeChatBridgeDecision,
  devRealEnabled: boolean,
): FreeModeChatBridgeDevRealResult {
  const sanitizedOutput = sanitizeProviderText(harnessResult.sanitized_text)
  return {
    ...baseResult('ok', decision, devRealEnabled),
    allowed: true,
    denied: false,
    fallback_required: false,
    sanitized_output: sanitizedOutput,
    runtime_truth: {
      ...baseRuntimeTruth('', decision),
      provider_attempted: true,
      provider_succeeded: true,
      provider_failed_reason: '',
      fallback_triggered: false,
      sanitized_output: sanitizedOutput,
    },
  }
}

function baseResult(
  reason: string,
  decision: FreeModeChatBridgeDecision,
  devRealEnabled: boolean,
): Omit<FreeModeChatBridgeDevRealResult, 'allowed' | 'denied' | 'fallback_required' | 'sanitized_output' | 'runtime_truth'> {
  return {
    dev_real_bridge_version: FREE_MODE_CHAT_BRIDGE_DEV_REAL_VERSION,
    reason: safeReason(reason),
    dev_real_enabled: devRealEnabled,
    provider_family: decision.provider_family,
    adapter_id: decision.adapter_id,
  }
}

function baseRuntimeTruth(
  reason: string,
  decision: FreeModeChatBridgeDecision,
): FreeModeChatBridgeDevRealRuntimeTruth {
  return {
    access_layer_plan_mode: decision.runtime_truth.access_layer_plan_mode,
    provider_family: decision.runtime_truth.provider_family,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: reason ? safeReason(reason) : '',
    fallback_triggered: true,
    quota_allowed: decision.runtime_truth.quota_allowed,
    quota_exceeded: decision.runtime_truth.quota_exceeded,
    routing_allowed: decision.runtime_truth.routing_allowed,
    selected_adapter_id: decision.runtime_truth.selected_adapter_id,
    boundary_version: decision.runtime_truth.boundary_version,
    snapshot_version: decision.runtime_truth.snapshot_version,
    sanitized_output: null,
  }
}

function sanitizeProviderText(value: string): string {
  let sanitized = String(value || '')
  for (const pattern of SECRET_PATTERNS) {
    sanitized = sanitized.replace(pattern, '[redacted]')
  }
  return sanitized.trim()
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'dev_real_bridge_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModeChatBridgeDevRealResult(value: unknown): value is FreeModeChatBridgeDevRealResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_DEV_REAL_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
