import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_CHAT_WIRING_HARNESS_OUTPUT,
  FREE_MODE_CHAT_WIRING_HARNESS_VERSION,
  isFreeModeChatWiringHarnessResult,
  runFreeModeChatWiringHarness,
} from './freeModeChatWiringHarness'

const RESULT_KEYS = [
  'ok',
  'status',
  'reason',
  'user_message',
  'sanitized_output',
  'retry_allowed',
  'manual_action_required',
  'fallback_triggered',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
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
    allowlistedPilotFeatureEnabled: true,
    mockFeatureEnabled: true,
    rollbackActive: false,
    allowlistRequired: true,
    allowlistMatched: true,
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
    messageSummary: 'safe summary',
    promptSummary: 'safe prompt summary',
    ...overrides,
  }
}

function expectDenied(overrides: Record<string, unknown>, reason: string, status?: string) {
  const result = runFreeModeChatWiringHarness(input(overrides))
  expect(result.ok).toBe(false)
  expect(result.reason).toBe(reason)
  if (status) {
    expect(result.status).toBe(status)
  }
  expect(result.sanitized_output).toBeNull()
  expect(result.fallback_triggered).toBe(true)
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

describe('Free Mode chat wiring harness', () => {
  it('exposes the expected harness version constant for docs and tests', () => {
    expect(FREE_MODE_CHAT_WIRING_HARNESS_VERSION).toBe('free_mode_chat_wiring_harness_v1')
  })

  it('denies when flags are false and never attempts a provider', () => {
    const result = expectDenied({
      experimentalFeatureEnabled: false,
      chatBridgeFeatureEnabled: false,
      pilotFeatureEnabled: false,
      allowlistedPilotFeatureEnabled: false,
      mockFeatureEnabled: false,
    }, 'feature_disabled', 'denied_by_flag')

    expect(result.runtime_truth.pilot_enabled).toBe(false)
  })

  it('denies rollback active before mock or provider status changes', () => {
    const result = expectDenied({ rollbackActive: true }, 'rollback_active', 'denied_by_rollback')
    expect(result.runtime_truth.rollback_active).toBe(true)
  })

  it('denies allowlist missing or mismatch before mock execution', () => {
    const missing = expectDenied({ allowlistMatched: undefined }, 'allowlist_not_matched', 'denied_by_allowlist')
    expect(missing.runtime_truth.allowlist_required).toBe(true)
    expect(missing.runtime_truth.allowlist_matched).toBe(false)

    const mismatch = expectDenied({ allowlistMatched: false }, 'allowlist_not_matched', 'denied_by_allowlist')
    expect(mismatch.runtime_truth.allowlist_required).toBe(true)
    expect(mismatch.runtime_truth.allowlist_matched).toBe(false)
  })

  it('denies quota, routing, provider family, and malformed inputs fail-closed', () => {
    expectDenied({ quotaExceeded: true }, 'quota_exceeded', 'denied_by_quota')
    expectDenied({ quotaAllowed: false }, 'quota_exceeded', 'denied_by_quota')
    expectDenied({ routingAllowed: false }, 'routing_denied', 'denied_by_routing')
    expectDenied({ selectedProviderFamily: 'managed_provider' }, 'provider_family_not_allowed', 'denied_by_access_layer')
    expectDenied({ planMode: 'pro' }, 'not_free_mode', 'denied_by_access_layer')
    expectDenied({ inputTokenEstimate: -1 }, 'invalid_token_estimate', 'denied_by_access_layer')
  })

  it('maps consent/auth pending to a safe pending state with no success', () => {
    const result = expectDenied({
      consentState: 'provider_consent_or_auth_pending',
    }, 'provider_consent_or_auth_pending', 'provider_consent_or_auth_pending')

    expect(result.retry_allowed).toBe(true)
    expect(result.manual_action_required).toBe(true)
    expect(result.runtime_truth.consent_state).toBe('provider_consent_or_auth_pending')
    expect(result.runtime_truth.sanitized_output_present).toBe(false)
  })

  it('denies unsafe fields including camelCase, kebab-case, and spaced variants', () => {
    for (const requestOptions of [
      { apiKey: 'hidden' },
      { APIKey: 'hidden' },
      { 'api-key': 'hidden' },
      { 'api key': 'hidden' },
      { accessToken: 'hidden' },
      { providerFamily: 'managed_provider' },
      { providerConfig: { model: 'hidden' } },
      { 'private-endpoint': 'hidden' },
      { 'raw provider payload': { text: 'hidden' } },
      { policyOverrides: { providerMode: 'managed' } },
      { billingConfig: 'hidden' },
      { debugMode: true },
    ]) {
      const result = expectDenied({ requestOptions }, 'unsafe_request_options', 'denied_by_access_layer')
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
      const result = runFreeModeChatWiringHarness(input({ requestedCapabilities }))
      expect(result.ok).toBe(false)
      expect(['unsafe_request_options', 'unsupported_capability']).toContain(result.reason)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(result.runtime_truth.provider_succeeded).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('returns deterministic mock-only success only when all gates pass', () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    const result = runFreeModeChatWiringHarness(input())

    expect(result).toMatchObject({
      ok: true,
      status: 'provider_succeeded_sanitized',
      reason: 'mock_wiring_allowed',
      user_message: 'Free chat wiring harness completed with deterministic mock output.',
      sanitized_output: FREE_MODE_CHAT_WIRING_HARNESS_OUTPUT,
      retry_allowed: false,
      manual_action_required: false,
      fallback_triggered: false,
    })
    expect(result.sanitized_output).not.toBe('Omni Free pilot mock response.')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.mock_provider_attempted).toBe(true)
    expect(result.runtime_truth.mock_provider_succeeded).toBe(true)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expect(result.runtime_truth.sanitized_output_present).toBe(true)
    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('returns exact public result and runtime truth key sets', () => {
    const allowed = runFreeModeChatWiringHarness(input())
    const denied = runFreeModeChatWiringHarness(input({ pilotFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModeChatWiringHarnessResult(allowed)).toBe(true)
    expect(isFreeModeChatWiringHarnessResult(denied)).toBe(true)
  })

  it('does not echo raw IDs, unsafe keys, or sensitive fragments', () => {
    const result = runFreeModeChatWiringHarness(input({
      planMode: 'sk-test-apiKey-accessToken-providerConfig-privateEndpoint-billing-debug-process.env',
      messageSummary: 'user@example.com sk-test rawProviderPayload',
      promptSummary: 'process.env providerConfig privateEndpoint',
      requestOptions: {
        publicSessionId: 'user@example.com sk-test process.env providerConfig rawProviderPayload',
      },
    }))

    expect(result.ok).toBe(false)
    expectNoEcho(result, [
      'apiKey',
      'accessToken',
      'providerFamily',
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

  it('does not call on import or default path', async () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    await import('./freeModeChatWiringHarness')

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('does not import chat send, real Puter, dev-real, manual harness, or network paths', async () => {
    const source = await import('./freeModeChatWiringHarness?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('freemodechatbridgedevreal')
    expect(lowered).not.toContain('runfreemodepilotinternalreal')
    expect(lowered).not.toContain('invokeputerfreemodemanualharness')
    expect(lowered).not.toContain('freemodeputermanualharness')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
