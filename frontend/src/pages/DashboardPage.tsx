import { useEffect, useState } from 'react'
import { AppShell } from '../components/AppShell'
import {
  fetchHealth,
  fetchMilestones,
  fetchPrSummaries,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../lib/api'
import { canUseApi } from '../lib/env'
import { Sidebar } from '../components/Sidebar'
import { MetricCard } from '../components/MetricCard'
import { SignalList } from '../components/SignalList'
import type {
  ChatMode,
  ConversationSummary,
  HealthResponse,
  MilestonesResponse,
  PrSummariesResponse,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types'

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
      <section className="dashboard-page">
        <section className="panel-card hero-card dashboard-hero">
          <div>
            <p className="eyebrow">Runtime observability</p>
            <h2>Inspect health, strategy, milestones and recent execution activity.</h2>
            <p className="subtitle">
              Read-only telemetry for operators and engineering users. No mutation
              controls are exposed here.
            </p>
          </div>
          <div className="hero-meta">
            <span className="status-pill">{loading ? 'Refreshing' : 'Live snapshot'}</span>
            {error ? <span className="status-pill danger">{error}</span> : null}
          </div>
        </section>

        <div className="dashboard-grid">
          <MetricCard eyebrow="System health" title="Rust, Python and Node status">
            <div className="metric-stack">
              <div className="metric-row">
                <span>Rust service</span>
                <strong>{data.health?.rust_service ?? 'unknown'}</strong>
              </div>
              <div className="metric-row">
                <span>Runtime mode</span>
                <strong>{data.health?.runtime_mode ?? 'unknown'}</strong>
              </div>
              <div className="metric-row">
                <span>Python</span>
                <strong>{data.health?.python.last_status ?? 'not checked'}</strong>
              </div>
              <div className="metric-row">
                <span>Node</span>
                <strong>{data.health?.node.last_status ?? 'unknown'}</strong>
              </div>
            </div>
          </MetricCard>

          <MetricCard eyebrow="Milestones" title="Phase 10 engineering state">
            <div className="metric-stack">
              <div className="metric-row">
                <span>Latest run</span>
                <strong>{data.milestones?.latest_run_id ?? 'none'}</strong>
              </div>
              <div className="metric-row">
                <span>Completed</span>
                <strong>{String(data.milestones?.milestone_state?.completed_milestones ?? 0)}</strong>
              </div>
              <div className="metric-row">
                <span>Blocked</span>
                <strong>{String(data.milestones?.milestone_state?.blocked_milestones ?? 0)}</strong>
              </div>
              <div className="metric-row">
                <span>Patch sets</span>
                <strong>{String(data.milestones?.patch_sets?.length ?? 0)}</strong>
              </div>
            </div>
          </MetricCard>

          <MetricCard eyebrow="Strategy state" title="Current optimization posture">
            <div className="metric-stack">
              <div className="metric-row">
                <span>Version</span>
                <strong>{String(data.strategyState?.strategy_state?.version ?? 0)}</strong>
              </div>
              <div className="metric-row">
                <span>History limit</span>
                <strong>{String((data.strategyState?.strategy_state?.memory_rules as Record<string, unknown> | undefined)?.history_limit ?? 'n/a')}</strong>
              </div>
              <div className="metric-row">
                <span>Plan weight</span>
                <strong>{String((data.strategyState?.strategy_state?.capability_weights as Record<string, unknown> | undefined)?.create_plan ?? 'n/a')}</strong>
              </div>
            </div>
          </MetricCard>

          <MetricCard eyebrow="Runtime summary" title="Latest executed run">
            <div className="metric-stack">
              <div className="metric-row">
                <span>Run id</span>
                <strong>{String(latestSummary.run_id ?? 'none')}</strong>
              </div>
              <div className="metric-row">
                <span>Plan kind</span>
                <strong>{String(latestSummary.plan_kind ?? 'unknown')}</strong>
              </div>
              <div className="metric-row">
                <span>Message</span>
                <strong>{String(latestSummary.message ?? 'n/a')}</strong>
              </div>
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
      </section>
    </AppShell>
  )
}

