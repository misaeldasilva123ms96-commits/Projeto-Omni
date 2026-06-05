import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniSidebar } from './OmniSidebar'

const defaultProps = {
  activeConversationId: undefined,
  conversations: [],
  mode: 'chat' as const,
  onChangeMode: vi.fn(),
  onNewConversation: undefined,
  onRestoreSession: undefined,
  onSelectView: vi.fn(),
  onSidebarItemSelected: undefined,
  view: 'chat' as const,
}

describe('OmniSidebar', () => {
  it('renders Sidebar by default', () => {
    render(<OmniSidebar {...defaultProps} />)
    expect(screen.getByText('IA Console')).toBeInTheDocument()
  })

  it('renders expand button when collapsed', async () => {
    render(<OmniSidebar {...defaultProps} />)
    const collapseBtn = screen.getByRole('button', { name: /collapse sidebar/i })
    await userEvent.click(collapseBtn)
    expect(screen.getByRole('button', { name: /expand sidebar/i })).toBeInTheDocument()
  })

  it('expands when expand button is clicked after collapse', async () => {
    render(<OmniSidebar {...defaultProps} />)
    await userEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
    await userEvent.click(screen.getByRole('button', { name: /expand sidebar/i }))
    expect(screen.getByText('IA Console')).toBeInTheDocument()
  })
})
