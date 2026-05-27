import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  checkPuterAuthStatus,
  getInitialPuterAuthStatusOutput,
  isPuterAuthStatusOutput,
} from './puterAuthStatus'

const OUTPUT_KEYS = [
  'ok',
  'status',
  'reason',
  'user_message',
  'is_signed_in',
  'user_present',
  'sanitized_user',
  'retry_allowed',
  'manual_action_required',
  'runtime_truth',
]

const RUNTIME_TRUTH_KEYS = [
  'puter_runtime_loaded',
  'auth_api_available',
  'auth_status_checked',
  'is_signed_in',
  'user_present',
  'sanitized_user_present',
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
  'password',
  'private_endpoint',
  'provider_config',
  'secret',
  'sessionstorage',
  'sk-',
  'stack',
  'token',
  'traceback',
]

function puterRuntime(auth: Record<string, unknown>, overrides: Record<string, unknown> = {}) {
  const runtime = {
    auth,
    ...overrides,
  }
  ;(window as Window & { puter?: unknown }).puter = runtime
  return runtime
}

function expectExactKeys(value: unknown) {
  expect(isPuterAuthStatusOutput(value)).toBe(true)
  const result = value as ReturnType<typeof getInitialPuterAuthStatusOutput>
  expect(Object.keys(result).sort()).toEqual([...OUTPUT_KEYS].sort())
  expect(Object.keys(result.runtime_truth).sort()).toEqual([...RUNTIME_TRUTH_KEYS].sort())
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Puter auth status check', () => {
  beforeEach(() => {
    delete (window as Window & { puter?: unknown }).puter
    vi.clearAllMocks()
  })

  afterEach(() => {
    delete (window as Window & { puter?: unknown }).puter
    vi.restoreAllMocks()
  })

  it('returns not_invoked without calling Puter APIs', () => {
    const isSignedIn = vi.fn()
    puterRuntime({ isSignedIn })

    const result = getInitialPuterAuthStatusOutput()

    expect(result.status).toBe('not_invoked')
    expect(result.runtime_truth.auth_status_checked).toBe(false)
    expect(isSignedIn).not.toHaveBeenCalled()
    expectExactKeys(result)
    expectPublicSafe(result)
  })

  it('denies when runtime is absent', async () => {
    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('runtime_not_loaded')
    expect(result.runtime_truth.puter_runtime_loaded).toBe(false)
    expect(result.runtime_truth.auth_status_checked).toBe(false)
    expectExactKeys(result)
  })

  it('denies spoofed non-browser runtime and does not call isSignedIn', async () => {
    const isSignedIn = vi.fn().mockReturnValue(true)
    const spoofedRuntime = {
      auth: { isSignedIn },
    }

    const result = await checkPuterAuthStatus({ puter: spoofedRuntime })

    expect(result.status).toBe('runtime_not_loaded')
    expect(isSignedIn).not.toHaveBeenCalled()
  })

  it('returns auth_api_unavailable when auth is missing', async () => {
    puterRuntime({})

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('auth_api_unavailable')
    expect(result.runtime_truth.puter_runtime_loaded).toBe(true)
    expect(result.runtime_truth.auth_api_available).toBe(false)
  })

  it('calls isSignedIn exactly once and does not call getUser when signed out', async () => {
    const isSignedIn = vi.fn().mockReturnValue(false)
    const getUser = vi.fn()
    puterRuntime({ isSignedIn, getUser })

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('signed_out')
    expect(result.ok).toBe(true)
    expect(result.is_signed_in).toBe(false)
    expect(isSignedIn).toHaveBeenCalledTimes(1)
    expect(getUser).not.toHaveBeenCalled()
  })

  it('calls getUser at most once when signed in and returns only presence booleans', async () => {
    const isSignedIn = vi.fn().mockReturnValue(true)
    const getUser = vi.fn().mockResolvedValue({
      id: 'raw-id-123',
      username: 'raw-user',
      email: 'raw@example.test',
      token: 'raw-token',
    })
    puterRuntime({ isSignedIn, getUser })

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('signed_in_sanitized')
    expect(result.is_signed_in).toBe(true)
    expect(result.user_present).toBe(true)
    expect(getUser).toHaveBeenCalledTimes(1)
    expect(result.sanitized_user).toEqual({
      user_present: true,
      username_present: true,
      email_present: true,
      id_present: true,
    })
    expect(JSON.stringify(result)).not.toContain('raw-id-123')
    expect(JSON.stringify(result)).not.toContain('raw-user')
    expect(JSON.stringify(result)).not.toContain('raw@example.test')
    expect(JSON.stringify(result)).not.toContain('raw-token')
    expectExactKeys(result)
    expectPublicSafe(result)
  })

  it('returns user_unavailable_safe when signed in but getUser is absent', async () => {
    puterRuntime({ isSignedIn: vi.fn().mockReturnValue(true) })

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('user_unavailable_safe')
    expect(result.is_signed_in).toBe(true)
    expect(result.user_present).toBe(false)
    expect(result.sanitized_user).toBeNull()
  })

  it('returns auth_status_check_failed_safe when isSignedIn throws', async () => {
    puterRuntime({
      isSignedIn: vi.fn().mockImplementation(() => {
        throw new Error('unsafe raw stack')
      }),
      getUser: vi.fn(),
    })

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('auth_status_check_failed_safe')
    expect(result.ok).toBe(false)
    expectPublicSafe(result)
  })

  it('returns user_unavailable_safe when getUser throws', async () => {
    puterRuntime({
      isSignedIn: vi.fn().mockReturnValue(true),
      getUser: vi.fn().mockRejectedValue(new Error('raw getUser stack')),
    })

    const result = await checkPuterAuthStatus()

    expect(result.status).toBe('user_unavailable_safe')
    expect(result.runtime_truth.provider_attempted).toBe(false)
    expect(result.runtime_truth.provider_succeeded).toBe(false)
    expect(result.runtime_truth.raw_provider_payload_exposed).toBe(false)
  })

  it('does not call puter.ai.chat during status check', async () => {
    const chat = vi.fn()
    puterRuntime({
      isSignedIn: vi.fn().mockReturnValue(true),
      getUser: vi.fn().mockResolvedValue({ id: 'safe' }),
    }, {
      ai: { chat },
    })

    await checkPuterAuthStatus()

    expect(chat).not.toHaveBeenCalled()
  })

  it('does not add direct network primitives to the source', async () => {
    const source = await import('./puterAuthStatus?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('sendbeacon')
    expect(lowered).not.toContain('websocket')
    expect(lowered).not.toContain('localstorage')
    expect(lowered).not.toContain('sessionstorage')
    expect(lowered).not.toContain('document.cookie')
  })
})
