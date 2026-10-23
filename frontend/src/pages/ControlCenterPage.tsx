import { useCallback, useEffect, useState, type ReactNode } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import type {
  Agent, ChatMode, ConversationSummary, PublicMilestonesSummaryV1,
  PublicRuntimeSignalsSummaryV1, PublicStatusResponseV1, PublicStrategySummaryV1,
  RuntimeSignalsResponse, TokenUsageSummary,
} from '../types'
import type { ProviderRecord } from '../features/settings/types'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { PageHero } from '../components/ui/PageHero'
import { StatusBadge } from '../components/ui/StatusBadge'
import { DataScopeBadge } from '../components/ui/DataScopeBadge'
import { canUseApi } from '../lib/env'
import {
  fetchPublicMilestonesSummaryV1,
  fetchPublicRuntimeSignalsSummaryV1,
  fetchPublicRuntimeStatusV1,
  fetchPublicStrategySummaryV1,
  fetchRuntimeSignalsPreferOperator,
} from '../lib/api/runtime'
import { listProviders } from '../lib/api/settings'
import { fetchAgents, fetchTokenUsage } from '../lib/omniData'
import { formatCompactTokenCount } from '../lib/tokenUsage'
import { redactRuntimeDebugText } from '../lib/runtimeDebugSanitizer'
import { useObservabilityStream } from '../hooks/useObservabilityStream'
import { useObservabilitySnapshot } from '../hooks/useObservabilitySnapshot'
import {
  providerOperationalState, recentRuntimeMode, RUNTIME_LAYERS,
  safeCount, type RuntimeLayerId,
} from '../features/control-center/model'

type Props = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

const POLL_RUNTIME_MS = 15_000
const POLL_PROVIDERS_MS = 60_000

function Panel({ title, description, children }: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="min-w-0 rounded-[22px] border border-white/10 bg-[rgba(13,17,37,0.78)] p-4 shadow-lg">
      <h3 className="text-base font-semibold text-white">{title}</h3>
      {description ? <p className="mt-1 text-xs text-slate-400">{description}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 break-words text-lg font-semibold text-white">{value}</p>
      {hint ? <p className="mt-1 text-[11px] text-slate-500">{hint}</p> : null}
    </div>
  )
}

function displayTimestamp(value: number | null): string {
  return value === null ? 'Ainda sem leitura' : new Date(value).toLocaleString('pt-BR')
}

const providerLabels = {
  unconfigured: 'Não configurado',
  healthy: 'Saudável (teste válido)',
  unhealthy: 'Falha no teste válido',
  unverified: 'Sem teste válido',
} as const

