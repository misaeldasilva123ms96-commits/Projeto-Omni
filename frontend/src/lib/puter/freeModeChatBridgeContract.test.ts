import { describe, expect, it } from 'vitest'
import {
  FREE_MODE_CHAT_BRIDGE_VERSION,
  decideFreeModeChatBridge,
  isFreeModeChatBridgeDecision,
  isPuterChatBridgeFlagEnabled,
} from './freeModeChatBridgeContract'

const DECISION_KEYS = [
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

const FORBIDDEN_OUTPUT_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing_config',
  'credential',
  'debug_payload',
  'env_var',
  'private_endpoint',
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
    requestedCapabilities: {},
    requestOptions: {},
    browserRuntimeAvailable: true,
    puterRuntimeAvailable: true,
    ...overrides,
  }
}

function expectDenied(overrides: Record<string, unknown>, reason: string) {
  const decision = decideFreeModeChatBridge(input(overrides))
  expect(decision.allowed).toBe(false)
  expect(decision.denied).toBe(true)
  expect(decision.reason).toBe(reason)
  expect(decision.runtime_truth.provider_attempted).toBe(false)
  expect(decision.runtime_truth.provider_succeeded).toBe(false)
  expect(decision.runtime_truth.sanitized_output).toBeNull()
  return decision
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_OUTPUT_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Free Mode chat bridge contract', () => {
  it('keeps the future chat bridge feature flag disabled unless explicitly enabled', () => {
    expect(isPuterChatBridgeFlagEnabled()).toBe(false)
    expect(isPuterChatBridgeFlagEnabled('')).toBe(false)
    expect(isPuterChatBridgeFlagEnabled('false')).toBe(false)
    expect(isPuterChatBridgeFlagEnabled('true')).toBe(true)
    expect(isPuterChatBridgeFlagEnabled('1')).toBe(true)
  })

  it('allows a contract decision only when all gates pass', () => {
    const decision = decideFreeModeChatBridge(input())

    expect(decision).toMatchObject({
      bridge_version: FREE_MODE_CHAT_BRIDGE_VERSION,
      allowed: true,
      denied: false,
      reason: 'selection_allowed',
      plan_mode: 'free',
      provider_family: 'experimental_free_provider',
      adapter_id: 'puter_browser_skeleton_adapter',
      quota_allowed: true,
      quota_exceeded: false,
      routing_allowed: true,
      feature_flag_allowed: true,
      runtime_allowed: true,
      puter_runtime_required: true,
      fallback_required: false,
    })
    expect(decision.runtime_truth).toMatchObject({
      access_layer_plan_mode: 'free',
      provider_family: 'experimental_free_provider',
      provider_attempted: false,
      provider_succeeded: false,
      provider_failed_reason: '',
      fallback_triggered: false,
      quota_allowed: true,
      quota_exceeded: false,
      routing_allowed: true,
      selected_adapter_id: 'experimental_free_adapter',
      boundary_version: 'access_snapshot_boundary_v1',
      snapshot_version: 'public_access_snapshot_v1',
      sanitized_output: null,
    })
  })

  it('denies non-Free plan mode', () => {
    expectDenied({ planMode: 'pro' }, 'not_free_mode')
  })

  it('denies when the Free Puter feature flag is false', () => {
    expectDenied({ experimentalFeatureEnabled: false }, 'feature_disabled')
  })

  it('denies when the chat bridge feature flag is false', () => {
    expectDenied({ chatBridgeFeatureEnabled: false }, 'chat_bridge_disabled')
  })

  it('denies denied or malformed boundary envelopes', () => {
    expectDenied({
      accessSnapshotEnvelope: {
        ...safeEnvelope({ ok: false, denied: true, reason: 'quota_exceeded' }),
        access_snapshot: {
          ...safeEnvelope().access_snapshot,
          routing_allowed: false,
        },
      },
    }, 'routing_denied')

    const malformed = safeEnvelope()
    delete (malformed as Record<string, unknown>).boundary_version
    expectDenied({ accessSnapshotEnvelope: malformed }, 'invalid_access_snapshot')
  })

  it('denies quota exceeded or not allowed states', () => {
    expectDenied({
      accessSnapshotEnvelope: {
        ...safeEnvelope(),
        access_snapshot: {
          ...safeEnvelope().access_snapshot,
          quota_exceeded: true,
        },
      },
    }, 'quota_exceeded')

    expectDenied({
      accessSnapshotEnvelope: {
        ...safeEnvelope(),
        access_snapshot: {
          ...safeEnvelope().access_snapshot,
          quota_allowed: false,
        },
      },
    }, 'quota_exceeded')
  })

  it('denies routing false and wrong provider family', () => {
    expectDenied({
      accessSnapshotEnvelope: {
        ...safeEnvelope(),
        access_snapshot: {
          ...safeEnvelope().access_snapshot,
          routing_allowed: false,
        },
      },
    }, 'routing_denied')

    expectDenied({
      accessSnapshotEnvelope: {
        ...safeEnvelope(),
        access_snapshot: {
          ...safeEnvelope().access_snapshot,
          selected_provider_family: 'managed_provider',
        },
      },
    }, 'provider_family_not_allowed')
  })

  it('denies missing browser runtime and missing Puter runtime safely', () => {
    expectDenied({ browserRuntimeAvailable: false }, 'non_browser_runtime')
    const missingPuter = expectDenied({ puterRuntimeAvailable: false }, 'puter_runtime_unavailable')
    expect(missingPuter.puter_runtime_required).toBe(true)
    expect(missingPuter.fallback_required).toBe(true)
    expect(missingPuter.runtime_truth.fallback_triggered).toBe(true)
  })

  it('denies invalid token estimates', () => {
    expectDenied({ inputTokenEstimate: -1 }, 'invalid_token_estimate')
    expectDenied({ outputTokenBudgetEstimate: 1.5 }, 'invalid_token_estimate')
    expectDenied({ dailyTokenUsage: '125' }, 'invalid_token_estimate')
  })

  it('denies tools, files, function-calling, long memory, and sensitive tools', () => {
    for (const requestedCapabilities of [
      { tools: true },
      { files: true },
      { function_calling: true },
      { long_memory: true },
      { sensitive_tools: true },
    ]) {
      const decision = decideFreeModeChatBridge(input({ requestedCapabilities }))
      expect(decision.allowed).toBe(false)
      expect(decision.denied).toBe(true)
      expect(['unsupported_capability', 'unsafe_request_options']).toContain(decision.reason)
    }
  })

  it('denies forbidden override and sensitive request option fields', () => {
    for (const requestOptions of [
      { provider_mode: 'managed' },
      { provider_family: 'managed_provider' },
      { adapter_id: 'managed' },
      { selected_adapter_id: 'managed' },
      { policy_overrides: { provider_mode: 'managed' } },
      { daily_token_limit: 999999 },
      { api_key: 'hidden' },
      { access_token: 'hidden' },
      { credential: 'hidden' },
      { env: 'hidden' },
      { provider_config: { model: 'hidden' } },
      { private_endpoint: 'hidden' },
      { billing: true },
      { debug: true },
      { tools: true },
      { files: true },
      { function_calling: true },
      { raw_provider_payload: { text: 'hidden' } },
      { raw_provider_response: { text: 'hidden' } },
    ]) {
      expectDenied({ requestOptions }, 'unsafe_request_options')
    }
  })

  it('returns exact public decision and runtime truth key sets', () => {
    const allowed = decideFreeModeChatBridge(input())
    const denied = decideFreeModeChatBridge(input({ puterRuntimeAvailable: false }))

    expect(Object.keys(allowed).sort()).toEqual([...DECISION_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...DECISION_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModeChatBridgeDecision(allowed)).toBe(true)
    expect(isFreeModeChatBridgeDecision(denied)).toBe(true)
  })

  it('keeps runtime truth public-safe and never marks provider execution', () => {
    const decisions = [
      decideFreeModeChatBridge(input()),
      decideFreeModeChatBridge(input({ puterRuntimeAvailable: false })),
      decideFreeModeChatBridge(input({ requestOptions: { api_key: 'sk-hiddenhidden' } })),
    ]

    for (const decision of decisions) {
      expect(decision.runtime_truth.provider_attempted).toBe(false)
      expect(decision.runtime_truth.provider_succeeded).toBe(false)
      expect(decision.runtime_truth.sanitized_output).toBeNull()
      expectPublicSafe(decision)
    }
  })

  it('does not import chat transport or contain provider/network execution paths', async () => {
    const source = await import('./freeModeChatBridgeContract?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
  })
})
