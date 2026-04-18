import { DataScopeBadge } from '../ui/DataScopeBadge'
import { PanelCard } from '../ui/PanelCard'

export type FutureModuleCardProps = {
  title: string
  description: string
}

/** Clearly labeled placeholder — no live data until a public contract exists. */
export function FutureModuleCard({ title, description }: FutureModuleCardProps) {
  return (
    <PanelCard className="cognitive-future-card">
      <div className="cognitive-future-card__head">
        <p className="card-eyebrow">Extension point</p>
        <DataScopeBadge variant="future" />
      </div>
      <h3 className="cognitive-future-title">{title}</h3>
      <p className="muted-copy">{description}</p>
    </PanelCard>
  )
}
