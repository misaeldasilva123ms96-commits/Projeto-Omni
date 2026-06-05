import type { ReactNode } from 'react'

type OmniSystemNoticeProps = {
  children: ReactNode
  variant?: 'info' | 'warning' | 'error'
  onDismiss?: () => void
  className?: string
}

const variantClasses = {
  info: 'border-neon-cyan/20 bg-neon-cyan/8',
  warning: 'border-amber-400/20 bg-amber-400/8',
  error: 'border-red-400/20 bg-red-400/8',
}

export function OmniSystemNotice({ children, variant = 'info', onDismiss, className = '' }: OmniSystemNoticeProps) {
  return (
    <div className={`flex items-start justify-between gap-3 rounded-2xl border px-3 py-2.5 text-sm text-slate-100 ${variantClasses[variant]} ${className}`.trim()}>
      <span>{children}</span>
      {onDismiss ? (
        <button
          className="rounded-full border border-white/10 px-2 text-xs text-slate-200 transition hover:text-white"
          onClick={onDismiss}
          type="button"
        >
          OK
        </button>
      ) : null}
    </div>
  )
}
