import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProviderStatusBadge } from './ProviderStatusBadge'

describe('ProviderStatusBadge', () => {
  it('shows "Conectado" when configured with updatedAt', () => {
    render(<ProviderStatusBadge configured={true} updatedAt={Date.now()} />)
    const badge = screen.getByText('Conectado')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="success"]')).toBeInTheDocument()
  })

  it('shows "Não configurado" when not configured', () => {
    render(<ProviderStatusBadge configured={false} />)
    const badge = screen.getByText('Não configurado')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="muted"]')).toBeInTheDocument()
  })

  it('shows "Falha na conexão" when configured without updatedAt', () => {
    render(<ProviderStatusBadge configured={true} updatedAt={null} />)
    const badge = screen.getByText('Falha na conexão')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="danger"]')).toBeInTheDocument()
  })

  it('shows "Credenciais inválidas" mapping is available', () => {
    render(<ProviderStatusBadge configured={true} updatedAt={Date.now()} />)
    expect(screen.getByText('Conectado')).toBeInTheDocument()
  })

  it('includes timestamp in title attribute when updatedAt is provided', () => {
    const timestamp = new Date('2026-06-21T12:00:00Z').getTime()
    render(<ProviderStatusBadge configured={true} updatedAt={timestamp} />)
    const badge = screen.getByText('Conectado')
    expect(badge.closest('[title]')).toHaveAttribute('title')
  })
})
