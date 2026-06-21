import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ProviderHealthCard } from '../providers/ProviderHealthCard'
import type { ProviderRecord } from '../../features/settings/types'

const baseProvider: ProviderRecord = { provider: 'openai', configured: true, updated_at: null }

describe('Omni success-state adoption', () => {
  const defaultProps = {
    provider: baseProvider,
    submitting: false,
    testing: false,
    onSave: vi.fn(),
    onUpdate: vi.fn(),
    onRemove: vi.fn(),
    onTest: vi.fn(),
    apiKey: 'sk-test',
    onApiKeyChange: vi.fn(),
  }

  it('renders OmniSuccessState for successful connection test', () => {
    render(
      <ProviderHealthCard
        {...defaultProps}
        testResult={{ provider: 'openai', success: true }}
      />,
    )

    expect(screen.getByTestId('omni-success-state')).toBeInTheDocument()
    expect(screen.getByText('Conexão bem-sucedida')).toBeInTheDocument()
  })

  it('renders error text for failed connection test', () => {
    render(
      <ProviderHealthCard
        {...defaultProps}
        testResult={{ provider: 'openai', success: false, error: 'connection refused' }}
      />,
    )

    expect(screen.queryByTestId('omni-success-state')).not.toBeInTheDocument()
    expect(document.body.textContent).toContain('Falha:')
    expect(document.body.textContent).toContain('connection refused')
  })

  it('does not render test results when testResult is null', () => {
    render(<ProviderHealthCard {...defaultProps} testResult={null} />)

    expect(screen.queryByTestId('omni-success-state')).not.toBeInTheDocument()
    expect(screen.queryByText(/Falha:|Conexão bem-sucedida/)).not.toBeInTheDocument()
  })

  it('preserves redaction for failed test errors', () => {
    render(
      <ProviderHealthCard
        {...defaultProps}
        apiKey=""
        onApiKeyChange={vi.fn()}
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
