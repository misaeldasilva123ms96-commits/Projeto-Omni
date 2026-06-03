import {
  runFreeModeChatBridgeDevReal,
  type FreeModeChatBridgeDevRealInput,
  type FreeModeChatBridgeDevRealResult,
} from './freeModeChatBridgeDevReal'
import {
  decideFreeModePilotFlag,
  type FreeModePilotFlagContractInput,
  type FreeModePilotFlagDecision,
} from './freeModePilotFlagContract'

export const FREE_MODE_PILOT_INTERNAL_REAL_VERSION = 'free_mode_pilot_internal_real_v1'
export const PUTER_FREE_PILOT_INTERNAL_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL'

const APPROVED_INTERNAL_REAL_RESULT_KEYS = new Set([
  'internal_real_pilot_version',
  'allowed',
  'denied',
  'reason',
  'internal_pilot',
  'pilot_enabled',
  'pilot_eligible',
  'bridge_allowed',
  'provider_family',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'internal_pilot',
  'bridge_allowed',
  'bridge_denied_reason',
  'access_layer_plan_mode',
  'provider_family',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'fallback_triggered',
  'quota_allowed',
  'quota_exceeded',
  'routing_allowed',
  'consent_state',
  'selected_adapter_id',
  'boundary_version',
  'snapshot_version',
  'sanitized_output_present',
  'raw_provider_payload_exposed',
])

const SECRET_PATTERNS = [
  /\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b/g,
  /\bbearer\s+[A-Za-z0-9._~+/=-]{8,}/gi,
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
]

export type FreeModePilotInternalRealInput = FreeModePilotFlagContractInput
  & FreeModeChatBridgeDevRealInput
  & {
    internalPilotFeatureEnabled?: boolean
  }

export type FreeModePilotInternalRealRuntimeTruth = {
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  internal_pilot: boolean
  bridge_allowed: boolean
  bridge_denied_reason: string
  access_layer_plan_mode: string
  provider_family: string
  provider_attempted: boolean
  provider_succeeded: boolean
  provider_failed_reason: string
  fallback_triggered: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  consent_state: string
  selected_adapter_id: string
  boundary_version: string
  snapshot_version: string
  sanitized_output_present: boolean
  raw_provider_payload_exposed: false
}

export type FreeModePilotInternalRealResult = {
  internal_real_pilot_version: typeof FREE_MODE_PILOT_INTERNAL_REAL_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  internal_pilot: boolean
  pilot_enabled: boolean
  pilot_eligible: boolean
  bridge_allowed: boolean
  provider_family: string
  fallback_required: boolean
  sanitized_output: string | null
  runtime_truth: FreeModePilotInternalRealRuntimeTruth
}

export function isPuterFreePilotInternalFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export async function runFreeModePilotInternalReal(
  input: FreeModePilotInternalRealInput,
): Promise<FreeModePilotInternalRealResult> {
  const pilotDecision = decideFreeModePilotFlag(input)

  if (!pilotDecision.pilot_eligible) {
    return denied(pilotDecision.reason, pilotDecision, false, '')
  }

  if (input.internalPilotFeatureEnabled !== true) {
    return denied('internal_pilot_disabled', pilotDecision, false, '')
  }

  const bridgeResult = await runFreeModeChatBridgeDevReal(input)
  if (!bridgeResult.allowed) {
    return denied(bridgeResult.reason, pilotDecision, true, bridgeResult.reason, bridgeResult)
  }

  return allowed(pilotDecision, bridgeResult)
}

