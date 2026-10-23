import { describe, expect, it } from 'vitest'
import type { ProviderRecord } from '../settings/types'
import type { RuntimeSignalsResponse } from '../../types'
import { providerOperationalState, recentRuntimeMode, safeCount, RUNTIME_LAYERS } from './model'

const provider = (changes: Partial<ProviderRecord>): ProviderRecord => ({
  provider: 'groq',
  configured: true,
  health_valid: false,
  healthy: null,
  updated_at: null,
  ...changes,
})

describe('Control Center truthful monitoring model', () => {
  it('does not equate a configured API key with a healthy provider', () => {
    expect(providerOperationalState(provider({}))).toBe('unverified')
    expect(providerOperationalState(provider({ configured: false, healthy: true, health_valid: true }))).toBe('unconfigured')
    expect(providerOperationalState(provider({ health_valid: true, healthy: false }))).toBe('unhealthy')
    expect(providerOperationalState(provider({ health_valid: true, healthy: true }))).toBe('healthy')
  })

  it('reports only an explicitly returned runtime mode', () => {
    expect(recentRuntimeMode(null)).toBeNull()
    expect(recentRuntimeMode({ latest_run_summary: {}, recent_mode_transitions: [], recent_signals: [], status: 'ok' })).toBeNull()
    const result: RuntimeSignalsResponse = {
      status: 'ok',
      latest_run_summary: { runtime_mode: 'SAFE_DEGRADED_FALLBACK' },
      recent_mode_transitions: [],
      recent_signals: [],
    }
    expect(recentRuntimeMode(result)).toBe('SAFE_DEGRADED_FALLBACK')
  })

  it('does not fabricate unknown metric values', () => {
    expect(safeCount(null)).toBe('—')
    expect(safeCount(undefined)).toBe('—')
    expect(safeCount(-1)).toBe('—')
    expect(safeCount(0)).toBe('0')
  })

  it('maps every documented runtime layer to a real source path', () => {
    expect(RUNTIME_LAYERS.map((layer) => layer.id)).toEqual(['frontend', 'rust', 'python', 'node'])
    expect(RUNTIME_LAYERS.every((layer) => layer.path.length > 0)).toBe(true)
  })
})
