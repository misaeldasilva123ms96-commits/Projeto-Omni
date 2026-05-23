import type { DataScopeVariant } from '../ui/DataScopeBadge'
import { DataScopeBadge } from '../ui/DataScopeBadge'

type CognitiveSectionHeaderProps = {
  title: string
  scope: DataScopeVariant
}

export function CognitiveSectionHeader({ title, scope }: CognitiveSectionHeaderProps) {
  return (
    <div className="cognitive-section-header">
      <p className="sidebar-label">{title}</p>
      <DataScopeBadge variant={scope} />
    </div>
  )
}