function allowed(
  pilotDecision: FreeModePilotFlagDecision,
  bridgeResult: FreeModeChatBridgeDevRealResult,
): FreeModePilotInternalRealResult {
  const sanitizedOutput = sanitizeVisibleText(bridgeResult.sanitized_output)
  return {
    ...baseResult('ok', pilotDecision, true, true),
    allowed: true,
    denied: false,
    fallback_required: false,
    sanitized_output: sanitizedOutput,
    runtime_truth: {
      ...baseRuntimeTruth('', pilotDecision, true, true, bridgeResult),
      provider_attempted: bridgeResult.runtime_truth.provider_attempted,
      provider_succeeded: bridgeResult.runtime_truth.provider_succeeded,
      provider_failed_reason: '',
      fallback_triggered: false,
      sanitized_output_present: Boolean(sanitizedOutput),
    },
  }
}

function denied(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  internalPilot: boolean,
  bridgeDeniedReason: string,
  bridgeResult?: FreeModeChatBridgeDevRealResult,
): FreeModePilotInternalRealResult {
  return {
    ...baseResult(reason, pilotDecision, internalPilot, false),
    allowed: false,
    denied: true,
    fallback_required: true,
    sanitized_output: null,
    runtime_truth: baseRuntimeTruth(reason, pilotDecision, internalPilot, false, bridgeResult, bridgeDeniedReason),
  }
}

function baseResult(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  internalPilot: boolean,
  bridgeAllowed: boolean,
): Omit<FreeModePilotInternalRealResult, 'allowed' | 'denied' | 'fallback_required' | 'sanitized_output' | 'runtime_truth'> {
  return {
    internal_real_pilot_version: FREE_MODE_PILOT_INTERNAL_REAL_VERSION,
    reason: safeReason(reason),
    internal_pilot: internalPilot,
    pilot_enabled: pilotDecision.pilot_enabled,
    pilot_eligible: pilotDecision.pilot_eligible,
    bridge_allowed: bridgeAllowed,
    provider_family: pilotDecision.provider_family,
  }
}

function baseRuntimeTruth(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  internalPilot: boolean,
  bridgeAllowed: boolean,
  bridgeResult?: FreeModeChatBridgeDevRealResult,
  bridgeDeniedReason = reason,
): FreeModePilotInternalRealRuntimeTruth {
  const providerFailedReason = bridgeResult?.runtime_truth.provider_failed_reason || safeReason(reason)
  return {
    pilot_enabled: pilotDecision.runtime_truth.pilot_enabled,
    pilot_eligible: pilotDecision.runtime_truth.pilot_eligible,
    pilot_denied_reason: pilotDecision.runtime_truth.pilot_denied_reason,
    internal_pilot: internalPilot,
    bridge_allowed: bridgeAllowed,
    bridge_denied_reason: bridgeAllowed ? '' : safeReason(bridgeDeniedReason || reason),
    access_layer_plan_mode: pilotDecision.runtime_truth.access_layer_plan_mode,
    provider_family: pilotDecision.runtime_truth.provider_family,
    provider_attempted: bridgeResult?.runtime_truth.provider_attempted === true,
    provider_succeeded: bridgeResult?.runtime_truth.provider_succeeded === true,
    provider_failed_reason: bridgeAllowed ? '' : safeReason(providerFailedReason),
    fallback_triggered: true,
    quota_allowed: pilotDecision.runtime_truth.quota_allowed,
    quota_exceeded: pilotDecision.runtime_truth.quota_exceeded,
    routing_allowed: pilotDecision.runtime_truth.routing_allowed,
    consent_state: pilotDecision.runtime_truth.consent_state,
    selected_adapter_id: pilotDecision.runtime_truth.selected_adapter_id,
    boundary_version: pilotDecision.runtime_truth.boundary_version,
    snapshot_version: pilotDecision.runtime_truth.snapshot_version,
    sanitized_output_present: false,
    raw_provider_payload_exposed: false,
  }
}

function sanitizeVisibleText(value: string | null): string {
  let sanitized = String(value || '')
  for (const pattern of SECRET_PATTERNS) {
    sanitized = sanitized.replace(pattern, '[redacted]')
  }
  return sanitized.trim()
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'internal_real_pilot_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModePilotInternalRealResult(value: unknown): value is FreeModePilotInternalRealResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_INTERNAL_REAL_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
