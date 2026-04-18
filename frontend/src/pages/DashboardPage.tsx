import { useEffect, useState } from 'react'
import { MetricCard } from '../components/dashboard/MetricCard'
import { SignalList } from '../components/dashboard/SignalList'
import { AppShell } from '../components/layout/AppShell'
import { Sidebar } from '../components/layout/Sidebar'
import {
  fetchHealth,
  fetchMilestones,
  fetchPrSummaries,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../features/runtime'
import { canUseApi } from '../lib/env'
import { FutureModuleCard } from '../components/status/FutureModuleCard'
import { DataScopeBadge } from '../components/ui/DataScopeBadge'
import { MetricRow } from '../components/ui/MetricRow'
import { PageHero } from '../components/ui/PageHero'
import { StatusBadge } from '../components/ui/StatusBadge'
import type { ChatMode, ConversationSummary } from '../types'
import type {
  HealthResponse,
  MilestonesResponse,
  PrSummariesResponse,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types/api/wire'

type View = 'chat' | 'dashboard' | 'observability'

type DashboardPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

type DashboardState = {
  health: HealthResponse | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
  strategyState: StrategyStateResponse | null
  swarmLog: SwarmLogResponse | null
}

const EMPTY_STATE: DashboardState = {
  health: null,
  milestones: null,
  prSummaries: null,
  runtimeSignals: null,
  strategyState: null,
  swarmLog: null,
}

export function DashboardPage({
  mode,
  onChangeMode,
  onChangeView,
  view,
}: DashboardPageProps) {
  const [data, setData] = useState<DashboardState>(EMPTY_STATE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const apiReady = canUseApi()
  const conversations: ConversationSummary[] = []

  useEffect(() => {
    if (!apiReady) {
      setError('Configure VITE_OMNI_API_URL to load dashboard telemetry.')
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      fetchHealth(),
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(([health, runtimeSignals, swarmLog, strategyState, milestones, prSummaries]) => {
        if (cancelled) {
          return
        }
        setData({
          health,
          milestones,
          prSummaries,
          runtimeSignals,
          strategyState,
          swarmLog,
        })
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard data.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [apiReady])

  const milestoneItems = data.milestones?.milestone_state?.milestones ?? []
  const recentSignals = data.runtimeSignals?.recent_signals ?? []
  const recentTransitions = data.runtimeSignals?.recent_mode_transitions ?? []
  const recentChanges = data.strategyState?.recent_changes ?? []
  const recentSwarmEvents = data.swarmLog?.events ?? []
  const recentPrSummaries = data.prSummaries?.summaries ?? []
  const latestSummary = data.runtimeSignals?.latest_run_summary ?? {}

  return (
    <AppShell
      sidebar={(
        <Sidebar
          conversations={conversations}
          mode={mode}
          onChangeMode={onChangeMode}
          onSelectView={onChangeView}
          view={view}
        />
      )}
    >
      <section className="dashboard-page omni-dashboard">
        <PageHero
          eyebrow="Runtime observability"
          meta={(
            <>
              <StatusBadge tone={loading ? 'active' : 'default'}>
                {loading ? 'Refreshing' : 'Live snapshot'}
              </StatusBadge>
              {error ? <StatusBadge tone="danger">{error}</StatusBadge> : null}
            </>
          )}
          subtitle="Read-only telemetry for operators and engineering users. No mutation controls are exposed here."
          title="Inspect health, strategy, milestones and recent execution activity."
        />

        <div className="cognitive-trust-strip" role="note">
          <DataScopeBadge variant="live" />
          <DataScopeBadge variant="internal" />
          <span className="muted-copy">
            Cards below map to <code>/health</code> and <code>/internal/*</code> only — no speculative public API.
          </span>
        </div>

        <div className="dashboard-grid">
          <MetricCard eyebrow="System health" title="Rust, Python and Node status">
            <div className="metric-stack">
              <MetricRow label="Rust service" value={data.health?.rust_service ?? 'unknown'} />
              <MetricRow label="Runtime mode" value={data.health?.runtime_mode ?? 'unknown'} />
              <MetricRow label="Python" value={data.health?.python.last_status ?? 'not checked'} />
              <MetricRow label="Node" value={data.health?.node.last_status ?? 'unknown'} />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Milestones" title="Phase 10 engineering state">
            <div className="metric-stack">
              <MetricRow label="Latest run" value={data.milestones?.latest_run_id ?? 'none'} />
              <MetricRow label="Completed" value={String(data.milestones?.milestone_state?.completed_milestones ?? 0)} />
              <MetricRow label="Blocked" value={String(data.milestones?.milestone_state?.blocked_milestones ?? 0)} />
              <MetricRow label="Patch sets" value={String(data.milestones?.patch_sets?.length ?? 0)} />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Strategy state" title="Current optimization posture">
            <div className="metric-stack">
              <MetricRow label="Version" value={String(data.strategyState?.strategy_state?.version ?? 0)} />
              <MetricRow
                label="History limit"
                value={String((data.strategyState?.strategy_state?.memory_rules as Record<string, unknown> | undefined)?.history_limit ?? 'n/a')}
              />
              <MetricRow
                label="Plan weight"
                value={String((data.strategyState?.strategy_state?.capability_weights as Record<string, unknown> | undefined)?.create_plan ?? 'n/a')}
              />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Runtime summary" title="Latest executed run">
            <div className="metric-stack">
              <MetricRow label="Run id" value={String(latestSummary.run_id ?? 'none')} />
              <MetricRow label="Plan kind" value={String(latestSummary.plan_kind ?? 'unknown')} />
              <MetricRow label="Message" value={String(latestSummary.message ?? 'n/a')} />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Signals" title="Recent internal runtime events">
            <SignalList emptyLabel="No runtime events recorded yet." items={recentSignals} />
          </MetricCard>

          <MetricCard eyebrow="Mode transitions" title="Fallback and degraded visibility">
            <SignalList emptyLabel="No runtime mode transitions recorded." items={recentTransitions} />
          </MetricCard>

          <MetricCard eyebrow="Swarm log" title="Recent cooperative agent activity">
            <SignalList emptyLabel="No swarm events available." items={recentSwarmEvents} />
          </MetricCard>

          <MetricCard eyebrow="PR summaries" title="Reviewer-facing outputs">
            <SignalList emptyLabel="No PR-style summaries available." items={recentPrSummaries} />
          </MetricCard>

          <MetricCard eyebrow="Strategy changes" title="Recent learning updates">
            <SignalList emptyLabel="No strategy changes recorded." items={recentChanges} />
          </MetricCard>

          <MetricCard eyebrow="Milestone details" title="Active milestone list">
            <SignalList emptyLabel="No milestone records available." items={milestoneItems} />
          </MetricCard>
        </div>

        <section className="cognitive-future-grid omni-dashboard-future" aria-label="Future public API modules">
          <FutureModuleCard
            description="Will consume a versioned public status contract instead of raw internal JSON."
            title="Public runtime status (/api/v1/...)"
          />
          <FutureModuleCard
            description="Goal graph read model is not exposed on current HTTP routes."
            title="Goals read API"
          />
          <FutureModuleCard
            description="Evolution and learning metrics await stable, typed endpoints."
            title="Evolution metrics"
          />
          <FutureModuleCard
            description="OIL envelopes remain Python-internal until an explicit HTTP mapping ships."
            title="OIL / memory contract"
          />
        </section>
      </section>
    </AppShell>
  )
}

