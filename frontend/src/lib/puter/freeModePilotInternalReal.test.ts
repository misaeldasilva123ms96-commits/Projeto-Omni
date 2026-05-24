import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_PILOT_INTERNAL_REAL_VERSION,
  isFreeModePilotInternalRealResult,
  isPuterFreePilotInternalFlagEnabled,
  runFreeModePilotInternalReal,
} from './freeModePilotInternalReal'

const RESULT_KEYS = [
  'internal_real_pilot_version',
  'allowed',
  'denied',
  'reason',
  'internal_pilot',
  'pilot_enabled',
  'pilot_eligible',
  'bridge_allowed',
  'provider_family',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'internal_pilot',
  'bridge_allowed',
  'bridge_denied_reason',
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

function puterRuntime(chat = vi.fn().mockResolvedValue('OMNI_INTERNAL_REAL_OK')) {
  return {
    window: {
      puter: {
        ai: {
          chat,
        },
      },
    },
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
    internalPilotFeatureEnabled: true,
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
    prompt: 'Reply with a safe internal pilot result.',
    runtime: puterRuntime(),
    ...overrides,
  }
}

async function expectDenied(overrides: Record<string, unknown>, reason: string) {
  const result = await runFreeModePilotInternalReal(input(overrides))
  expect(result.allowed).toBe(false)
  expect(result.denied).toBe(true)
  expect(result.reason).toBe(reason)
  expect(result.sanitized_output).toBeNull()
  expect(result.runtime_truth.provider_succeeded).toBe(false)
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

describe('Free Mode pilot internal-real', () => {
  it('keeps the internal pilot flag disabled unless explicitly enabled', () => {
    expect(isPuterFreePilotInternalFlagEnabled()).toBe(false)
    expect(isPuterFreePilotInternalFlagEnabled('')).toBe(false)
    expect(isPuterFreePilotInternalFlagEnabled('false')).toBe(false)
    expect(isPuterFreePilotInternalFlagEnabled('true')).toBe(true)
    expect(isPuterFreePilotInternalFlagEnabled('1')).toBe(true)
  })

  it('denies when the internal pilot flag is false without invoking the bridge', async () => {
    const chat = vi.fn()
    const result = await expectDenied({
      internalPilotFeatureEnabled: false,
      runtime: puterRuntime(chat),
    }, 'internal_pilot_disabled')

    expect(result.internal_pilot).toBe(false)
    expect(result.runtime_truth.internal_pilot).toBe(false)
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('denies pilot contract fail-closed cases before provider invocation', async () => {
    for (const overrides of [
      { pilotFeatureEnabled: false, reason: 'pilot_flag_disabled' },
      { rollbackActive: true, reason: 'rollback_active' },
      { allowlistRequired: true, allowlistMatched: false, reason: 'allowlist_not_matched' },
      { planMode: 'pro', reason: 'not_free_mode' },
      { quotaExceeded: true, reason: 'quota_exceeded' },
      { quotaAllowed: false, reason: 'quota_exceeded' },
      { routingAllowed: false, reason: 'routing_denied' },
      { selectedProviderFamily: 'managed_provider', reason: 'provider_family_not_allowed' },
      { consentState: 'provider_consent_or_auth_pending', reason: 'provider_consent_or_auth_pending' },
      { requestOptions: { apiKey: 'hidden' }, reason: 'unsafe_request_options' },
      { requestOptions: { 'private-endpoint': 'hidden' }, reason: 'unsafe_request_options' },
      { requestOptions: { 'raw provider payload': { text: 'hidden' } }, reason: 'unsafe_request_options' },
      { requestedCapabilities: { functionCalling: true }, reason: 'unsafe_request_options' },
      { requestedCapabilities: { 'long-memory': true }, reason: 'unsafe_request_options' },
    ]) {
      const chat = vi.fn()
      const { reason, ...inputOverrides } = overrides
      const result = await expectDenied({
        ...inputOverrides,
        runtime: puterRuntime(chat),
      }, reason as string)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('denies when Puter runtime is missing or the bridge contract denies', async () => {
    const missingMarker = await expectDenied({ puterRuntimeAvailable: false }, 'puter_runtime_unavailable')
    expect(missingMarker.internal_pilot).toBe(true)
    expect(missingMarker.runtime_truth.provider_attempted).toBe(false)
    expect(missingMarker.runtime_truth.bridge_denied_reason).toBe('puter_runtime_unavailable')

    const missingRuntime = await expectDenied({ runtime: { window: {} } }, 'puter_unavailable')
    expect(missingRuntime.runtime_truth.provider_attempted).toBe(false)
    expect(missingRuntime.runtime_truth.bridge_denied_reason).toBe('puter_unavailable')
  })

  it('uses the Phase 7L dev-real bridge only after all gates pass', async () => {
    const chat = vi.fn().mockResolvedValue('OMNI_INTERNAL_REAL_OK')
    const result = await runFreeModePilotInternalReal(input({ runtime: puterRuntime(chat) }))

    expect(chat).toHaveBeenCalledOnce()
    expect(chat).toHaveBeenCalledWith('Reply with a safe internal pilot result.')
    expect(result).toMatchObject({
      internal_real_pilot_version: FREE_MODE_PILOT_INTERNAL_REAL_VERSION,
      allowed: true,
      denied: false,
      reason: 'ok',
      internal_pilot: true,
      pilot_enabled: true,
      pilot_eligible: true,
      bridge_allowed: true,
      provider_family: 'experimental_free_provider',
      fallback_required: false,
      sanitized_output: 'OMNI_INTERNAL_REAL_OK',
    })
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(true)
    expect(result.runtime_truth.sanitized_output_present).toBe(true)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
  })

  it('sanitizes successful provider text', async () => {
    const chat = vi.fn().mockResolvedValue({
      text: 'safe text sk-proj-hidden123456789 user@example.com',
      raw_provider_payload: 'must not surface',
    })
    const result = await runFreeModePilotInternalReal(input({ runtime: puterRuntime(chat) }))

    expect(result.allowed).toBe(true)
    expect(result.sanitized_output).toBe('safe text [redacted] [redacted]')
    expect(JSON.stringify(result).toLowerCase()).not.toContain('must not surface')
    expectPublicSafe(result)
  })

  it('turns provider failure into sanitized fail-closed output', async () => {
    const chat = vi.fn().mockRejectedValue(new Error('stack sk-test-hidden provider_config'))
    const result = await expectDenied({ runtime: puterRuntime(chat) }, 'puter_call_failed')

    expect(chat).toHaveBeenCalledOnce()
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.provider_failed_reason).toBe('puter_call_failed')
    expectPublicSafe(result)
  })

  it('returns exact public result and runtime truth key sets', async () => {
    const allowed = await runFreeModePilotInternalReal(input())
    const denied = await runFreeModePilotInternalReal(input({ internalPilotFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModePilotInternalRealResult(allowed)).toBe(true)
    expect(isFreeModePilotInternalRealResult(denied)).toBe(true)
  })

  it('does not echo raw IDs, unsafe keys, or sensitive fragments', async () => {
    const result = await runFreeModePilotInternalReal(input({
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

  it('does not call on import or default path', async () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    await import('./freeModePilotInternalReal')

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('does not contain chat send or direct provider/network execution paths', async () => {
    const source = await import('./freeModePilotInternalReal?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('invokeputerfreemodemanualharness')
    expect(lowered).not.toContain('freemodeputermanualharness')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
