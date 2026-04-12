import { useMemo } from 'react'
import { AppShell } from '../components/AppShell'
import { Sidebar } from '../components/Sidebar'
import { GoalStatePanel } from '../components/observability/GoalStatePanel'
import { LearningSignalsPanel } from '../components/observability/LearningSignalsPanel'
import { OperationalTimeline } from '../components/observability/OperationalTimeline'
import { SimulationMemoryPanel } from '../components/observability/SimulationMemoryPanel'
import { SpecialistTraceViewer } from '../components/observability/SpecialistTraceViewer'
import { useObservabilitySnapshot } from '../hooks/useObservabilitySnapshot'
import { useObservabilityStream } from '../hooks/useObservabilityStream'
import { canUseApi } from '../lib/env'
import type { ChatMode, ConversationSummary } from '../types'

type View = 'chat' | 'dashboard' | 'observability'

type ObservabilityPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

export function ObservabilityPage({
  mode,
  onChangeMode,
  onChangeView,
  view,
}: ObservabilityPageProps) {
  const apiReady = canUseApi()
  const { snapshot: initialSnapshot, loading, error: snapshotError } = useObservabilitySnapshot(apiReady)
  const { snapshot: liveSnapshot, status, error: streamError } = useObservabilityStream(apiReady)
  const snapshot = liveSnapshot ?? initialSnapshot
  const semanticReinforcements = useMemo(
    () => (snapshot?.semantic_facts ?? []).slice(0, 5),
    [snapshot],
  )
  const conversations: ConversationSummary[] = []
  const connectionLabel = status === 'live' ? 'Live' : status === 'reconnecting' ? 'Reconnecting' : status === 'error' ? 'Error' : 'Idle'

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
            <p className="eyebrow">Cognitive observability</p>
            <h2>Inspect goals, memory, simulation and specialist coordination in one read-only surface.</h2>
            <p className="subtitle">This panel only exposes persisted runtime artifacts. It does not mutate the cognitive runtime.</p>
          </div>
          <div className="hero-meta">
            <span className={status === 'live' ? 'status-pill active' : 'status-pill'}>{loading ? 'Loading' : connectionLabel}</span>
            {snapshotError || streamError ? <span className="status-pill danger">{streamError || snapshotError}</span> : null}
          </div>
        </section>

        {!apiReady ? (
          <section className="panel-card metric-card observability-card">
            <p className="card-eyebrow">Configuration</p>
            <h3>Observability API unavailable</h3>
            <p className="muted-copy">Configure VITE_OMNI_API_URL so the panel can consume the Rust observability endpoints.</p>
          </section>
        ) : (
          <div className="dashboard-grid observability-grid">
            <GoalStatePanel goal={snapshot?.goal ?? null} />
            <OperationalTimeline events={snapshot?.timeline ?? []} />
            <SpecialistTraceViewer
              latestTrace={snapshot?.latest_trace ?? null}
              recentTraces={snapshot?.recent_traces ?? []}
            />
            <SimulationMemoryPanel
              episodes={snapshot?.recent_episodes ?? []}
              proceduralPattern={snapshot?.active_procedural_pattern ?? null}
              semanticFacts={snapshot?.semantic_facts ?? []}
              simulation={snapshot?.latest_simulation ?? null}
            />
            <LearningSignalsPanel
              pendingEvolutionProposalCount={snapshot?.pending_evolution_proposal_count ?? 0}
              recentEvolutionProposals={snapshot?.recent_evolution_proposals ?? []}
              recentLearningSignals={snapshot?.recent_learning_signals ?? []}
              recentProceduralUpdates={snapshot?.recent_procedural_updates ?? []}
              recentSemanticFacts={semanticReinforcements}
            />
          </div>
        )}
      </section>
    </AppShell>
  )
}
