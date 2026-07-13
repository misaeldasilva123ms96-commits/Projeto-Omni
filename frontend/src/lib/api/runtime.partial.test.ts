import { beforeEach, describe, expect, it, vi } from 'vitest'

const getJson = vi.hoisted(() => vi.fn())
vi.mock('./client', () => ({ getJson }))
vi.mock('./operator', () => ({
  tryFetchOperatorMilestones: vi.fn(async () => null),
  tryFetchOperatorRuntimeSignals: vi.fn(async () => null),
  tryFetchOperatorStrategyChanges: vi.fn(async () => null),
}))

import { loadCognitiveTelemetryBundle } from './runtime'

describe('cognitive telemetry bundle resilience', () => {
  beforeEach(() => {
    getJson.mockImplementation(async (path: string) => {
      if (path === '/internal/swarm-log') throw new Error('optional endpoint unavailable')
      return { path }
    })
  })

  it('preserves successful telemetry when an optional source fails', async () => {
    const bundle = await loadCognitiveTelemetryBundle()
    expect(bundle.publicRuntime).toEqual({ path: '/api/v1/status' })
    expect(bundle.swarmLog).toBeNull()
    expect(bundle.failedSources).toContain('swarm log')
  })

  it('fails explicitly when every telemetry source is unavailable', async () => {
    getJson.mockRejectedValue(new Error('offline'))
    await expect(loadCognitiveTelemetryBundle()).rejects.toThrow('Telemetry endpoints are unavailable')
  })
})
