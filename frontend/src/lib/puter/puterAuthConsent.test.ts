import { describe, expect, it, vi } from 'vitest'
import {
  createPuterAuthConsentResult,
  isPuterAuthConsentResult,
  isPuterRuntimeLoadedForAuth,
  requestPuterAuthConsent,
} from './puterAuthConsent'

const RESULT_KEYS = [
  'ok',
  'status',
  'reason',
  'user_message',
  'retry_allowed',
  'manual_action_required',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
  'puter_runtime_loaded',
  'auth_api_available',
  'auth_attempted',
  'auth_completed',
  'auth_failed_reason',
  'consent_state',
  'raw_auth_payload_exposed',
  'provider_attempted',
  'provider_succeeded',
  'raw_provider_payload_exposed',
]

const FORBIDDEN_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'cookie',
  'credential',
  'debug',
  'env',
  'localstorage',
  'private_endpoint',
  'provider_config',
  'request_payload',
  'secret',
  'sessionstorage',
  'sk-',
  'stack',
  'token',
  'traceback',
]

function authRuntime(signIn = vi.fn()) {
  return {
    window: {
      puter: {
        auth: {
          signIn,
        },
        ai: {
          chat: vi.fn(),
        },
      },
    },
  }
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Puter auth consent helper', () => {
  it('creates an exact public-safe result shape', () => {
    const result = createPuterAuthConsentResult()

    expect(Object.keys(result).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(result.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
    expect(isPuterAuthConsentResult(result)).toBe(true)
    expectPublicSafe(result)
  })

  it('does not call auth on import or result construction', () => {
    const signIn = vi.fn()

    createPuterAuthConsentResult('not_invoked', {
      puter_runtime_loaded: true,
      auth_api_available: true,
    })

    expect(signIn).not.toHaveBeenCalled()
  })

  it('detects whether the Puter runtime is loaded for auth', () => {
    expect(isPuterRuntimeLoadedForAuth({})).toBe(false)
    expect(isPuterRuntimeLoadedForAuth({ window: {} })).toBe(false)
    expect(isPuterRuntimeLoadedForAuth({ window: { puter: {} } })).toBe(true)
    expect(isPuterRuntimeLoadedForAuth({ puter: {} })).toBe(true)
  })

  it('returns runtime_not_loaded without attempting auth when runtime is missing', async () => {
    const result = await requestPuterAuthConsent({ runtime: {} })

    expect(result.status).toBe('runtime_not_loaded')
    expect(result.runtime_truth.auth_attempted).toBe(false)
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
  })

  it('returns auth_api_unavailable when signIn is missing', async () => {
    const result = await requestPuterAuthConsent({ runtime: { window: { puter: { auth: {} } } } })

    expect(result.status).toBe('auth_api_unavailable')
    expect(result.runtime_truth.puter_runtime_loaded).toBe(true)
    expect(result.runtime_truth.auth_api_available).toBe(false)
    expect(result.runtime_truth.auth_attempted).toBe(false)
    expectPublicSafe(result)
  })

  it('invokes puter.auth.signIn once and discards a raw success payload', async () => {
    const signIn = vi.fn().mockResolvedValue({
      access_token: 'sk-test-token',
      raw_auth_response: 'provider_config private_endpoint billing debug stack',
    })
    const runtime = authRuntime(signIn)

    const result = await requestPuterAuthConsent({ runtime })

    expect(signIn).toHaveBeenCalledTimes(1)
    expect(runtime.window.puter.ai.chat).not.toHaveBeenCalled()
    expect(result.status).toBe('consent_or_auth_completed')
    expect(result.ok).toBe(true)
    expect(result.runtime_truth.auth_completed).toBe(true)
    expect(result.runtime_truth.raw_auth_payload_exposed).toBe(false)
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
    expectPublicSafe(result)
  })

  it('returns safe cancelled state without exposing the rejection payload', async () => {
    const error = new Error('cancelled with sk-test-token provider_config stack')
    const signIn = vi.fn().mockRejectedValue(error)
    const runtime = authRuntime(signIn)

    const result = await requestPuterAuthConsent({ runtime })

    expect(result.status).toBe('consent_or_auth_cancelled')
    expect(result.ok).toBe(false)
    expect(result.runtime_truth.auth_attempted).toBe(true)
    expect(result.runtime_truth.auth_completed).toBe(false)
    expectPublicSafe(result)
  })

  it('returns safe failed state without exposing raw errors', async () => {
    const signIn = vi.fn().mockRejectedValue(new Error('sk-test-token private_endpoint traceback'))

    const result = await requestPuterAuthConsent({ runtime: authRuntime(signIn) })

    expect(result.status).toBe('consent_or_auth_failed_safe')
    expect(result.runtime_truth.auth_failed_reason).toBe('consent_or_auth_failed_safe')
    expectPublicSafe(result)
  })

  it('returns pending state when signIn does not settle within the safe timeout', async () => {
    const signIn = vi.fn().mockReturnValue(new Promise(() => undefined))

    const result = await requestPuterAuthConsent({
      runtime: authRuntime(signIn),
      timeoutMs: 1,
    })

    expect(result.status).toBe('consent_or_auth_pending')
    expect(result.runtime_truth.auth_attempted).toBe(true)
    expect(result.runtime_truth.auth_completed).toBe(false)
    expect(result.retry_allowed).toBe(false)
  })

  it('contains no direct provider chat or network paths', async () => {
    const source = await import('./puterAuthConsent?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})
