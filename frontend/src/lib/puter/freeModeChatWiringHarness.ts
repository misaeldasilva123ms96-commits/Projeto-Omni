import {
  decideFreeModePilotFlag,
  type FreeModePilotFlagContractInput,
  type FreeModePilotFlagDecision,
} from './freeModePilotFlagContract'
import {
  runFreeModePilotMock,
  type FreeModePilotMockInput,
  type FreeModePilotMockResult,
} from './freeModePilotMock'

export const FREE_MODE_CHAT_WIRING_HARNESS_VERSION = 'free_mode_chat_wiring_harness_v1'
export const FREE_MODE_CHAT_WIRING_HARNESS_OUTPUT = 'Omni Free chat wiring harness mock response.'

const APPROVED_HARNESS_RESULT_KEYS = new Set([
  'ok',
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
  'mock_provider_attempted',
  'mock_provider_succeeded',
  'consent_state',
  'sanitized_output_present',
  'raw_provider_payload_exposed',
])

type ResultStatus =
  | 'denied_by_access_layer'
  | 'denied_by_allowlist'
  | 'denied_by_flag'
  | 'denied_by_quota'
  | 'denied_by_rollback'
  | 'denied_by_routing'
  | 'fallback_used'
  | 'provider_consent_or_auth_pending'
  | 'provider_succeeded_sanitized'

export type FreeModeChatWiringHarnessInput = FreeModePilotFlagContractInput
  & FreeModePilotMockInput
  & {
    allowlistedPilotFeatureEnabled?: boolean
    messageSummary?: unknown
    promptSummary?: unknown
  }

export type FreeModeChatWiringHarnessRuntimeTruth = {
  access_layer_plan_mode: string
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  allowlisted_pilot: boolean
  allowlist_required: true
  allowlist_matched: boolean
  rollback_active: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  provider_family: string
  provider_attempted: false
  provider_succeeded: false
  provider_failed_reason: string
  mock_provider_attempted: boolean
  mock_provider_succeeded: boolean
  consent_state: string
  sanitized_output_present: boolean
  raw_provider_payload_exposed: false
}

export type FreeModeChatWiringHarnessResult = {
  ok: boolean
  status: ResultStatus
  reason: string
  user_message: string
  sanitized_output: string | null
  retry_allowed: boolean
  manual_action_required: boolean
  fallback_triggered: boolean
  runtime_truth: FreeModeChatWiringHarnessRuntimeTruth
}

export function runFreeModeChatWiringHarness(
  input: FreeModeChatWiringHarnessInput,
): FreeModeChatWiringHarnessResult {
  const pilotInput = withHarnessPilotDefaults(input)
  const pilotDecision = decideFreeModePilotFlag(pilotInput)

  if (!pilotDecision.pilot_eligible) {
    return denied(pilotDecision.reason, statusForDeniedReason(pilotDecision.reason), pilotDecision)
  }

  if (input.allowlistedPilotFeatureEnabled !== true) {
    return denied('allowlisted_pilot_disabled', 'denied_by_flag', pilotDecision)
  }

  if (pilotInput.allowlistMatched !== true) {
    return denied('allowlist_not_matched', 'denied_by_allowlist', pilotDecision)
  }

  const mockResult = runFreeModePilotMock({
    ...pilotInput,
    mockPrompt: undefined,
  })

  if (!mockResult.allowed) {
    return denied(mockResult.reason, statusForDeniedReason(mockResult.reason), pilotDecision, mockResult)
  }

  return {
    ok: true,
    status: 'provider_succeeded_sanitized',
    reason: 'mock_wiring_allowed',
    user_message: 'Free chat wiring harness completed with deterministic mock output.',
    sanitized_output: FREE_MODE_CHAT_WIRING_HARNESS_OUTPUT,
    retry_allowed: false,
    manual_action_required: false,
    fallback_triggered: false,
    runtime_truth: {
      ...baseRuntimeTruth('', pilotDecision, true, mockResult),
      pilot_denied_reason: '',
      provider_failed_reason: '',
      mock_provider_attempted: true,
      mock_provider_succeeded: true,
      sanitized_output_present: true,
    },
  }
}

