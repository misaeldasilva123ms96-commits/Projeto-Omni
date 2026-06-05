import { useCallback, useEffect, useMemo, useState } from 'react'
import type { View } from '../app/App'
import { GovernanceDecisionsList } from '../components/governance/GovernanceDecisionsList'
import { OmniShell } from '../components/shell/OmniShell'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { OmniCard } from '../components/ui/OmniCard'
import { fetchGovernanceDecisions } from '../lib/omniData'
import type { ChatMode, ConversationSummary, GovernanceDecision } from '../types'

type GovernanceCenterPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

export function GovernanceCenterPage({ mode, onChangeMode, onChangeView, view }: GovernanceCenterPageProps) {
  const [decisions, setDecisions] = useState<GovernanceDecision[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchGovernanceDecisions()
      .then((data) => {
        if (!cancelled) {
          setDecisions(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const refresh = useCallback(() => {
    fetchGovernanceDecisions().then(setDecisions).catch(() => {})
  }, [])

  const stats = useMemo(() => {
    const total = decisions.length
    const allowed = decisions.filter((d) => d.decision === 'allowed').length
    const blocked = decisions.filter((d) => d.decision === 'blocked').length
    const pendingApproval = decisions.filter((d) => d.decision === 'requires_approval').length
    const highRisk = decisions.filter((d) => d.riskLevel === 'high' || d.riskLevel === 'critical').length
    return { total, allowed, blocked, pendingApproval, highRisk }
  }, [decisions])

  const conversations: ConversationSummary[] = []

  return (
    <OmniShell
      sidebar={(
        <OmniSidebar
          conversations={conversations}
          mode={mode}
          onChangeMode={onChangeMode}
          onSelectView={onChangeView}
          view={view}
        />
      )}
    >
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-white">Centro de Governança</h1>
          <p className="mt-1 text-sm text-slate-400">
            Visualize decisões de governança, políticas e regras aplicadas pelo runtime
          </p>
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Total</p>
            <p className="mt-2 text-2xl font-semibold text-white">{stats.total}</p>
            <p className="mt-1 text-xs text-slate-400">Decisões registradas</p>
          </OmniCard>

          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Allow</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-300">{stats.allowed}</p>
            <p className="mt-1 text-xs text-slate-400">Requisições permitidas</p>
          </OmniCard>

          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Block</p>
            <p className={`mt-2 text-2xl font-semibold ${stats.blocked > 0 ? 'text-red-300' : 'text-slate-400'}`}>
              {stats.blocked}
            </p>
            <p className="mt-1 text-xs text-slate-400">Requisições bloqueadas</p>
          </OmniCard>

          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Alto Risco</p>
            <p className={`mt-2 text-2xl font-semibold ${stats.highRisk > 0 ? 'text-amber-300' : 'text-slate-400'}`}>
              {stats.highRisk}
            </p>
            <p className="mt-1 text-xs text-slate-400">Risco alto ou crítico</p>
          </OmniCard>
        </div>

        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-white">Decisões Recentes</h2>
          <button
            className="rounded-xl border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition hover:border-white/20 hover:text-slate-300"
            onClick={refresh}
            type="button"
          >
            Atualizar
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-400">
            Carregando decisões de governança...
          </div>
        ) : (
          <GovernanceDecisionsList decisions={decisions} />
        )}
      </div>
    </OmniShell>
  )
}
