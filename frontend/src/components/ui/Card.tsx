import type { HTMLAttributes, ReactNode } from 'react'

export type CardProps = {
  children: ReactNode
  className?: string
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

/**
 * Base surface primitive; prefer `PanelCard` for glass panels that match Omni shell.
 */
export function Card({ children, className = '', ...rest }: CardProps) {
  return (
    <div className={`omni-card ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
