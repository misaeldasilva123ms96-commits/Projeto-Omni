import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { GovernanceCenterPage } from './GovernanceCenterPage'
import { ObservabilityPage } from './ObservabilityPage'
import { ProviderCenterPage } from './ProviderCenterPage'

const mocks = vi.hoisted(() => ({
  fetchGovernanceDecisions: vi.fn(),
}))

vi.mock('../hooks/useObservabilitySnapshot', () => ({
  useObservabilitySnapshot: () => ({
    snapshot: {
      generated_at: '2026-06-19T00:00:00Z',
      goal: null,
      goal_history: [],
      timeline: [],
      latest_trace: null,
      recent_traces: [],
      latest_simulation: null,
      recent_simulations: [],
      recent_episodes: [],
      semantic_facts: [],
      active_procedural_pattern: null,
      recent_procedural_updates: [],
      recent_learning_signals: [],
      pending_evolution_proposal_count: 0,
      recent_evolution_proposals: [],
      warnings: [],
    },
    loading: false,
    error: null,
  }),
}))

vi.mock('../hooks/useObservabilityStream', () => ({
  useObservabilityStream: () => ({
    snapshot: null,
    status: 'idle',
    error: null,
  }),
}))

vi.mock('../features/settings/hooks/useProviders', () => ({
  useProviders: () => ({
    actionError: null,
    clearActionError: vi.fn(),
    createProvider: vi.fn(),
    editProvider: vi.fn(),
    lastTestResult: null,
    loading: false,
    providers: [{ provider: 'openai', configured: true, updated_at: null }],
    removeProvider: vi.fn(),
    runConnectionTest: vi.fn(),
    submitting: false,
    testingProvider: null,
  }),
}))

vi.mock('../lib/omniData', () => ({
  fetchGovernanceDecisions: mocks.fetchGovernanceDecisions,
}))

vi.mock('../lib/env', () => ({
  canUseApi: () => true,
}))

const renderShell = (content: ReactNode) => content
const commonProps = {
  mode: 'chat' as const,
  onChangeMode: vi.fn(),
  onChangeView: vi.fn(),
  renderShell,
}

describe('destination context filtering', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    mocks.fetchGovernanceDecisions.mockReset()
    mocks.fetchGovernanceDecisions.mockResolvedValue([])
  })

  it('shows observability contextual empty state when no data matches', () => {
    window.history.replaceState({}, '', '/observability?trace_id=missing')

    render(<ObservabilityPage {...commonProps} view="observability" />)

    expect(screen.getByText('Contexto do Runtime Inspector')).toBeInTheDocument()
    expect(screen.getByText('Nenhum registro correspondente encontrado.')).toBeInTheDocument()
  })

  it('filters Provider Center by provider context', () => {
    window.history.replaceState({}, '', '/provider-center?provider=deepseek')

    render(<ProviderCenterPage {...commonProps} view="provider-center" />)

    expect(screen.getByText('Contexto recebido, mas não há dados disponíveis para este filtro.')).toBeInTheDocument()
    expect(screen.queryByText('OpenAI')).not.toBeInTheDocument()
  })

  it('filters Governance Center by decision context', async () => {
    mocks.fetchGovernanceDecisions.mockResolvedValue([{
      id: 'decision-1',
      sessionId: 'req-1',
      decision: 'allowed',
      category: 'read',
      policy: 'default',
      reason: 'ok',
      riskLevel: 'low',
      timestamp: '2026-06-19T00:00:00Z',
    }])
    window.history.replaceState({}, '', '/governance?decision=blocked')

    render(<GovernanceCenterPage {...commonProps} view="governance" />)

    await waitFor(() => {
      expect(screen.getByText('Contexto recebido, mas não há dados disponíveis para este filtro.')).toBeInTheDocument()
    })
    expect(screen.queryByText('Allowed')).not.toBeInTheDocument()
  })

  it('preserves Provider Center behavior without query context', () => {
    window.history.replaceState({}, '', '/provider-center')

    render(<ProviderCenterPage {...commonProps} view="provider-center" />)

    expect(screen.queryByText('Contexto do Runtime Inspector')).not.toBeInTheDocument()
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
  })
})
