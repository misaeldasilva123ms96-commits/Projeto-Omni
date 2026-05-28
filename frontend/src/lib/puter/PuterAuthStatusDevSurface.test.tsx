import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PuterAuthStatusDevSurface } from './PuterAuthStatusDevSurface'
import * as puterAuthStatus from './puterAuthStatus'

function mockStatus(overrides: Partial<puterAuthStatus.PuterAuthStatusOutput> = {}) {
  return vi.spyOn(puterAuthStatus, 'checkPuterAuthStatus').mockResolvedValue({
    ok: true,
    status: 'signed_out',
    reason: 'signed_out',
    user_message: 'Puter reports signed out.',
    is_signed_in: false,
    user_present: false,
    sanitized_user: null,
    retry_allowed: false,
    manual_action_required: true,
    runtime_truth: {
      puter_runtime_loaded: true,
      auth_api_available: true,
      auth_status_checked: true,
      is_signed_in: false,
      user_present: false,
      sanitized_user_present: false,
      raw_auth_payload_exposed: false,
      provider_attempted: false,
      provider_succeeded: false,
      raw_provider_payload_exposed: false,
    },
    ...overrides,
  })
}

describe('Puter auth status dev surface', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    delete (window as Window & { puter?: unknown }).puter
  })

  it('does not auto-check on render or mount', () => {
    const spy = vi.spyOn(puterAuthStatus, 'checkPuterAuthStatus')

    render(<PuterAuthStatusDevSurface puterRuntimeLoaded />)

    expect(screen.getByLabelText('Puter auth status dev surface')).toBeInTheDocument()
    expect(screen.getByLabelText('Puter auth status result')).toHaveTextContent('not_invoked')
    expect(spy).not.toHaveBeenCalled()
  })

  it('disables the status button until Puter runtime is loaded', () => {
    const spy = vi.spyOn(puterAuthStatus, 'checkPuterAuthStatus')

    render(<PuterAuthStatusDevSurface puterRuntimeLoaded={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Check Puter auth status' }))

    expect(screen.getByRole('button', { name: 'Check Puter auth status' })).toBeDisabled()
    expect(screen.getByText('Load Puter runtime first before checking auth status.')).toBeInTheDocument()
    expect(spy).not.toHaveBeenCalled()
  })

  it('invokes checkPuterAuthStatus once on explicit click when runtime is loaded', async () => {
    const check = mockStatus()

    render(<PuterAuthStatusDevSurface puterRuntimeLoaded />)
    fireEvent.click(screen.getByRole('button', { name: 'Check Puter auth status' }))

    await waitFor(() => expect(check).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Puter auth status result')).toHaveTextContent('signed_out')
  })

  it('renders only sanitized user presence booleans', async () => {
    mockStatus({
      status: 'signed_in_sanitized',
      is_signed_in: true,
      user_present: true,
      user_message: 'Puter reports signed in. Only sanitized user presence was returned.',
      manual_action_required: false,
      sanitized_user: {
        user_present: true,
        username_present: true,
        email_present: true,
        id_present: true,
      },
      runtime_truth: {
        puter_runtime_loaded: true,
        auth_api_available: true,
        auth_status_checked: true,
        is_signed_in: true,
        user_present: true,
        sanitized_user_present: true,
        raw_auth_payload_exposed: false,
        provider_attempted: false,
        provider_succeeded: false,
        raw_provider_payload_exposed: false,
      },
    })

    render(<PuterAuthStatusDevSurface puterRuntimeLoaded />)
    fireEvent.click(screen.getByRole('button', { name: 'Check Puter auth status' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter auth status result')).toHaveTextContent('signed_in_sanitized')
    })

    const text = screen.getByLabelText('Puter auth status dev surface').textContent?.toLowerCase() ?? ''
    expect(text).toContain('username_present=true')
    expect(text).toContain('email_present=true')
    expect(text).toContain('id_present=true')
    expect(text).not.toContain('raw@example.test')
    expect(text).not.toContain('token')
    expect(text).not.toContain('cookie')
  })

  it('does not call puter.ai.chat during auth status check', async () => {
    const chat = vi.fn()
    ;(window as Window & { puter?: unknown }).puter = {
      ai: { chat },
    }
    mockStatus()

    render(<PuterAuthStatusDevSurface puterRuntimeLoaded />)
    fireEvent.click(screen.getByRole('button', { name: 'Check Puter auth status' }))

    await waitFor(() => expect(puterAuthStatus.checkPuterAuthStatus).toHaveBeenCalledTimes(1))
    expect(chat).not.toHaveBeenCalled()
  })

  it('does not add direct network primitives to the source', async () => {
    const source = await import('./PuterAuthStatusDevSurface?raw')
    const lowered = source.default.toLowerCase()

    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('sendbeacon')
    expect(lowered).not.toContain('websocket')
    expect(lowered).not.toContain('localstorage')
    expect(lowered).not.toContain('sessionstorage')
  })
})
