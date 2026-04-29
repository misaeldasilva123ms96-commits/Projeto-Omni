import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ChatPanel } from './ChatPanel'

const baseProps = {
  error: null,
  helperText: 'helper',
  lastMetadata: null,
  loading: false,
  messages: [],
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  requestState: 'idle' as const,
  sessionId: 'session-test',
}

describe('ChatPanel', () => {
  it('sends message through submit action', async () => {
    const onSubmit = vi.fn()
    render(<ChatPanel {...baseProps} canSend input="hello" onSubmit={onSubmit} />)
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('blocks empty messages with disabled send button', () => {
    render(<ChatPanel {...baseProps} canSend={false} input="" />)
    expect(screen.getByRole('button', { name: /Enviar/i })).toBeDisabled()
  })

  it('shows loading state', () => {
    render(<ChatPanel {...baseProps} canSend={false} input="" loading requestState="loading" />)
    expect(screen.getByRole('button', { name: '...' })).toBeDisabled()
    expect(screen.getByText('loading')).toBeInTheDocument()
  })
})
