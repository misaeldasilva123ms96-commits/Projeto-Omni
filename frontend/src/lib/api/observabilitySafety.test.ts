import { describe, expect, it } from 'vitest'
import type { ObservabilityApiResponse } from '../../types/observability'
import { observabilityApiEnvelopeToUi } from './adapters'

describe('observability API safety', () => {
  it('sanitizes nested snapshots and public errors', () => {
    const response = {
      status: 'error',
      error: 'Bearer abcdefghijklmnopqrstuvwxyz',
      snapshot: {
        generated_at: '2026-06-20T00:00:00Z',
        timeline: [{
          event_id: 'event-1',
          event_type: 'runtime',
          description: 'sk_proj_abcdefghijklmnop',
          outcome: 'failed',
          progress_score: 0,
          timestamp: '2026-06-20T00:00:00Z',
          evidence_ids: [],
          metadata: { headers: { authorization: 'secret' } },
        }],
        recent_traces: [],
        stack: 'should-not-render',
      },
    } as unknown as ObservabilityApiResponse

    const ui = observabilityApiEnvelopeToUi(response)
    const text = JSON.stringify(ui)

    expect(text).toContain('[REDACTED]')
    expect(text).not.toMatch(/abcdefghijklmnopqrstuvwxyz|sk_proj_|authorization|should-not-render/)
  })
})
