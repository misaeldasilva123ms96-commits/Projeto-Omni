import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniEmptyState } from './OmniEmptyState'

describe('OmniEmptyState', () => {
  it('renders title and description safely', () => {
    render(
      <OmniEmptyState
        title="Nenhum registro"
        description="Os registros aparecerão quando estiverem disponíveis."
      />,
    )

    expect(screen.getByRole('status')).toHaveTextContent('Nenhum registro')
    expect(screen.getByRole('status')).toHaveTextContent(
      'Os registros aparecerão quando estiverem disponíveis.',
    )
  })

  it('renders an optional action and calls its callback', async () => {
    const onAction = vi.fn()
    render(
      <OmniEmptyState
        actionLabel="Criar Projeto"
        onAction={onAction}
        title="Nenhum projeto ainda."
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Criar Projeto' }))
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('redacts secret-like values and never renders unsafe HTML', () => {
    render(
      <OmniEmptyState
        title={'<script>alert("unsafe")</script>'}
        description="Authorization: Bearer abcdefghijklmnopqrstuvwxyz"
      />,
    )

    expect(screen.getByRole('status')).toHaveTextContent('<script>alert("unsafe")</script>')
    expect(screen.getByRole('status')).toHaveTextContent('[REDACTED]')
    expect(screen.getByRole('status')).not.toHaveTextContent('abcdefghijklmnopqrstuvwxyz')
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })
})
