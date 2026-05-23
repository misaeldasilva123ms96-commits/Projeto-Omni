import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  PUTER_DEV_SURFACE_VERSION,
  PuterDevManualSurface,
  createPuterDevSurfaceState,
  isPuterDevSurfaceFlagEnabled,
  resultToPuterDevSurfaceState,
} from './PuterDevManualSurface'
import { PUTER_MANUAL_HARNESS_VERSION } from './freeModePuterManualHarness'
import {
  PUTER_SCRIPT_ID,
  PUTER_SCRIPT_SRC,
} from './puterScriptLoader'

const DEV_STATE_KEYS = [
  'surface_version',
  'harness_version',
  'active',
  'denied',
  'pending',
  'reason',
  'provider_family',
  'adapter_id',
  'sanitized_text',
  'experimental',
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

function renderEnabledSurface(chat = vi.fn(), envelope: unknown = safeEnvelope()) {
  render(
    <PuterDevManualSurface
      accessSnapshotEnvelope={envelope}
      defaultPrompt="hello"
      devSurfaceEnabled
      experimentalFeatureEnabled
      runtime={puterRuntime(chat)}
    />,
  )
}

function renderEnabledSurfaceWithRuntime(runtime: unknown, envelope: unknown = safeEnvelope()) {
  render(
    <PuterDevManualSurface
      accessSnapshotEnvelope={envelope}
      defaultPrompt="hello"
      devSurfaceEnabled
      experimentalFeatureEnabled
      runtime={runtime}
    />,
  )
}

describe('Puter dev manual surface', () => {
  afterEach(() => {
    delete (window as Window & { puter?: unknown }).puter
    document.querySelectorAll('script').forEach((script) => script.remove())
  })

  it('keeps the dev surface feature flag disabled by default', () => {
    expect(isPuterDevSurfaceFlagEnabled()).toBe(false)
    expect(isPuterDevSurfaceFlagEnabled('')).toBe(false)
    expect(isPuterDevSurfaceFlagEnabled('false')).toBe(false)
    expect(isPuterDevSurfaceFlagEnabled('true')).toBe(true)
    expect(isPuterDevSurfaceFlagEnabled('1')).toBe(true)
  })

  it('does not render or activate by default', () => {
    const chat = vi.fn()

    render(
      <PuterDevManualSurface
        accessSnapshotEnvelope={safeEnvelope()}
        defaultPrompt="hello"
        runtime={puterRuntime(chat)}
      />,
    )

    expect(screen.queryByLabelText('Puter manual dev surface')).toBeNull()
    expect(chat).not.toHaveBeenCalled()
  })

  it('does not call Puter on import, render, or mount', () => {
    const chat = vi.fn()

    renderEnabledSurface(chat)

    expect(screen.getByLabelText('Puter manual dev surface')).toBeInTheDocument()
    expect(chat).not.toHaveBeenCalled()
  })

  it('shows puter_unavailable before the runtime loader succeeds', async () => {
    const user = userEvent.setup()

    renderEnabledSurfaceWithRuntime({ window })
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('puter_unavailable')
    })
  })

  it('can trigger the Puter script loader manually without calling AI', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue('loaded response')

    renderEnabledSurfaceWithRuntime({ window })
    expect(document.getElementById(PUTER_SCRIPT_ID)).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Load Puter runtime' }))
    const script = document.getElementById(PUTER_SCRIPT_ID) as HTMLScriptElement | null

    expect(script).not.toBeNull()
    expect(script?.src).toBe(PUTER_SCRIPT_SRC)
    expect(chat).not.toHaveBeenCalled()

    ;(window as Window & { puter?: unknown }).puter = { ai: { chat } }
    script?.dispatchEvent(new Event('load'))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter runtime loader status')).toHaveTextContent('loaded')
    })
    expect(chat).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))
    await waitFor(() => expect(chat).toHaveBeenCalledTimes(1))
  })

  it('requires a manual click before invoking the harness', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue('safe dev response')

    renderEnabledSurface(chat)
    expect(chat).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => expect(chat).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('safe dev response')
  })

  it('denies safely when the boundary state is denied', async () => {
    const user = userEvent.setup()
    const chat = vi.fn()

    renderEnabledSurface(chat, deniedEnvelope('quota_exceeded'))
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('quota_exceeded')
    })
    expect(chat).not.toHaveBeenCalled()
  })

  it('denies safely when the boundary state is malformed', async () => {
    const user = userEvent.setup()
    const chat = vi.fn()
    const malformed = safeEnvelope()
    delete (malformed as Record<string, unknown>).boundary_version

    renderEnabledSurface(chat, malformed)
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('invalid_access_snapshot')
    })
    expect(chat).not.toHaveBeenCalled()
  })

  it('does not expose request option controls or provider override controls', () => {
    renderEnabledSurface()

    const surfaceText = screen.getByLabelText('Puter manual dev surface').textContent?.toLowerCase() ?? ''
    for (const fragment of [
      'provider_mode',
      'provider_family',
      'adapter_id',
      'selected_adapter_id',
      'policy_overrides',
      'quota',
      'billing',
      'debug',
      'tools',
      'files',
      'function',
    ]) {
      expect(surfaceText).not.toContain(fragment)
    }
  })

  it('shows sanitized success output only', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue({
      text: 'visible answer with sk-proj-abcdefghijkl hidden',
      raw_provider_payload: { text: 'raw hidden value' },
    })

    renderEnabledSurface(chat)
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('visible answer with [redacted] hidden')
    })
    expect(screen.getByLabelText('Puter manual result')).not.toHaveTextContent('raw hidden value')
  })

  it('shows sanitized error output only', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockRejectedValue(new Error('sk-proj-abcdefghijkl stack trace'))

    renderEnabledSurface(chat)
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('puter_call_failed')
    })
    expect(screen.getByLabelText('Puter manual result')).not.toHaveTextContent('sk-proj-')
    expect(screen.getByLabelText('Puter manual result')).not.toHaveTextContent('stack')
  })

  it('returns a stable public-safe dev surface state shape', () => {
    const initialState = createPuterDevSurfaceState()
    const successState = resultToPuterDevSurfaceState({
      ok: true,
      denied: false,
      reason: 'ok',
      provider_family: 'experimental_free_provider',
      adapter_id: 'puter_browser_skeleton_adapter',
      sanitized_text: 'safe',
      experimental: true,
      harness_version: PUTER_MANUAL_HARNESS_VERSION,
    })

    expect(initialState.surface_version).toBe(PUTER_DEV_SURFACE_VERSION)
    expect(successState.surface_version).toBe(PUTER_DEV_SURFACE_VERSION)
    expect(Object.keys(initialState).sort()).toEqual([...DEV_STATE_KEYS].sort())
    expect(Object.keys(successState).sort()).toEqual([...DEV_STATE_KEYS].sort())
    expectPublicSafe(initialState)
    expectPublicSafe(successState)
  })

  it('does not import chat flow or contain automatic network paths', async () => {
    const source = await import('./PuterDevManualSurface?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('chatpage')
    expect(lowered).not.toContain('chatpanel')
    expect(lowered).not.toContain('sendmessage')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('onload')
    expect(lowered).not.toContain('addeventlistener')
  })
})
