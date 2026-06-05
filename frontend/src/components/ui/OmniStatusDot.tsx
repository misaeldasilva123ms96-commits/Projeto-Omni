type OmniStatusDotTone = 'success' | 'warning' | 'danger' | 'info' | 'inactive'

type OmniStatusDotProps = {
  tone?: OmniStatusDotTone
  className?: string
  animate?: boolean
}

const toneClasses: Record<OmniStatusDotTone, string> = {
  success: 'bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.5)]',
  warning: 'bg-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.5)]',
  danger: 'bg-red-400 shadow-[0_0_12px_rgba(248,113,113,0.5)]',
  info: 'bg-blue-400 shadow-[0_0_12px_rgba(96,165,250,0.5)]',
  inactive: 'bg-slate-500',
}

export function OmniStatusDot({ tone = 'info', className = '', animate = false }: OmniStatusDotProps) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${toneClasses[tone]} ${animate ? 'omni-active-dot' : ''} ${className}`.trim()}
    />
  )
}
