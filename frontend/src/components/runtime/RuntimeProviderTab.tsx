import type { RuntimeProviderStatus } from '../../lib/providerTypes'
import type { RuntimeProviderAutoRouting } from '../../lib/runtimeTypes'
import { RuntimeLinkAction } from './RuntimeLinkAction'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { TokenUsageMeter } from '../tokens/TokenUsageMeter'

type RuntimeProviderTabProps = {
  data: RuntimeProviderStatus[]
  autoRouting: RuntimeProviderAutoRouting | null
  providerHref: string | null
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
            {redactRuntimeDebugText(provider.provider_name ?? '') || 'Unknown'}
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
        <p className="mt-2 text-xs text-red-200/80">
          {redactRuntimeDebugText(provider.failure_reason)}
        </p>
      ) : null}
      {provider.model ? (
        <p className="mt-1 text-xs text-slate-300/70">
          {redactRuntimeDebugText(provider.model)}
        </p>
      ) : null}
      <TokenUsageMeter
        className="mt-2"
        usage={{
          inputTokens: provider.tokens_in,
          outputTokens: provider.tokens_out,
          totalTokens: provider.total_tokens,
        }}
        variant="detailed"
      />
    </div>
  )
}

function StatusPill({ autoRouting }: { autoRouting: RuntimeProviderAutoRouting }) {
  const label = autoRouting.fail_closed_reason
    ? 'Fail-closed'
    : autoRouting.fallback_used
      ? 'Fallback usado'
      : 'Decisão normal'
  const className = autoRouting.fail_closed_reason
    ? 'border-red-400/30 bg-red-500/10 text-red-200'
    : autoRouting.fallback_used
      ? 'border-amber-400/30 bg-amber-500/10 text-amber-200'
      : 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  )
}

function FieldRow({ label, value }: { label: string, value: string | number | boolean | null }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-slate-500">{label}</span>
      <strong className="max-w-[12rem] truncate text-right font-medium text-slate-200">
        {typeof value === 'boolean' ? (value ? 'Sim' : 'Não') : String(value ?? '—')}
      </strong>
    </div>
  )
}

function ProviderAutoRoutingSection({ autoRouting }: { autoRouting: RuntimeProviderAutoRouting | null }) {
  if (!autoRouting) {
    return (
      <section className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-white">Provider Auto Routing</h3>
            <p className="mt-1 text-xs text-slate-400">sem auto-routing disponível</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-white">Provider Auto Routing</h3>
          <p className="mt-1 text-xs text-slate-400">
            {autoRouting.decision_reason || 'decisão não informada'}
          </p>
        </div>
        <StatusPill autoRouting={autoRouting} />
      </div>

      <div className="mt-3 space-y-1.5">
        <FieldRow label="Modo" value={autoRouting.routing_mode} />
        <FieldRow label="Provider" value={autoRouting.selected_provider} />
        <FieldRow label="Modelo" value={autoRouting.selected_model} />
        <FieldRow label="Fallback" value={autoRouting.fallback_used} />
        <FieldRow label="Candidatos" value={autoRouting.candidate_count} />
        <FieldRow label="Policy" value={autoRouting.policy_result} />
        <FieldRow label="Criado em" value={autoRouting.created_at} />
        {autoRouting.fail_closed_reason ? (
          <FieldRow label="Fail-closed" value={autoRouting.fail_closed_reason} />
        ) : null}
      </div>

      {autoRouting.rejected_candidates.length ? (
        <div className="mt-3">
          <div className="mb-1 text-xs font-medium text-slate-300">Candidatos rejeitados</div>
          <ul className="space-y-1">
            {autoRouting.rejected_candidates.map((candidate, index) => (
              <li key={`${candidate.provider ?? 'provider'}-${index}`} className="rounded-lg bg-black/20 px-2 py-1 text-xs text-slate-300">
                <span className="font-medium text-slate-200">
                  {candidate.provider || 'unknown'}
                </span>
                {candidate.model ? <span>{` / ${candidate.model}`}</span> : null}
                {candidate.reason ? <span className="text-slate-500">{` — ${candidate.reason}`}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {autoRouting.rejected_reasons.length ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {autoRouting.rejected_reasons.map((reason, index) => (
            <span key={`${reason}-${index}`} className="rounded-full bg-white/[0.06] px-2 py-0.5 text-xs text-slate-300">
              {reason}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  )
}

export function RuntimeProviderTab({ data, autoRouting, providerHref }: RuntimeProviderTabProps) {
  if (!data.length) {
    return (
      <div className="space-y-3">
        <ProviderAutoRoutingSection autoRouting={autoRouting} />
        <p className="text-sm text-slate-400">não disponível</p>
        <RuntimeLinkAction
          href={providerHref}
          label="Ver provider"
          unavailableLabel="sem referência disponível"
        />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <ProviderAutoRoutingSection autoRouting={autoRouting} />
      {data.map((provider, index) => (
        <ProviderCard key={index} provider={provider} />
      ))}
      <RuntimeLinkAction
        href={providerHref}
        label="Ver provider"
        unavailableLabel="sem referência disponível"
      />
    </div>
  )
}
