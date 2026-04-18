import type { StrategyStateResponse } from '../../types/api/wire'
import type { UiStrategySummary } from '../../types/ui/telemetry'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type StrategyStateSectionProps = {
  publicStrategySummary: UiStrategySummary | null
  strategyState: StrategyStateResponse | null
}

export function StrategyStateSection({ publicStrategySummary, strategyState }: StrategyStateSectionProps) {
  const state = strategyState?.strategy_state ?? {}
  const memoryRules = state.memory_rules as Record<string, unknown> | undefined
  const weights = state.capability_weights as Record<string, unknown> | undefined

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="live" title="Strategy (public summary)" />
      <div className="status-grid">
        <MetricRow label="Version" value={String(publicStrategySummary?.strategyVersion ?? '—')} />
        <MetricRow
          label="Plan weight"
          value={publicStrategySummary?.createPlanWeight != null
            ? String(publicStrategySummary.createPlanWeight)
            : String(weights?.create_plan ?? '—')}
        />
        <MetricRow label="Change log entries" value={String(publicStrategySummary?.recentChangeLogCount ?? '—')} />
      </div>
      <CognitiveSectionHeader scope="internal" title="Strategy rules (internal)" />
      <div className="status-grid">
        <MetricRow label="History limit" value={String(memoryRules?.history_limit ?? '—')} />
        <MetricRow label="Recent changes (sample)" value={String(strategyState?.recent_changes?.length ?? 0)} />
      </div>
    </PanelCard>
  )
}
