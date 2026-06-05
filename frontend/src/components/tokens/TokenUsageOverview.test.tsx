import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TokenUsageOverview } from './TokenUsageOverview'
import type { TokenUsageSummary } from '../../types'

const sampleSummary: TokenUsageSummary = {
  totalTokens: 1_500_000,
  totalInputTokens: 1_000_000,
  totalOutputTokens: 500_000,
  totalRequests: 250,
  avgTokensPerRequest: 6000,
  byDate: [],
}

describe('TokenUsageOverview', () => {
  it('renders all four stat cards', () => {
    const { container } = render(<TokenUsageOverview summary={sampleSummary} />)
    expect(container.querySelectorAll('.grid > div')).toHaveLength(4)
  })

  it('formats total tokens in millions', () => {
    render(<TokenUsageOverview summary={sampleSummary} />)
    expect(screen.getByText('1.5M')).toBeInTheDocument()
  })

  it('formats input tokens in millions', () => {
    render(<TokenUsageOverview summary={sampleSummary} />)
    expect(screen.getByText('1.0M')).toBeInTheDocument()
  })

  it('formats output tokens', () => {
    render(<TokenUsageOverview summary={sampleSummary} />)
    expect(screen.getByText('500.0K')).toBeInTheDocument()
  })

  it('shows dash when there are no requests', () => {
    const empty = { ...sampleSummary, totalRequests: 0, avgTokensPerRequest: 0 }
    render(<TokenUsageOverview summary={empty} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('shows request count', () => {
    render(<TokenUsageOverview summary={sampleSummary} />)
    expect(screen.getByText(/250 requisições/)).toBeInTheDocument()
  })

  it('renders section headers', () => {
    render(<TokenUsageOverview summary={sampleSummary} />)
    expect(screen.getByText('Total de Tokens')).toBeInTheDocument()
    expect(screen.getByText('Tokens Input')).toBeInTheDocument()
    expect(screen.getByText('Tokens Output')).toBeInTheDocument()
    expect(screen.getByText('Média/Requisição')).toBeInTheDocument()
  })
})