function withHarnessPilotDefaults(
  input: FreeModeChatWiringHarnessInput,
): FreeModeChatWiringHarnessInput & { allowlistRequired: true } {
  return {
    ...input,
    allowlistRequired: true,
  }
}

function denied(
  reason: string,
  status: ResultStatus,
  pilotDecision: FreeModePilotFlagDecision,
  mockResult?: FreeModePilotMockResult,
): FreeModeChatWiringHarnessResult {
  const safe = safeReason(reason)
  return {
    ok: false,
    status,
    reason: safe,
    user_message: safeUserMessage(status),
    sanitized_output: null,
    retry_allowed: retryAllowedForStatus(status),
    manual_action_required: manualActionRequiredForStatus(status),
    fallback_triggered: true,
    runtime_truth: baseRuntimeTruth(safe, pilotDecision, false, mockResult),
  }
}

function baseRuntimeTruth(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  allowlistedPilot: boolean,
  mockResult?: FreeModePilotMockResult,
): FreeModeChatWiringHarnessRuntimeTruth {
  const safe = safeReason(reason)
  const mockTruth = mockResult?.runtime_truth
  return {
    access_layer_plan_mode: pilotDecision.runtime_truth.access_layer_plan_mode,
    pilot_enabled: pilotDecision.runtime_truth.pilot_enabled,
    pilot_eligible: pilotDecision.runtime_truth.pilot_eligible,
    pilot_denied_reason: reason ? safe : pilotDecision.runtime_truth.pilot_denied_reason,
    allowlisted_pilot: allowlistedPilot,
    allowlist_required: true,
    allowlist_matched: pilotDecision.allowlist_matched,
    rollback_active: pilotDecision.rollback_active,
    quota_allowed: pilotDecision.runtime_truth.quota_allowed,
    quota_exceeded: pilotDecision.runtime_truth.quota_exceeded,
    routing_allowed: pilotDecision.runtime_truth.routing_allowed,
    provider_family: pilotDecision.runtime_truth.provider_family,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: reason ? safe : '',
    mock_provider_attempted: mockTruth?.mock_provider_attempted === true,
    mock_provider_succeeded: mockTruth?.mock_provider_succeeded === true,
    consent_state: pilotDecision.runtime_truth.consent_state,
    sanitized_output_present: false,
    raw_provider_payload_exposed: false,
  }
}

function statusForDeniedReason(reason: string): ResultStatus {
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
    case 'mock_bridge_disabled':
      return 'denied_by_flag'
    default:
      return 'denied_by_access_layer'
  }
}

function safeUserMessage(status: ResultStatus): string {
  switch (status) {
    case 'denied_by_allowlist':
      return 'This session is not included in the Free chat pilot allowlist. No provider call was made.'
    case 'denied_by_flag':
      return 'The Free chat pilot wiring harness is disabled by feature flags. No provider call was made.'
    case 'denied_by_quota':
      return 'The Access Layer quota gate denied this pilot request. No provider call was made.'
    case 'denied_by_rollback':
      return 'The Free chat pilot is paused by rollback controls. No provider call was made.'
    case 'denied_by_routing':
      return 'The Access Layer routing gate denied this pilot request. No provider call was made.'
    case 'provider_consent_or_auth_pending':
      return 'Provider consent or authentication is pending. The harness did not produce a successful provider result.'
    default:
      return 'The Free chat pilot wiring harness denied this request safely. No provider call was made.'
  }
}

function retryAllowedForStatus(status: ResultStatus): boolean {
  return status === 'provider_consent_or_auth_pending' || status === 'fallback_used'
}

function manualActionRequiredForStatus(status: ResultStatus): boolean {
  return status === 'provider_consent_or_auth_pending'
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'wiring_harness_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModeChatWiringHarnessResult(value: unknown): value is FreeModeChatWiringHarnessResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_HARNESS_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
