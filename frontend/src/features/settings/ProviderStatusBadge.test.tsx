import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProviderStatusBadge } from './ProviderStatusBadge'

describe('ProviderStatusBadge', () => {
  it('shows configured without claiming connectivity', () => {
    render(<ProviderStatusBadge configured={true} updatedAt={Date.now()} />)
    const badge = screen.getByText('Configurado')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="info"]')).toBeInTheDocument()
  })

  it('shows "Não configurado" when not configured', () => {
    render(<ProviderStatusBadge configured={false} />)
    const badge = screen.getByText('Não configurado')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="muted"]')).toBeInTheDocument()
  })

  it('shows unreachable only after a valid active test', () => {
    render(
      <ProviderStatusBadge
        configured={true}
        executable={true}
        reachable={false}
        healthy={false}
        healthValid={true}
      />,
    )
    const badge = screen.getByText('Inacessível')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="danger"]')).toBeInTheDocument()
  })

  it('shows healthy only while the cached test is valid', () => {
    render(
      <ProviderStatusBadge
        configured={true}
        executable={true}
        reachable={true}
        healthy={true}
        healthValid={true}
      />,
    )
    expect(screen.getByText('Saudável')).toBeInTheDocument()
  })

  it('includes timestamp in title attribute when updatedAt is provided', () => {
    const timestamp = new Date('2026-06-21T12:00:00Z').getTime()
    render(<ProviderStatusBadge configured={true} updatedAt={timestamp} />)
    const badge = screen.getByText('Configurado')
    expect(badge.closest('[title]')).toHaveAttribute('title')
  })
})
