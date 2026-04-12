import type {
  EpisodeSnapshot,
  ProceduralPatternSnapshot,
  SemanticFactSnapshot,
  SimulationSnapshot,
} from '../../types/observability'

type SimulationMemoryPanelProps = {
  episodes: EpisodeSnapshot[]
  proceduralPattern: ProceduralPatternSnapshot | null
  semanticFacts: SemanticFactSnapshot[]
  simulation: SimulationSnapshot | null
}

export function SimulationMemoryPanel({
  episodes,
  proceduralPattern,
  semanticFacts,
  simulation,
}: SimulationMemoryPanelProps) {
  return (
    <section className="panel-card metric-card observability-card">
      <p className="card-eyebrow">Simulation and memory</p>
      <h3>Forecasts, episodes and reusable patterns</h3>

      <div className="observability-list-block">
        <strong>Latest simulation</strong>
        {!simulation ? <p className="muted-copy">No simulation artifact available.</p> : (
          <>
            <div className="metric-row"><span>Recommended route</span><strong>{simulation.recommended_route}</strong></div>
            <ul className="observability-list">
              {simulation.routes.map((route) => (
                <li key={route.route}>
                  <span>{route.route}</span>
                  <em>{Math.round(route.estimated_success_rate * 100)}% success</em>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Recent episodes</strong>
        {episodes.length === 0 ? <p className="muted-copy">No episodic memory for the active goal.</p> : (
          <ul className="observability-list">
            {episodes.map((episode) => (
              <li key={episode.episode_id}>
                <span>{episode.event_type}: {episode.outcome}</span>
                <em>{Math.round(episode.progress_at_end * 100)}%</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Top semantic facts</strong>
        {semanticFacts.length === 0 ? <p className="muted-copy">No semantic facts match the current runtime context.</p> : (
          <ul className="observability-list">
            {semanticFacts.map((fact) => (
              <li key={fact.fact_id}>
                <span>{fact.subject} {fact.predicate} {fact.object}</span>
                <em>{Math.round(fact.confidence * 100)}%</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Procedural pattern</strong>
        {!proceduralPattern ? <p className="muted-copy">No active procedural recommendation.</p> : (
          <ul className="observability-list">
            <li>
              <span>{proceduralPattern.name}</span>
              <em>{proceduralPattern.recommended_route}</em>
            </li>
          </ul>
        )}
      </div>
    </section>
  )
}
