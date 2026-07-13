import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { OmniApp } from './OmniApp'

vi.mock('../pages/ChatPage', () => ({
  ChatPage: ({
    onChangeView,
    renderShell,
  }: {
    onChangeView: (view: 'dashboard') => void
    renderShell: (content: ReactNode, options?: { sidebar?: ReactNode }) => ReactNode
  }) => renderShell(
    <button type="button" onClick={() => onChangeView('dashboard')}>Open dashboard</button>,
    { sidebar: <div>Chat sidebar</div> },
  ),
}))

vi.mock('../pages/DashboardPage', () => ({
  DashboardPage: ({
    renderShell,
  }: {
    renderShell: (content: ReactNode, options?: { sidebar?: ReactNode }) => ReactNode
  }) => renderShell(<div>Dashboard content</div>, { sidebar: <div>Dashboard sidebar</div> }),
}))

describe('OmniApp shell ownership', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
  })

  it('renders exactly one application shell for the active view', async () => {
    render(<OmniApp />)

    await screen.findByText('Chat sidebar')
    expect(screen.getAllByRole('banner')).toHaveLength(1)
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(screen.getByText('Chat sidebar')).toBeInTheDocument()
  })

  it('keeps one shell while navigating between current views', async () => {
    render(<OmniApp />)

    await userEvent.click(await screen.findByRole('button', { name: 'Open dashboard' }))

    expect(window.location.pathname).toBe('/dashboard')
    expect(await screen.findByText('Dashboard content')).toBeInTheDocument()
    expect(screen.getAllByRole('banner')).toHaveLength(1)
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })
})
