import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProviderCenterOverview } from './ProviderCenterOverview'
import type { ProviderRecord } from '../../features/settings/types'

const baseProviders: ProviderRecord[] = [
  { provider: 'openai', configured: true, updated_at: Date.now() },
  { provider: 'anthropic', configured: false, updated_at: null },
]

describe('ProviderCenterOverview', () => {
  it('renders total provider count', () => {
    render(<ProviderCenterOverview providers={baseProviders} lastTestResult={null} />)
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('Provedores registrados')).toBeInTheDocument()
  })

  it('renders configured count', () => {
    render(<ProviderCenterOverview providers={baseProviders} lastTestResult={null} />)
    expect(screen.getByText('Com credenciais armazenadas')).toBeInTheDocument()
    expect(screen.getByText('Configurados').nextElementSibling).toHaveTextContent('1')
  })

  it('renders not configured count', () => {
    render(<ProviderCenterOverview providers={baseProviders} lastTestResult={null} />)
    expect(screen.getByText('Sem credenciais')).toBeInTheDocument()
    expect(screen.getByText('Não configurados').nextElementSibling).toHaveTextContent('1')
  })

  it('counts only fresh healthy providers', () => {
    const providers: ProviderRecord[] = [
      { ...baseProviders[0], healthy: true, health_valid: true },
      { ...baseProviders[1], healthy: true, health_valid: false },
    ]
    render(<ProviderCenterOverview providers={providers} lastTestResult={null} />)
    expect(screen.getByText('Saudáveis').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Com teste recente válido')).toBeInTheDocument()
  })

  it('shows default state when no test result', () => {
    render(<ProviderCenterOverview providers={baseProviders} lastTestResult={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByText('Nenhum teste realizado')).toBeInTheDocument()
  })

  it('shows success badge for successful test', () => {
    render(
      <ProviderCenterOverview
        providers={baseProviders}
        lastTestResult={{ provider: 'openai', success: true }}
      />,
    )

    const badge = screen.getByText('Sucesso')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="success"]')).toBeInTheDocument()
  })

  it('shows failure badge for failed test', () => {
    render(
      <ProviderCenterOverview
        providers={baseProviders}
        lastTestResult={{ provider: 'openai', success: false, error: 'connection refused' }}
      />,
    )

    const badge = screen.getByText('Falha')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('[data-tone="danger"]')).toBeInTheDocument()
    expect(screen.getByText(/connection refused/)).toBeInTheDocument()
  })

  it('redacts secrets in failed test error', () => {
    render(
      <ProviderCenterOverview
        providers={baseProviders}
        lastTestResult={{
          provider: 'openai',
          success: false,
          error: 'Authorization Bearer sk-abcdefghijklmnopqrstuvwxyz',
        }}
      />,
    )

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toContain('sk-abcdefghijklmnopqrstuvwxyz')
  })

  it('shows provider name in test result', () => {
    render(
      <ProviderCenterOverview
        providers={baseProviders}
        lastTestResult={{ provider: 'anthropic', success: true }}
      />,
    )

    expect(screen.getByText('anthropic')).toBeInTheDocument()
  })
})
