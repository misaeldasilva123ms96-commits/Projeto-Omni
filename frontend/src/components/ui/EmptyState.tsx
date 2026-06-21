import type { ReactNode } from 'react'
import { OmniEmptyState } from './OmniEmptyState'

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
    <OmniEmptyState className={className} description={description} eyebrow={eyebrow} framed title={title}>
      {children}
    </OmniEmptyState>
  )
}
