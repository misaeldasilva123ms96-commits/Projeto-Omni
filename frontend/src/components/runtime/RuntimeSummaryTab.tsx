import type { ChatRequestState } from '../../types'
import type { RuntimeSummaryContract } from '../../lib/runtimeTypes'
import type { RuntimeProviderStatus } from '../../lib/providerTypes'
import { RuntimeStatusBadge } from './RuntimeStatusBadge'
import { ProviderStatusBadge } from './ProviderStatusBadge'
import { TokenUsageMeter } from './TokenUsageMeter'
import { RuntimeLinkAction } from './RuntimeLinkAction'

type RuntimeSummaryTabProps = {
  data: RuntimeSummaryContract | null
  provider: RuntimeProviderStatus | null
  requestState: ChatRequestState
  observabilityHref: string | null
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  )
}

export function RuntimeSummaryTab({
  data,
  provider,
  requestState,
  observabilityHref,
}: RuntimeSummaryTabProps) {
  const isLoading = requestState === 'loading'

  if (!data && !isLoading) {
    return (
      <div>
        <p className="text-sm text-slate-400">não disponível</p>
        <RuntimeLinkAction
          href={observabilityHref}
          label="Abrir em Observabilidade"
          unavailableLabel="sem referência disponível"
        />
      </div>
    )
  }

  const summary = data ?? {
    runtime_mode: 'UNKNOWN' as const,
    runtime_reason: null,
    provider_attempted: null,
    provider_succeeded: null,
    fallback_triggered: null,
    tool_invoked: null,
    governance_decision: null,
    tokens_in: null,
    tokens_out: null,
    latency_ms: null,
    request_id: null,
    trace_id: null,
    created_at: null,
  }

  return (
    <div className="space-y-4">
      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Runtime</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Mode</span>
          <RuntimeStatusBadge mode={summary.runtime_mode} fallback={summary.fallback_triggered === true} />
        </div>
        {summary.runtime_reason ? (
          <SummaryRow label="Reason" value={summary.runtime_reason} />
        ) : null}
        <SummaryRow label="Request ID" value={summary.request_id ?? 'não disponível'} />
        <SummaryRow label="Trace ID" value={summary.trace_id ?? 'não disponível'} />
        <SummaryRow label="Created" value={summary.created_at ?? 'não disponível'} />
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Provider & Latency</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Provider</span>
          <ProviderStatusBadge provider={provider?.provider_name ?? null} />
        </div>
        <SummaryRow label="Latency" value={summary.latency_ms != null ? `${summary.latency_ms}ms` : 'não disponível'} />
        <SummaryRow
          label="Governance"
          value={summary.governance_decision ?? 'não disponível'}
        />
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Usage</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Tokens</span>
          <TokenUsageMeter
            usage={summary.tokens_in === null && summary.tokens_out === null
              ? null
              : {
                  input_tokens: summary.tokens_in ?? undefined,
                  output_tokens: summary.tokens_out ?? undefined,
                }}
          />
        </div>
        <SummaryRow label="Input" value={summary.tokens_in?.toLocaleString() ?? 'não disponível'} />
        <SummaryRow label="Output" value={summary.tokens_out?.toLocaleString() ?? 'não disponível'} />
      </section>

      <RuntimeLinkAction
        href={observabilityHref}
        label="Abrir em Observabilidade"
        unavailableLabel="sem referência disponível"
      />
    </div>
  )
}
