import type { ReactNode } from 'react'

export type StatusBadgeTone = 'default' | 'active' | 'danger' | 'muted'

export type StatusBadgeProps = {
  children: ReactNode
  tone?: StatusBadgeTone
  className?: string
}

export function StatusBadge({ children, tone = 'default', className = '' }: StatusBadgeProps) {
  const toneClass =
    tone === 'active'
      ? 'status-pill active'
      : tone === 'danger'
        ? 'status-pill danger'
        : tone === 'muted'
          ? 'status-pill status-pill--muted'
          : 'status-pill'
  return <span className={`${toneClass} ${className}`.trim()}>{children}</span>
}
