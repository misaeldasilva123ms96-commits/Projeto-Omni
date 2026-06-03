import {
  runFreeModePilotAllowlisted,
  type FreeModePilotAllowlistedInput,
  type FreeModePilotAllowlistedResult,
} from './freeModePilotAllowlisted'

export const FREE_MODE_CHAT_INTERNAL_ALLOWLISTED_WIRING_VERSION = 'free_mode_chat_internal_allowlisted_wiring_v1'
export const PUTER_FREE_CHAT_INTERNAL_WIRING_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING'

const PUTER_PROVIDER_FAMILY = 'experimental_free_provider'
const UNKNOWN_VALUE = 'unknown'

const APPROVED_INTERNAL_WIRING_RESULT_KEYS = new Set([
  'ok',
  'mode',
  'should_use_normal_chat',
  'status',
  'reason',
  'user_message',
  'sanitized_output',
  'retry_allowed',
  'manual_action_required',
  'fallback_triggered',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'access_layer_plan_mode',
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'allowlisted_pilot',
  'allowlist_required',
  'allowlist_matched',
  'rollback_active',
  'quota_allowed',
  'quota_exceeded',
  'routing_allowed',
  'provider_family',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'consent_state',
  'sanitized_output_present',
  'raw_provider_payload_exposed',
  'should_use_normal_chat',
  'internal_allowlisted_wiring_enabled',
])

type InternalWiringMode = 'normal_chat' | 'internal_allowlisted_free_chat'
type InternalWiringStatus =
  | 'denied_by_access_layer'
  | 'denied_by_allowlist'
  | 'denied_by_flag'
  | 'denied_by_quota'
  | 'denied_by_rollback'
  | 'denied_by_routing'
  | 'normal_chat_bypass'
  | 'provider_consent_or_auth_pending'
  | 'provider_failed_safe'
  | 'provider_succeeded_sanitized'

export type FreeModeChatInternalAllowlistedWiringInput = FreeModePilotAllowlistedInput & {
  internalWiringFeatureEnabled?: boolean
  messageSummary?: unknown
  promptSummary?: unknown
}

export type FreeModeChatInternalAllowlistedWiringRuntimeTruth = {
  access_layer_plan_mode: string
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  allowlisted_pilot: boolean
  allowlist_required: boolean
  allowlist_matched: boolean
  rollback_active: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  provider_family: string
  provider_attempted: boolean
  provider_succeeded: boolean
  provider_failed_reason: string
  consent_state: string
  sanitized_output_present: boolean
  raw_provider_payload_exposed: false
  should_use_normal_chat: boolean
  internal_allowlisted_wiring_enabled: boolean
}

export type FreeModeChatInternalAllowlistedWiringResult = {
  ok: boolean
  mode: InternalWiringMode
  should_use_normal_chat: boolean
  status: InternalWiringStatus
  reason: string
  user_message: string
  sanitized_output: string | null
  retry_allowed: boolean
  manual_action_required: boolean
  fallback_triggered: boolean
  runtime_truth: FreeModeChatInternalAllowlistedWiringRuntimeTruth
}

export function isPuterFreeChatInternalWiringFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export async function runFreeModeChatInternalAllowlistedWiring(
  input: FreeModeChatInternalAllowlistedWiringInput,
): Promise<FreeModeChatInternalAllowlistedWiringResult> {
  if (input.internalWiringFeatureEnabled !== true) {
    return normalChatBypass(input)
  }

  const allowlistedResult = await runFreeModePilotAllowlisted({
    ...input,
    allowlistRequired: true,
  })

  if (!allowlistedResult.allowed) {
    return denied(allowlistedResult)
  }

  return {
    ok: true,
    mode: 'internal_allowlisted_free_chat',
    should_use_normal_chat: false,
    status: 'provider_succeeded_sanitized',
    reason: 'internal_allowlisted_wiring_allowed',
    user_message: 'Internal allowlisted Free chat wiring completed with sanitized output.',
    sanitized_output: sanitizeOutput(allowlistedResult.sanitized_output),
    retry_allowed: false,
    manual_action_required: false,
    fallback_triggered: false,
    runtime_truth: {
      ...runtimeTruthFromAllowlisted(allowlistedResult, false, true),
      pilot_denied_reason: '',
      provider_failed_reason: '',
      sanitized_output_present: Boolean(sanitizeOutput(allowlistedResult.sanitized_output)),
    },
  }
}

function normalChatBypass(
  input: FreeModeChatInternalAllowlistedWiringInput,
): FreeModeChatInternalAllowlistedWiringResult {
  return {
    ok: false,
    mode: 'normal_chat',
    should_use_normal_chat: true,
    status: 'normal_chat_bypass',
    reason: 'internal_wiring_disabled',
    user_message: 'Internal allowlisted Free chat wiring is disabled. Use the normal chat path.',
    sanitized_output: null,
    retry_allowed: false,
    manual_action_required: false,
    fallback_triggered: false,
    runtime_truth: {
      access_layer_plan_mode: normalizePlanMode(input.planMode),
      pilot_enabled: false,
      pilot_eligible: false,
      pilot_denied_reason: 'internal_wiring_disabled',
      allowlisted_pilot: false,
      allowlist_required: input.allowlistRequired === true,
      allowlist_matched: input.allowlistMatched === true,
      rollback_active: input.rollbackActive === true,
      quota_allowed: input.quotaAllowed === true,
      quota_exceeded: input.quotaExceeded === true,
      routing_allowed: input.routingAllowed === true,
      provider_family: normalizeProviderFamily(input.selectedProviderFamily),
      provider_attempted: false,
      provider_succeeded: false,
      provider_failed_reason: '',
      consent_state: normalizeConsentState(input.consentState),
      sanitized_output_present: false,
      raw_provider_payload_exposed: false,
      should_use_normal_chat: true,
      internal_allowlisted_wiring_enabled: false,
    },
  }
}

