import type { TimelineEvent } from '../../types/observability'

type OperationalTimelineProps = {
  events: TimelineEvent[]
}

export function OperationalTimeline({ events }: OperationalTimelineProps) {
  return (
    <section className="panel-card metric-card observability-card">
      <p className="card-eyebrow">Operational timeline</p>
      <h3>Recent runtime events</h3>
      {events.length === 0 ? <p className="muted-copy">No working-memory events are available yet.</p> : (
        <div className="timeline-list">
          {events.map((event) => (
            <article className="timeline-item" key={event.event_id}>
              <div className="timeline-item-header">
                <strong>{event.event_type}</strong>
                <span>{new Date(event.timestamp).toLocaleString('pt-BR')}</span>
              </div>
              <p>{event.description}</p>
              <div className="timeline-item-meta">
                <span>Outcome: {event.outcome || 'n/a'}</span>
                <span>Progress: {Math.round(event.progress_score * 100)}%</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
