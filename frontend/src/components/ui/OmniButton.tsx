import type { ButtonHTMLAttributes, ReactNode } from 'react'

type OmniButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

type OmniButtonProps = {
  children: ReactNode
  variant?: OmniButtonVariant
  className?: string
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'>

const variantClasses: Record<OmniButtonVariant, string> = {
  primary:
    'bg-[linear-gradient(135deg,rgba(181,109,255,0.92),rgba(78,164,255,0.92))] text-white hover:scale-[1.01] active:translate-y-px shadow-[0_0_20px_rgba(123,97,255,0.18)]',
  secondary:
    'border border-white/10 bg-white/[0.05] text-slate-200 hover:bg-white/[0.08] hover:text-white active:translate-y-px',
  ghost:
    'text-slate-300 hover:text-white active:translate-y-px',
  danger:
    'bg-red-500/20 border border-red-400/30 text-red-200 hover:bg-red-500/30 hover:text-red-100 active:translate-y-px',
}

export function OmniButton({ children, variant = 'primary', className = '', ...rest }: OmniButtonProps) {
  return (
    <button
      className={`rounded-full px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] transition disabled:opacity-60 disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  )
}
