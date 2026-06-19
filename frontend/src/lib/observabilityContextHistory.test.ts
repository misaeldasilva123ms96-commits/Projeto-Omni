import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ObservabilityContext } from './observabilityContext'
import {
  CONTEXT_HISTORY_MAX_ENTRIES,
  clearObservabilityContextHistory,
  loadObservabilityContextHistory,
  saveObservabilityContextHistory,
} from './observabilityContextHistory'

function storage(): Storage {
  const values = new Map<string, string>()
  return {
    get length() {
      return values.size
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  }
}

describe('observability context history', () => {
  let session: Storage

  beforeEach(() => {
    session = storage()
  })

  it('saves only sanitized allowlisted context', () => {
    saveObservabilityContextHistory(
      '/observability',
      {
        trace_id: 'trace-safe',
        request_id: 'r'.repeat(120),
        token: 'secret',
        payload: 'raw',
      } as ObservabilityContext,
      session,
    )

    const history = loadObservabilityContextHistory(session)
    expect(history).toHaveLength(1)
    expect(history[0].path).toBe('/observability')
    expect(history[0].context.trace_id).toBe('trace-safe')
    expect(history[0].context.request_id).toHaveLength(80)
    expect(JSON.stringify(history)).not.toMatch(/secret|payload|token|raw/)
  })

  it('deduplicates identical path and context while keeping the latest first', () => {
    saveObservabilityContextHistory('/observability', { trace_id: 'trace-1' }, session)
    saveObservabilityContextHistory('/provider-center', { provider: 'openai' }, session)
    saveObservabilityContextHistory('/observability', { trace_id: 'trace-1' }, session)

    const history = loadObservabilityContextHistory(session)
    expect(history).toHaveLength(2)
    expect(history[0]).toMatchObject({
      path: '/observability',
      context: { trace_id: 'trace-1' },
    })
  })

  it('limits history to the configured maximum', () => {
    for (let index = 0; index < CONTEXT_HISTORY_MAX_ENTRIES + 3; index += 1) {
      saveObservabilityContextHistory(
        '/observability',
        { trace_id: `trace-${index}` },
        session,
      )
    }

    const history = loadObservabilityContextHistory(session)
    expect(history).toHaveLength(CONTEXT_HISTORY_MAX_ENTRIES)
    expect(history[0].context.trace_id).toBe(
      `trace-${CONTEXT_HISTORY_MAX_ENTRIES + 2}`,
    )
  })

  it('ignores and resets corrupted sessionStorage data', () => {
    session.setItem('omni.observability.context-history.v1', '{broken')

    expect(loadObservabilityContextHistory(session)).toEqual([])
    expect(session.getItem('omni.observability.context-history.v1')).toBeNull()
  })

  it('degrades safely when sessionStorage is unavailable', () => {
    const unavailable = {
      getItem: vi.fn(() => {
        throw new Error('blocked')
      }),
      removeItem: vi.fn(() => {
        throw new Error('blocked')
      }),
      setItem: vi.fn(() => {
        throw new Error('blocked')
      }),
    } as unknown as Storage

    expect(loadObservabilityContextHistory(unavailable)).toEqual([])
    expect(() => {
      saveObservabilityContextHistory(
        '/observability',
        { trace_id: 'trace-safe' },
        unavailable,
      )
    }).not.toThrow()
    expect(() => {
      clearObservabilityContextHistory(unavailable)
    }).not.toThrow()
  })

  it('clears only context history', () => {
    session.setItem('unrelated', 'keep')
    saveObservabilityContextHistory('/governance', { decision: 'blocked' }, session)

    clearObservabilityContextHistory(session)

    expect(loadObservabilityContextHistory(session)).toEqual([])
    expect(session.getItem('unrelated')).toBe('keep')
  })
})
