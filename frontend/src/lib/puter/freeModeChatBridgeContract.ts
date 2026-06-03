import {
  PUTER_BROWSER_ADAPTER_ID,
  PUTER_PROVIDER_FAMILY,
} from './freeModePuterBrowserAdapter'

export const FREE_MODE_CHAT_BRIDGE_VERSION = 'free_mode_chat_bridge_contract_v1'
export const PUTER_CHAT_BRIDGE_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE'

const ACCESS_SNAPSHOT_BOUNDARY_VERSION = 'access_snapshot_boundary_v1'
const PUBLIC_ACCESS_SNAPSHOT_VERSION = 'public_access_snapshot_v1'
const EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID = 'experimental_free_adapter'
const UNKNOWN_PLAN_MODE = 'unknown'

const APPROVED_DECISION_KEYS = new Set([
  'bridge_version',
  'allowed',
  'denied',
  'reason',
  'plan_mode',
  'provider_family',
  'adapter_id',
  'quota_allowed',
  'quota_exceeded',
  'routing_allowed',
  'feature_flag_allowed',
  'runtime_allowed',
  'puter_runtime_required',
  'fallback_required',
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

const APPROVED_ENVELOPE_KEYS = new Set([
  'ok',
  'access_snapshot',
  'denied',
  'reason',
  'snapshot_version',
  'boundary_version',
])

const APPROVED_SNAPSHOT_KEYS = new Set([
  'snapshot_version',
  'plan_mode',
  'provider_mode',
  'subject_id',
  'usage_date',
  'tokens_in',
  'tokens_out',
  'tokens_total',
  'daily_token_limit',
  'quota_remaining',
  'quota_exceeded',
  'input_allowed',
  'output_allowed',
  'quota_allowed',
  'routing_allowed',
  'fallback_allowed',
  'selected_provider_family',
  'selected_adapter_id',
  'adapter_display_name',
  'adapter_capabilities',
  'decision_reason',
])

const APPROVED_CAPABILITY_KEYS = new Set([
  'supports_streaming',
  'supports_tools',
  'supports_files',
  'supports_long_context',
  'supports_sensitive_tools',
  'is_experimental',
  'is_user_key_required',
  'is_managed',
  'is_internal',
])

const UNSAFE_OPTION_KEYS = new Set([
  'access_token',
  'adapter_id',
  'api_key',
  'billing',
  'billing_config',
  'credential',
  'credentials',
  'daily_token_limit',
  'debug',
  'env',
  'environment',
  'environment_variable',
  'files',
  'function_calling',
  'function-calling',
  'long_memory',
  'max_context_tokens',
  'max_input_tokens',
  'max_output_tokens',
  'policy_overrides',
  'private_endpoint',
  'provider_config',
  'provider_family',
  'provider_mode',
  'provider_payload',
  'quota_limit',
  'quota_limits',
  'raw_provider_payload',
  'raw_provider_request',
  'raw_provider_response',
  'request_payload',
  'selected_adapter_id',
  'selected_provider_family',
  'sensitive_tools',
  'secret',
  'token',
  'tokens',
  'tools',
])

const UNSAFE_CAPABILITY_KEYS = new Set([
  'files',
  'function_calling',
  'function-calling',
  'long_memory',
  'sensitive_tools',
  'tools',
])

type AccessSnapshotBoundaryEnvelope = {
  ok: boolean
  access_snapshot: Record<string, unknown>
  denied: boolean
  reason: string
  snapshot_version: string
  boundary_version: string
}

export type FreeModeChatBridgeInput = {
  planMode: unknown
  inputTokenEstimate: unknown
  outputTokenBudgetEstimate: unknown
  dailyTokenUsage: unknown
  accessSnapshotEnvelope: unknown
  experimentalFeatureEnabled?: boolean
  chatBridgeFeatureEnabled?: boolean
  requestedCapabilities?: unknown
  requestOptions?: unknown
  browserRuntimeAvailable?: boolean
  puterRuntimeAvailable?: boolean
}

export type FreeModeChatBridgeRuntimeTruth = {
  access_layer_plan_mode: string
  provider_family: string
  provider_attempted: false
  provider_succeeded: false
  provider_failed_reason: string
  fallback_triggered: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  selected_adapter_id: string
  boundary_version: string
  snapshot_version: string
  sanitized_output: null
}

export type FreeModeChatBridgeDecision = {
  bridge_version: typeof FREE_MODE_CHAT_BRIDGE_VERSION
  allowed: boolean
  denied: boolean
  reason: string
  plan_mode: string
  provider_family: string
  adapter_id: string
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  feature_flag_allowed: boolean
  runtime_allowed: boolean
  puter_runtime_required: boolean
  fallback_required: boolean
  runtime_truth: FreeModeChatBridgeRuntimeTruth
}

type DecisionState = {
  planMode: string
  providerFamily: string
  selectedAdapterId: string
  quotaAllowed: boolean
  quotaExceeded: boolean
  routingAllowed: boolean
  featureFlagAllowed: boolean
  runtimeAllowed: boolean
  boundaryVersion: string
  snapshotVersion: string
}

export function isPuterChatBridgeFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function decideFreeModeChatBridge(input: FreeModeChatBridgeInput): FreeModeChatBridgeDecision {
  const requestedPlanMode = readLowerString(input.planMode)
  const tokenEstimatesValid = isNonNegativeInteger(input.inputTokenEstimate)
    && isNonNegativeInteger(input.outputTokenBudgetEstimate)
    && isNonNegativeInteger(input.dailyTokenUsage)
  const envelope = normalizeBoundaryEnvelope(input.accessSnapshotEnvelope)
  const snapshot = envelope?.access_snapshot
  const safeProviderFamily = snapshot?.selected_provider_family === PUTER_PROVIDER_FAMILY ? PUTER_PROVIDER_FAMILY : ''
  const state: DecisionState = {
    planMode: normalizePlanMode(requestedPlanMode),
    providerFamily: safeProviderFamily,
    selectedAdapterId: normalizeSelectedAdapterId(snapshot?.selected_adapter_id),
    quotaAllowed: snapshot?.quota_allowed === true,
    quotaExceeded: snapshot?.quota_exceeded === true,
    routingAllowed: snapshot?.routing_allowed === true,
    featureFlagAllowed: input.experimentalFeatureEnabled === true && input.chatBridgeFeatureEnabled === true,
    runtimeAllowed: input.browserRuntimeAvailable === true && input.puterRuntimeAvailable === true,
    boundaryVersion: normalizeBoundaryVersion(envelope?.boundary_version),
    snapshotVersion: normalizeSnapshotVersion(envelope?.snapshot_version),
  }

  if (requestedPlanMode !== 'free') {
    return denied('not_free_mode', state)
  }

  if (!tokenEstimatesValid) {
    return denied('invalid_token_estimate', state)
  }

  if (input.experimentalFeatureEnabled !== true) {
    return denied('feature_disabled', state)
  }

  if (input.chatBridgeFeatureEnabled !== true) {
    return denied('chat_bridge_disabled', state)
  }

  if (hasUnsafeOptions(input.requestOptions) || hasUnsafeOptions(input.requestedCapabilities)) {
    return denied('unsafe_request_options', state)
  }

  if (hasUnsupportedCapabilities(input.requestedCapabilities)) {
    return denied('unsupported_capability', state)
  }

  if (!envelope) {
    return denied('invalid_access_snapshot', state)
  }

  if (!envelope.ok || envelope.denied) {
    return denied('routing_denied', state)
  }

  if (envelope.access_snapshot.selected_provider_family !== PUTER_PROVIDER_FAMILY) {
    return denied('provider_family_not_allowed', state)
  }

  if (!isSafeFreeSnapshot(envelope)) {
    return denied('invalid_access_snapshot', state)
  }

  if (!state.quotaAllowed || state.quotaExceeded) {
    return denied('quota_exceeded', state)
  }

  if (!state.routingAllowed) {
    return denied('routing_denied', state)
  }

  if (state.providerFamily !== PUTER_PROVIDER_FAMILY) {
    return denied('provider_family_not_allowed', state)
  }

  if (input.browserRuntimeAvailable !== true) {
    return denied('non_browser_runtime', state)
  }

  if (input.puterRuntimeAvailable !== true) {
    return denied('puter_runtime_unavailable', state)
  }

  return allowed(state)
}

function allowed(state: DecisionState): FreeModeChatBridgeDecision {
  return {
    ...baseDecision('selection_allowed', state),
    allowed: true,
    denied: false,
    adapter_id: PUTER_BROWSER_ADAPTER_ID,
    fallback_required: false,
    runtime_truth: {
      ...baseRuntimeTruth('selection_allowed', state),
      fallback_triggered: false,
    },
  }
}

function denied(reason: string, state: DecisionState): FreeModeChatBridgeDecision {
  const safe = safeReason(reason)
  return {
    ...baseDecision(safe, state),
    allowed: false,
    denied: true,
    adapter_id: '',
    fallback_required: true,
    runtime_truth: baseRuntimeTruth(safe, state),
  }
}

function baseDecision(reason: string, state: DecisionState): Omit<FreeModeChatBridgeDecision, 'allowed' | 'denied' | 'adapter_id' | 'fallback_required' | 'runtime_truth'> {
  return {
    bridge_version: FREE_MODE_CHAT_BRIDGE_VERSION,
    reason: safeReason(reason),
    plan_mode: state.planMode,
    provider_family: state.providerFamily,
    quota_allowed: state.quotaAllowed,
    quota_exceeded: state.quotaExceeded,
    routing_allowed: state.routingAllowed,
    feature_flag_allowed: state.featureFlagAllowed,
    runtime_allowed: state.runtimeAllowed,
    puter_runtime_required: true,
  }
}

function baseRuntimeTruth(reason: string, state: DecisionState): FreeModeChatBridgeRuntimeTruth {
  return {
    access_layer_plan_mode: state.planMode,
    provider_family: state.providerFamily,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: reason === 'selection_allowed' ? '' : safeReason(reason),
    fallback_triggered: true,
    quota_allowed: state.quotaAllowed,
    quota_exceeded: state.quotaExceeded,
    routing_allowed: state.routingAllowed,
    selected_adapter_id: state.selectedAdapterId,
    boundary_version: state.boundaryVersion,
    snapshot_version: state.snapshotVersion,
    sanitized_output: null,
  }
}

function normalizeBoundaryEnvelope(value: unknown): AccessSnapshotBoundaryEnvelope | null {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_ENVELOPE_KEYS)) {
    return null
  }

  if (
    typeof value.ok !== 'boolean'
    || typeof value.denied !== 'boolean'
    || typeof value.reason !== 'string'
    || typeof value.snapshot_version !== 'string'
    || typeof value.boundary_version !== 'string'
  ) {
    return null
  }

  const snapshot = value.access_snapshot
  if (!isRecord(snapshot) || !hasExactKeys(snapshot, APPROVED_SNAPSHOT_KEYS)) {
    return null
  }

  const capabilities = snapshot.adapter_capabilities
  if (!isRecord(capabilities) || !hasExactKeys(capabilities, APPROVED_CAPABILITY_KEYS)) {
    return null
  }

  return value as AccessSnapshotBoundaryEnvelope
}

