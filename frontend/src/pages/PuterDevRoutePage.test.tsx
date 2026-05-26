import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveViewFromPath } from '../app/App'
import {
  PUTER_DEV_ROUTE_PATH,
  PUTER_DEV_ROUTE_VERSION,
  PuterDevRoutePage,
  buildPuterDevRouteBoundaryEnvelope,
  canShowPuterDevRoute,
} from './PuterDevRoutePage'

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
  ;(window as Window & { puter?: unknown }).puter = {
    auth: {
      signIn: vi.fn(),
    },
    ai: {
      chat,
    },
  }

  return {
    window,
  }
}

function deniedEnvelope(reason = 'quota_exceeded') {
  const envelope = buildPuterDevRouteBoundaryEnvelope({
    ok: false,
    denied: true,
    reason,
  })

  return {
    ...envelope,
    access_snapshot: {
      ...(envelope.access_snapshot as Record<string, unknown>),
      routing_allowed: false,
      fallback_allowed: true,
      decision_reason: reason,
    },
  }
}

function expectPublicSafeText(value: string | null | undefined) {
  const text = String(value ?? '').toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(text).not.toContain(fragment)
  }
}

function renderEnabledRoute(chat = vi.fn(), accessSnapshotEnvelope: unknown = buildPuterDevRouteBoundaryEnvelope()) {
  render(
    <PuterDevRoutePage
      accessSnapshotEnvelope={accessSnapshotEnvelope}
      devSurfaceEnabled
      experimentalFeatureEnabled
      runtime={puterRuntime(chat)}
    />,
  )
}

function renderEnabledRouteWithChatToggle(
  chat = vi.fn(),
  accessSnapshotEnvelope: unknown = buildPuterDevRouteBoundaryEnvelope(),
) {
  render(
    <PuterDevRoutePage
      accessSnapshotEnvelope={accessSnapshotEnvelope}
      chatBridgeFeatureEnabled
      chatDevToggleEnabled
      devRealFeatureEnabled
      devSurfaceEnabled
      experimentalFeatureEnabled
      runtime={puterRuntime(chat)}
    />,
  )
}

describe('Puter dev route mount', () => {
  afterEach(() => {
    delete (window as Window & { puter?: unknown }).puter
  })

  it('keeps route visibility disabled unless both flags are enabled', () => {
    expect(canShowPuterDevRoute(false, false)).toBe(false)
    expect(canShowPuterDevRoute(true, false)).toBe(false)
    expect(canShowPuterDevRoute(false, true)).toBe(false)
    expect(canShowPuterDevRoute(true, true)).toBe(true)
  })

  it('does not resolve the dev route when flags are disabled', () => {
    expect(resolveViewFromPath(PUTER_DEV_ROUTE_PATH, false)).toBe('chat')
    expect(resolveViewFromPath(PUTER_DEV_ROUTE_PATH, true)).toBe('puter-dev')
  })

  it('does not render the dev route or surface by default', () => {
    const chat = vi.fn()

    render(
      <PuterDevRoutePage
        accessSnapshotEnvelope={buildPuterDevRouteBoundaryEnvelope()}
        runtime={puterRuntime(chat)}
      />,
    )

    expect(screen.queryByLabelText('Puter dev route')).toBeNull()
    expect(screen.queryByLabelText('Puter manual dev surface')).toBeNull()
    expect(chat).not.toHaveBeenCalled()
  })

  it('renders only when both flags are enabled', () => {
    renderEnabledRoute()

    expect(screen.getByLabelText('Puter dev route')).toHaveAttribute(
      'data-puter-dev-route-version',
      PUTER_DEV_ROUTE_VERSION,
    )
    expect(screen.getByLabelText('Puter manual dev surface')).toBeInTheDocument()
    expect(screen.getByLabelText('Puter auth consent dev surface')).toBeInTheDocument()
    expect(screen.queryByLabelText('Puter Free chat dev toggle')).toBeNull()
  })

  it('renders the Free chat dev toggle only when its bridge flags are enabled', () => {
    renderEnabledRouteWithChatToggle()

    expect(screen.getByLabelText('Puter dev route')).toBeInTheDocument()
    expect(screen.getByLabelText('Puter Free chat dev toggle')).toBeInTheDocument()
  })

  it('does not call Puter on route render or mount', () => {
    const chat = vi.fn()

    renderEnabledRouteWithChatToggle(chat)

    expect(chat).not.toHaveBeenCalled()
  })

  it('requires a manual click before requesting Puter auth consent', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockResolvedValue({ raw_auth_response: 'hidden' })
    ;(window as Window & { puter?: unknown }).puter = {
      auth: { signIn },
      ai: { chat: vi.fn() },
    }

    render(
      <PuterDevRoutePage
        accessSnapshotEnvelope={buildPuterDevRouteBoundaryEnvelope()}
        devSurfaceEnabled
        experimentalFeatureEnabled
        runtime={{ window }}
      />,
    )

    expect(signIn).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Connect / Sign in with Puter' }))

    await waitFor(() => expect(signIn).toHaveBeenCalledTimes(1))
    expect(((window as Window & {
      puter?: { ai?: { chat?: ReturnType<typeof vi.fn> } }
    }).puter?.ai?.chat)).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Puter auth consent result')).toHaveTextContent('consent_or_auth_completed')
  })

  it('requires a manual click before the harness can call Puter', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue('safe route response')

    renderEnabledRoute(chat)
    expect(chat).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => expect(chat).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('safe route response')
  })

  it('denies safely when the boundary state is denied', async () => {
    const user = userEvent.setup()
    const chat = vi.fn()

    renderEnabledRoute(chat, deniedEnvelope('quota_exceeded'))
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent('quota_exceeded')
    })
    expect(chat).not.toHaveBeenCalled()
    expectPublicSafeText(screen.getByLabelText('Puter manual result').textContent)
  })

  it('shows sanitized output and never raw provider payload text', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue({
      text: 'visible route answer with sk-proj-abcdefghijkl hidden',
      raw_provider_payload: { text: 'raw hidden route value' },
    })

    renderEnabledRoute(chat)
    await user.click(screen.getByRole('button', { name: 'Run manual Puter check' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter manual result')).toHaveTextContent(
        'visible route answer with [redacted] hidden',
      )
    })
    expect(screen.getByLabelText('Puter manual result')).not.toHaveTextContent('raw hidden route value')
  })

  it('does not expose override controls or import chat send paths', async () => {
    renderEnabledRoute()

    const routeText = screen.getByLabelText('Puter dev route').textContent?.toLowerCase() ?? ''
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
      expect(routeText).not.toContain(fragment)
    }

    const source = await import('./PuterDevRoutePage?raw')
    const lowered = source.default.toLowerCase()
    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('sendbeacon')
    expect(lowered).not.toContain('websocket')
    expect(lowered).not.toContain('onload')
    expect(lowered).not.toContain('addeventlistener')
  })
})
