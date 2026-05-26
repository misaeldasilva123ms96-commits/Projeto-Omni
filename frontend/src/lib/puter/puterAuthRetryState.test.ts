import { describe, expect, it } from 'vitest'
import {
  PUTER_AUTH_RETRY_STATE_VERSION,
  createPuterAuthRetryState,
  isPuterAuthRetryState,
  retryStateFromManualHarnessResult,
} from './puterAuthRetryState'
import { PUTER_MANUAL_HARNESS_VERSION } from './freeModePuterManualHarness'

const RETRY_STATE_KEYS = [
  'state_version',
  'status',
  'reason',
  'user_message',
  'sanitized_output',
  'runtime_truth',
]

const RETRY_RUNTIME_TRUTH_KEYS = [
  'auth_completed',
  'retry_allowed',
  'retry_attempted',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'raw_auth_payload_exposed',
  'raw_provider_payload_exposed',
  'sanitized_output_present',
]

const FORBIDDEN_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'cookie',
  'credential',
  'debug',
  'env',
  'private_endpoint',
  'provider_config',
  'request_payload',
  'secret',
  'sk-',
  'stack',
  'traceback',
]

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

function harnessResult(overrides = {}) {
  return {
    ok: false,
    denied: true,
    reason: 'puter_call_failed',
    provider_family: 'experimental_free_provider',
    adapter_id: 'puter_browser_skeleton_adapter',
    sanitized_text: '',
    experimental: true,
    harness_version: PUTER_MANUAL_HARNESS_VERSION,
    ...overrides,
  } as const
}

describe('Puter auth retry state', () => {
  it('returns an exact public-safe shape', () => {
    const state = createPuterAuthRetryState()

    expect(state.state_version).toBe(PUTER_AUTH_RETRY_STATE_VERSION)
    expect(Object.keys(state).sort()).toEqual([...RETRY_STATE_KEYS].sort())
    expect(Object.keys(state.runtime_truth).sort()).toEqual([...RETRY_RUNTIME_TRUTH_KEYS].sort())
    expect(isPuterAuthRetryState(state)).toBe(true)
    expectPublicSafe(state)
  })

  it('keeps retry denied before auth completion', () => {
    const state = createPuterAuthRetryState({ authCompleted: false })

    expect(state.status).toBe('auth_required')
    expect(state.runtime_truth.auth_completed).toBe(false)
    expect(state.runtime_truth.retry_allowed).toBe(false)
    expect(state.runtime_truth.retry_attempted).toBe(false)
    expect(state.runtime_truth.provider_attempted).toBe(false)
  })

  it('marks retry ready after auth completion without provider attempt', () => {
    const state = createPuterAuthRetryState({ authCompleted: true })

    expect(state.status).toBe('retry_ready')
    expect(state.runtime_truth.auth_completed).toBe(true)
    expect(state.runtime_truth.retry_allowed).toBe(true)
    expect(state.runtime_truth.retry_attempted).toBe(false)
    expect(state.runtime_truth.provider_attempted).toBe(false)
  })

  it('maps sanitized provider success without raw payload exposure', () => {
    const state = retryStateFromManualHarnessResult(harnessResult({
      ok: true,
      denied: false,
      reason: 'ok',
      sanitized_text: 'safe text with sk-proj-abcdefghijkl hidden',
    }), true)

    expect(state.status).toBe('provider_succeeded_sanitized')
    expect(state.sanitized_output).toBe('safe text with [redacted] hidden')
    expect(state.runtime_truth.provider_attempted).toBe(true)
    expect(state.runtime_truth.provider_succeeded).toBe(true)
    expect(state.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expectPublicSafe(state)
  })

  it('maps provider failure safely', () => {
    const state = retryStateFromManualHarnessResult(harnessResult({
      reason: 'puter_call_failed',
    }), true)

    expect(state.status).toBe('provider_failed_safe')
    expect(state.runtime_truth.provider_attempted).toBe(true)
    expect(state.runtime_truth.provider_succeeded).toBe(false)
    expect(state.runtime_truth.provider_failed_reason).toBe('puter_call_failed')
    expectPublicSafe(state)
  })
})
