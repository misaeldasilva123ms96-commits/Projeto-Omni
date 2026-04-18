import type { PublicStatusResponseV1, RuntimeSignalsResponse } from '../../types/api/wire'
import type { UiRuntimeSignalsSummary } from '../../types/ui/telemetry'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type RuntimeStatusSectionProps = {
  publicRuntime: PublicStatusResponseV1 | null
  /** Public summary (`GET /api/v1/runtime/signals/summary`). */
  signalsSummary: UiRuntimeSignalsSummary | null
  runtimeSignals: RuntimeSignalsResponse | null
}

export function RuntimeStatusSection({ publicRuntime, signalsSummary, runtimeSignals }: RuntimeStatusSectionProps) {
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
      <CognitiveSectionHeader scope="live" title="Signals summary (/api/v1/runtime/signals/summary)" />
      <div className="status-grid">
        <MetricRow label="Signals (sample)" value={String(signalsSummary?.recentSignalCount ?? '—')} />
        <MetricRow label="Mode transitions" value={String(signalsSummary?.recentModeTransitionCount ?? '—')} />
        <MetricRow label="Latest run id" value={signalsSummary?.latestRunId || '—'} />
        <MetricRow label="Plan kind" value={signalsSummary?.latestPlanKind || '—'} />
        <MetricRow label="Message preview" value={signalsSummary?.latestRunMessagePreview || '—'} />
      </div>
      <CognitiveSectionHeader scope="internal" title="Signals detail (internal sample)" />
      <div className="status-grid">
        <MetricRow label="Internal sample rows" value={String(signalCount)} />
      </div>
    </PanelCard>
  )
}
