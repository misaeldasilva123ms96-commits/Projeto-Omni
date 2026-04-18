import type { ReactNode } from 'react'

export type MetricRowProps = {
  label: string
  value: ReactNode
  className?: string
}

export function MetricRow({ label, value, className = '' }: MetricRowProps) {
  return (
    <div className={`metric-row ${className}`.trim()}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
