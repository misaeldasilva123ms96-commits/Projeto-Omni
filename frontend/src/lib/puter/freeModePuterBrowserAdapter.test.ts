import { describe, expect, it, vi } from 'vitest'
import {
  PUTER_BROWSER_SKELETON_VERSION,
  isPuterFreeModeFlagEnabled,
  preparePuterFreeModeBrowserRequest,
  selectPuterFreeModeBrowserAdapter,
} from './freeModePuterBrowserAdapter'

const RESULT_KEYS = [
  'skeleton_version',
  'selection_allowed',
  'denied',
  'reason',
  'adapter_id',
  'client_adapter_id',
  'provider_family',
  'provider_mode',
  'is_experimental',
  'default_enabled',
  'requires_browser_runtime',
  'requires_user_session',
  'capabilities',
]

const CAPABILITY_KEYS = [
  'supports_streaming',
  'supports_tools',
  'supports_files',
  'supports_long_context',
  'supports_sensitive_tools',
  'is_experimental',
  'is_user_key_required',
  'is_managed',
  'is_internal',
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

describe('Puter Free Mode browser adapter skeleton', () => {
  it('defaults the feature flag to disabled', () => {
    expect(isPuterFreeModeFlagEnabled()).toBe(false)
    expect(isPuterFreeModeFlagEnabled('')).toBe(false)
    expect(isPuterFreeModeFlagEnabled('false')).toBe(false)
    expect(isPuterFreeModeFlagEnabled('true')).toBe(true)
  })

  it('does not select the adapter by default', () => {
    const chat = vi.fn()
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      runtime: puterRuntime(chat),
    })

    expect(result.selection_allowed).toBe(false)
    expect(result.denied).toBe(true)
    expect(result.reason).toBe('feature_disabled')
    expect(chat).not.toHaveBeenCalled()
  })

  it('does not perform a Puter or network call on import or default path', () => {
    const chat = vi.fn()

    preparePuterFreeModeBrowserRequest({
      accessSnapshotEnvelope: safeEnvelope(),
      runtime: puterRuntime(chat),
    })

    expect(chat).not.toHaveBeenCalled()
  })

  it('does not contain a callable network or Puter execution path', async () => {
    const source = await import('./freeModePuterBrowserAdapter?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('.chat(')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('xmlhttprequest')
  })

  it('fails closed outside a browser runtime', () => {
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: {},
    })

    expect(result.selection_allowed).toBe(false)
    expect(result.reason).toBe('non_browser_runtime')
    expectPublicSafe(result)
  })

  it('fails closed when Puter is unavailable', () => {
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: { window: {} },
    })

    expect(result.selection_allowed).toBe(false)
    expect(result.reason).toBe('puter_unavailable')
    expectPublicSafe(result)
  })

  it('denies denied AccessSnapshotBoundary responses', () => {
    const chat = vi.fn()
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: deniedEnvelope('quota_exceeded'),
      experimentalFeatureEnabled: true,
      runtime: puterRuntime(chat),
    })

    expect(result.selection_allowed).toBe(false)
    expect(result.reason).toBe('quota_exceeded')
    expect(chat).not.toHaveBeenCalled()
    expectPublicSafe(result)
  })

  it('denies malformed or unsafe AccessSnapshotBoundary envelopes', () => {
    const allowed = safeEnvelope()
    const missingEnvelopeKey = { ...allowed }
    delete (missingEnvelopeKey as Record<string, unknown>).boundary_version
    const extraEnvelopeKey = { ...allowed, api_key: 'sk-hidden' }
    const missingSnapshotKey = {
      ...allowed,
      access_snapshot: { ...allowed.access_snapshot },
    }
    delete (missingSnapshotKey.access_snapshot as Record<string, unknown>).snapshot_version

    for (const envelope of [missingEnvelopeKey, extraEnvelopeKey, missingSnapshotKey]) {
      const result = selectPuterFreeModeBrowserAdapter({
        accessSnapshotEnvelope: envelope,
        experimentalFeatureEnabled: true,
        runtime: puterRuntime(),
      })

      expect(result.selection_allowed).toBe(false)
      expect(result.reason).toBe('invalid_access_snapshot')
      expectPublicSafe(result)
    }
  })

  it('requires a safe Free mode boundary response for selection', () => {
    const chat = vi.fn()
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: puterRuntime(chat),
    })

    expect(result.selection_allowed).toBe(true)
    expect(result.denied).toBe(false)
    expect(result.reason).toBe('selection_allowed')
    expect(result.provider_family).toBe('experimental_free_provider')
    expect(result.provider_mode).toBe('experimental_free')
    expect(result.capabilities.supports_tools).toBe(false)
    expect(result.capabilities.supports_files).toBe(false)
    expect(result.capabilities.supports_sensitive_tools).toBe(false)
    expect(result.capabilities.supports_long_context).toBe(false)
    expect(chat).not.toHaveBeenCalled()
  })

  it('rejects public override attempts in request options', () => {
    const overrideOptions = [
      { provider_mode: 'managed' },
      { provider_family: 'managed_provider' },
      { adapter_id: 'managed_adapter' },
      { selected_adapter_id: 'managed_adapter' },
      { selected_provider_family: 'managed_provider' },
      { policy_overrides: { provider_mode: 'managed' } },
      { daily_token_limit: 999999 },
      { max_input_tokens: 999999 },
      { max_output_tokens: 999999 },
      { max_context_tokens: 999999 },
    ]

    for (const requestOptions of overrideOptions) {
      const result = selectPuterFreeModeBrowserAdapter({
        accessSnapshotEnvelope: safeEnvelope(),
        experimentalFeatureEnabled: true,
        runtime: puterRuntime(),
        requestOptions,
      })

      expect(result.selection_allowed).toBe(false)
      expect(result.reason).toBe('unsafe_request_options')
      expectPublicSafe(result)
    }
  })

  it('rejects credentials, provider config, debug, tools, files, and function-calling options', () => {
    const unsafeOptions = [
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
      { tool: 'search' },
      { tools: ['search'] },
      { file: 'document.pdf' },
      { files: ['document.pdf'] },
      { function_call: { name: 'lookup' } },
    ]

    for (const requestOptions of unsafeOptions) {
      const result = selectPuterFreeModeBrowserAdapter({
        accessSnapshotEnvelope: safeEnvelope(),
        experimentalFeatureEnabled: true,
        runtime: puterRuntime(),
        requestOptions,
      })

      expect(result.selection_allowed).toBe(false)
      expect(result.reason).toBe('unsafe_request_options')
      expectPublicSafe(result)
    }
  })

  it('does not expose raw provider payloads', () => {
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: puterRuntime(),
      requestOptions: {
        raw_provider_payload: {
          text: 'hidden',
        },
      },
    })

    expect(result.selection_allowed).toBe(false)
    expect(result.reason).toBe('unsafe_request_options')
    expect(JSON.stringify(result)).not.toContain('hidden')
    expectPublicSafe(result)
  })

  it('returns an exact public-safe result shape', () => {
    const result = selectPuterFreeModeBrowserAdapter({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: puterRuntime(),
    })

    expect(Object.keys(result).sort()).toEqual([...RESULT_KEYS].sort())
    expect(Object.keys(result.capabilities).sort()).toEqual([...CAPABILITY_KEYS].sort())
    expect(result.skeleton_version).toBe(PUTER_BROWSER_SKELETON_VERSION)
    expect(result.default_enabled).toBe(false)
  })

  it('prepares only sanitized metadata and never a raw provider request', () => {
    const prepared = preparePuterFreeModeBrowserRequest({
      accessSnapshotEnvelope: safeEnvelope(),
      experimentalFeatureEnabled: true,
      runtime: puterRuntime(),
    })

    expect(prepared.prepared).toBe(true)
    expect(prepared.selection_allowed).toBe(true)
    expect(JSON.stringify(prepared).toLowerCase()).not.toContain('raw_provider')
  })
})
