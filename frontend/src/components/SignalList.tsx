type SignalListProps = {
  emptyLabel: string
  items: Array<Record<string, unknown>>
}

export function SignalList({ emptyLabel, items }: SignalListProps) {
  if (items.length === 0) {
    return <p className="muted-copy">{emptyLabel}</p>
  }

  return (
    <div className="signal-list">
      {items.map((item, index) => (
        <article className="signal-item" key={`${String(item.event_type ?? item.run_id ?? index)}-${index}`}>
          <div className="signal-row">
            <strong>{String(item.event_type ?? item.title ?? item.run_id ?? 'event')}</strong>
            <span>{String(item.timestamp ?? item.updated_at ?? '')}</span>
          </div>
          <p>{String(item.reason_code ?? item.summary ?? item.message ?? '')}</p>
        </article>
      ))}
    </div>
  )
}
