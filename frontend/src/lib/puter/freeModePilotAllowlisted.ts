import {
  runFreeModePilotInternalReal,
  type FreeModePilotInternalRealInput,
  type FreeModePilotInternalRealResult,
} from './freeModePilotInternalReal'
import {
  decideFreeModePilotFlag,
  type FreeModePilotFlagContractInput,
  type FreeModePilotFlagDecision,
} from './freeModePilotFlagContract'

export const FREE_MODE_PILOT_ALLOWLISTED_VERSION = 'free_mode_pilot_allowlisted_v2'
export const PUTER_FREE_PILOT_ALLOWLISTED_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED'

const APPROVED_ALLOWLISTED_RESULT_KEYS = new Set([
  'allowlisted_pilot_version',
  'allowed',
  'denied',
  'reason',
  'allowlisted_pilot',
  'pilot_enabled',
  'pilot_eligible',
  'provider_family',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'allowlisted_pilot',
  'allowlist_required',
  'allowlist_matched',
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'rollback_active',
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

export type FreeModePilotAllowlistedInput = FreeModePilotFlagContractInput
  & FreeModePilotInternalRealInput
  & {
    allowlistedPilotFeatureEnabled?: boolean
    allowlistMatched?: boolean
  }

export type FreeModePilotAllowlistedRuntimeTruth = {
  allowlisted_pilot: boolean
  allowlist_required: true
  allowlist_matched: boolean
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  rollback_active: boolean
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

export type FreeModePilotAllowlistedResult = {
  allowlisted_pilot_version: typeof FREE_MODE_PILOT_ALLOWLISTED_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  allowlisted_pilot: boolean
  pilot_enabled: boolean
  pilot_eligible: boolean
  provider_family: string
  fallback_required: boolean
  sanitized_output: string | null
  runtime_truth: FreeModePilotAllowlistedRuntimeTruth
}

export function isPuterFreePilotAllowlistedFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export async function runFreeModePilotAllowlisted(
  input: FreeModePilotAllowlistedInput,
): Promise<FreeModePilotAllowlistedResult> {
  const pilotDecision = decideFreeModePilotFlag({
    ...input,
    allowlistRequired: true,
  })

  if (input.allowlistedPilotFeatureEnabled !== true) {
    return denied('allowlisted_pilot_disabled', pilotDecision, false)
  }

  if (input.allowlistMatched !== true) {
    return denied('allowlist_not_matched', pilotDecision, false)
  }

  if (!pilotDecision.pilot_eligible) {
    return denied(pilotDecision.reason, pilotDecision, false)
  }

  const internalResult = await runFreeModePilotInternalReal({
    ...input,
    allowlistRequired: true,
    allowlistMatched: true,
  })

  if (!internalResult.allowed) {
    return denied(internalResult.reason, pilotDecision, true, internalResult)
  }

  return allowed(pilotDecision, internalResult)
}

function allowed(
  pilotDecision: FreeModePilotFlagDecision,
  internalResult: FreeModePilotInternalRealResult,
): FreeModePilotAllowlistedResult {
  const sanitizedOutput = sanitizeVisibleText(internalResult.sanitized_output)
  return {
    ...baseResult('allowlisted_pilot_ok', pilotDecision, true),
    allowed: true,
    denied: false,
    fallback_required: false,
    sanitized_output: sanitizedOutput,
    runtime_truth: {
      ...baseRuntimeTruth('', pilotDecision, true, internalResult),
      pilot_denied_reason: '',
      provider_failed_reason: '',
      fallback_triggered: false,
      sanitized_output_present: Boolean(sanitizedOutput),
    },
  }
}

function denied(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  allowlistedPilot: boolean,
  internalResult?: FreeModePilotInternalRealResult,
): FreeModePilotAllowlistedResult {
  return {
    ...baseResult(reason, pilotDecision, allowlistedPilot),
    allowed: false,
    denied: true,
    fallback_required: true,
    sanitized_output: null,
    runtime_truth: baseRuntimeTruth(reason, pilotDecision, allowlistedPilot, internalResult),
  }
}

function baseResult(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  allowlistedPilot: boolean,
): Omit<FreeModePilotAllowlistedResult, 'allowed' | 'denied' | 'fallback_required' | 'sanitized_output' | 'runtime_truth'> {
  return {
    allowlisted_pilot_version: FREE_MODE_PILOT_ALLOWLISTED_VERSION,
    reason: safeReason(reason),
    allowlisted_pilot: allowlistedPilot,
    pilot_enabled: pilotDecision.pilot_enabled,
    pilot_eligible: pilotDecision.pilot_eligible,
    provider_family: pilotDecision.provider_family,
  }
}

function baseRuntimeTruth(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  allowlistedPilot: boolean,
  internalResult?: FreeModePilotInternalRealResult,
): FreeModePilotAllowlistedRuntimeTruth {
  const safe = safeReason(reason)
  const providerFailedReason = internalResult?.runtime_truth.provider_failed_reason || safe
  return {
    allowlisted_pilot: allowlistedPilot,
    allowlist_required: true,
    allowlist_matched: pilotDecision.allowlist_matched,
    pilot_enabled: pilotDecision.runtime_truth.pilot_enabled,
    pilot_eligible: pilotDecision.runtime_truth.pilot_eligible,
    pilot_denied_reason: reason ? safe : pilotDecision.runtime_truth.pilot_denied_reason,
    rollback_active: pilotDecision.rollback_active,
    access_layer_plan_mode: pilotDecision.runtime_truth.access_layer_plan_mode,
    provider_family: pilotDecision.runtime_truth.provider_family,
    provider_attempted: internalResult?.runtime_truth.provider_attempted === true,
    provider_succeeded: internalResult?.runtime_truth.provider_succeeded === true,
    provider_failed_reason: reason ? safeReason(providerFailedReason) : '',
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
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'allowlisted_pilot_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModePilotAllowlistedResult(value: unknown): value is FreeModePilotAllowlistedResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_ALLOWLISTED_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
