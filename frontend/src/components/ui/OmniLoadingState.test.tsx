import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OmniLoadingState } from './OmniLoadingState'

describe('OmniLoadingState', () => {
  it('renders the default state with safe accessible semantics', () => {
    render(
      <OmniLoadingState
        description="Aguarde enquanto os dados são preparados."
        label="Carregando dados..."
      />,
    )

    const status = screen.getByRole('status')
    expect(status).toHaveAttribute('aria-busy', 'true')
    expect(status).toHaveAttribute('data-size', 'default')
    expect(status).toHaveTextContent('Carregando dados...')
    expect(status).toHaveTextContent('Aguarde enquanto os dados são preparados.')
  })

  it('renders the compact variant without skeleton rows', () => {
    const { container } = render(<OmniLoadingState label="Sincronizando..." size="compact" />)

    expect(screen.getByRole('status')).toHaveAttribute('data-size', 'compact')
    expect(container.querySelectorAll('.omni-skeleton')).toHaveLength(0)
  })

  it('renders normalized skeleton rows when requested', () => {
    render(<OmniLoadingState label="Carregando cards..." skeletonRows={3.8} />)

    const skeletons = screen.getByTestId('omni-loading-skeletons')
    expect(skeletons.querySelectorAll('.omni-skeleton').length).toBeGreaterThan(0)
    expect(skeletons.children).toHaveLength(3)
  })

  it('redacts secrets and renders suspicious markup as text', () => {
    render(
      <OmniLoadingState
        description={'<script>alert("unsafe")</script> Authorization Bearer abcdefghijklmnopqrstuvwxyz'}
        label="Carregando sk-proj-abcdefghijklmnop..."
      />,
    )

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toMatch(/sk-proj-|abcdefghijklmnopqrstuvwxyz/)
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })
})
