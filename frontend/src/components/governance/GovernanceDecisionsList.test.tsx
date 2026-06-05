import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GovernanceDecisionsList } from './GovernanceDecisionsList'
import type { GovernanceDecision } from '../../types'

const decisions: GovernanceDecision[] = [
  {
    id: 'dec-1',
    sessionId: 'session-1',
    decision: 'allowed',
    category: 'data-access',
    policy: 'allow-data-read',
    reason: 'Access to read operations is permitted',
    riskLevel: 'low',
    timestamp: new Date().toISOString(),
  },
  {
    id: 'dec-2',
    sessionId: 'session-2',
    decision: 'blocked',
    category: 'system-call',
    policy: 'deny-system-write',
    reason: 'Write operations to system directory are blocked',
    riskLevel: 'high',
    timestamp: new Date().toISOString(),
  },
]

describe('GovernanceDecisionsList', () => {
  it('shows empty state when no decisions', () => {
    render(<GovernanceDecisionsList decisions={[]} />)
    expect(screen.getByText('Nenhuma decisão de governança registrada.')).toBeInTheDocument()
  })

  it('renders decision badges', () => {
    render(<GovernanceDecisionsList decisions={decisions} />)
    expect(screen.getByText('Allowed')).toBeInTheDocument()
    expect(screen.getByText('Blocked')).toBeInTheDocument()
  })

  it('renders risk level badges', () => {
    render(<GovernanceDecisionsList decisions={decisions} />)
    expect(screen.getByText('low')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('renders category labels', () => {
    render(<GovernanceDecisionsList decisions={decisions} />)
    expect(screen.getByText('data-access')).toBeInTheDocument()
    expect(screen.getByText('system-call')).toBeInTheDocument()
  })

  it('renders policy names', () => {
    render(<GovernanceDecisionsList decisions={decisions} />)
    expect(screen.getByText('allow-data-read')).toBeInTheDocument()
    expect(screen.getByText('deny-system-write')).toBeInTheDocument()
  })

  it('renders reason text', () => {
    render(<GovernanceDecisionsList decisions={decisions} />)
    expect(screen.getByText(/Access to read operations is permitted/)).toBeInTheDocument()
  })
})
