import type { HTMLAttributes, ReactNode } from 'react'

export type PanelCardProps = {
  children: ReactNode
  className?: string
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

/** Primary glass panel used across Omni shell (maps to `.panel-card`). */
export function PanelCard({ children, className = '', ...rest }: PanelCardProps) {
  return (
    <div className={`panel-card ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
