import type { ChatUsage } from '../../types'

type TokenUsageMeterProps = {
  usage: ChatUsage | null | undefined
  quotaLimit?: number
  className?: string
}

export function TokenUsageMeter({ usage, quotaLimit = 128_000, className = '' }: TokenUsageMeterProps) {
  const input = usage?.input_tokens ?? 0
  const output = usage?.output_tokens ?? 0
  const total = input + output
  const quotaPct = Math.min((total / quotaLimit) * 100, 100)

  if (total === 0) {
    return (
      <div className={`flex items-center gap-2 text-xs text-slate-400 ${className}`.trim()}>
        <span className="h-2 w-16 rounded-full bg-white/10" />
        <span>—</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 ${className}`.trim()} title={`${total.toLocaleString()} / ${quotaLimit.toLocaleString()} tokens`}>
      <div className="relative h-2 w-16 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            quotaPct > 80 ? 'bg-amber-400' : quotaPct > 95 ? 'bg-red-400' : 'bg-neon-cyan'
          }`}
          style={{ width: `${quotaPct}%` }}
        />
      </div>
      <span className="text-[11px] text-slate-300">
        {total.toLocaleString()}
      </span>
    </div>
  )
}
