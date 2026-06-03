import {
  decideFreeModeChatBridge,
  type FreeModeChatBridgeDecision,
  type FreeModeChatBridgeInput,
  type FreeModeChatBridgeRuntimeTruth,
} from './freeModeChatBridgeContract'

export const FREE_MODE_CHAT_BRIDGE_MOCK_VERSION = 'free_mode_chat_bridge_mock_v1'
export const PUTER_CHAT_BRIDGE_MOCK_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK'
export const FREE_MODE_CHAT_BRIDGE_MOCK_OUTPUT = 'Omni Free mock bridge response.'

const APPROVED_MOCK_RESULT_KEYS = new Set([
  'mock_bridge_version',
  'allowed',
  'denied',
  'reason',
  'mock_enabled',
  'mock_succeeded',
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

export type FreeModeChatBridgeMockInput = FreeModeChatBridgeInput & {
  mockFeatureEnabled?: boolean
  mockPrompt?: unknown
}

export type FreeModeChatBridgeMockResult = {
  mock_bridge_version: typeof FREE_MODE_CHAT_BRIDGE_MOCK_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  mock_enabled: boolean
  mock_succeeded: boolean
  provider_family: string
  adapter_id: string
  fallback_required: boolean
  sanitized_output: string | null
  runtime_truth: FreeModeChatBridgeRuntimeTruth
}

export function isPuterChatBridgeMockFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function runFreeModeChatBridgeMock(input: FreeModeChatBridgeMockInput): FreeModeChatBridgeMockResult {
  const decision = decideFreeModeChatBridge(input)
  const mockEnabled = input.mockFeatureEnabled === true

  if (!mockEnabled) {
    return denied('mock_bridge_disabled', decision, mockEnabled)
  }

  if (hasMockInputValue(input.mockPrompt)) {
    return denied('unsafe_mock_input', decision, mockEnabled)
  }

  if (!decision.allowed) {
    return denied(decision.reason, decision, mockEnabled)
  }

  return {
    ...baseResult('mock_allowed', decision, mockEnabled),
    allowed: true,
    denied: false,
    mock_succeeded: true,
    fallback_required: false,
    sanitized_output: FREE_MODE_CHAT_BRIDGE_MOCK_OUTPUT,
  }
}

function denied(
  reason: string,
  decision: FreeModeChatBridgeDecision,
  mockEnabled: boolean,
): FreeModeChatBridgeMockResult {
  return {
    ...baseResult(reason, decision, mockEnabled),
    allowed: false,
    denied: true,
    mock_succeeded: false,
    fallback_required: true,
    sanitized_output: null,
  }
}

function baseResult(
  reason: string,
  decision: FreeModeChatBridgeDecision,
  mockEnabled: boolean,
): Omit<FreeModeChatBridgeMockResult, 'allowed' | 'denied' | 'mock_succeeded' | 'fallback_required' | 'sanitized_output'> {
  return {
    mock_bridge_version: FREE_MODE_CHAT_BRIDGE_MOCK_VERSION,
    reason: safeReason(reason),
    mock_enabled: mockEnabled,
    provider_family: decision.provider_family,
    adapter_id: decision.adapter_id,
    runtime_truth: decision.runtime_truth,
  }
}

function hasMockInputValue(value: unknown): boolean {
  if (value === undefined || value === null || value === '') {
    return false
  }
  return true
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'mock_bridge_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModeChatBridgeMockResult(value: unknown): value is FreeModeChatBridgeMockResult {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_MOCK_RESULT_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
