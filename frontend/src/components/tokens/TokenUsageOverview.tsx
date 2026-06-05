import type { TokenUsageSummary } from '../../types'
import { OmniCard } from '../ui/OmniCard'

type TokenUsageOverviewProps = {
  summary: TokenUsageSummary
  className?: string
}

function formatNumber(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export function TokenUsageOverview({ summary, className = '' }: TokenUsageOverviewProps) {
  return (
    <div className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${className}`.trim()}>
      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Total de Tokens</p>
        <p className="mt-2 text-2xl font-semibold text-white">{formatNumber(summary.totalTokens)}</p>
        <p className="mt-1 text-xs text-slate-400">Input + Output</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Tokens Input</p>
        <p className="mt-2 text-2xl font-semibold text-emerald-300">{formatNumber(summary.totalInputTokens)}</p>
        <p className="mt-1 text-xs text-slate-400">Total de entrada</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Tokens Output</p>
        <p className={`mt-2 text-2xl font-semibold ${summary.totalOutputTokens > 0 ? 'text-amber-300' : 'text-slate-400'}`}>
          {formatNumber(summary.totalOutputTokens)}
        </p>
        <p className="mt-1 text-xs text-slate-400">Total de saída</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Média/Requisição</p>
        {summary.totalRequests > 0 ? (
          <>
            <p className="mt-2 text-2xl font-semibold text-white">{formatNumber(summary.avgTokensPerRequest)}</p>
            <p className="mt-1 text-xs text-slate-400">{formatNumber(summary.totalRequests)} requisições</p>
          </>
        ) : (
          <>
            <p className="mt-2 text-lg font-semibold text-slate-500">—</p>
            <p className="mt-1 text-xs text-slate-500">Nenhuma requisição</p>
          </>
        )}
      </OmniCard>
    </div>
  )
}
