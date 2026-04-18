import type { RuntimeSignalsResponse, SwarmLogResponse } from '../../types/api/wire'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type ExecutionSignalsSectionProps = {
  runtimeSignals: RuntimeSignalsResponse | null
  swarmLog: SwarmLogResponse | null
}

export function ExecutionSignalsSection({ runtimeSignals, swarmLog }: ExecutionSignalsSectionProps) {
  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="internal" title="Execution & swarm activity" />
      <div className="status-grid">
        <MetricRow label="Mode transitions" value={String(runtimeSignals?.recent_mode_transitions?.length ?? 0)} />
        <MetricRow label="Swarm events" value={String(swarmLog?.events?.length ?? 0)} />
        <MetricRow label="Swarm total (log)" value={String(swarmLog?.total_events ?? '—')} />
      </div>
    </PanelCard>
  )
}
