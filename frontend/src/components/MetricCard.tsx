import type { ReactNode } from 'react'

type MetricCardProps = {
  children: ReactNode
  eyebrow: string
  title: string
}

export function MetricCard({ children, eyebrow, title }: MetricCardProps) {
  return (
    <section className="panel-card metric-card">
      <p className="card-eyebrow">{eyebrow}</p>
      <h3>{title}</h3>
      <div className="card-content">{children}</div>
    </section>
  )
}
