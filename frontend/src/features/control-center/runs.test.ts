import { describe, expect, it } from 'vitest'
import { projectGovernedRuns } from './runs'

describe('Governed run projection', () => {
  it('returns only permitted status fields and ignores metadata', () => {
    const result = projectGovernedRuns([{
      run_id: 'run-123',
      status: 'running',
      updated_at: '2026-10-23T10:00:00Z',
      metadata: { api_key: 'secret', owner_id: 'private' },
      resolution: { reason: 'private' },
    }])
    expect(result).toEqual([{
      runId: 'run-123',
      status: 'running',
      updatedAt: '2026-10-23T10:00:00.000Z',
    }])
    expect(JSON.stringify(result)).not.toContain('secret')
    expect(JSON.stringify(result)).not.toContain('owner_id')
  })

  it('fails closed for unknown states, invalid IDs, invalid dates and non-arrays', () => {
    expect(projectGovernedRuns(null)).toEqual([])
    expect(projectGovernedRuns([{ run_id: '../../private', status: 'running' }])).toEqual([])
    expect(projectGovernedRuns([{ run_id: 'run_ok', status: 'custom', updated_at: 'not-a-date' }])).toEqual([
      { runId: 'run_ok', status: 'unknown', updatedAt: null },
    ])
  })

  it('limits the number of inspected rows', () => {
    const rows = Array.from({ length: 100 }, (_, index) => ({ run_id: 'run_' + index, status: 'completed' }))
    expect(projectGovernedRuns(rows)).toHaveLength(50)
  })
})
