import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_CHAT_BRIDGE_DEV_REAL_VERSION,
  isFreeModeChatBridgeDevRealResult,
  isPuterChatBridgeDevRealFlagEnabled,
  runFreeModeChatBridgeDevReal,
} from './freeModeChatBridgeDevReal'

const DEV_REAL_RESULT_KEYS = [
  'dev_real_bridge_version',
  'allowed',
  'denied',
  'reason',
  'dev_real_enabled',
  'provider_family',
  'adapter_id',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
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
]

const FORBIDDEN_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'credential',
  'debug',
  'env',
  'private_endpoint',
  'process.env',
  'provider_config',
  'provider_payload',
  'raw_provider',
  'request_payload',
  'secret',
  'sk-',
  'stack',
  'traceback',
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

function puterRuntime(chat = vi.fn().mockResolvedValue('OMNI_PUTER_DEV_REAL_OK')) {
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
    requestedCapabilities: {},
    requestOptions: {},
    browserRuntimeAvailable: true,
    puterRuntimeAvailable: true,
    prompt: 'Reply with a short safe smoke result.',
    runtime: puterRuntime(),
    ...overrides,
  }
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Free Mode chat bridge dev-real', () => {
  it('keeps the dev-real feature flag disabled unless explicitly enabled', () => {
    expect(isPuterChatBridgeDevRealFlagEnabled()).toBe(false)
    expect(isPuterChatBridgeDevRealFlagEnabled('')).toBe(false)
    expect(isPuterChatBridgeDevRealFlagEnabled('false')).toBe(false)
    expect(isPuterChatBridgeDevRealFlagEnabled('true')).toBe(true)
    expect(isPuterChatBridgeDevRealFlagEnabled('1')).toBe(true)
  })

  it('returns denied when all flags are false and does not call Puter', async () => {
    const chat = vi.fn()
    const result = await runFreeModeChatBridgeDevReal(input({
      chatBridgeFeatureEnabled: false,
      devRealFeatureEnabled: false,
      experimentalFeatureEnabled: false,
      runtime: puterRuntime(chat),
    }))

    expect(result.allowed).toBe(false)
    expect(result.reason).toBe('dev_real_bridge_disabled')
    expect(result.dev_real_enabled).toBe(false)
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('returns denied when only the dev-real flag is false', async () => {
    const chat = vi.fn()
    const result = await runFreeModeChatBridgeDevReal(input({
      devRealFeatureEnabled: false,
      runtime: puterRuntime(chat),
    }))

    expect(result.allowed).toBe(false)
    expect(result.reason).toBe('dev_real_bridge_disabled')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('returns denied when the contract denies', async () => {
    const chat = vi.fn()
    const result = await runFreeModeChatBridgeDevReal(input({
      planMode: 'pro',
      runtime: puterRuntime(chat),
    }))

    expect(result.allowed).toBe(false)
    expect(result.reason).toBe('not_free_mode')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('denies fail-closed contract cases without invoking Puter', async () => {
    for (const overrides of [
      {
        accessSnapshotEnvelope: {
          ...safeEnvelope(),
          access_snapshot: {
            ...safeEnvelope().access_snapshot,
            quota_exceeded: true,
          },
        },
      },
      {
        accessSnapshotEnvelope: {
          ...safeEnvelope(),
          access_snapshot: {
            ...safeEnvelope().access_snapshot,
            quota_allowed: false,
          },
        },
      },
      {
        accessSnapshotEnvelope: {
          ...safeEnvelope(),
          access_snapshot: {
            ...safeEnvelope().access_snapshot,
            routing_allowed: false,
          },
        },
      },
      {
        accessSnapshotEnvelope: {
          ...safeEnvelope(),
          access_snapshot: {
            ...safeEnvelope().access_snapshot,
            selected_provider_family: 'managed_provider',
          },
        },
      },
      { browserRuntimeAvailable: false },
      { puterRuntimeAvailable: false },
      { requestedCapabilities: { tools: true } },
      { requestedCapabilities: { files: true } },
      { requestedCapabilities: { function_calling: true } },
      { requestedCapabilities: { long_memory: true } },
      { requestedCapabilities: { sensitive_tools: true } },
      { requestOptions: { provider_config: { model: 'hidden' } } },
      { requestOptions: { private_endpoint: 'hidden' } },
      { requestOptions: { billing: true } },
      { requestOptions: { debug: true } },
      { requestOptions: { api_key: 'hidden' } },
      { requestOptions: { access_token: 'hidden' } },
      { requestOptions: { credential: 'hidden' } },
      { requestOptions: { raw_provider_payload: { text: 'hidden' } } },
    ]) {
      const chat = vi.fn()
      const result = await runFreeModeChatBridgeDevReal(input({
        ...overrides,
        runtime: puterRuntime(chat),
      }))
      expect(result.allowed).toBe(false)
      expect(result.denied).toBe(true)
      expect(result.sanitized_output).toBeNull()
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(result.runtime_truth.provider_succeeded).toBe(false)
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('denies safely when the Puter runtime marker is true but runtime is unavailable', async () => {
    const result = await runFreeModeChatBridgeDevReal(input({ runtime: { window: {} } }))

    expect(result.allowed).toBe(false)
    expect(result.reason).toBe('puter_unavailable')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
  })

  it('calls the existing manual harness path only after all gates pass', async () => {
    const chat = vi.fn().mockResolvedValue('OMNI_PUTER_DEV_REAL_OK')
    const result = await runFreeModeChatBridgeDevReal(input({ runtime: puterRuntime(chat) }))

    expect(chat).toHaveBeenCalledOnce()
    expect(chat).toHaveBeenCalledWith('Reply with a short safe smoke result.')
    expect(result).toMatchObject({
      dev_real_bridge_version: FREE_MODE_CHAT_BRIDGE_DEV_REAL_VERSION,
      allowed: true,
      denied: false,
      reason: 'ok',
      dev_real_enabled: true,
      provider_family: 'experimental_free_provider',
      adapter_id: 'puter_browser_skeleton_adapter',
      fallback_required: false,
      sanitized_output: 'OMNI_PUTER_DEV_REAL_OK',
    })
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(true)
    expect(result.runtime_truth.sanitized_output).toBe('OMNI_PUTER_DEV_REAL_OK')
  })

  it('sanitizes provider text and does not expose raw provider payloads', async () => {
    const chat = vi.fn().mockResolvedValue({
      text: 'hello sk-proj-hidden123456789 user@example.com',
      raw_provider_payload: 'must not surface',
    })
    const result = await runFreeModeChatBridgeDevReal(input({ runtime: puterRuntime(chat) }))

    expect(result.allowed).toBe(true)
    expect(result.sanitized_output).toBe('hello [redacted] [redacted]')
    expect(result.runtime_truth.sanitized_output).toBe('hello [redacted] [redacted]')
    expect(JSON.stringify(result).toLowerCase()).not.toContain('raw_provider_payload')
    expectPublicSafe(result)
  })

  it('turns provider errors into safe fail-closed output', async () => {
    const chat = vi.fn().mockRejectedValue(new Error('stack sk-test-hidden provider_config'))
    const result = await runFreeModeChatBridgeDevReal(input({ runtime: puterRuntime(chat) }))

    expect(chat).toHaveBeenCalledOnce()
    expect(result.allowed).toBe(false)
    expect(result.denied).toBe(true)
    expect(result.reason).toBe('puter_call_failed')
    expect(result.runtime_truth.provider_attempted).toBe(true)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.provider_failed_reason).toBe('puter_call_failed')
    expect(result.sanitized_output).toBeNull()
    expectPublicSafe(result)
  })

  it('does not call on import or default path', async () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    await import('./freeModeChatBridgeDevReal')

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('returns exact public result and runtime truth key sets', async () => {
    const allowed = await runFreeModeChatBridgeDevReal(input())
    const denied = await runFreeModeChatBridgeDevReal(input({ devRealFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...DEV_REAL_RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...DEV_REAL_RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModeChatBridgeDevRealResult(allowed)).toBe(true)
    expect(isFreeModeChatBridgeDevRealResult(denied)).toBe(true)
  })

  it('does not contain chat send or direct provider/network execution paths', async () => {
    const source = await import('./freeModeChatBridgeDevReal?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
