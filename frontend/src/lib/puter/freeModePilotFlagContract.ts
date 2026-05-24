export const FREE_MODE_PILOT_FLAG_CONTRACT_VERSION = 'free_mode_pilot_flag_contract_v1'
export const PUTER_FREE_PILOT_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT'

const PUTER_PROVIDER_FAMILY = 'experimental_free_provider'
const EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID = 'experimental_free_adapter'
const ACCESS_SNAPSHOT_BOUNDARY_VERSION = 'access_snapshot_boundary_v1'
const PUBLIC_ACCESS_SNAPSHOT_VERSION = 'public_access_snapshot_v1'
const UNKNOWN_VALUE = 'unknown'

const APPROVED_DECISION_KEYS = new Set([
  'pilot_enabled',
  'pilot_eligible',
  'denied',
  'reason',
  'plan_mode',
  'provider_family',
  'quota_allowed',
  'routing_allowed',
  'consent_state',
  'rollback_active',
  'allowlist_required',
  'allowlist_matched',
  'feature_flag_allowed',
  'pilot_version',
  'runtime_truth',
])

const APPROVED_RUNTIME_TRUTH_KEYS = new Set([
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
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
  'debug_mode',
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

const UNSUPPORTED_CAPABILITY_KEYS = new Set([
  'files',
  'function_calling',
  'function-calling',
  'long_memory',
  'sensitive_tools',
  'tools',
])

const ALLOWED_CONSENT_STATES = new Set(['ready', 'granted', 'not_required'])
const PENDING_CONSENT_STATES = new Set([
  'auth_pending',
  'auth_required',
  'consent_pending',
  'consent_required',
  'provider_consent_or_auth_pending',
])

const KEY_ALIASES: Record<string, string> = {
  accesshash: 'access_hash',
  accesstoken: 'access_token',
  adapterid: 'adapter_id',
  apikey: 'api_key',
  billingconfig: 'billing_config',
  billingmode: 'billing_mode',
  dailytokenlimit: 'daily_token_limit',
  debugmode: 'debug_mode',
  environmentvariable: 'environment_variable',
  functioncalling: 'function_calling',
  longmemory: 'long_memory',
  maxcontexttokens: 'max_context_tokens',
  maxinputtokens: 'max_input_tokens',
  maxoutputtokens: 'max_output_tokens',
  policyoverrides: 'policy_overrides',
  privateendpoint: 'private_endpoint',
  providerconfig: 'provider_config',
  providerfamily: 'provider_family',
  providermode: 'provider_mode',
  providerpayload: 'provider_payload',
  quotalimit: 'quota_limit',
  quotalimits: 'quota_limits',
  rawproviderpayload: 'raw_provider_payload',
  rawproviderrequest: 'raw_provider_request',
  rawproviderresponse: 'raw_provider_response',
  requestpayload: 'request_payload',
  selectedadapterid: 'selected_adapter_id',
  selectedproviderfamily: 'selected_provider_family',
  sensitivetools: 'sensitive_tools',
}

export type FreeModePilotFlagContractInput = {
  planMode: unknown
  experimentalFeatureEnabled?: boolean
  chatBridgeFeatureEnabled?: boolean
  devRealFeatureEnabled?: boolean
  pilotFeatureEnabled?: boolean
  rollbackActive?: boolean
  allowlistRequired?: boolean
  allowlistMatched?: boolean
  pilotEligible?: boolean
  quotaAllowed?: boolean
  quotaExceeded?: boolean
  routingAllowed?: boolean
  consentState?: unknown
  selectedProviderFamily?: unknown
  selectedAdapterId?: unknown
  boundaryVersion?: unknown
  snapshotVersion?: unknown
  requestedCapabilities?: unknown
  requestOptions?: unknown
}

export type FreeModePilotRuntimeTruth = {
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  access_layer_plan_mode: string
  provider_family: string
  provider_attempted: false
  provider_succeeded: false
  provider_failed_reason: string
  fallback_triggered: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  consent_state: string
  selected_adapter_id: string
  boundary_version: string
  snapshot_version: string
  sanitized_output_present: false
  raw_provider_payload_exposed: false
}

export type FreeModePilotFlagDecision = {
  pilot_enabled: boolean
  pilot_eligible: boolean
  denied: boolean
  reason: string
  plan_mode: string
  provider_family: string
  quota_allowed: boolean
  routing_allowed: boolean
  consent_state: string
  rollback_active: boolean
  allowlist_required: boolean
  allowlist_matched: boolean
  feature_flag_allowed: boolean
  pilot_version: typeof FREE_MODE_PILOT_FLAG_CONTRACT_VERSION
  runtime_truth: FreeModePilotRuntimeTruth
}

type PilotState = {
  planMode: string
  providerFamily: string
  selectedAdapterId: string
  quotaAllowed: boolean
  quotaExceeded: boolean
  routingAllowed: boolean
  consentState: string
  rollbackActive: boolean
  allowlistRequired: boolean
  allowlistMatched: boolean
  featureFlagAllowed: boolean
  pilotEnabled: boolean
  boundaryVersion: string
  snapshotVersion: string
}

export function isPuterFreePilotFlagEnabled(
  value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT,
): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function decideFreeModePilotFlag(
  input: FreeModePilotFlagContractInput,
): FreeModePilotFlagDecision {
  const state = buildPilotState(input)

  if (state.planMode !== 'free') {
    return denied('not_free_mode', state)
  }

  if (input.experimentalFeatureEnabled !== true) {
    return denied('feature_disabled', state)
  }

  if (input.chatBridgeFeatureEnabled !== true) {
    return denied('chat_bridge_disabled', state)
  }

  if (input.devRealFeatureEnabled !== true) {
    return denied('dev_real_bridge_disabled', state)
  }

  if (input.pilotFeatureEnabled !== true) {
    return denied('pilot_flag_disabled', state)
  }

  if (state.rollbackActive) {
    return denied('rollback_active', state)
  }

  if (state.allowlistRequired && !state.allowlistMatched) {
    return denied('allowlist_not_matched', state)
  }

  if (input.pilotEligible === false) {
    return denied('pilot_not_eligible', state)
  }

  if (hasUnsafeOptions(input.requestOptions) || hasUnsafeOptions(input.requestedCapabilities)) {
    return denied('unsafe_request_options', state)
  }

  if (hasUnsupportedCapabilities(input.requestedCapabilities)) {
    return denied('unsupported_capability', state)
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

  if (!ALLOWED_CONSENT_STATES.has(state.consentState)) {
    return denied(
      PENDING_CONSENT_STATES.has(state.consentState) ? 'provider_consent_or_auth_pending' : 'invalid_consent_state',
      state,
    )
  }

  if (
    state.selectedAdapterId !== EXPECTED_ACCESS_SNAPSHOT_ADAPTER_ID
    || state.boundaryVersion !== ACCESS_SNAPSHOT_BOUNDARY_VERSION
    || state.snapshotVersion !== PUBLIC_ACCESS_SNAPSHOT_VERSION
  ) {
    return denied('invalid_pilot_state', state)
  }

  return allowed(state)
}

function buildPilotState(input: FreeModePilotFlagContractInput): PilotState {
  const featureFlagAllowed = input.experimentalFeatureEnabled === true
    && input.chatBridgeFeatureEnabled === true
    && input.devRealFeatureEnabled === true
    && input.pilotFeatureEnabled === true

  const rollbackActive = input.rollbackActive === true

  return {
    planMode: normalizePlanMode(input.planMode),
    providerFamily: normalizeProviderFamily(input.selectedProviderFamily),
    selectedAdapterId: normalizeSelectedAdapterId(input.selectedAdapterId),
    quotaAllowed: input.quotaAllowed === true,
    quotaExceeded: input.quotaExceeded === true,
    routingAllowed: input.routingAllowed === true,
    consentState: normalizeConsentState(input.consentState),
    rollbackActive,
    allowlistRequired: input.allowlistRequired === true,
    allowlistMatched: input.allowlistMatched === true,
    featureFlagAllowed,
    pilotEnabled: featureFlagAllowed && !rollbackActive,
    boundaryVersion: normalizeBoundaryVersion(input.boundaryVersion),
    snapshotVersion: normalizeSnapshotVersion(input.snapshotVersion),
  }
}

function allowed(state: PilotState): FreeModePilotFlagDecision {
  return {
    ...baseDecision('pilot_allowed', state),
    pilot_eligible: true,
    denied: false,
    runtime_truth: {
      ...baseRuntimeTruth('pilot_allowed', state),
      pilot_eligible: true,
      pilot_denied_reason: '',
      provider_failed_reason: '',
      fallback_triggered: false,
    },
  }
}

function denied(reason: string, state: PilotState): FreeModePilotFlagDecision {
  const safe = safeReason(reason)
  return {
    ...baseDecision(safe, state),
    pilot_eligible: false,
    denied: true,
    runtime_truth: baseRuntimeTruth(safe, state),
  }
}

function baseDecision(
  reason: string,
  state: PilotState,
): Omit<FreeModePilotFlagDecision, 'pilot_eligible' | 'denied' | 'runtime_truth'> {
  return {
    pilot_enabled: state.pilotEnabled,
    reason: safeReason(reason),
    plan_mode: state.planMode,
    provider_family: state.providerFamily,
    quota_allowed: state.quotaAllowed,
    routing_allowed: state.routingAllowed,
    consent_state: state.consentState,
    rollback_active: state.rollbackActive,
    allowlist_required: state.allowlistRequired,
    allowlist_matched: state.allowlistMatched,
    feature_flag_allowed: state.featureFlagAllowed,
    pilot_version: FREE_MODE_PILOT_FLAG_CONTRACT_VERSION,
  }
}

function baseRuntimeTruth(reason: string, state: PilotState): FreeModePilotRuntimeTruth {
  const safe = safeReason(reason)
  return {
    pilot_enabled: state.pilotEnabled,
    pilot_eligible: false,
    pilot_denied_reason: safe,
    access_layer_plan_mode: state.planMode,
    provider_family: state.providerFamily,
    provider_attempted: false,
    provider_succeeded: false,
    provider_failed_reason: safe,
    fallback_triggered: true,
    quota_allowed: state.quotaAllowed,
    quota_exceeded: state.quotaExceeded,
    routing_allowed: state.routingAllowed,
    consent_state: state.consentState,
    selected_adapter_id: state.selectedAdapterId,
    boundary_version: state.boundaryVersion,
    snapshot_version: state.snapshotVersion,
    sanitized_output_present: false,
    raw_provider_payload_exposed: false,
  }
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
    if (UNSUPPORTED_CAPABILITY_KEYS.has(normalized) && nested !== false) {
      return true
    }
    return hasUnsupportedCapabilities(nested)
  })
}

function normalizePlanMode(value: unknown): string {
  return readLowerString(value) === 'free' ? 'free' : UNKNOWN_VALUE
}

function normalizeProviderFamily(value: unknown): string {
  return value === PUTER_PROVIDER_FAMILY ? PUTER_PROVIDER_FAMILY : ''
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

function normalizeConsentState(value: unknown): string {
  const normalized = readLowerString(value)
  if (ALLOWED_CONSENT_STATES.has(normalized) || PENDING_CONSENT_STATES.has(normalized)) {
    return normalized
  }
  return UNKNOWN_VALUE
}

function readLowerString(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function normalizeKey(value: string): string {
  const canonical = value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2')
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase()
  const compact = canonical.replace(/_/g, '')
  return KEY_ALIASES[compact] ?? canonical
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'pilot_denied'
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function isFreeModePilotFlagDecision(value: unknown): value is FreeModePilotFlagDecision {
  if (!isRecord(value) || !hasExactKeys(value, APPROVED_DECISION_KEYS)) {
    return false
  }

  const runtimeTruth = value.runtime_truth
  return isRecord(runtimeTruth) && hasExactKeys(runtimeTruth, APPROVED_RUNTIME_TRUTH_KEYS)
}
