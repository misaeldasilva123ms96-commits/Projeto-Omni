import {
  decideFreeModeChatBridge,
  type FreeModeChatBridgeInput,
} from './freeModeChatBridgeContract'
import {
  runFreeModeChatBridgeMock,
  type FreeModeChatBridgeMockInput,
} from './freeModeChatBridgeMock'
import {
  decideFreeModePilotFlag,
  type FreeModePilotFlagContractInput,
  type FreeModePilotFlagDecision,
} from './freeModePilotFlagContract'

export const FREE_MODE_PILOT_MOCK_VERSION = 'free_mode_pilot_mock_v1'
export const FREE_MODE_PILOT_MOCK_OUTPUT = 'Omni Free pilot mock response.'

const APPROVED_PILOT_MOCK_RESULT_KEYS = new Set([
  'pilot_mock_version',
  'allowed',
  'denied',
  'reason',
  'mock_only',
  'pilot_enabled',
  'pilot_eligible',
  'bridge_allowed',
  'mock_provider_succeeded',
  'provider_family',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'bridge_allowed',
  'bridge_denied_reason',
  'access_layer_plan_mode',
  'provider_family',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'mock_provider_attempted',
  'mock_provider_succeeded',
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

export type FreeModePilotMockInput = FreeModePilotFlagContractInput
  & FreeModeChatBridgeInput
  & Pick<FreeModeChatBridgeMockInput, 'mockFeatureEnabled' | 'mockPrompt'>

export type FreeModePilotMockRuntimeTruth = {
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  bridge_allowed: boolean
  bridge_denied_reason: string
  access_layer_plan_mode: string
  provider_family: string
  provider_attempted: false
  provider_succeeded: false
  provider_failed_reason: string
  mock_provider_attempted: boolean
  mock_provider_succeeded: boolean
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

export type FreeModePilotMockResult = {
  pilot_mock_version: typeof FREE_MODE_PILOT_MOCK_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  mock_only: true
  pilot_enabled: boolean
  pilot_eligible: boolean
  bridge_allowed: boolean
  mock_provider_succeeded: boolean
  provider_family: string
  fallback_required: boolean
  sanitized_output: string | null
  runtime_truth: FreeModePilotMockRuntimeTruth
}

export function runFreeModePilotMock(input: FreeModePilotMockInput): FreeModePilotMockResult {
  const pilotDecision = decideFreeModePilotFlag(input)

  if (!pilotDecision.pilot_eligible) {
    return denied(pilotDecision.reason, pilotDecision, null)
  }

  const bridgeDecision = decideFreeModeChatBridge(input)
  if (!bridgeDecision.allowed) {
    return denied(bridgeDecision.reason, pilotDecision, bridgeDecision.reason)
  }

  const mockResult = runFreeModeChatBridgeMock(input)
  if (!mockResult.allowed) {
    return denied(mockResult.reason, pilotDecision, mockResult.reason)
  }

  return {
    ...baseResult('mock_pilot_allowed', pilotDecision, true),
    allowed: true,
    denied: false,
    mock_provider_succeeded: true,
    fallback_required: false,
    sanitized_output: FREE_MODE_PILOT_MOCK_OUTPUT,
    runtime_truth: {
      ...baseRuntimeTruth('', pilotDecision, true),
      bridge_denied_reason: '',
      mock_provider_attempted: true,
      mock_provider_succeeded: true,
      fallback_triggered: false,
      sanitized_output_present: true,
    },
  }
}

function denied(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  bridgeDeniedReason: string | null,
): FreeModePilotMockResult {
  const safeBridgeReason = bridgeDeniedReason ?? ''
  return {
    ...baseResult(reason, pilotDecision, false),
    allowed: false,
    denied: true,
    fallback_required: true,
    sanitized_output: null,
    runtime_truth: baseRuntimeTruth(reason, pilotDecision, false, safeBridgeReason),
  }
}

function baseResult(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  bridgeAllowed: boolean,
): Omit<FreeModePilotMockResult, 'allowed' | 'denied' | 'fallback_required' | 'sanitized_output' | 'runtime_truth'> {
  return {
    pilot_mock_version: FREE_MODE_PILOT_MOCK_VERSION,
    reason: safeReason(reason),
    mock_only: true,
    pilot_enabled: pilotDecision.pilot_enabled,
    pilot_eligible: pilotDecision.pilot_eligible,
    bridge_allowed: bridgeAllowed,
    mock_provider_succeeded: false,
    provider_family: pilotDecision.provider_family,
  }
}

function baseRuntimeTruth(
  reason: string,
  pilotDecision: FreeModePilotFlagDecision,
  bridgeAllowed: boolean,
  bridgeDeniedReason = reason,
): FreeModePilotMockRuntimeTruth {
  const safe = safeReason(reason)
  const safeBridgeReason = bridgeAllowed ? '' : safeReason(bridgeDeniedReason || reason)
  return {
    pilot_enabled: pilotDecision.runtime_truth.pilot_enabled,
    pilot_eligible: pilotDecision.runtime_truth.pilot_eligible,
    pilot_denied_reason: pilotDecision.runtime_truth.pilot_denied_reason,
    bridge_allowed: bridgeAllowed,
    bridge_denied_reason: safeBridgeReason,
    access_layer_plan_mode: pilotDecision.runtime_truth.access_layer_plan_mode,
    provider_family: pilotDecision.runtime_truth.provider_family,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: '',
    mock_provider_attempted: false,
    mock_provider_succeeded: false,
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

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'pilot_mock_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModePilotMockResult(value: unknown): value is FreeModePilotMockResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_PILOT_MOCK_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
