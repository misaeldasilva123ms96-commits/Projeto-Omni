import { describe, expect, it } from 'vitest'
import type { ProviderRecord } from '../features/settings/types'
import type { GovernanceDecision } from '../types'
import type { ObservabilitySnapshot, TraceSnapshot } from '../types/observability'
import {
  filterGovernanceDecisionsByContext,
  filterObservabilitySnapshotByContext,
  filterProvidersByContext,
  parseObservabilityContext,
  serializeObservabilityContext,
} from './observabilityContext'

function trace(traceId: string, metadata: Record<string, unknown> = {}): TraceSnapshot {
  return {
    trace_id: traceId,
    final_outcome: 'ok',
    started_at: '2026-06-19T00:00:00Z',
    decisions: [],
    governance_verdicts: [],
    metadata,
  }
}

function snapshot(): ObservabilitySnapshot {
  const matchingTrace = trace('trace-1', {
    request_id: 'req-1',
    runtime_mode: 'FULL_COGNITIVE_RUNTIME',
    tool: 'read_file',
  })
  return {
    generated_at: '2026-06-19T00:00:00Z',
    goal: null,
    goal_history: [],
    timeline: [{
      event_id: 'event-1',
      event_type: 'runtime',
      description: 'runtime event',
      outcome: 'ok',
      progress_score: 1,
      timestamp: '2026-06-19T00:00:00Z',
      evidence_ids: [],
      metadata: { request_id: 'req-1' },
    }],
    latest_trace: matchingTrace,
    recent_traces: [matchingTrace, trace('trace-2')],
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
  }
}

describe('observability context', () => {
  it('parses only allowed query parameters', () => {
    const context = parseObservabilityContext(
      '?request_id=req-1&trace_id=trace-1&runtime_mode=FULL_COGNITIVE_RUNTIME&provider=openai&tool=read_file&decision=allowed',
    )

    expect(context).toEqual({
      request_id: 'req-1',
      trace_id: 'trace-1',
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      provider: 'openai',
      tool: 'read_file',
      decision: 'allowed',
    })
  })

  it('ignores forbidden, unknown, and sensitive values', () => {
    const context = parseObservabilityContext(
      '?trace_id=trace-safe&token=secret&payload=raw&unknown=value&request_id=Bearer%20should-not-render',
    )

    expect(context).toEqual({ trace_id: 'trace-safe' })
    expect(JSON.stringify(context)).not.toContain('should-not-render')
    expect(JSON.stringify(context)).not.toContain('secret')
  })

  it('truncates long safe values', () => {
    const context = parseObservabilityContext(`?request_id=${'a'.repeat(200)}`)

    expect(context.request_id).toHaveLength(80)
  })

  it('serializes only sanitized allowlisted context', () => {
    expect(serializeObservabilityContext({
      trace_id: 'trace-safe',
      provider: 'openai',
      request_id: 'Bearer should-not-render',
    })).toBe('?trace_id=trace-safe&provider=openai')
  })

  it('filters observability traces using prioritized context', () => {
    const result = filterObservabilitySnapshotByContext(
      snapshot(),
      parseObservabilityContext('?trace_id=trace-1&request_id=other'),
    )

    expect(result.matched).toBe(true)
    expect(result.snapshot?.recent_traces.map((item) => item.trace_id)).toEqual(['trace-1'])
    expect(result.snapshot?.latest_trace?.trace_id).toBe('trace-1')
  })

  it('returns a contextual empty result when observability data does not match', () => {
    const result = filterObservabilitySnapshotByContext(
      snapshot(),
      parseObservabilityContext('?trace_id=missing'),
    )

    expect(result.matched).toBe(false)
  })

  it('filters providers and governance decisions without changing no-context behavior', () => {
    const providers: ProviderRecord[] = [
      { provider: 'openai', configured: true, updated_at: null },
      { provider: 'groq', configured: false, updated_at: null },
    ]
    const decisions: GovernanceDecision[] = [
      {
        id: 'decision-1',
        sessionId: 'req-1',
        decision: 'allowed',
        category: 'read',
        policy: 'default',
        reason: 'ok',
        riskLevel: 'low',
        timestamp: '2026-06-19T00:00:00Z',
      },
      {
        id: 'decision-2',
        sessionId: 'req-2',
        decision: 'blocked',
        category: 'write',
        policy: 'strict',
        reason: 'blocked',
        riskLevel: 'high',
        timestamp: '2026-06-19T00:00:00Z',
      },
    ]

    expect(filterProvidersByContext(providers, {})).toEqual(providers)
    expect(filterProvidersByContext(providers, { provider: 'openai' })).toEqual([providers[0]])
    expect(filterProvidersByContext(providers, { request_id: 'req-1' })).toEqual([])
    expect(filterGovernanceDecisionsByContext(decisions, { decision: 'blocked' })).toEqual([decisions[1]])
    expect(filterGovernanceDecisionsByContext(decisions, { request_id: 'req-1' })).toEqual([decisions[0]])
    expect(filterGovernanceDecisionsByContext(decisions, { trace_id: 'trace-1' })).toEqual([])
  })
})
