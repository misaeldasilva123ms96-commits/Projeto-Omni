export type NormalizedTokenUsage = {
  inputTokens: number | null
  outputTokens: number | null
  totalTokens: number | null
}

export type TokenUsageSource = {
  inputTokens?: unknown
  outputTokens?: unknown
  totalTokens?: unknown
}

export function normalizeTokenCount(value: unknown): number | null {
  return typeof value === 'number'
    && Number.isFinite(value)
    && Number.isInteger(value)
    && value >= 0
    ? value
    : null
}

export function firstValidTokenCount(...values: unknown[]): number | null {
  for (const value of values) {
    const normalized = normalizeTokenCount(value)
    if (normalized !== null) return normalized
  }
  return null
}

export function normalizeTokenUsage(source: TokenUsageSource): NormalizedTokenUsage {
  const inputTokens = normalizeTokenCount(source.inputTokens)
  const outputTokens = normalizeTokenCount(source.outputTokens)
  const explicitTotal = normalizeTokenCount(source.totalTokens)
  const totalTokens = explicitTotal
    ?? (inputTokens !== null && outputTokens !== null
      ? inputTokens + outputTokens
      : null)

  return {
    inputTokens,
    outputTokens,
    totalTokens,
  }
}

function compactValue(value: number, divisor: number, suffix: string): string {
  const scaled = value / divisor
  const formatted = scaled >= 10 || Number.isInteger(scaled)
    ? scaled.toFixed(0)
    : scaled.toFixed(1)
  return `${formatted}${suffix}`
}

export function formatCompactTokenCount(value: number): string {
  if (value >= 1_000_000) return compactValue(value, 1_000_000, 'M')
  if (value >= 1_000) return compactValue(value, 1_000, 'k')
  return value.toLocaleString('pt-BR')
}
