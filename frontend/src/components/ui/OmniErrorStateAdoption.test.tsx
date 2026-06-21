import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SettingsView } from '../../pages/SettingsPage'

const mocks = vi.hoisted(() => ({
  clearActionError: vi.fn(),
}))

vi.mock('../../features/settings/hooks/useProviders', () => ({
  useProviders: () => ({
    actionError: 'Authorization Bearer abcdefghijklmnopqrstuvwxyz',
    clearActionError: mocks.clearActionError,
    createProvider: vi.fn(),
    editProvider: vi.fn(),
    lastTestResult: null,
    loading: false,
    providers: [],
    removeProvider: vi.fn(),
    runConnectionTest: vi.fn(),
    submitting: false,
    testingProvider: null,
  }),
}))

describe('Omni error-state adoption', () => {
  beforeEach(() => {
    mocks.clearActionError.mockReset()
  })

  it('preserves Settings dismissal behavior and redacts its action error', async () => {
    render(<SettingsView />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('[REDACTED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')

    await userEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(mocks.clearActionError).toHaveBeenCalledOnce()
  })
})
