import {
  formatCompactTokenCount,
  type NormalizedTokenUsage,
} from '../../lib/tokenUsage'

type TokenUsageMeterProps = {
  usage: NormalizedTokenUsage
  variant: 'compact' | 'detailed'
  className?: string
}

function hasTokenUsage(usage: NormalizedTokenUsage): boolean {
  return usage.inputTokens !== null
    || usage.outputTokens !== null
    || usage.totalTokens !== null
}

function formatDetailedTokenCount(value: number): string {
  return value.toLocaleString('pt-BR')
}

export function TokenUsageMeter({
  usage,
  variant,
  className = '',
}: TokenUsageMeterProps) {
  if (!hasTokenUsage(usage)) {
    return (
      <span className={`text-xs text-slate-500 ${className}`.trim()}>
        Tokens indisponíveis
      </span>
    )
  }

  if (variant === 'compact') {
    const compactLabel = usage.totalTokens !== null
      ? `Tokens: ${formatCompactTokenCount(usage.totalTokens)}`
      : usage.inputTokens !== null
        ? `Tokens entrada: ${formatCompactTokenCount(usage.inputTokens)}`
        : `Tokens saída: ${formatCompactTokenCount(usage.outputTokens as number)}`

    return (
      <span className={`text-xs font-medium text-slate-300 ${className}`.trim()}>
        {compactLabel}
      </span>
    )
  }

  return (
    <div className={`flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-300 ${className}`.trim()}>
      {usage.inputTokens !== null ? (
        <span>Entrada: {formatDetailedTokenCount(usage.inputTokens)}</span>
      ) : null}
      {usage.outputTokens !== null ? (
        <span>Saída: {formatDetailedTokenCount(usage.outputTokens)}</span>
      ) : null}
      {usage.totalTokens !== null ? (
        <span className="font-medium text-white">
          Total: {formatDetailedTokenCount(usage.totalTokens)}
        </span>
      ) : null}
    </div>
  )
}