function isSafeFreeSnapshot(envelope: AccessSnapshotBoundaryEnvelope): boolean {
  const snapshot = envelope.access_snapshot
  const capabilities = snapshot.adapter_capabilities
  return envelope.boundary_version === ACCESS_SNAPSHOT_BOUNDARY_VERSION
    && envelope.snapshot_version === PUBLIC_ACCESS_SNAPSHOT_VERSION
    && snapshot.snapshot_version === PUBLIC_ACCESS_SNAPSHOT_VERSION
    && snapshot.plan_mode === 'free'
    && snapshot.provider_mode === 'experimental_free'
    && snapshot.selected_adapter_id === EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID
    && snapshot.input_allowed === true
    && snapshot.output_allowed === true
    && isRecord(capabilities)
    && capabilities.supports_tools === false
    && capabilities.supports_files === false
    && capabilities.supports_sensitive_tools === false
    && capabilities.supports_long_context === false
    && capabilities.is_experimental === true
    && capabilities.is_user_key_required === false
    && capabilities.is_managed === false
    && capabilities.is_internal === false
}

function hasUnsafeOptions(value: unknown): boolean {
  if (!value || typeof value !== 'object') {
    return false
  }

  if (Array.isArray(value)) {
    return value.some((item) => hasUnsafeOptions(item))
  }

  return Object.entries(value as Record<string, unknown>).some(([key, nested]) => {
    const normalized = normalizeKey(key)
    return UNSAFE_OPTION_KEYS.has(normalized) || hasUnsafeOptions(nested)
  })
}

