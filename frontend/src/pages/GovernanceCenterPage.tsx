import { useCallback, useEffect, useMemo, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { GovernanceDecisionsList } from '../components/governance/GovernanceDecisionsList'
import { ContextFilterControls } from '../components/observability/ContextFilterControls'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { OmniButton } from '../components/ui/OmniButton'
import { OmniCard } from '../components/ui/OmniCard'
import { OmniLoadingState } from '../components/ui/OmniLoadingState'
import { PageHero } from '../components/ui/PageHero'
import { fetchGovernanceDecisions } from '../lib/omniData'
import type { ChatMode, ConversationSummary, GovernanceDecision } from '../types'
import {
  filterGovernanceDecisionsByContext,
  hasObservabilityContext,
  parseObservabilityContext,
  pickObservabilityContext,
} from '../lib/observabilityContext'

type GovernanceCenterPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function GovernanceCenterPage({ mode, onChangeMode, onChangeView, renderShell, view }: GovernanceCenterPageProps) {
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
  const context = pickObservabilityContext(
    parseObservabilityContext(window.location.search),
    ['decision', 'request_id', 'trace_id', 'runtime_mode'],
  )
  const hasContext = hasObservabilityContext(context)
  const visibleDecisions = filterGovernanceDecisionsByContext(decisions, context)

  const stats = useMemo(() => {
    const total = visibleDecisions.length
    const allowed = visibleDecisions.filter((d) => d.decision === 'allowed').length
    const blocked = visibleDecisions.filter((d) => d.decision === 'blocked').length
    const pendingApproval = visibleDecisions.filter((d) => d.decision === 'requires_approval').length
    const highRisk = visibleDecisions.filter((d) => d.riskLevel === 'high' || d.riskLevel === 'critical').length
    return { total, allowed, blocked, pendingApproval, highRisk }
  }, [visibleDecisions])

  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Conformidade"
          title="Centro de Governança"
          subtitle="Visualize decisões de governança, políticas e regras aplicadas pelo runtime"
          className="mb-6"
        />

        <ContextFilterControls context={context} overviewPath="/governance" />

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
          <OmniButton variant="secondary" onClick={refresh}>
            Atualizar
          </OmniButton>
        </div>

        {loading ? (
          <OmniLoadingState label="Carregando decisões de governança..." skeletonRows={3} />
        ) : hasContext && visibleDecisions.length === 0 ? (
          <div className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-8 text-center text-sm text-slate-400">
            <p>Contexto recebido, mas não há dados disponíveis para este filtro.</p>
            <p className="mt-2">
              O contexto foi recebido com segurança, mas nenhum registro correspondente foi encontrado nos dados disponíveis.
            </p>
          </div>
        ) : (
          <GovernanceDecisionsList decisions={visibleDecisions} />
        )}
      </div>,
    { sidebar },
  )
}
