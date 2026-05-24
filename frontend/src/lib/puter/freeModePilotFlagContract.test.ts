import { describe, expect, it } from 'vitest'
import {
  FREE_MODE_PILOT_FLAG_CONTRACT_VERSION,
  decideFreeModePilotFlag,
  isFreeModePilotFlagDecision,
  isPuterFreePilotFlagEnabled,
} from './freeModePilotFlagContract'

const DECISION_KEYS = [
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
]

const RUNTIME_TRUTH_KEYS = [
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
]

const FORBIDDEN_OUTPUT_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'credential',
  'debug',
  'env_var',
  'private_endpoint',
  'process.env',
  'provider_config',
  'request_payload',
  'secret',
  'sk-',
  'stack',
  'traceback',
  'user@example.com',
]

function input(overrides: Record<string, unknown> = {}) {
  return {
    planMode: 'free',
    experimentalFeatureEnabled: true,
    chatBridgeFeatureEnabled: true,
    devRealFeatureEnabled: true,
    pilotFeatureEnabled: true,
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
    ...overrides,
  }
}

function expectDenied(overrides: Record<string, unknown>, reason: string) {
  const decision = decideFreeModePilotFlag(input(overrides))
  expect(decision.pilot_eligible).toBe(false)
  expect(decision.denied).toBe(true)
  expect(decision.reason).toBe(reason)
  expect(decision.runtime_truth.provider_attempted).toBe(false)
  expect(decision.runtime_truth.provider_succeeded).toBe(false)
  expect(decision.runtime_truth.raw_provider_payload_exposed).toBe(false)
  expect(decision.runtime_truth.sanitized_output_present).toBe(false)
  return decision
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

describe('Free Mode pilot flag contract', () => {
  it('keeps the pilot feature flag disabled unless explicitly enabled', () => {
    expect(isPuterFreePilotFlagEnabled()).toBe(false)
    expect(isPuterFreePilotFlagEnabled('')).toBe(false)
    expect(isPuterFreePilotFlagEnabled('false')).toBe(false)
    expect(isPuterFreePilotFlagEnabled('true')).toBe(true)
    expect(isPuterFreePilotFlagEnabled('1')).toBe(true)
  })

  it('allows a pilot decision when all gates pass', () => {
    const decision = decideFreeModePilotFlag(input())

    expect(decision).toMatchObject({
      pilot_enabled: true,
      pilot_eligible: true,
      denied: false,
      reason: 'pilot_allowed',
      plan_mode: 'free',
      provider_family: 'experimental_free_provider',
      quota_allowed: true,
      routing_allowed: true,
      consent_state: 'ready',
      rollback_active: false,
      allowlist_required: false,
      allowlist_matched: false,
      feature_flag_allowed: true,
      pilot_version: FREE_MODE_PILOT_FLAG_CONTRACT_VERSION,
    })
    expect(decision.runtime_truth).toMatchObject({
      pilot_enabled: true,
      pilot_eligible: true,
      pilot_denied_reason: '',
      access_layer_plan_mode: 'free',
      provider_family: 'experimental_free_provider',
      provider_attempted: false,
      provider_succeeded: false,
      provider_failed_reason: '',
      fallback_triggered: false,
      quota_allowed: true,
      quota_exceeded: false,
      routing_allowed: true,
      consent_state: 'ready',
      selected_adapter_id: 'experimental_free_adapter',
      boundary_version: 'access_snapshot_boundary_v1',
      snapshot_version: 'public_access_snapshot_v1',
      sanitized_output_present: false,
      raw_provider_payload_exposed: false,
    })
  })

  it('denies when the pilot flag is false', () => {
    const decision = expectDenied({ pilotFeatureEnabled: false }, 'pilot_flag_disabled')
    expect(decision.pilot_enabled).toBe(false)
    expect(decision.feature_flag_allowed).toBe(false)
  })

  it('denies when rollback is active', () => {
    const decision = expectDenied({ rollbackActive: true }, 'rollback_active')
    expect(decision.rollback_active).toBe(true)
    expect(decision.pilot_enabled).toBe(false)
  })

  it('denies non-Free plan mode without echoing raw input', () => {
    expectDenied({ planMode: 'pro' }, 'not_free_mode')

    const malicious = 'sk-test-api_key-access_token-provider_config-private_endpoint-billing-debug-process.env-stack-traceback'
    const decision = expectDenied({ planMode: malicious }, 'not_free_mode')
    expect(decision.plan_mode).toBe('unknown')
    expect(decision.runtime_truth.access_layer_plan_mode).toBe('unknown')
    expectNoEcho(decision, malicious.split('-'))
  })

  it('denies when required lower-level flags are false', () => {
    expectDenied({ experimentalFeatureEnabled: false }, 'feature_disabled')
    expectDenied({ chatBridgeFeatureEnabled: false }, 'chat_bridge_disabled')
    expectDenied({ devRealFeatureEnabled: false }, 'dev_real_bridge_disabled')
  })

  it('denies when allowlist is required but not matched and allows when matched', () => {
    const denied = expectDenied({ allowlistRequired: true, allowlistMatched: false }, 'allowlist_not_matched')
    expect(denied.allowlist_required).toBe(true)
    expect(denied.allowlist_matched).toBe(false)

    const allowed = decideFreeModePilotFlag(input({ allowlistRequired: true, allowlistMatched: true }))
    expect(allowed.pilot_eligible).toBe(true)
    expect(allowed.denied).toBe(false)
    expect(allowed.allowlist_required).toBe(true)
    expect(allowed.allowlist_matched).toBe(true)
  })

  it('denies when an explicit pilot eligibility marker is false', () => {
    expectDenied({ pilotEligible: false }, 'pilot_not_eligible')
  })

  it('denies quota exceeded or not allowed states', () => {
    expectDenied({ quotaExceeded: true }, 'quota_exceeded')
    expectDenied({ quotaAllowed: false }, 'quota_exceeded')
  })

  it('denies routing false and wrong provider family', () => {
    expectDenied({ routingAllowed: false }, 'routing_denied')

    const decision = expectDenied({ selectedProviderFamily: 'managed_provider' }, 'provider_family_not_allowed')
    expect(decision.provider_family).toBe('')
    expect(decision.runtime_truth.provider_family).toBe('')
  })

  it('denies consent or auth pending states safely', () => {
    for (const consentState of [
      'provider_consent_or_auth_pending',
      'consent_pending',
      'consent_required',
      'auth_pending',
      'auth_required',
    ]) {
      const decision = expectDenied({ consentState }, 'provider_consent_or_auth_pending')
      expect(decision.consent_state).toBe(consentState)
      expectPublicSafe(decision)
    }
  })

  it('denies malformed or unknown state safely', () => {
    expectDenied({ consentState: 'unexpected' }, 'invalid_consent_state')
    expectDenied({ selectedAdapterId: 'wrong_adapter' }, 'invalid_pilot_state')
    expectDenied({ boundaryVersion: 'wrong_boundary' }, 'invalid_pilot_state')
    expectDenied({ snapshotVersion: 'wrong_snapshot' }, 'invalid_pilot_state')
  })

  it('denies tools, files, function-calling, long memory, and sensitive tools', () => {
    for (const requestedCapabilities of [
      { tools: true },
      { files: true },
      { function_calling: true },
      { long_memory: true },
      { sensitive_tools: true },
    ]) {
      const decision = decideFreeModePilotFlag(input({ requestedCapabilities }))
      expect(decision.pilot_eligible).toBe(false)
      expect(decision.denied).toBe(true)
      expect(['unsupported_capability', 'unsafe_request_options']).toContain(decision.reason)
      expectPublicSafe(decision)
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

  it('does not echo raw IDs or sensitive-looking string fields', () => {
    const malicious = 'sk-test-api_key-access_token-provider_config-private_endpoint-billing-debug-process.env-stack-traceback-user@example.com'
    const decision = decideFreeModePilotFlag(input({
      planMode: malicious,
      selectedProviderFamily: malicious,
      selectedAdapterId: malicious,
      boundaryVersion: malicious,
      snapshotVersion: malicious,
      consentState: malicious,
      requestOptions: {
        publicSessionId: malicious,
      },
    }))

    expect(decision.plan_mode).toBe('unknown')
    expect(decision.provider_family).toBe('')
    expect(decision.consent_state).toBe('unknown')
    expect(decision.runtime_truth.selected_adapter_id).toBe('')
    expect(decision.runtime_truth.boundary_version).toBe('')
    expect(decision.runtime_truth.snapshot_version).toBe('')
    expectNoEcho(decision, malicious.split('-'))
    expectPublicSafe(decision)
  })

  it('returns exact public decision and runtime truth key sets', () => {
    const allowed = decideFreeModePilotFlag(input())
    const denied = decideFreeModePilotFlag(input({ pilotFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...DECISION_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...DECISION_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModePilotFlagDecision(allowed)).toBe(true)
    expect(isFreeModePilotFlagDecision(denied)).toBe(true)
  })

  it('keeps runtime truth public-safe and never marks provider execution', () => {
    const decisions = [
      decideFreeModePilotFlag(input()),
      decideFreeModePilotFlag(input({ consentState: 'auth_pending' })),
      decideFreeModePilotFlag(input({ requestOptions: { api_key: 'sk-hiddenhidden' } })),
    ]

    for (const decision of decisions) {
      expect(decision.runtime_truth.provider_attempted).toBe(false)
      expect(decision.runtime_truth.provider_succeeded).toBe(false)
      expect(decision.runtime_truth.sanitized_output_present).toBe(false)
      expect(decision.runtime_truth.raw_provider_payload_exposed).toBe(false)
      expectPublicSafe(decision)
    }
  })

  it('does not import chat, Puter, dev-real bridge, manual harness, or network execution paths', async () => {
    const source = await import('./freeModePilotFlagContract?raw')
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
