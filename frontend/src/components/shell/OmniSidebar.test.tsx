import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniSidebar, OmniSidebarToggle } from './OmniSidebar'

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
  it('renders the shared Sidebar content', () => {
    render(<OmniSidebar {...defaultProps} />)
    expect(screen.getByText('IA Console')).toBeInTheDocument()
  })

  it('does not own a second collapse control', () => {
    render(<OmniSidebar {...defaultProps} />)
    expect(screen.queryByRole('button', { name: /collapse sidebar/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /expand sidebar/i })).not.toBeInTheDocument()
  })

  it('exposes a stateless collapse toggle for the shell owner', async () => {
    const onToggle = vi.fn()
    render(<OmniSidebarToggle collapsed={false} onToggle={onToggle} />)

    await userEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
    expect(onToggle).toHaveBeenCalledOnce()
  })
})
