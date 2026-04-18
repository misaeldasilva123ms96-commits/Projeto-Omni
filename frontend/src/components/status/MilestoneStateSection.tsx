import type { MilestonesResponse, PrSummariesResponse } from '../../types/api/wire'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type MilestoneStateSectionProps = {
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
}

export function MilestoneStateSection({ milestones, prSummaries }: MilestoneStateSectionProps) {
  const ms = milestones?.milestone_state

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="internal" title="Milestones & engineering state" />
      <div className="status-grid">
        <MetricRow label="Latest run" value={milestones?.latest_run_id ?? '—'} />
        <MetricRow label="Completed" value={String(ms?.completed_milestones ?? '—')} />
        <MetricRow label="Blocked" value={String(ms?.blocked_milestones ?? '—')} />
        <MetricRow label="Patch sets" value={String(milestones?.patch_sets?.length ?? 0)} />
      </div>
      <CognitiveSectionHeader scope="internal" title="PR-style summaries" />
      <div className="status-grid">
        <MetricRow label="Summaries" value={String(prSummaries?.summaries?.length ?? 0)} />
      </div>
    </PanelCard>
  )
}
