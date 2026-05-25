import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_CHAT_INTERNAL_ALLOWLISTED_WIRING_VERSION,
  isFreeModeChatInternalAllowlistedWiringResult,
  isPuterFreeChatInternalWiringFlagEnabled,
  runFreeModeChatInternalAllowlistedWiring,
} from './freeModeChatInternalAllowlistedWiring'

const RESULT_KEYS = [
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
  'consent_state',
  'sanitized_output_present',
  'raw_provider_payload_exposed',
  'should_use_normal_chat',
  'internal_allowlisted_wiring_enabled',
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

function puterRuntime(chat = vi.fn().mockResolvedValue('OMNI_INTERNAL_ALLOWLISTED_OK')) {
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
    allowlistedPilotFeatureEnabled: true,
    internalWiringFeatureEnabled: true,
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
    prompt: 'Reply with exactly: OMNI_INTERNAL_ALLOWLISTED_OK',
    messageSummary: 'safe summary',
    promptSummary: 'safe prompt summary',
    runtime: puterRuntime(),
    ...overrides,
  }
}

async function expectDenied(overrides: Record<string, unknown>, reason: string, status?: string) {
  const result = await runFreeModeChatInternalAllowlistedWiring(input(overrides))
  expect(result.ok).toBe(false)
  expect(result.mode).toBe('internal_allowlisted_free_chat')
  expect(result.reason).toBe(reason)
  if (status) {
    expect(result.status).toBe(status)
  }
  expect(result.sanitized_output).toBeNull()
  expect(result.fallback_triggered).toBe(true)
  expect(result.runtime_truth.provider_succeeded).toBe(false)
  expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
  expect(result.runtime_truth.internal_allowlisted_wiring_enabled).toBe(true)
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

describe('Free Mode internal allowlisted chat wiring', () => {
  it('keeps the internal wiring flag disabled unless explicitly enabled', () => {
    expect(FREE_MODE_CHAT_INTERNAL_ALLOWLISTED_WIRING_VERSION).toBe('free_mode_chat_internal_allowlisted_wiring_v1')
    expect(isPuterFreeChatInternalWiringFlagEnabled()).toBe(false)
    expect(isPuterFreeChatInternalWiringFlagEnabled('')).toBe(false)
    expect(isPuterFreeChatInternalWiringFlagEnabled('false')).toBe(false)
    expect(isPuterFreeChatInternalWiringFlagEnabled('true')).toBe(true)
    expect(isPuterFreeChatInternalWiringFlagEnabled('1')).toBe(true)
  })

  it('returns normal chat bypass when flags are false and does not attempt provider', async () => {
    const chat = vi.fn()
    const result = await runFreeModeChatInternalAllowlistedWiring(input({
      internalWiringFeatureEnabled: false,
      experimentalFeatureEnabled: false,
      chatBridgeFeatureEnabled: false,
      pilotFeatureEnabled: false,
      internalPilotFeatureEnabled: false,
      allowlistedPilotFeatureEnabled: false,
      runtime: puterRuntime(chat),
    }))

    expect(result).toMatchObject({
      ok: false,
      mode: 'normal_chat',
      should_use_normal_chat: true,
      status: 'normal_chat_bypass',
      reason: 'internal_wiring_disabled',
      sanitized_output: null,
      fallback_triggered: false,
    })
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.internal_allowlisted_wiring_enabled).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('documents that flags false leaves normal chat behavior expected unchanged', async () => {
    const result = await runFreeModeChatInternalAllowlistedWiring(input({ internalWiringFeatureEnabled: false }))

    expect(result.should_use_normal_chat).toBe(true)
    expect(result.mode).toBe('normal_chat')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
  })

  it('denies gate failures before provider invocation', async () => {
    for (const overrides of [
      { rollbackActive: true, reason: 'rollback_active', status: 'denied_by_rollback' },
      { allowlistMatched: false, reason: 'allowlist_not_matched', status: 'denied_by_allowlist' },
      { quotaExceeded: true, reason: 'quota_exceeded', status: 'denied_by_quota' },
      { quotaAllowed: false, reason: 'quota_exceeded', status: 'denied_by_quota' },
      { routingAllowed: false, reason: 'routing_denied', status: 'denied_by_routing' },
      { selectedProviderFamily: 'managed_provider', reason: 'provider_family_not_allowed', status: 'denied_by_access_layer' },
      { internalPilotFeatureEnabled: false, reason: 'internal_pilot_disabled', status: 'denied_by_flag' },
      { allowlistedPilotFeatureEnabled: false, reason: 'allowlisted_pilot_disabled', status: 'denied_by_flag' },
    ]) {
      const chat = vi.fn()
      const result = await expectDenied({
        ...overrides,
        runtime: puterRuntime(chat),
      }, overrides.reason, overrides.status)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(result.runtime_truth.should_use_normal_chat).toBe(true)
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('maps consent pending to safe pending and no success', async () => {
    const chat = vi.fn()
    const result = await expectDenied({
      consentState: 'provider_consent_or_auth_pending',
      runtime: puterRuntime(chat),
    }, 'provider_consent_or_auth_pending', 'provider_consent_or_auth_pending')

    expect(result.retry_allowed).toBe(true)
    expect(result.manual_action_required).toBe(true)
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.should_use_normal_chat).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('denies unsafe fields including camelCase, kebab-case, and spaced variants', async () => {
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
      const result = await expectDenied({ requestOptions }, 'unsafe_request_options', 'denied_by_access_layer')
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('denies tools, files, function-calling, and long memory requests', async () => {
    for (const requestedCapabilities of [
      { tools: true },
      { files: true },
      { functionCalling: true },
      { 'long-memory': true },
      { sensitiveTools: true },
    ]) {
      const result = await runFreeModeChatInternalAllowlistedWiring(input({ requestedCapabilities }))
      expect(result.ok).toBe(false)
      expect(['unsafe_request_options', 'unsupported_capability']).toContain(result.reason)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(result.runtime_truth.provider_succeeded).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('uses the existing gated allowlisted path only when all gates pass', async () => {
    const chat = vi.fn().mockResolvedValue('OMNI_INTERNAL_ALLOWLISTED_OK')
    const result = await runFreeModeChatInternalAllowlistedWiring(input({ runtime: puterRuntime(chat) }))

    expect(chat).toHaveBeenCalledOnce()
    expect(chat).toHaveBeenCalledWith('Reply with exactly: OMNI_INTERNAL_ALLOWLISTED_OK')
    expect(result).toMatchObject({
      ok: true,
      mode: 'internal_allowlisted_free_chat',
      should_use_normal_chat: false,
      status: 'provider_succeeded_sanitized',
      reason: 'internal_allowlisted_wiring_allowed',
      sanitized_output: 'OMNI_INTERNAL_ALLOWLISTED_OK',
      fallback_triggered: false,
    })
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(true)
    expect(result.runtime_truth.sanitized_output_present).toBe(true)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
  })

  it('marks provider failure as safe after a gated provider attempt', async () => {
    const chat = vi.fn().mockRejectedValue(new Error('stack sk-test provider_config'))
    const result = await expectDenied({ runtime: puterRuntime(chat) }, 'puter_call_failed', 'provider_failed_safe')

    expect(chat).toHaveBeenCalledOnce()
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.provider_failed_reason).toBe('puter_call_failed')
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expectPublicSafe(result)
  })

  it('returns exact public result and runtime truth key sets', async () => {
    const normalChat = await runFreeModeChatInternalAllowlistedWiring(input({ internalWiringFeatureEnabled: false }))
    const allowed = await runFreeModeChatInternalAllowlistedWiring(input())
    const denied = await runFreeModeChatInternalAllowlistedWiring(input({ rollbackActive: true }))

    for (const result of [normalChat, allowed, denied]) {
      expect(Object.keys(result).sort()).toEqual([...RESULT_KEYS].sort())
      expect(Object.keys(result.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
      expect(isFreeModeChatInternalAllowlistedWiringResult(result)).toBe(true)
    }
  })

  it('does not echo raw IDs, unsafe keys, or sensitive fragments', async () => {
    const result = await runFreeModeChatInternalAllowlistedWiring(input({
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

    await import('./freeModeChatInternalAllowlistedWiring')

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('does not import chat send, direct Puter, manual harness, or network paths', async () => {
    const source = await import('./freeModeChatInternalAllowlistedWiring?raw')
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

  it('does not modify sendOmniMessage or chat source on this branch', async () => {
    const source = await import('../api/chat?raw')
    expect(source.default).toContain('export async function sendOmniMessage')
    expect(source.default).not.toContain('freeModeChatInternalAllowlistedWiring')
    expect(source.default).not.toContain('runFreeModeChatInternalAllowlistedWiring')
  })
})
