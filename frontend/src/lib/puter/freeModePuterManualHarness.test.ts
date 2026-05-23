import { describe, expect, it, vi } from 'vitest'
import {
  PUTER_MANUAL_HARNESS_VERSION,
  invokePuterFreeModeManualHarness,
} from './freeModePuterManualHarness'

const RESULT_KEYS = [
  'ok',
  'denied',
  'reason',
  'provider_family',
  'adapter_id',
  'sanitized_text',
  'experimental',
  'harness_version',
]

const FORBIDDEN_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'credential',
  'debug',
  'env',
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

function puterRuntime(chat = vi.fn()) {
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

function deniedEnvelope(reason = 'quota_exceeded') {
  const envelope = safeEnvelope({
    ok: false,
    denied: true,
    reason,
  })
  return {
    ...envelope,
    access_snapshot: {
      ...envelope.access_snapshot,
      routing_allowed: false,
      fallback_allowed: true,
      decision_reason: reason,
    },
  }
}

function expectPublicSafe(value: unknown) {
  const serialized = JSON.stringify(value).toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(serialized).not.toContain(fragment)
  }
}

describe('Puter Free Mode manual harness', () => {
  it('is disabled by default and requires explicit manual invocation', async () => {
    const chat = vi.fn()

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(result.ok).toBe(false)
    expect(result.denied).toBe(true)
    expect(result.reason).toBe('manual_invocation_required')
    expect(chat).not.toHaveBeenCalled()
    expectPublicSafe(result)
  })

  it('does not call on import or default path', async () => {
    const chat = vi.fn()

    await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(chat).not.toHaveBeenCalled()
  })

  it('does not call when feature flag is false', async () => {
    const chat = vi.fn()

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: false,
      manualInvocation: true,
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(result.ok).toBe(false)
    expect(result.reason).toBe('feature_disabled')
    expect(chat).not.toHaveBeenCalled()
  })

  it('does not call when boundary envelope is denied or malformed', async () => {
    const chat = vi.fn()
    const malformed = safeEnvelope()
    delete (malformed as Record<string, unknown>).boundary_version

    for (const accessSnapshotEnvelope of [deniedEnvelope('quota_exceeded'), malformed]) {
      const result = await invokePuterFreeModeManualHarness({
        accessSnapshotEnvelope,
        experimentalFeatureEnabled: true,
        manualInvocation: true,
        prompt: 'hello',
        runtime: puterRuntime(chat),
      })

      expect(result.ok).toBe(false)
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('does not call when plan or provider family is not Free experimental', async () => {
    const nonFree = safeEnvelope({
      access_snapshot: {
        ...safeEnvelope().access_snapshot,
        plan_mode: 'pro',
      },
    })
    const wrongFamily = safeEnvelope({
      access_snapshot: {
        ...safeEnvelope().access_snapshot,
        selected_provider_family: 'managed_provider',
      },
    })

    for (const accessSnapshotEnvelope of [nonFree, wrongFamily]) {
      const chat = vi.fn()
      const result = await invokePuterFreeModeManualHarness({
        accessSnapshotEnvelope,
        experimentalFeatureEnabled: true,
        manualInvocation: true,
        prompt: 'hello',
        runtime: puterRuntime(chat),
      })

      expect(result.ok).toBe(false)
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('does not call in non-browser runtime or when Puter client is missing', async () => {
    const nonBrowser = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: {},
    })
    const missingPuter = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: { window: {} },
    })

    expect(nonBrowser.ok).toBe(false)
    expect(nonBrowser.reason).toBe('non_browser_runtime')
    expect(missingPuter.ok).toBe(false)
    expect(missingPuter.reason).toBe('puter_unavailable')
  })

  it('rejects tools, files, function-calling, credentials, config, endpoint, billing, debug, and env options', async () => {
    const unsafeOptions = [
      { tool: 'search' },
      { tools: ['search'] },
      { file: 'document.pdf' },
      { files: ['document.pdf'] },
      { function_call: { name: 'lookup' } },
      { api_key: 'sk-hidden' },
      { access_token: 'raw-token' },
      { token: 'raw-token' },
      { credential: 'provider-credential' },
      { secret: 'provider-secret' },
      { env: 'VITE_SECRET' },
      { env_var: 'VITE_SECRET' },
      { provider_config: { model: 'hidden' } },
      { private_endpoint: 'https://private.example.test' },
      { billing: 'managed-plan' },
      { debug: true },
    ]

    for (const requestOptions of unsafeOptions) {
      const chat = vi.fn()
      const result = await invokePuterFreeModeManualHarness({
        accessSnapshotEnvelope: safeEnvelope(),
        experimentalFeatureEnabled: true,
        manualInvocation: true,
        prompt: 'hello',
        requestOptions,
        runtime: puterRuntime(chat),
      })

      expect(result.ok).toBe(false)
      expect(result.reason).toBe('unsafe_request_options')
      expect(chat).not.toHaveBeenCalled()
      expectPublicSafe(result)
    }
  })

  it('uses mocked puter.ai.chat only when all gates pass', async () => {
    const chat = vi.fn().mockResolvedValue('hello from puter')

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(chat).toHaveBeenCalledTimes(1)
    expect(chat).toHaveBeenCalledWith('hello')
    expect(result.ok).toBe(true)
    expect(result.denied).toBe(false)
    expect(result.reason).toBe('ok')
    expect(result.sanitized_text).toBe('hello from puter')
    expect(Object.keys(result).sort()).toEqual([...RESULT_KEYS].sort())
    expectPublicSafe(result)
  })

  it('sanitizes provider text and never exposes raw provider payload', async () => {
    const chat = vi.fn().mockResolvedValue({
      text: 'safe text with sk-proj-abcdefghijkl hidden',
      raw_provider_payload: { text: 'hidden raw value' },
    })

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(result.ok).toBe(true)
    expect(result.sanitized_text).toBe('safe text with [redacted] hidden')
    expect(JSON.stringify(result)).not.toContain('hidden raw value')
    expectPublicSafe(result)
  })

  it('sanitizes thrown provider errors and fails closed', async () => {
    const chat = vi.fn().mockRejectedValue(new Error('sk-proj-abcdefghijkl stack trace'))

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: puterRuntime(chat),
    })

    expect(result.ok).toBe(false)
    expect(result.reason).toBe('puter_call_failed')
    expect(result.sanitized_text).toBe('')
    expectPublicSafe(result)
  })

  it('rejects prompts that look like credentials', async () => {
    const chat = vi.fn()

    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'sk-proj-abcdefghijkl',
      runtime: puterRuntime(chat),
    })

    expect(result.ok).toBe(false)
    expect(result.reason).toBe('invalid_prompt')
    expect(chat).not.toHaveBeenCalled()
    expectPublicSafe(result)
  })

  it('does not contain automatic network execution paths', async () => {
    const source = await import('./freeModePuterManualHarness?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('onload')
    expect(lowered).not.toContain('addeventlistener')
  })

  it('exposes the stable harness version', async () => {
    const result = await invokePuterFreeModeManualHarness({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      manualInvocation: true,
      prompt: 'hello',
      runtime: puterRuntime(vi.fn().mockResolvedValue('ok')),
    })

    expect(result.harness_version).toBe(PUTER_MANUAL_HARNESS_VERSION)
  })
})
