import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import { MarkdownRenderer } from '../MarkdownRenderer'
import type { ChatMessage, RuntimeMetadata } from '../../types'
import {
  BOTTOM_TABS,
  mockRuntimeState,
  useRuntimeConsoleStore,
} from '../../state/runtimeConsoleStore'
import { getGlowState } from '../../lib/ui/glow'

type ExtendedChatMessage = ChatMessage & {
  isLoading?: boolean
  isNew?: boolean
}

type ChatPanelProps = {
  canSend: boolean
  error: string | null
  input: string
  lastMetadata: RuntimeMetadata | null
  loading: boolean
  messages: ExtendedChatMessage[]
  onChange: (value: string) => void
  onSubmit: () => void
  requestState: 'idle' | 'loading' | 'error'
  sessionId: string
}

const PREVIEW_REPLY = `Claro! Aqui está um plano passo a passo para criar um SaaS:

1. Defina o problema e a solução.
2. Valide sua ideia.
3. Desenvolva o MVP.
4. Configure infraestrutura.
5. Lance e faça marketing.`

function messageBadges(metadata?: RuntimeMetadata) {
  if (!metadata) {
    return []
  }

  return [
    metadata.runtimeMode ? `Mode: ${metadata.runtimeMode}` : null,
    metadata.executionPathUsed ? `Path: ${metadata.executionPathUsed}` : null,
    typeof metadata.fallbackTriggered === 'boolean' ? `Fallback: ${metadata.fallbackTriggered ? 'yes' : 'no'}` : null,
    typeof metadata.compatibilityExecutionActive === 'boolean'
      ? `Compatibility: ${metadata.compatibilityExecutionActive ? 'yes' : 'no'}`
      : null,
    metadata.providerActual ? `Provider: ${metadata.providerActual}` : null,
    metadata.toolExecution?.tool_selected ? `Tool: ${metadata.toolExecution.tool_selected}` : null,
  ].filter((item): item is string => Boolean(item))
}

function safeMessageContent(message: ExtendedChatMessage) {
  if (typeof message.content === 'string' && message.content.trim()) {
    return message.content.trim()
  }
  return '...'
}

function sidebarModuleCopy(item: string, metadata: RuntimeMetadata | null) {
  const safePlaceholder = 'Este módulo ainda não possui backend dedicado nesta branch, mas a navegação e o estado da interface estão funcionais.'
  const copies: Record<string, string[]> = {
    historico: [
      'Histórico local ativo: a conversa atual é persistida no navegador e pode ser reiniciada por Nova conversa.',
      `Último runtime: ${metadata?.runtimeMode ?? 'sem execução registrada nesta sessão.'}`,
    ],
    memoria: [
      'Memória em modo leitura: exibindo status conhecido do runtime sem gravar dados privados.',
      `Status: ${metadata?.cognitiveRuntimeInspection ? 'inspection presente' : safePlaceholder}`,
    ],
    simulacoes: [
      'Simulações conectadas ao painel inferior. Use a aba Simulação para ver caminhos considerados.',
      `Caminhos disponíveis: ${metadata?.matchedTools?.length ?? mockRuntimeState.pathsConsidered}`,
    ],
    insights: [
      'Insights derivados dos metadados disponíveis, sem alegar inferência backend dedicada.',
      `Failure class atual: ${metadata?.failureClass ?? 'none'}`,
    ],
    logs: [
      'Logs apontam para a superfície de observabilidade do runtime.',
      `Execution path: ${metadata?.executionPathUsed ?? 'não registrado ainda'}`,
    ],
    'configuracoes-ia': [
      'Configurações IA estão em modo seguro nesta branch.',
      `Provider atual: ${metadata?.providerActual ?? 'não informado pelo runtime'}`,
    ],
  }
  return copies[item] ?? null
}

