import type { GovernanceDecision } from '../../types'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniCard } from '../ui/OmniCard'
import { OmniEmptyState } from '../ui/OmniEmptyState'

type GovernanceDecisionsListProps = {
  decisions: GovernanceDecision[]
  className?: string
}

const DECISION_LABELS: Record<string, string> = {
  allowed: 'Allowed',
  blocked: 'Blocked',
  requires_approval: 'Pending',
  unknown: 'Unknown',
}

const DECISION_TONES: Record<string, 'success' | 'danger' | 'warning' | 'muted'> = {
  allowed: 'success',
  blocked: 'danger',
  requires_approval: 'warning',
  unknown: 'muted',
}

const RISK_TONES: Record<string, 'danger' | 'warning' | 'success' | 'muted'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'warning',
  low: 'success',
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / 86400000)
    if (diffDays === 0) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    if (diffDays < 7) return `${diffDays} dias atrás`
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  } catch {
    return ''
  }
}

export function GovernanceDecisionsList({ decisions, className = '' }: GovernanceDecisionsListProps) {
  if (decisions.length === 0) {
    return (
      <OmniEmptyState
        description="As decisões aparecerão após requisições com inspeção de governança."
        icon={(
          <svg className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        )}
        title="Nenhuma decisão de governança registrada."
      />
    )
  }

  return (
    <div className={`space-y-2 ${className}`.trim()}>
      {decisions.map((d) => (
        <OmniCard
          key={d.id}
          variant="elevated"
          className="rounded-3xl px-4 py-3 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition hover:border-white/18"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <OmniBadge tone={DECISION_TONES[d.decision] ?? 'muted'}>
                  {DECISION_LABELS[d.decision] ?? d.decision}
                </OmniBadge>
                {d.riskLevel ? (
                  <OmniBadge tone={RISK_TONES[d.riskLevel] ?? 'muted'}>
                    {d.riskLevel}
                  </OmniBadge>
                ) : null}
                {d.category ? (
                  <span className="text-xs text-slate-400">
                    {redactRuntimeDebugText(d.category)}
                  </span>
                ) : null}
              </div>

              {d.policy ? (
                <p className="mt-1.5 text-sm text-slate-300/80">
                  <span className="text-xs text-slate-500">Policy: </span>
                  {redactRuntimeDebugText(d.policy)}
                </p>
              ) : null}

              {d.reason ? (
                <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                  {redactRuntimeDebugText(d.reason)}
                </p>
              ) : null}
            </div>

            <span className="shrink-0 text-xs text-slate-500">{formatDate(d.timestamp)}</span>
          </div>
        </OmniCard>
      ))}
    </div>
  )
}
