import type { ProviderRecord, ProviderTestResult } from '../../features/settings/types'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniCard } from '../ui/OmniCard'
import { OmniStatusDot } from '../ui/OmniStatusDot'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

type ProviderCenterOverviewProps = {
  providers: ProviderRecord[]
  lastTestResult: ProviderTestResult | null
  className?: string
}

export function ProviderCenterOverview({ providers, lastTestResult, className = '' }: ProviderCenterOverviewProps) {
  const total = providers.length
  const configured = providers.filter((p) => p.configured).length
  const notConfigured = total - configured
  const healthy = providers.filter((p) => p.health_valid && p.healthy).length
  const openCircuits = providers.filter((p) => p.circuit_state === 'open').length

  return (
    <div className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${className}`.trim()}>
      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Total</p>
        <p className="mt-2 text-2xl font-semibold text-white">{total}</p>
        <p className="mt-1 text-xs text-slate-400">Provedores registrados</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Configurados</p>
        <p className="mt-2 text-2xl font-semibold text-emerald-300">{configured}</p>
        <p className="mt-1 text-xs text-slate-400">Com credenciais armazenadas</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Saudáveis</p>
        <p className="mt-2 text-2xl font-semibold text-emerald-300">{healthy}</p>
        <p className="mt-1 text-xs text-slate-400">Com teste recente válido</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Circuitos abertos</p>
        <p className={`mt-2 text-2xl font-semibold ${openCircuits > 0 ? 'text-red-300' : 'text-slate-400'}`}>{openCircuits}</p>
        <p className="mt-1 text-xs text-slate-400">Aguardando próximo probe</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Não configurados</p>
        <p className={`mt-2 text-2xl font-semibold ${notConfigured > 0 ? 'text-amber-300' : 'text-slate-400'}`}>{notConfigured}</p>
        <p className="mt-1 text-xs text-slate-400">Sem credenciais</p>
      </OmniCard>

      <OmniCard variant="panel">
        <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Último teste</p>
        {lastTestResult ? (
          <div className="mt-2 space-y-2">
            <OmniBadge tone={lastTestResult.success ? 'success' : 'danger'}>
              <OmniStatusDot tone={lastTestResult.success ? 'success' : 'danger'} />
              <span>{lastTestResult.success ? 'Sucesso' : 'Falha'}</span>
            </OmniBadge>
            <p className="text-xs text-slate-400 truncate">
              {lastTestResult.provider}
              {lastTestResult.error ? `: ${redactRuntimeDebugText(lastTestResult.error)}` : ''}
            </p>
          </div>
        ) : (
          <>
            <p className="mt-2 text-lg font-semibold text-slate-500">—</p>
            <p className="mt-1 text-xs text-slate-500">Nenhum teste realizado</p>
          </>
        )}
      </OmniCard>
    </div>
  )
}
