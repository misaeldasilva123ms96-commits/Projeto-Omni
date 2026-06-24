import type { RuntimeAutonomyStats, RuntimeAutonomyStatus } from '../../lib/runtimeTypes'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

type RuntimeAutonomyTabProps = {
  data: RuntimeAutonomyStatus | null
  stats: RuntimeAutonomyStats | null
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">
        {redactRuntimeDebugText(value) || '—'}
      </span>
    </div>
  )
}

function Badge({ label, variant }: { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }) {
  const colors = {
    success: 'bg-emerald-500/20 text-emerald-300',
    warning: 'bg-amber-500/20 text-amber-300',
    danger: 'bg-red-500/20 text-red-300',
    info: 'bg-blue-500/20 text-blue-300',
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[variant]}`}>
      {label}
    </span>
  )
}

function decisionVariant(decision: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (decision) {
    case 'CONTINUE':
      return 'success'
    case 'RETRY':
      return 'warning'
    case 'REPLAN':
      return 'warning'
    case 'ESCALATE_TO_MISAEL':
      return 'danger'
    case 'ABORT_SAFE':
      return 'danger'
    case 'PAUSE':
      return 'warning'
    default:
      return 'info'
  }
}

export function RuntimeAutonomyTab({ data, stats }: RuntimeAutonomyTabProps) {
  if (!data && !stats) {
    return (
      <div>
        <p className="text-sm text-slate-400">não disponível</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-xs italic text-slate-400">
        Métricas somente leitura — nenhuma ação autônoma executada.
      </p>

      {data ? (
        <>
          <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
            <h4 className="mb-3 text-sm font-medium text-white">Decisão</h4>
            <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
              <span className="text-sm text-slate-300/70">Decision</span>
              <Badge label={data.decision} variant={decisionVariant(data.decision)} />
            </div>
            <DetailRow label="Advisory" value={data.advisory ? 'Yes' : 'No'} />
            <DetailRow label="Risk Level" value={data.risk_level ?? '—'} />
            {data.reason ? (
              <div className="py-2.5">
                <span className="text-sm text-slate-300/70">Reason</span>
                <p className="mt-1 text-sm text-white">
                  {redactRuntimeDebugText(data.reason)}
                </p>
              </div>
            ) : null}
          </section>

          <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
            <h4 className="mb-3 text-sm font-medium text-white">Progress Tracker</h4>
            <DetailRow label="Progress Score" value={data.progress_score != null ? String(data.progress_score) : '—'} />
            <DetailRow label="Stagnation Score" value={data.stagnation_score != null ? String(data.stagnation_score) : '—'} />
            <DetailRow label="State" value={data.is_stagnation ? 'Stagnation' : data.is_progress ? 'Progress' : 'Neutral'} />
            <DetailRow label="Stagnant Attempts" value={data.stagnant_attempts != null ? String(data.stagnant_attempts) : '—'} />
            <DetailRow label="Fingerprint" value={data.fingerprint_id ?? '—'} />
            <DetailRow label="Recommended Hint" value={data.recommended_decision_hint ?? '—'} />
            {data.evidence_summary ? (
              <div className="py-2.5">
                <span className="text-sm text-slate-300/70">Evidence</span>
                <p className="mt-1 text-sm text-white">
                  {redactRuntimeDebugText(data.evidence_summary)}
                </p>
              </div>
            ) : null}
          </section>

          {data.session_id ? (
            <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
              <h4 className="mb-3 text-sm font-medium text-white">Session</h4>
              <DetailRow label="Session ID" value={data.session_id} />
            </section>
          ) : null}
        </>
      ) : null}

      {stats ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Métricas do Controlador</h4>
          <DetailRow label="Total de Avaliações" value={stats.total_evaluations != null ? String(stats.total_evaluations) : '—'} />
          <DetailRow label="Taxa de Escalação" value={stats.escalation_rate != null ? `${(stats.escalation_rate * 100).toFixed(1)}%` : '—'} />
          <DetailRow label="Sessões Ativas" value={stats.active_session_count != null ? String(stats.active_session_count) : '—'} />
          <DetailRow label="Última Decisão" value={stats.last_decision ?? '—'} />
          <DetailRow label="Último Risk Level" value={stats.last_risk_level ?? '—'} />
          <DetailRow label="Modo Consultivo" value={stats.advisory_mode_enabled ? 'Sim' : 'Não'} />
        </section>
      ) : null}
    </div>
  )
}