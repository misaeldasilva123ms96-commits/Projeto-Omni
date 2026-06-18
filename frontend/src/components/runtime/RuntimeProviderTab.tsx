import type { RuntimeProviderStatus } from '../../lib/providerTypes'

type RuntimeProviderTabProps = {
  data: RuntimeProviderStatus[]
}

function ProviderCard({ provider }: { provider: RuntimeProviderStatus }) {
  const status = provider.succeeded
    ? 'Succeeded'
    : provider.attempted && provider.succeeded === false
      ? 'Failed'
      : provider.attempted
        ? 'Attempted'
        : 'Unavailable'

  const statusColor = provider.succeeded
    ? 'text-emerald-300'
    : provider.attempted && provider.succeeded === false
      ? 'text-red-300'
      : 'text-slate-500'

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium text-white">
            {provider.provider_name || 'Unknown'}
          </div>
          <div className={`mt-1 text-xs ${statusColor}`}>
            {status}
          </div>
        </div>
        {provider.latency_ms != null ? (
          <span className="text-xs text-slate-400">{provider.latency_ms}ms</span>
        ) : null}
      </div>
      {provider.failure_reason ? (
        <p className="mt-2 text-xs text-red-200/80">{provider.failure_reason}</p>
      ) : null}
      {provider.model ? (
        <p className="mt-1 text-xs text-slate-300/70">{provider.model}</p>
      ) : null}
      <p className="mt-1 text-xs text-slate-400">
        Tokens: {provider.tokens_in ?? 'não disponível'} in / {provider.tokens_out ?? 'não disponível'} out
      </p>
    </div>
  )
}

export function RuntimeProviderTab({ data }: RuntimeProviderTabProps) {
  if (!data.length) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-3">
      {data.map((provider, index) => (
        <ProviderCard key={index} provider={provider} />
      ))}
    </div>
  )
}
