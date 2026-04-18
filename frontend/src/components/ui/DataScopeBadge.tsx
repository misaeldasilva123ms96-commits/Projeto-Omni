export type DataScopeVariant = 'live' | 'internal' | 'operator' | 'protected' | 'future'

const COPY: Record<DataScopeVariant, string> = {
  live: 'Live runtime',
  internal: 'Internal telemetry',
  operator: 'Operator (JWT)',
  protected: 'Protected',
  future: 'Future module',
}

export type DataScopeBadgeProps = {
  variant: DataScopeVariant
  className?: string
}

/** Honest labeling for data provenance (Phase 4 cognitive UI). */
export function DataScopeBadge({ variant, className = '' }: DataScopeBadgeProps) {
  return (
    <span className={`status-pill data-scope-badge data-scope-badge--${variant} ${className}`.trim()}>
      {COPY[variant]}
    </span>
  )
}
