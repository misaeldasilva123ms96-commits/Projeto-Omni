import type { PublicStatusResponseV1, RuntimeSignalsResponse } from '../../types/api/wire'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type RuntimeStatusSectionProps = {
  health: HealthResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
}

export function RuntimeStatusSection({ health, runtimeSignals }: RuntimeStatusSectionProps) {
  const summary = runtimeSignals?.latest_run_summary ?? {}
  const signalCount = runtimeSignals?.recent_signals?.length ?? 0

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="live" title="Runtime health" />
      <div className="status-grid">
        <MetricRow label="Rust" value={publicRuntime?.rust_service ?? '—'} />
        <MetricRow label="Runtime mode" value={publicRuntime?.runtime_mode ?? '—'} />
        <MetricRow label="Python" value={publicRuntime?.python_status ?? '—'} />
        <MetricRow label="Node" value={publicRuntime?.node_status ?? '—'} />
        <MetricRow
          label="Runtime epoch"
          value={publicRuntime != null ? String(publicRuntime.runtime_session_version) : '—'}
        />
      </div>
      <CognitiveSectionHeader scope="internal" title="Runtime signals (read model)" />
      <div className="status-grid">
        <MetricRow label="Recent signals" value={String(signalCount)} />
        <MetricRow label="Latest run id" value={String(summary.run_id ?? '—')} />
        <MetricRow label="Plan kind" value={String(summary.plan_kind ?? '—')} />
      </div>
    </PanelCard>
  )
}
