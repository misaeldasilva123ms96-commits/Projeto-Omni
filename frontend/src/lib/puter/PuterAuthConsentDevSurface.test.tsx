import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  PUTER_AUTH_CONSENT_DEV_SURFACE_VERSION,
  PuterAuthConsentDevSurface,
} from './PuterAuthConsentDevSurface'

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

function renderEnabled(runtime: unknown, timeoutMs?: number) {
  render(
    <PuterAuthConsentDevSurface
      devSurfaceEnabled
      experimentalFeatureEnabled
      runtime={runtime}
      timeoutMs={timeoutMs}
    />,
  )
}

function expectPublicSafeText(value: string | null | undefined) {
  const text = String(value ?? '').toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(text).not.toContain(fragment)
  }
}

describe('Puter auth consent dev surface', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not render by default', () => {
    const signIn = vi.fn()

    render(<PuterAuthConsentDevSurface runtime={authRuntime(signIn)} />)

    expect(screen.queryByLabelText('Puter auth consent dev surface')).toBeNull()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('does not call auth on render or mount', () => {
    const signIn = vi.fn()

    renderEnabled(authRuntime(signIn))

    expect(screen.getByLabelText('Puter auth consent dev surface')).toHaveAttribute(
      'data-puter-auth-consent-dev-surface',
      PUTER_AUTH_CONSENT_DEV_SURFACE_VERSION,
    )
    expect(signIn).not.toHaveBeenCalled()
  })

  it('keeps the auth button disabled until the Puter runtime exists', () => {
    renderEnabled({ window: {} })

    expect(screen.getByRole('button', { name: 'Connect / Sign in with Puter' })).toBeDisabled()
    expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('not_invoked')
  })

  it('enables the auth button after the dev runtime appears without calling auth', async () => {
    vi.useFakeTimers()
    const signIn = vi.fn()
    const runtime = { window: {} as { puter?: unknown } }

    renderEnabled(runtime)
    expect(screen.getByRole('button', { name: 'Connect / Sign in with Puter' })).toBeDisabled()

    runtime.window.puter = { auth: { signIn } }
    act(() => {
      vi.advanceTimersByTime(500)
    })

    expect(screen.getByRole('button', { name: 'Connect / Sign in with Puter' })).toBeEnabled()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('invokes puter.auth.signIn once on explicit click only', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockResolvedValue({
      access_token: 'sk-test-token',
      raw_auth_response: 'debug provider_config stack',
    })
    const runtime = authRuntime(signIn)

    renderEnabled(runtime)
    await user.click(screen.getByRole('button', { name: 'Connect / Sign in with Puter' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('consent_or_auth_completed')
    })
    expect(signIn).toHaveBeenCalledTimes(1)
    expect(runtime.window.puter.ai.chat).not.toHaveBeenCalled()
    expectPublicSafeText(screen.getByLabelText('Puter auth consent result').textContent)
  })

  it('returns safe unavailable state when auth API is missing', async () => {
    const user = userEvent.setup()

    renderEnabled({ window: { puter: {} } })
    await user.click(screen.getByRole('button', { name: 'Connect / Sign in with Puter' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('auth_api_unavailable')
    })
  })

  it('shows safe cancelled and failed states without raw response text', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockRejectedValue(new Error('cancelled sk-test-token private_endpoint stack'))

    renderEnabled(authRuntime(signIn))
    await user.click(screen.getByRole('button', { name: 'Connect / Sign in with Puter' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('consent_or_auth_cancelled')
    })
    expectPublicSafeText(screen.getByLabelText('Puter auth consent result').textContent)
  })

  it('does not expose raw auth output when auth remains pending', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockReturnValue(new Promise(() => undefined))

    renderEnabled(authRuntime(signIn), 1)
    await user.click(screen.getByRole('button', { name: 'Connect / Sign in with Puter' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('consent_or_auth_pending')
    })
    expectPublicSafeText(screen.getByLabelText('Puter auth consent result').textContent)
  })

  it('contains no chat, provider, or network paths', async () => {
    const source = await import('./PuterAuthConsentDevSurface?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('sendbeacon')
    expect(lowered).not.toContain('websocket')
    expect(lowered).not.toContain('manualharness')
  })
})
