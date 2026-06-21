import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniErrorState } from './OmniErrorState'

describe('OmniErrorState', () => {
  it('renders a safe title and description with alert semantics', () => {
    render(
      <OmniErrorState
        description="Tente novamente em alguns instantes."
        title="Não foi possível carregar os dados."
      />,
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveAttribute('data-size', 'default')
    expect(alert).toHaveTextContent('Não foi possível carregar os dados.')
    expect(alert).toHaveTextContent('Tente novamente em alguns instantes.')
  })

  it('renders an optional action and preserves its callback', async () => {
    const onAction = vi.fn()
    render(
      <OmniErrorState
        actionLabel="Tentar novamente"
        description="Falha temporária."
        onAction={onAction}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(onAction).toHaveBeenCalledOnce()
  })

  it('redacts secrets in technical details', () => {
    render(
      <OmniErrorState
        description="Falha segura."
        technicalDetail="Authorization Bearer abcdefghijklmnopqrstuvwxyz"
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('[REDACTED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })

  it.each([
    'stack: sensitive internal frames',
    'traceback: sensitive internal frames',
    'stdout: sensitive process output',
    'stderr: sensitive process output',
  ])('does not render raw diagnostic detail: %s', (technicalDetail) => {
    render(<OmniErrorState description="Falha segura." technicalDetail={technicalDetail} />)

    expect(screen.getByRole('alert')).toHaveTextContent('[REDACTED]')
    expect(document.body.textContent).not.toContain(technicalDetail)
  })

  it('renders suspicious markup as text instead of HTML', () => {
    render(<OmniErrorState description={'<script>alert("unsafe")</script>'} />)

    expect(screen.getByRole('alert')).toHaveTextContent('<script>alert("unsafe")</script>')
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })
})
