import { useMemo } from 'react'
import type { TokenUsageSummary } from '../../types'
import { OmniCard } from '../ui/OmniCard'

type TokenUsageChartProps = {
  summary: TokenUsageSummary
  className?: string
}

function formatDateLabel(iso: string) {
  try {
    const d = new Date(iso + 'T00:00:00')
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  } catch {
    return iso.slice(5, 10)
  }
}

const MAX_BARS = 30

export function TokenUsageChart({ summary, className = '' }: TokenUsageChartProps) {
  const recent = useMemo(() => {
    const sorted = [...summary.byDate].sort((a, b) => a.date.localeCompare(b.date))
    return sorted.slice(-MAX_BARS)
  }, [summary.byDate])

  const maxTokens = useMemo(() => {
    if (recent.length === 0) return 0
    return Math.max(...recent.map((r) => r.totalTokens), 1)
  }, [recent])

  if (recent.length === 0) {
    return (
      <OmniCard variant="panel" className={className}>
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Consumo Diário</p>
        <p className="mt-6 text-center text-sm text-slate-500">Nenhum dado de uso disponível</p>
      </OmniCard>
    )
  }

  return (
    <OmniCard variant="panel" className={className}>
      <p className="mb-4 text-xs uppercase tracking-[0.25em] text-violet-200/70">Consumo Diário</p>

      <div className="flex items-end gap-1.5" style={{ height: 160 }}>
        {recent.map((record) => {
          const inputHeight = maxTokens > 0 ? (record.inputTokens / maxTokens) * 120 : 0
          const outputHeight = maxTokens > 0 ? ((record.inputTokens + record.outputTokens) / maxTokens) * 120 : 0

          return (
            <div
              key={record.date}
              className="group relative flex flex-1 flex-col items-center justify-end"
              title={`${formatDateLabel(record.date)} — Input: ${record.inputTokens.toLocaleString()} / Output: ${record.outputTokens.toLocaleString()}`}
            >
              <div className="w-full rounded-t-sm bg-emerald-500/40 transition hover:bg-emerald-500/60" style={{ height: Math.max(inputHeight, 1) }} />
              <div className="w-full rounded-t-sm bg-amber-500/30 transition hover:bg-amber-500/50" style={{ height: Math.max(outputHeight - inputHeight, 1) }} />
              <span className="mt-1 text-[10px] text-slate-500">{formatDateLabel(record.date)}</span>
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-emerald-500/40" /> Input
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-amber-500/30" /> Output
        </span>
      </div>
    </OmniCard>
  )
}
