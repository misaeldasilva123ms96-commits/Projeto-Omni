import { useMemo } from 'react'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { DataScopeBadge } from '../components/ui/DataScopeBadge'
import { PageHero } from '../components/ui/PageHero'
import { PanelCard } from '../components/ui/PanelCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { GoalStatePanel } from '../components/observability/GoalStatePanel'
import { LearningSignalsPanel } from '../components/observability/LearningSignalsPanel'
import { OperationalTimeline } from '../components/observability/OperationalTimeline'
import { SimulationMemoryPanel } from '../components/observability/SimulationMemoryPanel'
import { SpecialistTraceViewer } from '../components/observability/SpecialistTraceViewer'
import { ObservabilityContextBanner } from '../components/observability/ObservabilityContextBanner'
import { useObservabilitySnapshot } from '../hooks/useObservabilitySnapshot'
import { useObservabilityStream } from '../hooks/useObservabilityStream'
import { canUseApi } from '../lib/env'
import type { RenderOmniShell, View } from '../app/App'
import type { ChatMode, ConversationSummary } from '../types'
import {
  filterObservabilitySnapshotByContext,
  hasObservabilityContext,
  parseObservabilityContext,
  pickObservabilityContext,
} from '../lib/observabilityContext'

type ObservabilityPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function ObservabilityPage({
  mode,
  onChangeMode,
  onChangeView,
  renderShell,
  view,
}: ObservabilityPageProps) {
  const apiReady = canUseApi()
  const { snapshot: initialSnapshot, loading, error: snapshotError } = useObservabilitySnapshot(apiReady)
  const { snapshot: liveSnapshot, status, error: streamError } = useObservabilityStream(apiReady)
  const snapshot = liveSnapshot ?? initialSnapshot
  const context = pickObservabilityContext(
    parseObservabilityContext(window.location.search),
    ['request_id', 'trace_id', 'runtime_mode', 'tool'],
  )
  const hasContext = hasObservabilityContext(context)
  const contextual = filterObservabilitySnapshotByContext(snapshot, context)
  const visibleSnapshot = hasContext ? contextual.snapshot : snapshot
  const semanticReinforcements = useMemo(
    () => (visibleSnapshot?.semantic_facts ?? []).slice(0, 5),
    [visibleSnapshot],
  )
  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )
  const connectionLabel = status === 'live' ? 'Live' : status === 'reconnecting' ? 'Reconnecting' : status === 'error' ? 'Error' : 'Idle'

  return renderShell(
      <section className="dashboard-page omni-observability">
        <PageHero
          eyebrow="Cognitive observability"
          meta={(
            <>
              <StatusBadge tone={status === 'live' ? 'active' : 'default'}>
                {loading ? 'Loading' : connectionLabel}
              </StatusBadge>
              {snapshotError || streamError ? (
                <StatusBadge tone="danger">{streamError || snapshotError}</StatusBadge>
              ) : null}
            </>
          )}
          subtitle="This panel only exposes persisted runtime artifacts. It does not mutate the cognitive runtime."
          title="Inspect goals, memory, simulation and specialist coordination in one read-only surface."
        />

        <div className="cognitive-trust-strip" role="note">
          <DataScopeBadge variant="protected" />
          <span className="muted-copy">
            Snapshot, traces, and SSE require Supabase JWT per Rust middleware — same data model as the Python
            observability CLI.
          </span>
        </div>

        <ObservabilityContextBanner context={context} />

        {!apiReady ? (
          <PanelCard className="metric-card observability-card">
            <p className="card-eyebrow">Configuration</p>
            <h3>Observability API unavailable</h3>
            <p className="muted-copy">Configure VITE_OMNI_API_URL so the panel can consume the Rust observability endpoints.</p>
          </PanelCard>
        ) : hasContext && !contextual.matched ? (
          <PanelCard className="metric-card observability-card">
            <p className="card-eyebrow">Filtro contextual</p>
            <h3>
              {snapshot
                ? 'Nenhum registro correspondente encontrado.'
                : 'Contexto recebido, mas não há dados disponíveis para este filtro.'}
            </h3>
          </PanelCard>
        ) : (
          <div className="dashboard-grid observability-grid">
            <GoalStatePanel goal={visibleSnapshot?.goal ?? null} />
            <OperationalTimeline events={visibleSnapshot?.timeline ?? []} />
            <SpecialistTraceViewer
              latestTrace={visibleSnapshot?.latest_trace ?? null}
              recentTraces={visibleSnapshot?.recent_traces ?? []}
            />
            <SimulationMemoryPanel
              episodes={visibleSnapshot?.recent_episodes ?? []}
              proceduralPattern={visibleSnapshot?.active_procedural_pattern ?? null}
              semanticFacts={visibleSnapshot?.semantic_facts ?? []}
              simulation={visibleSnapshot?.latest_simulation ?? null}
            />
            <LearningSignalsPanel
              pendingEvolutionProposalCount={visibleSnapshot?.pending_evolution_proposal_count ?? 0}
              recentEvolutionProposals={visibleSnapshot?.recent_evolution_proposals ?? []}
              recentLearningSignals={visibleSnapshot?.recent_learning_signals ?? []}
              recentProceduralUpdates={visibleSnapshot?.recent_procedural_updates ?? []}
              recentSemanticFacts={semanticReinforcements}
            />
          </div>
        )}
      </section>,
    { sidebar },
  )
}