function denied(
  allowlistedResult: FreeModePilotAllowlistedResult,
): FreeModeChatInternalAllowlistedWiringResult {
  const status = statusForReason(allowlistedResult.reason, allowlistedResult.runtime_truth.provider_attempted)
  return {
    ok: false,
    mode: 'internal_allowlisted_free_chat',
    should_use_normal_chat: shouldFallbackToNormalChat(status),
    status,
    reason: safeReason(allowlistedResult.reason),
    user_message: safeUserMessage(status),
    sanitized_output: null,
    retry_allowed: status === 'provider_consent_or_auth_pending',
    manual_action_required: status === 'provider_consent_or_auth_pending',
    fallback_triggered: true,
    runtime_truth: runtimeTruthFromAllowlisted(
      allowlistedResult,
      shouldFallbackToNormalChat(status),
      true,
    ),
  }
}

function runtimeTruthFromAllowlisted(
  allowlistedResult: FreeModePilotAllowlistedResult,
  shouldUseNormalChat: boolean,
  internalWiringEnabled: boolean,
): FreeModeChatInternalAllowlistedWiringRuntimeTruth {
  return {
    access_layer_plan_mode: allowlistedResult.runtime_truth.access_layer_plan_mode,
    pilot_enabled: allowlistedResult.runtime_truth.pilot_enabled,
    pilot_eligible: allowlistedResult.runtime_truth.pilot_eligible,
    pilot_denied_reason: allowlistedResult.runtime_truth.pilot_denied_reason,
    allowlisted_pilot: allowlistedResult.runtime_truth.allowlisted_pilot,
    allowlist_required: allowlistedResult.runtime_truth.allowlist_required,
    allowlist_matched: allowlistedResult.runtime_truth.allowlist_matched,
    rollback_active: allowlistedResult.runtime_truth.rollback_active,
    quota_allowed: allowlistedResult.runtime_truth.quota_allowed,
    quota_exceeded: allowlistedResult.runtime_truth.quota_exceeded,
    routing_allowed: allowlistedResult.runtime_truth.routing_allowed,
    provider_family: allowlistedResult.runtime_truth.provider_family,
    provider_attempted: allowlistedResult.runtime_truth.provider_attempted,
    provider_succeeded: allowlistedResult.runtime_truth.provider_succeeded,
    provider_failed_reason: allowlistedResult.runtime_truth.provider_failed_reason,
    consent_state: allowlistedResult.runtime_truth.consent_state,
    sanitized_output_present: allowlistedResult.runtime_truth.sanitized_output_present,
    raw_provider_payload_exposed: false,
    should_use_normal_chat: shouldUseNormalChat,
    internal_allowlisted_wiring_enabled: internalWiringEnabled,
  }
}

function statusForReason(reason: string, providerAttempted: boolean): InternalWiringStatus {
  switch (safeReason(reason)) {
    case 'allowlist_not_matched':
      return 'denied_by_allowlist'
    case 'rollback_active':
      return 'denied_by_rollback'
    case 'quota_exceeded':
      return 'denied_by_quota'
    case 'routing_denied':
      return 'denied_by_routing'
    case 'provider_consent_or_auth_pending':
      return 'provider_consent_or_auth_pending'
    case 'feature_disabled':
    case 'chat_bridge_disabled':
    case 'dev_real_bridge_disabled':
    case 'pilot_flag_disabled':
    case 'internal_pilot_disabled':
    case 'allowlisted_pilot_disabled':
      return 'denied_by_flag'
    default:
      return providerAttempted ? 'provider_failed_safe' : 'denied_by_access_layer'
  }
}

function shouldFallbackToNormalChat(status: InternalWiringStatus): boolean {
  return status !== 'provider_consent_or_auth_pending' && status !== 'provider_failed_safe'
}

function safeUserMessage(status: InternalWiringStatus): string {
  switch (status) {
    case 'denied_by_allowlist':
      return 'This session is not included in the internal Free chat pilot allowlist. No provider call was made.'
    case 'denied_by_flag':
      return 'Internal allowlisted Free chat wiring is disabled by feature flags. No provider call was made.'
    case 'denied_by_quota':
      return 'The Access Layer quota gate denied this pilot request. No provider call was made.'
    case 'denied_by_rollback':
      return 'The internal Free chat pilot is paused by rollback controls. No provider call was made.'
    case 'denied_by_routing':
      return 'The Access Layer routing gate denied this pilot request. No provider call was made.'
    case 'provider_consent_or_auth_pending':
      return 'Provider consent or authentication is pending. No successful provider response was produced.'
    case 'provider_failed_safe':
      return 'The provider request did not complete safely. Omni recorded only a safe failure state.'
    default:
      return 'Internal allowlisted Free chat wiring denied this request safely.'
  }
}

function sanitizeOutput(value: string | null): string | null {
  const sanitized = String(value || '').trim()
  return sanitized ? sanitized : null
}

function normalizePlanMode(value: unknown): string {
  return typeof value === 'string' && value.trim().toLowerCase() === 'free' ? 'free' : UNKNOWN_VALUE
}

function normalizeProviderFamily(value: unknown): string {
  return value === PUTER_PROVIDER_FAMILY ? PUTER_PROVIDER_FAMILY : ''
}

function normalizeConsentState(value: unknown): string {
  const normalized = typeof value === 'string' ? value.trim().toLowerCase() : ''
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : UNKNOWN_VALUE
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'internal_allowlisted_wiring_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModeChatInternalAllowlistedWiringResult(
  value: unknown,
): value is FreeModeChatInternalAllowlistedWiringResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_INTERNAL_WIRING_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
