import { describe, expect, it, vi } from 'vitest'
import {
  FREE_MODE_PILOT_ALLOWLISTED_VERSION,
  decideFreeModePilotAllowlisted,
  isFreeModePilotAllowlistedResult,
  isPuterFreePilotAllowlistedFlagEnabled,
} from './freeModePilotAllowlisted'

const RESULT_KEYS = [
  'allowlisted_pilot_version',
  'allowed',
  'denied',
  'reason',
  'allowlisted_pilot',
  'pilot_enabled',
  'pilot_eligible',
  'provider_family',
  'fallback_required',
  'sanitized_output',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
  'allowlisted_pilot',
  'allowlist_required',
  'allowlist_matched',
  'pilot_enabled',
  'pilot_eligible',
  'pilot_denied_reason',
  'rollback_active',
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

function input(overrides: Record<string, unknown> = {}) {
  return {
    planMode: 'free',
    experimentalFeatureEnabled: true,
    chatBridgeFeatureEnabled: true,
    devRealFeatureEnabled: true,
    pilotFeatureEnabled: true,
    allowlistedPilotFeatureEnabled: true,
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
    puterRuntimeAvailable: true,
    ...overrides,
  }
}

function expectDenied(overrides: Record<string, unknown>, reason: string) {
  const result = decideFreeModePilotAllowlisted(input(overrides))
  expect(result.allowed).toBe(false)
  expect(result.denied).toBe(true)
  expect(result.reason).toBe(reason)
  expect(result.sanitized_output).toBeNull()
  expect(result.runtime_truth.provider_attempted).toBe(false)
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

describe('Free Mode allowlisted pilot contract', () => {
  it('keeps the allowlisted pilot flag disabled unless explicitly enabled', () => {
    expect(isPuterFreePilotAllowlistedFlagEnabled()).toBe(false)
    expect(isPuterFreePilotAllowlistedFlagEnabled('')).toBe(false)
    expect(isPuterFreePilotAllowlistedFlagEnabled('false')).toBe(false)
    expect(isPuterFreePilotAllowlistedFlagEnabled('true')).toBe(true)
    expect(isPuterFreePilotAllowlistedFlagEnabled('1')).toBe(true)
  })

  it('denies when the allowlisted pilot flag is false', () => {
    const result = expectDenied({ allowlistedPilotFeatureEnabled: false }, 'allowlisted_pilot_disabled')
    expect(result.allowlisted_pilot).toBe(false)
    expect(result.runtime_truth.allowlisted_pilot).toBe(false)
  })

  it('denies when allowlist is missing or mismatched', () => {
    const missing = expectDenied({ allowlistMatched: undefined }, 'allowlist_not_matched')
    expect(missing.runtime_truth.allowlist_required).toBe(true)
    expect(missing.runtime_truth.allowlist_matched).toBe(false)

    const mismatch = expectDenied({ allowlistMatched: false }, 'allowlist_not_matched')
    expect(mismatch.runtime_truth.allowlist_required).toBe(true)
    expect(mismatch.runtime_truth.allowlist_matched).toBe(false)
  })

  it('denies inherited pilot contract fail-closed cases', () => {
    for (const overrides of [
      { rollbackActive: true, reason: 'rollback_active' },
      { pilotFeatureEnabled: false, reason: 'pilot_flag_disabled' },
      { planMode: 'pro', reason: 'not_free_mode' },
      { quotaExceeded: true, reason: 'quota_exceeded' },
      { quotaAllowed: false, reason: 'quota_exceeded' },
      { routingAllowed: false, reason: 'routing_denied' },
      { selectedProviderFamily: 'managed_provider', reason: 'provider_family_not_allowed' },
      { consentState: 'provider_consent_or_auth_pending', reason: 'provider_consent_or_auth_pending' },
    ]) {
      const { reason, ...inputOverrides } = overrides
      const result = expectDenied(inputOverrides, reason as string)
      expectPublicSafe(result)
    }
  })

  it('denies when Puter runtime is unavailable for future real-path readiness', () => {
    const result = expectDenied({ puterRuntimeAvailable: false }, 'puter_runtime_unavailable')
    expect(result.allowlisted_pilot).toBe(true)
    expect(result.runtime_truth.provider_attempted).toBe(false)
  })

  it('denies unsafe fields including camelCase, kebab-case, spaced variants, and capabilities', () => {
    for (const requestOptions of [
      { apiKey: 'hidden' },
      { APIKey: 'hidden' },
      { 'api-key': 'hidden' },
      { 'api key': 'hidden' },
      { accessToken: 'hidden' },
      { providerConfig: { model: 'hidden' } },
      { 'private-endpoint': 'hidden' },
      { 'raw provider payload': { text: 'hidden' } },
      { policyOverrides: { providerMode: 'managed' } },
    ]) {
      const result = expectDenied({ requestOptions }, 'unsafe_request_options')
      expectPublicSafe(result)
    }

    for (const requestedCapabilities of [
      { tools: true },
      { files: true },
      { functionCalling: true },
      { 'long-memory': true },
      { sensitiveTools: true },
    ]) {
      const result = decideFreeModePilotAllowlisted(input({ requestedCapabilities }))
      expect(result.allowed).toBe(false)
      expect(result.denied).toBe(true)
      expect(['unsafe_request_options', 'unsupported_capability']).toContain(result.reason)
      expect(result.runtime_truth.provider_attempted).toBe(false)
      expectPublicSafe(result)
    }
  })

  it('returns allowlisted readiness only when all gates pass without provider execution', () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    const result = decideFreeModePilotAllowlisted(input())

    expect(result).toMatchObject({
      allowlisted_pilot_version: FREE_MODE_PILOT_ALLOWLISTED_VERSION,
      allowed: true,
      denied: false,
      reason: 'allowlisted_pilot_ready',
      allowlisted_pilot: true,
      pilot_enabled: true,
      pilot_eligible: true,
      provider_family: 'experimental_free_provider',
      fallback_required: false,
      sanitized_output: null,
    })
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.sanitized_output_present).toBe(false)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('returns exact public result and runtime truth key sets', () => {
    const allowed = decideFreeModePilotAllowlisted(input())
    const denied = decideFreeModePilotAllowlisted(input({ allowlistedPilotFeatureEnabled: false }))

    expect(Object.keys(allowed).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(denied).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(allowed.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(Object.keys(denied.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isFreeModePilotAllowlistedResult(allowed)).toBe(true)
    expect(isFreeModePilotAllowlistedResult(denied)).toBe(true)
  })

  it('does not echo raw IDs, unsafe keys, or sensitive fragments', () => {
    const result = decideFreeModePilotAllowlisted(input({
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

    await import('./freeModePilotAllowlisted')

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('does not contain chat, direct provider, internal-real, or network execution paths', async () => {
    const source = await import('./freeModePilotAllowlisted?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('freemodepilotinternalreal')
    expect(lowered).not.toContain('runfreemodepilotinternalreal')
    expect(lowered).not.toContain('invokeputerfreemodemanualharness')
    expect(lowered).not.toContain('freemodeputermanualharness')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