export function ControlCenterPage({ mode, onChangeMode, onChangeView, renderShell, view }: Props) {
  const apiReady = canUseApi()
  const [selectedLayer, setSelectedLayer] = useState<RuntimeLayerId>('rust')
  const [refreshKey, setRefreshKey] = useState(0)
  const [status, setStatus] = useState<PublicStatusResponseV1 | null>(null)
  const [signals, setSignals] = useState<PublicRuntimeSignalsSummaryV1 | null>(null)
  const [milestones, setMilestones] = useState<PublicMilestonesSummaryV1 | null>(null)
  const [strategy, setStrategy] = useState<PublicStrategySummaryV1 | null>(null)
  const [runtimeDetail, setRuntimeDetail] = useState<RuntimeSignalsResponse | null>(null)
  const [runtimeDetailSource, setRuntimeDetailSource] = useState<string | null>(null)
  const [runtimeWarning, setRuntimeWarning] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<number | null>(null)
  const [providers, setProviders] = useState<ProviderRecord[] | null>(null)
  const [providerError, setProviderError] = useState<string | null>(null)
  const [agents, setAgents] = useState<Agent[] | null>(null)
  const [usage, setUsage] = useState<TokenUsageSummary | null>(null)

  // Reuse the Rust-authenticated SSE stream and existing snapshot adapter.
  // The auth gate guarantees the page is not mounted for unauthenticated viewers.
  const live = useObservabilityStream(apiReady)
  const initial = useObservabilitySnapshot(apiReady)
  const snapshot = live.snapshot ?? initial.snapshot

  useEffect(() => {
    if (!apiReady) return
    let cancelled = false
    let running = false
    const refresh = async () => {
      if (running) return
      running = true
      try {
        const result = await Promise.allSettled([
          fetchPublicRuntimeStatusV1(),
          fetchPublicRuntimeSignalsSummaryV1(),
          fetchPublicMilestonesSummaryV1(),
          fetchPublicStrategySummaryV1(),
          fetchRuntimeSignalsPreferOperator(),
        ])
        if (cancelled) return
        if (result[0].status === 'fulfilled') setStatus(result[0].value)
        if (result[1].status === 'fulfilled') setSignals(result[1].value)
        if (result[2].status === 'fulfilled') setMilestones(result[2].value)
        if (result[3].status === 'fulfilled') setStrategy(result[3].value)
        if (result[4].status === 'fulfilled') {
          setRuntimeDetail(result[4].value.data)
          setRuntimeDetailSource(result[4].value.source)
        }
        const failed = result.filter((item) => item.status === 'rejected').length
        setRuntimeWarning(failed ? String(failed) + ' fontes não responderam nesta atualização.' : null)
        if (result.some((item) => item.status === 'fulfilled')) setLastUpdated(Date.now())
      } finally {
        running = false
      }
    }
    void refresh()
    const interval = window.setInterval(() => { void refresh() }, POLL_RUNTIME_MS)
    return () => { cancelled = true; window.clearInterval(interval) }
  }, [apiReady, refreshKey])

  useEffect(() => {
    let cancelled = false
    const refreshProviders = () => {
      if (!apiReady) return
      listProviders()
        .then((values) => {
          if (!cancelled) {
            setProviders(values)
            setProviderError(null)
          }
        })
        .catch((error) => {
          if (!cancelled) setProviderError(redactRuntimeDebugText(
            error instanceof Error ? error.message : 'Não foi possível consultar os provedores.',
          ))
        })
    }
    refreshProviders()
    const interval = window.setInterval(refreshProviders, POLL_PROVIDERS_MS)
    return () => { cancelled = true; window.clearInterval(interval) }
  }, [apiReady, refreshKey])

  useEffect(() => {
    let cancelled = false
    // Registered agents are currently browser-local configuration, NOT live worker status.
    void fetchAgents().then((values) => {
      if (!cancelled) setAgents(values)
    }).catch(() => { if (!cancelled) setAgents(null) })
    // Historical token usage is sampled from accessible chat sessions, not provider billing.
    void fetchTokenUsage().then((values) => {
      if (!cancelled) setUsage(values)
    }).catch(() => { if (!cancelled) setUsage(null) })
    return () => { cancelled = true }
  }, [refreshKey])

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), [])
  const sidebar = (
    <OmniSidebar
      conversations={[] as ConversationSummary[]}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )
  const layer = RUNTIME_LAYERS.find((item) => item.id === selectedLayer) ?? RUNTIME_LAYERS[1]
  const layerStatus: Record<RuntimeLayerId, string> = {
    frontend: 'Interface renderizada',
    rust: status?.rust_service ?? 'Não verificado',
    python: status?.python_status ?? 'Não verificado',
    node: status?.node_status ?? 'Não verificado',
  }
  const activeAgentConfigs = agents?.filter((agent) => agent.status === 'active').length
  const healthyProviders = providers?.filter((p) => providerOperationalState(p) === 'healthy').length
  const runtimeMode = recentRuntimeMode(runtimeDetail)
  const recentEvents = snapshot?.timeline?.slice(0, 8) ?? []
  const transitions = runtimeDetail?.recent_mode_transitions?.slice(0, 5) ?? []

  return renderShell(
    <div className="flex h-full min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-2 py-5" data-testid="omni-control-center">
      <PageHero
        eyebrow="Omni / Operator workspace"
        title="Omni Control Center"
        subtitle="Arquitetura interativa e telemetria real, somente leitura. Ausência de evidência nunca é apresentada como sucesso."
        meta={(
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={live.status === 'live' ? 'active' : 'muted'}>
              SSE: {live.status === 'live' ? 'ao vivo' : live.status}
            </StatusBadge>
            <DataScopeBadge variant="operator" />
            <button type="button" onClick={refresh} className="rounded-full border border-white/20 px-3 py-1.5 text-sm text-white hover:bg-white/10">
              Atualizar agora
            </button>
          </div>
        )}
      />
      {!apiReady ? (
        <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          Configure VITE_OMNI_API_URL para consultar o backend.
        </p>
      ) : null}
      {runtimeWarning ? (
        <p role="status" className="rounded-xl border border-amber-500/30 p-3 text-sm text-amber-200">
          Telemetria parcial: {runtimeWarning} Valores anteriores podem estar desatualizados.
        </p>
      ) : null}
      <p className="text-xs text-slate-400">
        Última leitura HTTP: {displayTimestamp(lastUpdated)} · API pública a cada 15 s · Provedores a cada 60 s · SSE por ticket autenticado.
      </p>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="Serviço Rust" value={status?.rust_service ?? '—'} hint="GET /api/v1/status" />
        <Stat label="Modo do serviço" value={status?.runtime_mode ?? '—'} hint="Não é o resultado cognitivo de uma execução" />
        <Stat label="Provedores com teste saudável" value={providers ? safeCount(healthyProviders) : '—'} hint="Não equivale a modelo executando" />
        <Stat label="Agentes ativos na configuração" value={agents ? safeCount(activeAgentConfigs) : '—'} hint="Cadastro local, não workers em execução" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel title="Arquitetura interativa" description="Clique em uma camada para ver sua responsabilidade e a evidência disponível.">
          <div className="flex flex-col items-stretch gap-2">
            {RUNTIME_LAYERS.map((item, index) => (
              <div key={item.id}>
                <button
                  type="button"
                  aria-pressed={selectedLayer === item.id}
                  onClick={() => setSelectedLayer(item.id)}
                  className={
                    'flex w-full items-center justify-between gap-3 rounded-xl border p-3 text-left transition ' +
                    (selectedLayer === item.id ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-white/10 bg-white/[0.03] hover:border-white/30')
                  }
                >
                  <span className="min-w-0">
                    <span className="block font-medium text-white">{item.title}</span>
                    <span className="block text-xs text-slate-400">{item.technology}</span>
                  </span>
                  <StatusBadge>{layerStatus[item.id]}</StatusBadge>
                </button>
                {index < RUNTIME_LAYERS.length - 1 ? (
                  <div aria-hidden="true" className="py-1 text-center text-sm text-slate-500">↓</div>
                ) : null}
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-3">
            <p className="font-semibold text-cyan-200">{layer.title}</p>
            <p className="mt-1 text-sm text-slate-300">{layer.responsibility}</p>
            <p className="mt-2 break-all text-xs text-slate-400">Código: {layer.path}</p>
            <p className="mt-2 text-xs text-slate-300">Sinal disponível: {layerStatus[layer.id]}</p>
          </div>
        </Panel>

        <Panel title="Runtime Truth" description="Não confundir HTTP 200 com sucesso cognitivo. Resumo público + projeção de operador.">
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Último run" value={signals?.latest_run_id || '—'} />
            <Stat label="Sinais recentes" value={safeCount(signals?.recent_signal_count)} />
            <Stat label="Transições de modo" value={safeCount(signals?.recent_mode_transition_count)} />
            <Stat label="Modo do último run" value={runtimeMode ?? 'Não informado'} />
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Fonte detalhada: {runtimeDetailSource ?? 'indisponível'}.
            O modo é exibido somente quando consta da evidência retornada pelo backend.
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {transitions.length ? transitions.map((transition, index) => (
              <pre key={index} className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-black/25 p-2 text-xs text-slate-300">
                {redactRuntimeDebugText(JSON.stringify(transition && typeof transition === 'object'
                  ? Object.fromEntries(Object.entries(transition).filter(([key]) =>
                    ['runtime_mode', 'previous_mode', 'new_mode', 'timestamp', 'reason', 'run_id'].includes(key)
                  )) : {}, null, 2))}
              </pre>
            )) : <p className="text-sm text-slate-500">Sem transições detalhadas disponíveis.</p>}
          </div>
        </Panel>

        <Panel title="Agentes" description="Somente configurações salvas neste navegador; telemetria de workers ainda não existe.">
          {agents === null ? <p className="text-sm text-slate-400">Carregando cadastro local…</p> : agents.length === 0 ? (
            <p className="text-sm text-slate-400">Nenhum agente cadastrado neste navegador.</p>
          ) : (
            <ul className="space-y-2">
              {agents.slice(0, 10).map((agent) => (
                <li key={agent.id} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{redactRuntimeDebugText(agent.name)}</p>
                    <p className="text-xs text-slate-400">{redactRuntimeDebugText(agent.provider)} / {redactRuntimeDebugText(agent.model)}</p>
                  </div>
                  <StatusBadge tone={agent.status === 'active' ? 'active' : 'muted'}>
                    {agent.status === 'active' ? 'Habilitado' : 'Inativo'}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="mt-3 text-sm text-cyan-300 hover:underline" onClick={() => onChangeView('agents')}>
            Abrir Centro de Agentes →
          </button>
        </Panel>

        <Panel title="Provedores" description="Configuração e última verificação de saúde. A consulta não dispara testes nem usa chaves na interface.">
          {providerError ? <p role="alert" className="mb-3 text-xs text-amber-200">Consulta indisponível: {providerError}</p> : null}
          {providers === null ? <p className="text-sm text-slate-400">Sem resposta autenticada de configuração.</p> : providers.length === 0 ? (
            <p className="text-sm text-slate-400">Nenhum registro retornado pela API de configurações.</p>
          ) : (
            <ul className="space-y-2">
              {providers.map((provider) => (
                <li key={provider.provider} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <span className="text-sm font-medium">{redactRuntimeDebugText(provider.provider)}</span>
                  <StatusBadge tone={providerOperationalState(provider) === 'healthy' ? 'active' : 'muted'}>
                    {providerLabels[providerOperationalState(provider)]}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="mt-3 text-sm text-cyan-300 hover:underline" onClick={() => onChangeView('provider-center')}>
            Abrir Centro de Provedores →
          </button>
        </Panel>

        <Panel title="Eventos ao vivo" description="Snapshots do backend Rust. A conexão SSE exige autenticação e pode estar indisponível.">
          {live.error ? <p className="mb-2 text-xs text-amber-200">{redactRuntimeDebugText(live.error)}</p> : null}
          {initial.error && !snapshot ? <p className="mb-2 text-xs text-amber-200">{redactRuntimeDebugText(initial.error)}</p> : null}
          <p className="mb-3 text-xs text-slate-400">
            Fonte: {live.snapshot ? 'SSE' : snapshot ? 'snapshot autenticado' : 'indisponível'}.
            Último trace: {snapshot?.latest_trace?.trace_id ? redactRuntimeDebugText(snapshot.latest_trace.trace_id) : '—'}.
          </p>
          {recentEvents.length === 0 ? <p className="text-sm text-slate-500">Nenhum evento registrado no snapshot.</p> : (
            <ul className="space-y-2">
              {recentEvents.map((event) => (
                <li key={event.event_id} className="rounded-lg border border-white/10 p-2">
                  <p className="text-sm font-medium">{redactRuntimeDebugText(event.event_type)}</p>
                  <p className="mt-1 text-xs text-slate-400">{redactRuntimeDebugText(event.description).slice(0, 220)}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{redactRuntimeDebugText(event.outcome)} · {event.timestamp}</p>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="mt-3 text-sm text-cyan-300 hover:underline" onClick={() => onChangeView('observability')}>
            Inspeção detalhada →
          </button>
        </Panel>

        <Panel title="Tokens e custos" description="Consumo histórico de mensagens acessíveis, não é métrica global nem faturamento dos provedores.">
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Tokens registrados" value={usage ? formatCompactTokenCount(usage.totalTokens) : '—'} />
            <Stat label="Requisições com uso" value={safeCount(usage?.totalRequests)} />
            <Stat label="Entrada" value={usage ? formatCompactTokenCount(usage.totalInputTokens) : '—'} />
            <Stat label="Saída" value={usage ? formatCompactTokenCount(usage.totalOutputTokens) : '—'} />
          </div>
          <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3">
            <p className="text-sm font-medium text-amber-200">Custo em R$: indisponível</p>
            <p className="mt-1 text-xs text-slate-400">Não há preço unitário confirmado nem integração de billing. Não é seguro estimar cobrança a partir destes números.</p>
          </div>
          <button type="button" className="mt-3 text-sm text-cyan-300 hover:underline" onClick={() => onChangeView('token-usage')}>
            Ver histórico de tokens →
          </button>
        </Panel>
      </div>

      <Panel title="Governança e marcos" description="Resumos públicos, não substituem uma auditoria de execução.">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <Stat label="Marcos concluídos" value={safeCount(milestones?.completed_milestone_count)} />
          <Stat label="Marcos bloqueados" value={safeCount(milestones?.blocked_milestone_count)} />
          <Stat label="Versão da estratégia" value={safeCount(strategy?.strategy_version)} />
          <Stat label="Atualizações de estratégia" value={safeCount(strategy?.recent_change_log_count)} />
        </div>
      </Panel>
    </div>,
    { sidebar },
  )
}
