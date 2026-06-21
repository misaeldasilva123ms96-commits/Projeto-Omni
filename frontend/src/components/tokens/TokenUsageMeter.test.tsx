import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TokenUsageMeter } from './TokenUsageMeter'

describe('TokenUsageMeter', () => {
  it('renders complete detailed usage', () => {
    render(
      <TokenUsageMeter
        usage={{ inputTokens: 1_000, outputTokens: 200, totalTokens: 1_200 }}
        variant="detailed"
      />,
    )

    expect(screen.getByText('Entrada: 1.000')).toBeInTheDocument()
    expect(screen.getByText('Saída: 200')).toBeInTheDocument()
    expect(screen.getByText('Total: 1.200')).toBeInTheDocument()
  })

  it('renders only available partial values', () => {
    render(
      <TokenUsageMeter
        usage={{ inputTokens: 24, outputTokens: null, totalTokens: null }}
        variant="detailed"
      />,
    )

    expect(screen.getByText('Entrada: 24')).toBeInTheDocument()
    expect(screen.queryByText(/Saída:/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Total:/)).not.toBeInTheDocument()
  })

  it('renders a safe empty state', () => {
    render(
      <TokenUsageMeter
        usage={{ inputTokens: null, outputTokens: null, totalTokens: null }}
        variant="detailed"
      />,
    )

    expect(screen.getByText('Tokens indisponíveis')).toBeInTheDocument()
  })

  it('renders a compact topbar total without quota language', () => {
    render(
      <TokenUsageMeter
        usage={{ inputTokens: 1_000, outputTokens: 200, totalTokens: 1_200 }}
        variant="compact"
      />,
    )

    expect(screen.getByText('Tokens: 1.2k')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('/')
    expect(document.body.textContent).not.toContain('quota')
  })

  it('renders the available value for compact partial usage', () => {
    render(
      <TokenUsageMeter
        usage={{ inputTokens: 1_200, outputTokens: null, totalTokens: null }}
        variant="compact"
      />,
    )

    expect(screen.getByText('Tokens entrada: 1.2k')).toBeInTheDocument()
  })
})
