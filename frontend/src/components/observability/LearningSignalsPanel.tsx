import type {
  ProceduralPatternSnapshot,
  SemanticFactSnapshot,
} from '../../types/observability'

type LearningSignalsPanelProps = {
  pendingEvolutionProposalCount: number
  recentEvolutionProposals: Array<Record<string, unknown>>
  recentLearningSignals: Array<Record<string, unknown>>
  recentProceduralUpdates: ProceduralPatternSnapshot[]
  recentSemanticFacts: SemanticFactSnapshot[]
}

export function LearningSignalsPanel({
  pendingEvolutionProposalCount,
  recentEvolutionProposals,
  recentLearningSignals,
  recentProceduralUpdates,
  recentSemanticFacts,
}: LearningSignalsPanelProps) {
  return (
    <section className="panel-card metric-card observability-card">
      <p className="card-eyebrow">Learning and evolution</p>
      <h3>Signals ready for operator review</h3>
      <div className="metric-stack">
        <div className="metric-row"><span>Pending evolution proposals</span><strong>{pendingEvolutionProposalCount}</strong></div>
        <div className="metric-row"><span>Learning signals</span><strong>{recentLearningSignals.length}</strong></div>
        <div className="metric-row"><span>Procedural updates</span><strong>{recentProceduralUpdates.length}</strong></div>
      </div>

      <div className="observability-list-block">
        <strong>Recent learning signals</strong>
        {recentLearningSignals.length === 0 ? <p className="muted-copy">No recent learning signals.</p> : (
          <ul className="observability-list">
            {recentLearningSignals.slice(0, 5).map((signal, index) => (
              <li key={`${String(signal.signal_id ?? index)}`}>
                <span>{String(signal.signal_type ?? 'signal')}</span>
                <em>{String(signal.recommendation ?? 'no recommendation')}</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Recent semantic reinforcements</strong>
        {recentSemanticFacts.length === 0 ? <p className="muted-copy">No recent semantic reinforcements.</p> : (
          <ul className="observability-list">
            {recentSemanticFacts.slice(0, 5).map((fact) => (
              <li key={fact.fact_id}>
                <span>{fact.subject} {fact.predicate}</span>
                <em>{Math.round(fact.confidence * 100)}%</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Recent procedural updates</strong>
        {recentProceduralUpdates.length === 0 ? <p className="muted-copy">No procedural updates recorded.</p> : (
          <ul className="observability-list">
            {recentProceduralUpdates.map((pattern) => (
              <li key={pattern.pattern_id}>
                <span>{pattern.name}</span>
                <em>{pattern.recommended_route}</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Recent evolution proposals</strong>
        {recentEvolutionProposals.length === 0 ? <p className="muted-copy">No recent evolution proposals.</p> : (
          <ul className="observability-list">
            {recentEvolutionProposals.slice(0, 5).map((proposal, index) => (
              <li key={`${String(proposal.proposal_id ?? index)}`}>
                <span>{String(proposal.title ?? proposal.target_subsystem ?? 'proposal')}</span>
                <em>{String(proposal.risk_level ?? 'unknown')}</em>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
