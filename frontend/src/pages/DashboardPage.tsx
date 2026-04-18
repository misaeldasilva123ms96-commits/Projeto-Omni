import { useEffect, useState } from 'react'
import { MetricCard } from '../components/dashboard/MetricCard'
import { SignalList } from '../components/dashboard/SignalList'
import { AppShell } from '../components/layout/AppShell'
import { Sidebar } from '../components/layout/Sidebar'
import {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicMilestonesSummaryV1,
  fetchPublicRuntimeSignalsSummaryV1,
  fetchPublicRuntimeStatusV1,
  fetchPublicStrategySummaryV1,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
  publicMilestonesSummaryV1ToUi,
  publicRuntimeSignalsSummaryV1ToUi,
  publicStrategySummaryV1ToUi,
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
import type { UiMilestonesSummary, UiRuntimeSignalsSummary, UiStrategySummary } from '../types/ui/telemetry'

type View = 'chat' | 'dashboard' | 'observability'

type DashboardPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

type DashboardState = {
  publicRuntime: PublicStatusResponseV1 | null
  publicSignalsSummary: UiRuntimeSignalsSummary | null
  publicMilestonesSummary: UiMilestonesSummary | null
  publicStrategySummary: UiStrategySummary | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
  strategyState: StrategyStateResponse | null
  swarmLog: SwarmLogResponse | null
}

const EMPTY_STATE: DashboardState = {
  publicRuntime: null,
  publicSignalsSummary: null,
  publicMilestonesSummary: null,
  publicStrategySummary: null,
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
      fetchPublicRuntimeSignalsSummaryV1(),
      fetchPublicMilestonesSummaryV1(),
      fetchPublicStrategySummaryV1(),
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(
        ([
          publicRuntime,
          publicSignalsWire,
          publicMilestonesWire,
          publicStrategyWire,
          runtimeSignals,
          swarmLog,
          strategyState,
          milestones,
          prSummaries,
        ]) => {
          if (cancelled) {
            return
          }
          setData({
            publicRuntime,
            publicSignalsSummary: publicRuntimeSignalsSummaryV1ToUi(publicSignalsWire),
            publicMilestonesSummary: publicMilestonesSummaryV1ToUi(publicMilestonesWire),
            publicStrategySummary: publicStrategySummaryV1ToUi(publicStrategyWire),
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
            Summary cards use <code>/api/v1/status</code> and <code>/api/v1/*/summary</code>; lists and deep rows still use{' '}
            <code>/internal/*</code> where richer payloads are required.
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

          <MetricCard eyebrow="Milestones" title="Public summary (/api/v1/milestones/summary)">
            <div className="metric-stack">
              <MetricRow label="Latest run" value={data.publicMilestonesSummary?.latestRunId || 'none'} />
              <MetricRow label="Completed" value={String(data.publicMilestonesSummary?.completedMilestoneCount ?? 0)} />
              <MetricRow label="Blocked" value={String(data.publicMilestonesSummary?.blockedMilestoneCount ?? 0)} />
              <MetricRow label="Patch sets" value={String(data.publicMilestonesSummary?.patchSetCount ?? 0)} />
              <MetricRow label="Checkpoint" value={data.publicMilestonesSummary?.checkpointStatus ?? 'unknown'} />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Strategy state" title="Public summary + one internal field">
            <div className="metric-stack">
              <MetricRow label="Version" value={String(data.publicStrategySummary?.strategyVersion ?? 0)} />
              <MetricRow
                label="History limit (internal)"
                value={String((data.strategyState?.strategy_state?.memory_rules as Record<string, unknown> | undefined)?.history_limit ?? 'n/a')}
              />
              <MetricRow
                label="Plan weight"
                value={data.publicStrategySummary?.createPlanWeight != null
                  ? String(data.publicStrategySummary.createPlanWeight)
                  : String((data.strategyState?.strategy_state?.capability_weights as Record<string, unknown> | undefined)?.create_plan ?? 'n/a')}
              />
              <MetricRow label="Change log entries" value={String(data.publicStrategySummary?.recentChangeLogCount ?? 0)} />
            </div>
          </MetricCard>

          <MetricCard eyebrow="Runtime summary" title="Public summary (/api/v1/runtime/signals/summary)">
            <div className="metric-stack">
              <MetricRow label="Run id" value={data.publicSignalsSummary?.latestRunId || 'none'} />
              <MetricRow label="Plan kind" value={data.publicSignalsSummary?.latestPlanKind || 'unknown'} />
              <MetricRow label="Message preview" value={data.publicSignalsSummary?.latestRunMessagePreview || 'n/a'} />
              <MetricRow label="Signals (sample)" value={String(data.publicSignalsSummary?.recentSignalCount ?? 0)} />
              <MetricRow label="Mode transitions" value={String(data.publicSignalsSummary?.recentModeTransitionCount ?? 0)} />
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

