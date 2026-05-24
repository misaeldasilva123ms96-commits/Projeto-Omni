import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_CHAT_BRIDGE_MOCK_OUTPUT,
  FREE_MODE_CHAT_BRIDGE_MOCK_VERSION,
  isFreeModeChatBridgeMockResult,
  isPuterChatBridgeMockFlagEnabled,
  runFreeModeChatBridgeMock,
} from './freeModeChatBridgeMock'

const MOCK_RESULT_KEYS = [
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
      usage_date: '2026-05-23',
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
    mockFeatureEnabled: true,
    requestedCapabilities: {},
    requestOptions: {},
    browserRuntimeAvailable: true,
    puterRuntimeAvailable: true,
    ...overrides,
  }
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Free Mode chat bridge mock', () => {
  it('keeps the mock bridge flag disabled unless explicitly enabled', () => {
    expect(isPuterChatBridgeMockFlagEnabled()).toBe(false)
    expect(isPuterChatBridgeMockFlagEnabled('')).toBe(false)
    expect(isPuterChatBridgeMockFlagEnabled('false')).toBe(false)
    expect(isPuterChatBridgeMockFlagEnabled('true')).toBe(true)
    expect(isPuterChatBridgeMockFlagEnabled('1')).toBe(true)
  })

  it('returns denied when mock flag is false', () => {
    const result = runFreeModeChatBridgeMock(input({ mockFeatureEnabled: false }))

    expect(result.allowed).toBe(false)
    expect(result.denied).toBe(true)
    expect(result.reason).toBe('mock_bridge_disabled')
    expect(result.mock_enabled).toBe(false)
    expect(result.mock_succeeded).toBe(false)
    expect(result.sanitized_output).toBeNull()
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
  })

  it('returns denied when the contract denies', () => {
    const result = runFreeModeChatBridgeMock(input({ planMode: 'pro' }))

    expect(result.allowed).toBe(false)
    expect(result.denied).toBe(true)
    expect(result.reason).toBe('not_free_mode')
    expect(result.mock_succeeded).toBe(false)
    expect(result.sanitized_output).toBeNull()
  })

  it('returns deterministic mock output when all gates pass', () => {
    const result = runFreeModeChatBridgeMock(input())

    expect(result).toMatchObject({
      mock_bridge_version: FREE_MODE_CHAT_BRIDGE_MOCK_VERSION,
      allowed: true,
      denied: false,
      reason: 'mock_allowed',
      mock_enabled: true,
      mock_succeeded: true,
      provider_family: 'experimental_free_provider',
      adapter_id: 'puter_browser_skeleton_adapter',
      fallback_required: false,
      sanitized_output: FREE_MODE_CHAT_BRIDGE_MOCK_OUTPUT,
    })
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.sanitized_output).toBeNull()
  })

  it('does not call real Puter or browser runtime functions', () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    const result = runFreeModeChatBridgeMock(input())

    expect(result.allowed).toBe(true)
    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('denies contract fail-closed cases without mock output', () => {
    for (const overrides of [
      { experimentalFeatureEnabled: false },
      { chatBridgeFeatureEnabled: false },
      { puterRuntimeAvailable: false },
      { browserRuntimeAvailable: false },
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
      { requestedCapabilities: { tools: true } },
      { requestedCapabilities: { files: true } },
      { requestedCapabilities: { function_calling: true } },
      { requestedCapabilities: { long_memory: true } },
      { requestOptions: { provider_config: { model: 'hidden' } } },
      { requestOptions: { private_endpoint: 'hidden' } },
      { requestOptions: { billing: true } },
      { requestOptions: { debug: true } },
      { requestOptions: { api_key: 'hidden' } },
      { requestOptions: { access_token: 'hidden' } },
      { requestOptions: { credential: 'hidden' } },
      { requestOptions: { raw_provider_payload: { text: 'hidden' } } },
    ]) {
      const result = runFreeModeChatBridgeMock(input(overrides))
      expect(result.allowed).toBe(false)
      expect(result.denied).toBe(true)
      expect(result.mock_succeeded).toBe(false)
      expect(result.sanitized_output).toBeNull()
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expect(result.runtime_truth.provider_succeeded).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('rejects mock prompt input instead of echoing it', () => {
    const result = runFreeModeChatBridgeMock(input({
      mockPrompt: 'sk-hidden api_key access_token provider_config private_endpoint billing debug stack',
    }))

    expect(result.allowed).toBe(false)
    expect(result.reason).toBe('unsafe_mock_input')
    expectPublicSafe(result)
  })

  it('returns exact public mock result and runtime truth key sets', () => {
    const allowed = runFreeModeChatBridgeMock(input())
    const denied = runFreeModeChatBridgeMock(input({ mockFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...MOCK_RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...MOCK_RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModeChatBridgeMockResult(allowed)).toBe(true)
    expect(isFreeModeChatBridgeMockResult(denied)).toBe(true)
  })

  it('does not contain real provider, chat, or network execution paths', async () => {
    const source = await import('./freeModeChatBridgeMock?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('invokestaticputerfreemodemanualharness')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
  })
})
