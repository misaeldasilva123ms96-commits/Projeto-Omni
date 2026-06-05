import type { HTMLAttributes, ReactNode } from 'react'

type OmniCardVariant = 'default' | 'panel' | 'elevated'

type OmniCardProps = {
  children: ReactNode
  variant?: OmniCardVariant
  className?: string
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

const variantClasses: Record<OmniCardVariant, string> = {
  default: 'omni-card',
  panel: 'panel-card',
  elevated: 'panel-card shadow-[0_28px_64px_rgba(0,0,0,0.36)]',
}

export function OmniCard({ children, variant = 'default', className = '', ...rest }: OmniCardProps) {
  return (
    <div className={`${variantClasses[variant]} ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
