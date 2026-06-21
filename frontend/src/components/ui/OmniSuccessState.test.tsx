import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniSuccessState } from './OmniSuccessState'

describe('OmniSuccessState', () => {
  it('renders a safe description with status semantics', () => {
    render(
      <OmniSuccessState description="Conexão estabelecida com sucesso." />,
    )

    const status = screen.getByRole('status')
    expect(status).toHaveAttribute('data-size', 'default')
    expect(status).toHaveTextContent('Conexão estabelecida com sucesso.')
  })

  it('renders an optional title', () => {
    render(
      <OmniSuccessState
        title="Provedor conectado"
        description="Conexão estabelecida com sucesso."
      />,
    )

    expect(screen.getByText('Provedor conectado')).toBeInTheDocument()
  })

  it('renders an optional action and preserves its callback', async () => {
    const onAction = vi.fn()
    render(
      <OmniSuccessState
        actionLabel="Ver detalhes"
        description="Operação concluída."
        onAction={onAction}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Ver detalhes' }))
    expect(onAction).toHaveBeenCalledOnce()
  })

  it('falls back to a default message when description is empty', () => {
    render(<OmniSuccessState description="" />)

    expect(screen.getByRole('status')).toHaveTextContent('Operação concluída com sucesso.')
  })

  it('renders in compact mode', () => {
    render(<OmniSuccessState description="Sucesso." size="compact" />)

    const status = screen.getByRole('status')
    expect(status).toHaveAttribute('data-size', 'compact')
  })

  it('renders suspicious markup as text instead of HTML', () => {
    render(<OmniSuccessState description={'<script>alert("unsafe")</script>'} />)

    expect(screen.getByRole('status')).toHaveTextContent('<script>alert("unsafe")</script>')
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })

  it('redacts secrets in description', () => {
    render(
      <OmniSuccessState description="Token validado: Bearer sk-abcdefghijklmnopqrstuvwxyz" />,
    )

    expect(screen.getByRole('status')).toHaveTextContent('[REDACTED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })

  it('redacts secrets in title', () => {
    render(
      <OmniSuccessState
        title="Chave sk-abcdefghijklmnopqrstuvwxyz configurada"
        description="Conexão estabelecida."
      />,
    )

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })

  it('does not render an action button when no callback is provided', () => {
    render(
      <OmniSuccessState
        actionLabel="Continuar"
        description="Concluído."
      />,
    )

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('accepts custom class name', () => {
    const { container } = render(
      <OmniSuccessState description="Sucesso." className="custom-class" />,
    )

    expect(container.querySelector('[data-testid="omni-success-state"]')).toHaveClass('custom-class')
  })
})
