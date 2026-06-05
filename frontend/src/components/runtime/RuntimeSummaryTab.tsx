import type { ChatRequestState, RuntimeMetadata } from '../../types'
import { RuntimeStatusBadge } from './RuntimeStatusBadge'
import { ProviderStatusBadge } from './ProviderStatusBadge'
import { TokenUsageMeter } from './TokenUsageMeter'

type RuntimeSummaryTabProps = {
  metadata: RuntimeMetadata | null
  sessionId: string
  requestState: ChatRequestState
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  )
}

export function RuntimeSummaryTab({ metadata, sessionId, requestState }: RuntimeSummaryTabProps) {
  const runtimeMode = metadata?.runtimeMode ?? 'Unknown'
  const runtimeReason = metadata?.runtimeReason ?? metadata?.cognitiveRuntimeInspection?.runtime_reason as string | undefined
  const executionPath = metadata?.executionPathUsed ?? '—'
  const isFallback = metadata?.fallbackTriggered ?? false
  const latencyMs = metadata?.providerDiagnostics?.find((p) => p.selected)?.latency_ms
  const toolLatency = metadata?.toolExecution?.tool_latency_ms
  const isLoading = requestState === 'loading'

  if (!metadata && !isLoading) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-4">
      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Runtime</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Mode</span>
          <RuntimeStatusBadge mode={runtimeMode} fallback={isFallback} />
        </div>
        {runtimeReason ? (
          <SummaryRow label="Reason" value={runtimeReason} />
        ) : null}
        <SummaryRow label="Execution Path" value={executionPath} />
        <SummaryRow label="Run ID" value={sessionId || '—'} />
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Provider & Latency</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Provider</span>
          <ProviderStatusBadge provider={metadata?.providerActual ?? null} />
        </div>
        <SummaryRow label="Latency" value={latencyMs != null ? `${latencyMs}ms` : '—'} />
        {toolLatency != null ? (
          <SummaryRow label="Tool Latency" value={`${toolLatency}ms`} />
        ) : null}
      </section>

      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Usage</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Tokens</span>
          <TokenUsageMeter usage={metadata?.usage ?? null} />
        </div>
        <SummaryRow label="Input" value={metadata?.usage?.input_tokens?.toLocaleString() ?? '—'} />
        <SummaryRow label="Output" value={metadata?.usage?.output_tokens?.toLocaleString() ?? '—'} />
      </section>
    </div>
  )
}
