import { describe, expect, it } from 'vitest'
import { formatCompactTokenCount, normalizeTokenUsage } from './tokenUsage'

describe('token usage normalization', () => {
  it('normalizes complete usage and calculates the total', () => {
    expect(normalizeTokenUsage({
      inputTokens: 1_000,
      outputTokens: 250,
    })).toEqual({
      inputTokens: 1_000,
      outputTokens: 250,
      totalTokens: 1_250,
    })
  })

  it('preserves partial usage without inventing a total', () => {
    expect(normalizeTokenUsage({ inputTokens: 32 })).toEqual({
      inputTokens: 32,
      outputTokens: null,
      totalTokens: null,
    })
  })

  it('uses an explicit valid total when available', () => {
    expect(normalizeTokenUsage({
      inputTokens: 10,
      outputTokens: 5,
      totalTokens: 20,
    })).toEqual({
      inputTokens: 10,
      outputTokens: 5,
      totalTokens: 20,
    })
  })

  it.each([
    [-1],
    [1.5],
    [Number.POSITIVE_INFINITY],
    [Number.NaN],
  ])('ignores invalid token values: %s', (invalidValue) => {
    expect(normalizeTokenUsage({
      inputTokens: invalidValue,
      outputTokens: 4,
      totalTokens: invalidValue,
    })).toEqual({
      inputTokens: null,
      outputTokens: 4,
      totalTokens: null,
    })
  })

  it('accepts zero as factual usage', () => {
    expect(normalizeTokenUsage({
      inputTokens: 0,
      outputTokens: 0,
    })).toEqual({
      inputTokens: 0,
      outputTokens: 0,
      totalTokens: 0,
    })
  })

  it('formats compact totals for the topbar', () => {
    expect(formatCompactTokenCount(999)).toBe('999')
    expect(formatCompactTokenCount(1_200)).toBe('1.2k')
    expect(formatCompactTokenCount(1_000_000)).toBe('1M')
  })
})
