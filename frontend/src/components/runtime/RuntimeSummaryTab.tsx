import type { ChatRequestState } from '../../types'
import type { RuntimeSummaryContract } from '../../lib/runtimeTypes'
import type { RuntimeProviderStatus } from '../../lib/providerTypes'
import { RuntimeStatusBadge } from './RuntimeStatusBadge'
import { ProviderStatusBadge } from './ProviderStatusBadge'
import { TokenUsageMeter } from './TokenUsageMeter'

type RuntimeSummaryTabProps = {
  data: RuntimeSummaryContract
  provider: RuntimeProviderStatus | null
  requestState: ChatRequestState
  hasMetadata: boolean
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  )
}

export function RuntimeSummaryTab({ data, provider, requestState, hasMetadata }: RuntimeSummaryTabProps) {
  const isLoading = requestState === 'loading'

  if (!hasMetadata && !isLoading) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-4">
      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Runtime</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Mode</span>
          <RuntimeStatusBadge mode={data.runtime_mode} fallback={data.fallback_triggered === true} />
        </div>
        {data.runtime_reason ? (
          <SummaryRow label="Reason" value={data.runtime_reason} />
        ) : null}
        <SummaryRow label="Request ID" value={data.request_id ?? 'não disponível'} />
        <SummaryRow label="Trace ID" value={data.trace_id ?? 'não disponível'} />
        <SummaryRow label="Created" value={data.created_at ?? 'não disponível'} />
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Provider & Latency</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Provider</span>
          <ProviderStatusBadge provider={provider?.provider_name ?? null} />
        </div>
        <SummaryRow label="Latency" value={data.latency_ms != null ? `${data.latency_ms}ms` : 'não disponível'} />
        <SummaryRow
          label="Governance"
          value={data.governance_decision ?? 'não disponível'}
        />
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Usage</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Tokens</span>
          <TokenUsageMeter
            usage={data.tokens_in === null && data.tokens_out === null
              ? null
              : {
                  input_tokens: data.tokens_in ?? undefined,
                  output_tokens: data.tokens_out ?? undefined,
                }}
          />
        </div>
        <SummaryRow label="Input" value={data.tokens_in?.toLocaleString() ?? 'não disponível'} />
        <SummaryRow label="Output" value={data.tokens_out?.toLocaleString() ?? 'não disponível'} />
      </section>
    </div>
  )
}
