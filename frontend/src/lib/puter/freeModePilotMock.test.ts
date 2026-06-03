import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_PILOT_MOCK_OUTPUT,
  FREE_MODE_PILOT_MOCK_VERSION,
  isFreeModePilotMockResult,
  runFreeModePilotMock,
} from './freeModePilotMock'

const RESULT_KEYS = [
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
]

const RUNTIME_TRUTH_KEYS = [
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
]

const FORBIDDEN_OUTPUT_FRAGMENTS = [
  'access_token',
  'apikey',
  'api_key',
  'billing',
  'credential',
  'debug',
  'env_var',
  'private_endpoint',
  'process.env',
  'provider_config',
  'rawproviderpayload',
  'request_payload',
  'secret',
  'sk-',
  'stack',
  'traceback',
  'user@example.com',
]

function safeEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    ok: true,
    access_snapshot: {
      snapshot_version: 'public_access_snapshot_v1',
      plan_mode: 'free',
      provider_mode: 'experimental_free',
      subject_id: 'session-1',
      usage_date: '2026-05-24',
      tokens_in: 100,
      tokens_out: 25,
      tokens_total: 125,
      daily_token_limit: 15000,
      quota_remaining: 14875,
      quota_exceeded: false,
      input_allowed: true,
      output_allowed: true,
      quota_allowed: true,
      routing_allowed: true,
      fallback_allowed: false,
      selected_provider_family: 'experimental_free_provider',
      selected_adapter_id: 'experimental_free_adapter',
      adapter_display_name: 'Experimental Free Provider',
      adapter_capabilities: {
        supports_streaming: false,
        supports_tools: false,
        supports_files: false,
        supports_long_context: false,
        supports_sensitive_tools: false,
        is_experimental: true,
        is_user_key_required: false,
        is_managed: false,
        is_internal: false,
      },
      decision_reason: 'routing_allowed',
    },
    denied: false,
    reason: 'ok',
    snapshot_version: 'public_access_snapshot_v1',
    boundary_version: 'access_snapshot_boundary_v1',
    ...overrides,
  }
}

function input(overrides: Record<string, unknown> = {}) {
  return {
    planMode: 'free',
    inputTokenEstimate: 100,
    outputTokenBudgetEstimate: 25,
    dailyTokenUsage: 125,
    accessSnapshotEnvelope: safeEnvelope(),
    experimentalFeatureEnabled: true,
    chatBridgeFeatureEnabled: true,
    devRealFeatureEnabled: true,
    pilotFeatureEnabled: true,
    mockFeatureEnabled: true,
    rollbackActive: false,
    allowlistRequired: false,
    allowlistMatched: false,
    pilotEligible: true,
    quotaAllowed: true,
    quotaExceeded: false,
    routingAllowed: true,
    consentState: 'ready',
    selectedProviderFamily: 'experimental_free_provider',
    selectedAdapterId: 'experimental_free_adapter',
    boundaryVersion: 'access_snapshot_boundary_v1',
    snapshotVersion: 'public_access_snapshot_v1',
    requestedCapabilities: {},
    requestOptions: {},
    browserRuntimeAvailable: true,
    puterRuntimeAvailable: true,
    ...overrides,
  }
}

function expectDenied(overrides: Record<string, unknown>, reason: string) {
  const result = runFreeModePilotMock(input(overrides))
  expect(result.allowed).toBe(false)
  expect(result.denied).toBe(true)
  expect(result.reason).toBe(reason)
  expect(result.sanitized_output).toBeNull()
  expect(result.runtime_truth.provider_attempted).toBe(false)
  expect(result.runtime_truth.provider_succeeded).toBe(false)
  expect(result.runtime_truth.mock_provider_attempted).toBe(false)
  expect(result.runtime_truth.mock_provider_succeeded).toBe(false)
  expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
  return result
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_OUTPUT_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

function expectNoEcho(value: unknown, fragments: string[]) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of fragments) {
    expect(serialized).not.toContain(fragment.toLowerCase())
  }
}

