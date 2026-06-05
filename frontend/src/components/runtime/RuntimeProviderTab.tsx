import type { ProviderDiagnostic, RuntimeMetadata } from '../../types'

type RuntimeProviderTabProps = {
  metadata: RuntimeMetadata | null
}

function ProviderCard({ provider }: { provider: ProviderDiagnostic }) {
  const status = provider.succeeded
    ? 'Succeeded'
    : provider.failed
      ? 'Failed'
      : provider.attempted
        ? 'Attempted'
        : provider.available
          ? 'Available'
          : 'Unavailable'

  const statusColor = provider.succeeded
    ? 'text-emerald-300'
    : provider.failed
      ? 'text-red-300'
      : provider.available
        ? 'text-slate-300'
        : 'text-slate-500'

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium text-white">
            {provider.provider || 'Unknown'}
          </div>
          <div className={`mt-1 text-xs ${statusColor}`}>
            {status}
            {provider.selected ? ' (selected)' : ''}
            {provider.configured === false ? ' (not configured)' : ''}
          </div>
        </div>
        {provider.latency_ms != null ? (
          <span className="text-xs text-slate-400">{provider.latency_ms}ms</span>
        ) : null}
      </div>
      {provider.failure_reason ? (
        <p className="mt-2 text-xs text-red-200/80">{provider.failure_reason}</p>
      ) : null}
      {provider.failure_class ? (
        <p className="mt-1 text-xs text-amber-200/60">{provider.failure_class}</p>
      ) : null}
    </div>
  )
}

export function RuntimeProviderTab({ metadata }: RuntimeProviderTabProps) {
  const providers = metadata?.providerDiagnostics ?? []

  if (!providers.length) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  const sorted = [...providers].sort((a, b) => {
    if (a.selected) return -1
    if (b.selected) return 1
    return 0
  })

  return (
    <div className="space-y-3">
      {sorted.map((provider, index) => (
        <ProviderCard key={index} provider={provider} />
      ))}
    </div>
  )
}
