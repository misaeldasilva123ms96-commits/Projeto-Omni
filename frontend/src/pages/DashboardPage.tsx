import { useEffect, useState } from 'react'
import { MetricCard } from '../components/dashboard/MetricCard'
import { SignalList } from '../components/dashboard/SignalList'
import { AppShell } from '../components/layout/AppShell'
import { Sidebar } from '../components/layout/Sidebar'
import {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicRuntimeStatusV1,
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
  MilestonesResponse,
  PrSummariesResponse,
  PublicStatusResponseV1,
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
  publicRuntime: PublicStatusResponseV1 | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
  strategyState: StrategyStateResponse | null
  swarmLog: SwarmLogResponse | null
}

const EMPTY_STATE: DashboardState = {
  publicRuntime: null,
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
      fetchPublicRuntimeStatusV1(),
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(([publicRuntime, runtimeSignals, swarmLog, strategyState, milestones, prSummaries]) => {
        if (cancelled) {
          return
        }
        setData({
          publicRuntime,
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
            System health row uses <code>/api/v1/status</code>; detailed cards use <code>/internal/*</code> only — no
            speculative endpoints.
          </span>
        </div>

        <div className="dashboard-grid">
          <MetricCard eyebrow="System health" title="Public runtime snapshot (/api/v1/status)">
            <div className="metric-stack">
              <MetricRow label="Rust service" value={data.publicRuntime?.rust_service ?? 'unknown'} />
              <MetricRow label="Runtime mode" value={data.publicRuntime?.runtime_mode ?? 'unknown'} />
              <MetricRow label="Python" value={data.publicRuntime?.python_status ?? 'not checked'} />
              <MetricRow label="Node" value={data.publicRuntime?.node_status ?? 'unknown'} />
              <MetricRow
                label="Runtime epoch"
                value={data.publicRuntime != null ? String(data.publicRuntime.runtime_session_version) : 'unknown'}
              />
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
            description="v1 status is adopted; further public read models (goals, evolution) remain future work."
            title="Extended public read APIs"
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

