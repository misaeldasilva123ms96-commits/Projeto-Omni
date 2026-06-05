import { describe, expect, test, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsAuthGate } from '../features/settings/SettingsAuthGate'

const BASE_PROPS = {
  mode: 'chat',
  onChangeMode: vi.fn(),
  onChangeView: vi.fn(),
  view: 'settings',
}

describe('SettingsAuthGate', () => {
  test('renders access denied text when session is unavailable', async () => {
    vi.resetModules()
    vi.doMock('../hooks/useRequireAuth', () => ({
      useRequireAuth: () => ({ session: null, loading: false }),
    }))

    const { SettingsAuthGate } = await import('../features/settings/SettingsAuthGate')
    render(<SettingsAuthGate {...BASE_PROPS} />)

    expect(await screen.findByText(/Configurações de provedores exigem acesso autenticado/i)).toBeDefined()
  })
})
