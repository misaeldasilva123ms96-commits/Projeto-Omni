import type { MilestonesResponse, PrSummariesResponse } from '../../types/api/wire'
import type { UiMilestonesSummary } from '../../types/ui/telemetry'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type MilestoneStateSectionProps = {
  publicMilestonesSummary: UiMilestonesSummary | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
}

export function MilestoneStateSection({ publicMilestonesSummary, milestones, prSummaries }: MilestoneStateSectionProps) {
  const ms = milestones?.milestone_state

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="live" title="Milestones (public summary)" />
      <div className="status-grid">
        <MetricRow label="Latest run" value={publicMilestonesSummary?.latestRunId || '—'} />
        <MetricRow label="Completed" value={String(publicMilestonesSummary?.completedMilestoneCount ?? '—')} />
        <MetricRow label="Blocked" value={String(publicMilestonesSummary?.blockedMilestoneCount ?? '—')} />
        <MetricRow label="Patch sets" value={String(publicMilestonesSummary?.patchSetCount ?? 0)} />
        <MetricRow label="Checkpoint" value={publicMilestonesSummary?.checkpointStatus ?? '—'} />
      </div>
      <CognitiveSectionHeader scope="internal" title="Milestone detail (internal)" />
      <div className="status-grid">
        <MetricRow
          label="Milestone records"
          value={String(Array.isArray(ms?.milestones) ? (ms.milestones as unknown[]).length : 0)}
        />
      </div>
      <CognitiveSectionHeader scope="internal" title="PR-style summaries" />
      <div className="status-grid">
        <MetricRow label="Summaries" value={String(prSummaries?.summaries?.length ?? 0)} />
      </div>
    </PanelCard>
  )
}
