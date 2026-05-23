export const PUTER_BROWSER_SKELETON_VERSION = 'puter_browser_skeleton_v1'
export const PUTER_BROWSER_ADAPTER_ID = 'puter_browser_skeleton_adapter'
export const PUTER_CLIENT_ADAPTER_ID = 'puter_client_adapter'
export const PUTER_PROVIDER_FAMILY = 'experimental_free_provider'
export const PUTER_PROVIDER_MODE = 'experimental_free'
export const PUTER_EXPERIMENTAL_FLAG_NAME = 'VITE_OMNI_EXPERIMENTAL_PUTER_FREE'

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

const DENIED_CAPABILITIES = {
  supports_streaming: false,
  supports_tools: false,
  supports_files: false,
  supports_long_context: false,
  supports_sensitive_tools: false,
  is_experimental: true,
  is_user_key_required: false,
  is_managed: false,
  is_internal: false,
} as const

export type PuterAdapterCapabilities = typeof DENIED_CAPABILITIES

export type AccessSnapshotBoundaryEnvelope = {
  ok: boolean
  access_snapshot: Record<string, unknown>
  denied: boolean
  reason: string
  snapshot_version: string
  boundary_version: string
}

export type PuterBrowserSelectionResult = {
  skeleton_version: typeof PUTER_BROWSER_SKELETON_VERSION
  selection_allowed: boolean
  denied: boolean
  reason: string
  adapter_id: typeof PUTER_BROWSER_ADAPTER_ID
  client_adapter_id: typeof PUTER_CLIENT_ADAPTER_ID
  provider_family: typeof PUTER_PROVIDER_FAMILY
  provider_mode: typeof PUTER_PROVIDER_MODE
  is_experimental: true
  default_enabled: false
  requires_browser_runtime: true
  requires_user_session: true
  capabilities: PuterAdapterCapabilities
}

export type PuterBrowserSelectionInput = {
  accessSnapshotEnvelope: unknown
  experimentalFeatureEnabled?: boolean
  requestOptions?: unknown
  runtime?: unknown
}

export type PuterBrowserPreparedRequest = PuterBrowserSelectionResult & {
  prepared: boolean
}

export function isPuterFreeModeFlagEnabled(value = import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function selectPuterFreeModeBrowserAdapter(input: PuterBrowserSelectionInput): PuterBrowserSelectionResult {
  if (hasRequestOptions(input.requestOptions)) {
    return denied('unsafe_request_options')
  }

  if (!input.experimentalFeatureEnabled) {
    return denied('feature_disabled')
  }

  if (!isBrowserRuntime(input.runtime)) {
    return denied('non_browser_runtime')
  }

  if (!hasPuterClient(input.runtime)) {
    return denied('puter_unavailable')
  }

  const envelope = normalizeBoundaryEnvelope(input.accessSnapshotEnvelope)
  if (!envelope) {
    return denied('invalid_access_snapshot')
  }

  if (!envelope.ok || envelope.denied) {
    return denied(safeReason(envelope.reason, 'routing_denied'))
  }

  const snapshot = envelope.access_snapshot
  if (snapshot.routing_allowed !== true) {
    return denied(safeReason(readString(snapshot.decision_reason), 'routing_denied'))
  }

  if (snapshot.plan_mode !== 'free') {
    return denied('not_free_mode')
  }

  if (snapshot.provider_mode !== PUTER_PROVIDER_MODE) {
    return denied('provider_mode_not_allowed')
  }

  if (snapshot.selected_provider_family !== PUTER_PROVIDER_FAMILY) {
    return denied('provider_family_not_allowed')
  }

  const capabilities = snapshot.adapter_capabilities
  if (!isSafeFreeCapabilities(capabilities)) {
    return denied('adapter_capabilities_not_allowed')
  }

  return {
    ...baseResult(),
    selection_allowed: true,
    denied: false,
    reason: 'selection_allowed',
  }
}

export function preparePuterFreeModeBrowserRequest(input: PuterBrowserSelectionInput): PuterBrowserPreparedRequest {
  const selection = selectPuterFreeModeBrowserAdapter(input)
  return {
    ...selection,
    prepared: selection.selection_allowed,
  }
}

function denied(reason: string): PuterBrowserSelectionResult {
  return {
    ...baseResult(),
    selection_allowed: false,
    denied: true,
    reason,
  }
}

function baseResult(): Omit<PuterBrowserSelectionResult, 'selection_allowed' | 'denied' | 'reason'> {
  return {
    skeleton_version: PUTER_BROWSER_SKELETON_VERSION,
    adapter_id: PUTER_BROWSER_ADAPTER_ID,
    client_adapter_id: PUTER_CLIENT_ADAPTER_ID,
    provider_family: PUTER_PROVIDER_FAMILY,
    provider_mode: PUTER_PROVIDER_MODE,
    is_experimental: true,
    default_enabled: false,
    requires_browser_runtime: true,
    requires_user_session: true,
    capabilities: { ...DENIED_CAPABILITIES },
  }
}

function isBrowserRuntime(runtime: unknown): runtime is { window: unknown } {
  return Boolean(runtime && typeof runtime === 'object' && 'window' in runtime)
}

function hasPuterClient(runtime: unknown): boolean {
  if (!isBrowserRuntime(runtime)) {
    return false
  }

  const record = runtime as { window: Record<string, unknown> }
  const puter = record.window?.puter
  if (!puter || typeof puter !== 'object') {
    return false
  }

  const ai = (puter as Record<string, unknown>).ai
  return Boolean(ai && typeof ai === 'object' && typeof (ai as Record<string, unknown>).chat === 'function')
}

function hasRequestOptions(value: unknown): boolean {
  return Boolean(value && typeof value === 'object' && Object.keys(value as Record<string, unknown>).length > 0)
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

function isSafeFreeCapabilities(value: unknown): boolean {
  if (!isRecord(value)) {
    return false
  }

  return value.supports_tools === false
    && value.supports_files === false
    && value.supports_sensitive_tools === false
    && value.supports_long_context === false
    && value.is_experimental === true
    && value.is_user_key_required === false
    && value.is_managed === false
    && value.is_internal === false
}

function hasExactKeys(value: Record<string, unknown>, approvedKeys: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === approvedKeys.size && keys.every((key) => approvedKeys.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function safeReason(value: string | undefined, fallback: string): string {
  if (!value) {
    return fallback
  }

  const normalized = value.trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : fallback
}
