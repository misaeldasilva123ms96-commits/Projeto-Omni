import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ProviderHealthCard } from './ProviderHealthCard'
import type { ProviderRecord } from '../../features/settings/types'

const baseProvider: ProviderRecord = { provider: 'openai', configured: false, updated_at: null }

describe('ProviderHealthCard', () => {
  const defaultProps = {
    provider: baseProvider,
    testResult: null,
    submitting: false,
    testing: false,
    onSave: vi.fn(),
    onUpdate: vi.fn(),
    onRemove: vi.fn(),
    onTest: vi.fn(),
    apiKey: '',
    onApiKeyChange: vi.fn(),
  }

  it('renders provider display name', () => {
    render(<ProviderHealthCard {...defaultProps} />)
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
  })

  it('shows configured badge when provider is configured', () => {
    render(<ProviderHealthCard {...defaultProps} provider={{ ...baseProvider, configured: true }} />)
    expect(screen.getByText('Conectado')).toBeInTheDocument()
  })

  it('shows not configured badge when not configured', () => {
    render(<ProviderHealthCard {...defaultProps} />)
    expect(screen.getByText('Não configurado')).toBeInTheDocument()
  })

  it('renders API key input', () => {
    render(<ProviderHealthCard {...defaultProps} />)
    expect(screen.getByLabelText('API Key')).toBeInTheDocument()
  })

  it('calls onApiKeyChange when input changes', async () => {
    const onApiKeyChange = vi.fn()
    render(<ProviderHealthCard {...defaultProps} onApiKeyChange={onApiKeyChange} />)
    await userEvent.type(screen.getByLabelText('API Key'), 's')
    expect(onApiKeyChange).toHaveBeenCalledWith('s')
  })

  it('calls onSave when configure button is clicked', async () => {
    const onSave = vi.fn()
    render(<ProviderHealthCard {...defaultProps} onSave={onSave} apiKey="sk-test" />)
    await userEvent.click(screen.getByRole('button', { name: /configurar/i }))
    expect(onSave).toHaveBeenCalledWith('sk-test')
  })

  it('calls onUpdate when update button is clicked for configured provider', async () => {
    const onUpdate = vi.fn()
    render(
      <ProviderHealthCard
        {...defaultProps}
        provider={{ ...baseProvider, configured: true }}
        onUpdate={onUpdate}
        apiKey="sk-test"
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /atualizar/i }))
    expect(onUpdate).toHaveBeenCalledWith('sk-test')
  })

  it('calls onTest when test button is clicked', async () => {
    const onTest = vi.fn()
    render(<ProviderHealthCard {...defaultProps} onTest={onTest} apiKey="sk-test" />)
    await userEvent.click(screen.getByRole('button', { name: /testar conexão/i }))
    expect(onTest).toHaveBeenCalledWith('sk-test')
  })

  it('shows remove button when configured', () => {
    render(<ProviderHealthCard {...defaultProps} provider={{ ...baseProvider, configured: true }} />)
    expect(screen.getByRole('button', { name: /remover/i })).toBeInTheDocument()
  })

  it('disables buttons when submitting', () => {
    render(<ProviderHealthCard {...defaultProps} submitting={true} apiKey="sk-test" />)
    expect(screen.getByRole('button', { name: /salvando/i })).toBeDisabled()
  })

  it('disables test button when apiKey is empty', () => {
    render(<ProviderHealthCard {...defaultProps} apiKey="" />)
    expect(screen.getByRole('button', { name: /testar conexão/i })).toBeDisabled()
  })

  it('does not render raw provider test errors', () => {
    render(
      <ProviderHealthCard
        {...defaultProps}
        testResult={{
          provider: 'openai',
          success: false,
          error: 'headers authorization Bearer abcdefghijklmnopqrstuvwxyz',
        }}
      />,
    )

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })
})