export function ChatPanel({
  canSend,
  error,
  input,
  lastMetadata,
  loading,
  messages,
  onChange,
  onSubmit,
  requestState,
  sessionId,
}: ChatPanelProps) {
  const [inputFocused, setInputFocused] = useState(false)
  const activeSidebarItem = useRuntimeConsoleStore((state) => state.activeSidebarItem)
  const activeTab = useRuntimeConsoleStore((state) => state.activeTab)
  const uiNotice = useRuntimeConsoleStore((state) => state.uiNotice)
  const clearUiNotice = useRuntimeConsoleStore((state) => state.clearUiNotice)
  const selectBottomTab = useRuntimeConsoleStore((state) => state.selectBottomTab)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)

  const moduleCopy = useMemo(() => sidebarModuleCopy(activeSidebarItem, lastMetadata), [activeSidebarItem, lastMetadata])
  const latestUserPrompt = messages.findLast((message) => message.role === 'user')?.content ?? 'Como criar um SaaS?'
  const visibleMessages: ExtendedChatMessage[] = messages.length > 0
    ? messages
    : [
        {
          id: 'preview-user',
          role: 'user',
          content: latestUserPrompt,
          createdAt: new Date().toISOString(),
        },
        {
          id: 'preview-assistant',
          role: 'assistant',
          content: PREVIEW_REPLY,
          createdAt: new Date().toISOString(),
          metadata: lastMetadata ?? undefined,
        },
      ]
  const runtimeActive = loading || requestState === 'loading'

  return (
    <div className="flex h-full min-h-[calc(100vh-2rem)] flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className={`min-h-0 flex-1 overflow-hidden rounded-[32px] border bg-[linear-gradient(180deg,rgba(15,15,34,0.72),rgba(10,11,27,0.68))] px-5 py-5 shadow-[0_18px_48px_rgba(0,0,0,0.32)] backdrop-blur-xl ${runtimeActive ? `${getGlowState('runtime')} omni-runtime-glow` : 'border-[rgba(180,109,255,0.16)]'}`}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.35em] text-slate-400">Hoje</div>
              <div className="mt-1 text-sm text-slate-300/80">Sessão {sessionId}</div>
            </div>
            <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-300">
              <span className={`mr-2 inline-block h-2 w-2 rounded-full ${runtimeActive ? 'bg-neon-cyan omni-active-dot' : 'bg-slate-500'}`} />
              {requestState}
            </div>
          </div>

          <div className="flex max-h-[calc(100vh-18rem)] min-h-[360px] flex-col gap-4 overflow-y-auto pr-2">
            <AnimatePresence initial={false}>
              {visibleMessages.map((message, index) => {
                const isUser = message.role === 'user'
                const badges = messageBadges(message.metadata)
                return (
                  <motion.article
                    key={message.id}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.28, delay: Math.min(index * 0.04, 0.18) }}
                  >
                    {isUser ? (
                      <div className={`max-w-[72%] rounded-[26px] border bg-[linear-gradient(135deg,rgba(28,60,190,0.74),rgba(10,24,74,0.98))] px-8 py-4 text-right text-[18px] font-medium leading-8 tracking-tight text-white ${getGlowState('active')}`}>
                        {safeMessageContent(message)}
                      </div>
                    ) : (
                      <div className={`w-full max-w-[84%] rounded-[28px] border bg-[linear-gradient(180deg,rgba(15,15,32,0.88),rgba(8,9,22,0.74))] px-8 py-6 text-slate-100 shadow-[0_14px_34px_rgba(0,0,0,0.28)] backdrop-blur-xl ${message.isLoading ? `${getGlowState('runtime')} omni-runtime-glow` : 'border-[rgba(180,109,255,0.16)]'}`}>
                        <div className="mb-4 flex items-center justify-between gap-4 text-xs uppercase tracking-[0.32em] text-slate-300/70">
                          <span>Omni Runtime</span>
                          <span>{new Date(message.createdAt).toLocaleTimeString('pt-BR')}</span>
                        </div>
                        {message.isLoading ? (
                          <div className="space-y-4 py-3">
                            <div className="flex items-center gap-2">
                              {[0, 1, 2].map((dot) => (
                                <span
                                  key={dot}
                                className="h-2.5 w-2.5 animate-shimmer rounded-full bg-gradient-to-r from-neon-purple via-neon-blue to-neon-cyan"
                                style={{ animationDelay: `${dot * 140}ms` }}
                                />
                              ))}
                            </div>
                            <div className="space-y-2">
                              <div className="h-3 w-5/6 rounded-full bg-white/10 omni-skeleton" />
                              <div className="h-3 w-3/4 rounded-full bg-white/10 omni-skeleton" />
                              <div className="h-3 w-2/3 rounded-full bg-white/10 omni-skeleton" />
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-5">
                            <MarkdownRenderer content={safeMessageContent(message)} />
                            {badges.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {badges.map((badge) => (
                                  <span
                                    key={badge}
                                    className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-200/75"
                                  >
                                    {badge}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                            <div className="flex justify-end gap-3 text-violet-200/80">
                              <button className="rounded-full border border-white/8 bg-white/[0.04] p-2 transition hover:border-neon-purple/40 hover:text-white" onClick={() => setUiNotice('Feedback positivo registrado apenas no estado local da interface.')} type="button">
                                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M14 9V5a3 3 0 0 0-3-3L6 9v11h10.28a2 2 0 0 0 1.98-1.72l1.2-8A2 2 0 0 0 17.48 8H15a1 1 0 0 0-1 1Z" /></svg>
                              </button>
                              <button className="rounded-full border border-white/8 bg-white/[0.04] p-2 transition hover:border-neon-blue/40 hover:text-white" onClick={() => setUiNotice('Feedback negativo registrado apenas no estado local da interface.')} type="button">
                                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M10 15v4a3 3 0 0 0 3 3l5-7V4H7.72a2 2 0 0 0-1.98 1.72l-1.2 8A2 2 0 0 0 6.52 16H9a1 1 0 0 0 1-1Z" /></svg>
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </motion.article>
                )
              })}
            </AnimatePresence>
          </div>
        </div>

        <motion.div
          className="rounded-[24px] border border-[rgba(180,109,255,0.16)] bg-[linear-gradient(180deg,rgba(14,15,34,0.8),rgba(10,11,27,0.74))] p-2 shadow-[0_20px_48px_rgba(0,0,0,0.34)] backdrop-blur-xl"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.12 }}
        >
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              {BOTTOM_TABS.map((tab) => {
                const active = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    className={`rounded-2xl border px-3 py-1.5 text-xs transition ${
                      active
                        ? `bg-neon-purple/14 text-white ${getGlowState('active')}`
                        : `border-white/8 bg-white/[0.03] text-slate-300 hover:text-white ${getGlowState('hover')}`
                    }`}
                    onClick={() => selectBottomTab(tab.id)}
                    onFocus={() => selectBottomTab(tab.id)}
                    type="button"
                  >
                    {tab.label}
                  </button>
                )
              })}
            </div>
            <button
              className={`rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-200 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`}
              onClick={() => setUiNotice('Logs detalhados vivem na rota de observabilidade. Use o item Logs da sidebar para abrir o painel completo.')}
              type="button"
            >
              Logs
            </button>
          </div>

          {uiNotice || moduleCopy ? (
            <div className="mb-3 rounded-[22px] border border-white/8 bg-black/15 px-4 py-2.5">
              <div className="grid gap-2 text-sm text-slate-200/80">
                {uiNotice ? (
                  <div className="flex items-start justify-between gap-3 rounded-2xl border border-neon-cyan/20 bg-neon-cyan/8 px-3 py-2.5 text-slate-100">
                    <span>{uiNotice}</span>
                    <button
                      className={`rounded-full border border-white/10 px-2 text-xs text-slate-200 transition hover:text-white ${getGlowState('hover')}`}
                      onClick={clearUiNotice}
                      type="button"
                    >
                      OK
                    </button>
                  </div>
                ) : null}
                {moduleCopy ? (
                  <div className="rounded-2xl border border-white/8 bg-white/[0.035] px-3 py-2.5">
                    <div className="mb-2 text-xs uppercase tracking-[0.24em] text-neon-cyan/80">
                      {activeSidebarItem.replaceAll('-', ' ')}
                    </div>
                    <div className="grid gap-2">
                      {moduleCopy.slice(0, 1).map((line) => (
                        <div key={line} className="flex items-start gap-3">
                          <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-neon-cyan" />
                          <span>{line}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className={`flex items-center gap-2 rounded-[22px] border bg-[rgba(7,8,22,0.78)] px-2.5 py-1.5 transition-all duration-300 ${inputFocused ? `${getGlowState('focus')} scale-[1.005]` : 'border-white/10'}`}>
            <button
              aria-label="Adicionar ação"
              className={`rounded-full border border-white/12 bg-white/[0.05] p-2 text-slate-200 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`}
              onClick={() => setUiNotice('Ações adicionais ainda não possuem backend dedicado nesta branch.')}
              type="button"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
            </button>
            <button
              aria-label="Anexar arquivo"
              className={`rounded-full border border-white/12 bg-white/[0.05] p-2 text-slate-200 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`}
              onClick={() => setUiNotice('Anexos ainda não estão conectados ao runtime nesta branch.')}
              type="button"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m21.4 11.6-8.8 8.8a6 6 0 0 1-8.5-8.5l9.4-9.4a4 4 0 0 1 5.7 5.7l-9.4 9.4a2 2 0 0 1-2.8-2.8l8.8-8.8" /></svg>
            </button>
            <textarea
              className={`flex-1 resize-none rounded-[20px] border border-neon-purple/20 bg-[rgba(11,15,34,0.92)] px-4 py-2 text-sm text-white outline-none placeholder:text-violet-200/40 transition-all duration-300 ${inputFocused ? 'min-h-[52px]' : 'min-h-[40px]'}`}
              onChange={(event) => onChange(event.target.value)}
              onBlur={() => setInputFocused(false)}
              onFocus={() => setInputFocused(true)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  if (canSend) {
                    onSubmit()
                  }
                }
              }}
              placeholder="Digite uma mensagem..."
              value={input}
            />
            <button aria-label="Entrada por voz" className={`rounded-full border border-white/12 bg-white/[0.05] p-2 text-slate-200 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`} onClick={() => setUiNotice('Microfone ainda não está conectado a um runtime de voz nesta branch.')} type="button">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 18a3 3 0 0 0 3-3V8a3 3 0 1 0-6 0v7a3 3 0 0 0 3 3Z" /><path d="M19 11v4a7 7 0 0 1-14 0v-4M12 22v-3" /></svg>
            </button>
            <button
              className={`rounded-full px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] transition ${
                canSend
                  ? `bg-[linear-gradient(135deg,rgba(181,109,255,0.92),rgba(78,164,255,0.92))] text-white hover:scale-[1.01] active:translate-y-px ${getGlowState('active')}`
                  : 'cursor-not-allowed bg-white/[0.08] text-slate-400'
              }`}
              disabled={!canSend || loading}
              onClick={onSubmit}
              type="button"
            >
              {loading ? '...' : 'Enviar'}
            </button>
          </div>

          {error ? (
            <div className="mt-1.5 flex justify-end text-sm">
              <div className="max-w-[420px] text-right text-[11px] leading-4 text-rose-300">
                {error}
              </div>
            </div>
          ) : null}
        </motion.div>
      </div>
    </div>
  )
}
