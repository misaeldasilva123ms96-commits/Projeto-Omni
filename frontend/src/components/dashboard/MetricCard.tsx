import type { ReactNode } from 'react'
import { PanelCard } from '../ui/PanelCard'
import { SectionHeader } from '../ui/SectionHeader'

type MetricCardProps = {
  children: ReactNode
  eyebrow: string
  title: string
}

export function MetricCard({ children, eyebrow, title }: MetricCardProps) {
  return (
    <PanelCard className="metric-card omni-metric-card">
      <SectionHeader eyebrow={eyebrow} eyebrowClassName="card-eyebrow" title={title} titleElement="h3" />
      <div className="card-content">{children}</div>
    </PanelCard>
  )
}
