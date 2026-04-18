import type { ReactNode } from 'react'

export type EmptyStateProps = {
  eyebrow?: string
  title: string
  description?: string
  children?: ReactNode
  className?: string
}

/** Generic zero-state surface; feature-specific flows compose actions as `children`. */
export function EmptyState({ eyebrow, title, description, children, className = '' }: EmptyStateProps) {
  return (
    <div className={`empty-state omni-empty-state ${className}`.trim()}>
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2>{title}</h2>
      {description ? <p className="muted-copy">{description}</p> : null}
      {children}
    </div>
  )
}