describe('Free Mode pilot mock', () => {
  it('denies when the pilot flag is false', () => {
    const result = expectDenied({ pilotFeatureEnabled: false }, 'pilot_flag_disabled')
    expect(result.pilot_enabled).toBe(false)
    expect(result.pilot_eligible).toBe(false)
    expect(result.bridge_allowed).toBe(false)
  })

  it('denies when rollback is active', () => {
    const result = expectDenied({ rollbackActive: true }, 'rollback_active')
    expect(result.runtime_truth.fallback_triggered).toBe(true)
  })

  it('denies when allowlist is required but not matched', () => {
    const result = expectDenied({ allowlistRequired: true, allowlistMatched: false }, 'allowlist_not_matched')
    expect(result.runtime_truth.pilot_denied_reason).toBe('allowlist_not_matched')
  })

  it('denies when the pilot contract denies', () => {
    expectDenied({ planMode: 'pro' }, 'not_free_mode')
    expectDenied({ quotaExceeded: true }, 'quota_exceeded')
    expectDenied({ routingAllowed: false }, 'routing_denied')
    expectDenied({ selectedProviderFamily: 'managed_provider' }, 'provider_family_not_allowed')
  })

  it('denies when the bridge contract denies after the pilot allows', () => {
    const missingRuntime = expectDenied({ puterRuntimeAvailable: false }, 'puter_runtime_unavailable')
    expect(missingRuntime.pilot_eligible).toBe(true)
    expect(missingRuntime.runtime_truth.bridge_denied_reason).toBe('puter_runtime_unavailable')

    const malformedBoundary = expectDenied({ accessSnapshotEnvelope: { ok: true } }, 'invalid_access_snapshot')
    expect(malformedBoundary.pilot_eligible).toBe(true)
    expect(malformedBoundary.runtime_truth.bridge_denied_reason).toBe('invalid_access_snapshot')
  })

  it('denies when the underlying mock bridge is disabled', () => {
    const result = expectDenied({ mockFeatureEnabled: false }, 'mock_bridge_disabled')
    expect(result.pilot_eligible).toBe(true)
    expect(result.runtime_truth.bridge_denied_reason).toBe('mock_bridge_disabled')
  })

  it('denies consent pending states through the pilot contract', () => {
    const result = expectDenied({ consentState: 'provider_consent_or_auth_pending' }, 'provider_consent_or_auth_pending')
    expect(result.runtime_truth.consent_state).toBe('provider_consent_or_auth_pending')
  })

  it('denies unsafe fields including inherited camelCase, kebab-case, and spaced variants', () => {
    for (const requestOptions of [
      { apiKey: 'hidden' },
      { 'api-key': 'hidden' },
      { 'api key': 'hidden' },
      { accessToken: 'hidden' },
      { providerConfig: { model: 'hidden' } },
      { 'private-endpoint': 'hidden' },
      { rawProviderPayload: { text: 'hidden' } },
      { 'raw provider response': { text: 'hidden' } },
      { policyOverrides: { providerMode: 'managed' } },
    ]) {
      const result = expectDenied({ requestOptions }, 'unsafe_request_options')
      expectPublicSafe(result)
    }
  })

  it('denies tools, files, function-calling, and long memory requests', () => {
    for (const requestedCapabilities of [
      { tools: true },
      { files: true },
      { functionCalling: true },
      { 'long-memory': true },
      { sensitiveTools: true },
    ]) {
      const result = runFreeModePilotMock(input({ requestedCapabilities }))
      expect(result.allowed).toBe(false)
      expect(result.denied).toBe(true)
      expect(['unsafe_request_options', 'unsupported_capability']).toContain(result.reason)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('returns deterministic mock-only output when all gates pass', () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    const result = runFreeModePilotMock(input())

    expect(result).toMatchObject({
      pilot_mock_version: FREE_MODE_PILOT_MOCK_VERSION,
      allowed: true,
      denied: false,
      reason: 'mock_pilot_allowed',
      mock_only: true,
      pilot_enabled: true,
      pilot_eligible: true,
      bridge_allowed: true,
      mock_provider_succeeded: true,
      provider_family: 'experimental_free_provider',
      fallback_required: false,
      sanitized_output: FREE_MODE_PILOT_MOCK_OUTPUT,
    })
    expect(result.sanitized_output).not.toBe('Omni Free mock bridge response.')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.mock_provider_attempted).toBe(true)
    expect(result.runtime_truth.mock_provider_succeeded).toBe(true)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('returns exact public result and runtime truth key sets', () => {
    const allowed = runFreeModePilotMock(input())
    const denied = runFreeModePilotMock(input({ pilotFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModePilotMockResult(allowed)).toBe(true)
    expect(isFreeModePilotMockResult(denied)).toBe(true)
  })

  it('does not echo raw IDs, unsafe keys, or sensitive fragments', () => {
    const result = runFreeModePilotMock(input({
      planMode: 'sk-test-apiKey-accessToken-providerConfig-privateEndpoint-billing-debug-process.env',
      requestOptions: {
        publicSessionId: 'user@example.com sk-test process.env providerConfig rawProviderPayload',
      },
    }))

    expect(result.allowed).toBe(false)
    expectNoEcho(result, [
      'apiKey',
      'accessToken',
      'providerConfig',
      'privateEndpoint',
      'rawProviderPayload',
      'sk-test',
      'process.env',
      'billing',
      'debug',
      'user@example.com',
    ])
    expectPublicSafe(result)
  })

  it('does not import chat, Puter, dev-real bridge, manual harness, or network execution paths', async () => {
    const source = await import('./freeModePilotMock?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('freemodechatbridgedevreal')
    expect(lowered).not.toContain('invokeputerfreemodemanualharness')
    expect(lowered).not.toContain('freemodeputermanualharness')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
