import type { UiObservabilitySnapshot } from '../../types/ui/observability'
import { CognitiveSectionHeader } from './CognitiveSectionHeader'
import { ErrorNotice } from '../ui/ErrorNotice'
import { LoadingState } from '../ui/LoadingState'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'

export type ObservabilitySummarySectionProps = {
  canRequest: boolean
  error: string | null
  loading: boolean
  snapshot: UiObservabilitySnapshot | null
}

/**
 * Read-only slice of the protected observability snapshot (same contract as Observability page).
 */
export function ObservabilitySummarySection({
  canRequest,
  error,
  loading,
  snapshot,
}: ObservabilitySummarySectionProps) {
  if (!canRequest) {
    return (
      <PanelCard className="cognitive-section-card">
        <CognitiveSectionHeader scope="protected" title="Observability snapshot" />
        <p className="muted-copy">
          Sign in with Supabase and open the Observability view for the full protected panel. No snapshot is
          fetched here without an access token.
        </p>
      </PanelCard>
    )
  }

  if (loading && !snapshot) {
    return (
      <PanelCard className="cognitive-section-card">
        <CognitiveSectionHeader scope="protected" title="Observability snapshot" />
        <LoadingState label="Carregando snapshot…" />
      </PanelCard>
    )
  }

  if (error) {
    return (
      <PanelCard className="cognitive-section-card">
        <CognitiveSectionHeader scope="protected" title="Observability snapshot" />
        <ErrorNotice message={error} />
      </PanelCard>
    )
  }

  return (
    <PanelCard className="cognitive-section-card">
      <CognitiveSectionHeader scope="protected" title="Observability snapshot" />
      <div className="status-grid">
        <MetricRow label="Generated at" value={snapshot?.generated_at ?? '—'} />
        <MetricRow label="Goal status" value={snapshot?.goal?.status ?? '—'} />
        <MetricRow label="Timeline events" value={String(snapshot?.timeline?.length ?? 0)} />
        <MetricRow label="Recent traces" value={String(snapshot?.recent_traces?.length ?? 0)} />
        <MetricRow label="Pending evolution" value={String(snapshot?.pending_evolution_proposal_count ?? 0)} />
      </div>
    </PanelCard>
  )
}
