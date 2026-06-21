import type { HTMLAttributes, ReactNode } from 'react'

export type OmniBadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'muted'

export type OmniBadgeProps = {
  children: ReactNode
  tone?: OmniBadgeTone
  className?: string
} & Omit<HTMLAttributes<HTMLSpanElement>, 'children'>

const toneClasses: Record<OmniBadgeTone, string> = {
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  warning: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
  danger: 'bg-red-500/15 text-red-300 border-red-500/25',
  info: 'bg-blue-500/15 text-blue-300 border-blue-500/25',
  muted: 'bg-white/[0.04] text-slate-400 border-white/10',
}

export function OmniBadge({ children, tone = 'info', className = '', ...rest }: OmniBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] ${toneClasses[tone]} ${className}`.trim()}
      data-tone={tone}
      {...rest}
    >
      {children}
    </span>
  )
}
