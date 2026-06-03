import {
  runFreeModeChatWiringHarness,
  type FreeModeChatWiringHarnessInput,
  type FreeModeChatWiringHarnessResult,
} from './freeModeChatWiringHarness'

export const FREE_MODE_CHAT_MOCKED_WIRING_VERSION = 'free_mode_chat_mocked_wiring_v1'
export const PUTER_FREE_CHAT_MOCKED_WIRING_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING'
export const FREE_MODE_CHAT_MOCKED_WIRING_OUTPUT = 'Omni Free chat mocked wiring response.'

const PUTER_PROVIDER_FAMILY = 'experimental_free_provider'
const UNKNOWN_VALUE = 'unknown'

const APPROVED_MOCKED_WIRING_RESULT_KEYS = new Set([
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
  'mock_provider_attempted',
  'mock_provider_succeeded',
  'consent_state',
  'sanitized_output_present',
  'raw_provider_payload_exposed',
  'should_use_normal_chat',
])

type MockedWiringMode = 'normal_chat' | 'mocked_free_chat'
type MockedWiringStatus =
  | 'denied_by_access_layer'
  | 'denied_by_allowlist'
  | 'denied_by_flag'
  | 'denied_by_quota'
  | 'denied_by_rollback'
  | 'denied_by_routing'
  | 'normal_chat_bypass'
  | 'provider_consent_or_auth_pending'
  | 'provider_succeeded_sanitized'

export type FreeModeChatMockedWiringInput = FreeModeChatWiringHarnessInput & {
  mockedWiringFeatureEnabled?: boolean
}

export type FreeModeChatMockedWiringRuntimeTruth = {
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
  provider_attempted: false
  provider_succeeded: false
  provider_failed_reason: string
  mock_provider_attempted: boolean
  mock_provider_succeeded: boolean
  consent_state: string
  sanitized_output_present: boolean
  raw_provider_payload_exposed: false
  should_use_normal_chat: boolean
}

export type FreeModeChatMockedWiringResult = {
  ok: boolean
  mode: MockedWiringMode
  should_use_normal_chat: boolean
  status: MockedWiringStatus
  reason: string
  user_message: string
  sanitized_output: string | null
  retry_allowed: boolean
  manual_action_required: boolean
  fallback_triggered: boolean
  runtime_truth: FreeModeChatMockedWiringRuntimeTruth
}

export function isPuterFreeChatMockedWiringFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function runFreeModeChatMockedWiring(
  input: FreeModeChatMockedWiringInput,
): FreeModeChatMockedWiringResult {
  if (input.mockedWiringFeatureEnabled !== true) {
    return normalChatBypass(input)
  }

  const harnessResult = runFreeModeChatWiringHarness(input)
  if (!harnessResult.ok) {
    return denied(harnessResult)
  }

  return {
    ok: true,
    mode: 'mocked_free_chat',
    should_use_normal_chat: false,
    status: 'provider_succeeded_sanitized',
    reason: 'mocked_wiring_allowed',
    user_message: 'Free chat mocked wiring completed with deterministic mock output.',
    sanitized_output: FREE_MODE_CHAT_MOCKED_WIRING_OUTPUT,
    retry_allowed: false,
    manual_action_required: false,
    fallback_triggered: false,
    runtime_truth: {
      ...runtimeTruthFromHarness(harnessResult, false),
      pilot_denied_reason: '',
      provider_failed_reason: '',
      mock_provider_attempted: true,
      mock_provider_succeeded: true,
      sanitized_output_present: true,
    },
  }
}

function normalChatBypass(input: FreeModeChatMockedWiringInput): FreeModeChatMockedWiringResult {
  return {
    ok: false,
    mode: 'normal_chat',
    should_use_normal_chat: true,
    status: 'normal_chat_bypass',
    reason: 'mocked_wiring_disabled',
    user_message: 'Mocked Free chat wiring is disabled. Use the normal chat path.',
    sanitized_output: null,
    retry_allowed: false,
    manual_action_required: false,
    fallback_triggered: false,
    runtime_truth: {
      access_layer_plan_mode: normalizePlanMode(input.planMode),
      pilot_enabled: false,
      pilot_eligible: false,
      pilot_denied_reason: 'mocked_wiring_disabled',
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
      mock_provider_attempted: false,
      mock_provider_succeeded: false,
      consent_state: normalizeConsentState(input.consentState),
      sanitized_output_present: false,
      raw_provider_payload_exposed: false,
      should_use_normal_chat: true,
    },
  }
}

function denied(harnessResult: FreeModeChatWiringHarnessResult): FreeModeChatMockedWiringResult {
  return {
    ok: false,
    mode: 'mocked_free_chat',
    should_use_normal_chat: false,
    status: normalizeHarnessStatus(harnessResult.status),
    reason: safeReason(harnessResult.reason),
    user_message: harnessResult.user_message,
    sanitized_output: null,
    retry_allowed: harnessResult.retry_allowed,
    manual_action_required: harnessResult.manual_action_required,
    fallback_triggered: true,
    runtime_truth: runtimeTruthFromHarness(harnessResult, false),
  }
}

function runtimeTruthFromHarness(
  harnessResult: FreeModeChatWiringHarnessResult,
  shouldUseNormalChat: boolean,
): FreeModeChatMockedWiringRuntimeTruth {
  return {
    access_layer_plan_mode: harnessResult.runtime_truth.access_layer_plan_mode,
    pilot_enabled: harnessResult.runtime_truth.pilot_enabled,
    pilot_eligible: harnessResult.runtime_truth.pilot_eligible,
    pilot_denied_reason: harnessResult.runtime_truth.pilot_denied_reason,
    allowlisted_pilot: harnessResult.runtime_truth.allowlisted_pilot,
    allowlist_required: harnessResult.runtime_truth.allowlist_required,
    allowlist_matched: harnessResult.runtime_truth.allowlist_matched,
    rollback_active: harnessResult.runtime_truth.rollback_active,
    quota_allowed: harnessResult.runtime_truth.quota_allowed,
    quota_exceeded: harnessResult.runtime_truth.quota_exceeded,
    routing_allowed: harnessResult.runtime_truth.routing_allowed,
    provider_family: harnessResult.runtime_truth.provider_family,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: harnessResult.runtime_truth.provider_failed_reason,
    mock_provider_attempted: harnessResult.runtime_truth.mock_provider_attempted,
    mock_provider_succeeded: harnessResult.runtime_truth.mock_provider_succeeded,
    consent_state: harnessResult.runtime_truth.consent_state,
    sanitized_output_present: harnessResult.runtime_truth.sanitized_output_present,
    raw_provider_payload_exposed: false,
    should_use_normal_chat: shouldUseNormalChat,
  }
}

function normalizeHarnessStatus(status: string): MockedWiringStatus {
  switch (status) {
    case 'denied_by_allowlist':
    case 'denied_by_flag':
    case 'denied_by_quota':
    case 'denied_by_rollback':
    case 'denied_by_routing':
    case 'provider_consent_or_auth_pending':
    case 'provider_succeeded_sanitized':
      return status
    default:
      return 'denied_by_access_layer'
  }
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
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'mocked_wiring_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModeChatMockedWiringResult(value: unknown): value is FreeModeChatMockedWiringResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_MOCKED_WIRING_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
