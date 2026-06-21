import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OperationalTimeline } from './OperationalTimeline'
import { SpecialistTraceViewer } from './SpecialistTraceViewer'

describe('observability rendering safety', () => {
  it('redacts sensitive timeline and trace strings', () => {
    render(
      <>
        <OperationalTimeline
          events={[{
            event_id: 'event-1',
            event_type: 'runtime',
            description: 'headers authorization Bearer abcdefghijklmnopqrstuvwxyz',
            outcome: 'stderr sk_proj_abcdefghijklmnop',
            progress_score: 1,
            timestamp: '2026-06-20T00:00:00Z',
            evidence_ids: [],
            metadata: {},
          }]}
        />
        <SpecialistTraceViewer
          latestTrace={{
            trace_id: 'trace-safe',
            final_outcome: 'stack ghp_abcdefghijklmnopqrstuvwxyz123456',
            started_at: '2026-06-20T00:00:00Z',
            decisions: [{
              decision_id: 'decision-1',
              specialist_type: 'planner',
              status: 'done',
              reasoning: 'Bearer abcdefghijklmnopqrstuvwxyz',
              confidence: 1,
              decided_at: '2026-06-20T00:00:00Z',
              metadata: {},
            }],
            governance_verdicts: [],
            metadata: {},
          }}
          recentTraces={[]}
        />
      </>,
    )

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toMatch(/abcdefghijklmnopqrstuvwxyz|sk_proj_|ghp_/)
  }, 20_000)
})
