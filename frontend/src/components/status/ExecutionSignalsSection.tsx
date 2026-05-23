import type { RichTelemetryDetailSource } from '../../types/api/wire'
import type { RuntimeSignalsResponse, SwarmLogResponse } from '../../types/api/wire'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type ExecutionSignalsSectionProps = {
  runtimeSignals: RuntimeSignalsResponse | null
  runtimeSignalsSource: RichTelemetryDetailSource | null
  swarmLog: SwarmLogResponse | null
}

export function ExecutionSignalsSection({
  runtimeSignals,
  runtimeSignalsSource,
  swarmLog,
}: ExecutionSignalsSectionProps) {
  const signalScope: 'operator' | 'internal' = runtimeSignalsSource === 'operator' ? 'operator' : 'internal'

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope={signalScope} title="Runtime signals (detail)" />
      <div className="status-grid">
        <MetricRow label="Mode transitions" value={String(runtimeSignals?.recent_mode_transitions?.length ?? 0)} />
        <MetricRow label="Signal rows (sample)" value={String(runtimeSignals?.recent_signals?.length ?? 0)} />
      </div>
      <CognitiveSectionHeader scope="internal" title="Swarm activity" />
      <div className="status-grid">
        <MetricRow label="Swarm events" value={String(swarmLog?.events?.length ?? 0)} />
        <MetricRow label="Swarm total (log)" value={String(swarmLog?.total_events ?? '—')} />
      </div>
    </PanelCard>
  )
}