function hasUnsupportedCapabilities(value: unknown): boolean {
  if (!value || typeof value !== 'object') {
    return false
  }

  if (Array.isArray(value)) {
    return value.some((item) => hasUnsupportedCapabilities(item))
  }

  return Object.entries(value as Record<string, unknown>).some(([key, nested]) => {
    const normalized = normalizeKey(key)
    if (UNSAFE_CAPABILITY_KEYS.has(normalized) && nested !== false) {
      return true
    }
    return hasUnsupportedCapabilities(nested)
  })
}

function isNonNegativeInteger(value: unknown): boolean {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0
}

function readLowerString(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function normalizePlanMode(value: string): string {
  return value === 'free' ? 'free' : UNKNOWN_PLAN_MODE
}

function normalizeSelectedAdapterId(value: unknown): string {
  return value === EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID ? EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID : ''
}

function normalizeBoundaryVersion(value: unknown): string {
  return value === ACCESS_SNAPSHOT_BOUNDARY_VERSION ? ACCESS_SNAPSHOT_BOUNDARY_VERSION : ''
}

function normalizeSnapshotVersion(value: unknown): string {
  return value === PUBLIC_ACCESS_SNAPSHOT_VERSION ? PUBLIC_ACCESS_SNAPSHOT_VERSION : ''
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizeKey(value: string): string {
  return value.trim().toLowerCase()
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'bridge_denied'
}

export function isFreeModeChatBridgeDecision(value: unknown): value is FreeModeChatBridgeDecision {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_DECISION_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
