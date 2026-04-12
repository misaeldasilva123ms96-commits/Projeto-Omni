import type { TraceSnapshot } from '../../types/observability'

type SpecialistTraceViewerProps = {
  latestTrace: TraceSnapshot | null
  recentTraces: TraceSnapshot[]
}

export function SpecialistTraceViewer({ latestTrace, recentTraces }: SpecialistTraceViewerProps) {
  return (
    <section className="panel-card metric-card observability-card">
      <p className="card-eyebrow">Specialist trace</p>
      <h3>Coordination path</h3>
      {!latestTrace ? <p className="muted-copy">No coordination trace recorded yet.</p> : (
        <>
          <div className="metric-stack">
            <div className="metric-row"><span>Trace</span><strong>{latestTrace.trace_id}</strong></div>
            <div className="metric-row"><span>Outcome</span><strong>{latestTrace.final_outcome}</strong></div>
            <div className="metric-row"><span>Decisions</span><strong>{latestTrace.decisions.length}</strong></div>
            <div className="metric-row"><span>Governance verdicts</span><strong>{latestTrace.governance_verdicts.length}</strong></div>
          </div>
          <div className="timeline-list">
            {latestTrace.decisions.map((decision) => (
              <article className="timeline-item" key={decision.decision_id}>
                <div className="timeline-item-header">
                  <strong>{decision.specialist_type}</strong>
                  <span>{Math.round(decision.confidence * 100)}%</span>
                </div>
                <p>{decision.reasoning || 'No reasoning captured.'}</p>
                <div className="timeline-item-meta">
                  <span>Status: {decision.status}</span>
                  <span>Simulation: {decision.simulation_id || 'n/a'}</span>
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {recentTraces.length > 1 ? (
        <div className="observability-list-block">
          <strong>Recent trace history</strong>
          <ul className="observability-list">
            {recentTraces.slice(0, 5).map((trace) => (
              <li key={trace.trace_id}>
                <span>{trace.trace_id}</span>
                <em>{trace.final_outcome}</em>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
