import type { StrategyStateResponse } from '../../types/api/wire'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'

export type StrategyStateSectionProps = {
  strategyState: StrategyStateResponse | null
}

export function StrategyStateSection({ strategyState }: StrategyStateSectionProps) {
  const state = strategyState?.strategy_state ?? {}
  const memoryRules = state.memory_rules as Record<string, unknown> | undefined
  const weights = state.capability_weights as Record<string, unknown> | undefined

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="internal" title="Strategy / reasoning posture" />
      <div className="status-grid">
        <MetricRow label="Version" value={String(state.version ?? '—')} />
        <MetricRow label="History limit" value={String(memoryRules?.history_limit ?? '—')} />
        <MetricRow label="Plan weight" value={String(weights?.create_plan ?? '—')} />
        <MetricRow label="Recent changes" value={String(strategyState?.recent_changes?.length ?? 0)} />
      </div>
    </PanelCard>
  )
}
