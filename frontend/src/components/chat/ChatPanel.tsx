import { AnimatePresence } from 'framer-motion'
import { useMemo, useState } from 'react'
import { MarkdownRenderer } from '../MarkdownRenderer'
import type { ChatMessage, RuntimeMetadata } from '../../types'
import {
  BOTTOM_TABS,
  mockRuntimeState,
  useRuntimeConsoleStore,
} from '../../state/runtimeConsoleStore'
import { getGlowState } from '../../lib/ui/glow'
import { OmniMessageList } from './OmniMessageList'
import { OmniUserMessage } from './OmniUserMessage'
import { OmniAssistantMessage } from './OmniAssistantMessage'
import { OmniSystemNotice } from './OmniSystemNotice'
import { OmniComposer } from './OmniComposer'
import { OmniAttachmentButton } from './OmniAttachmentButton'

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
  if (!metadata) return []
  return [
    metadata.runtimeMode ? `Mode: ${metadata.runtimeMode}` : null,
    metadata.executionPathUsed ? `Path: ${metadata.executionPathUsed}` : null,
    typeof metadata.fallbackTriggered === 'boolean' ? `Fallback: ${metadata.fallbackTriggered ? 'yes' : 'no'}` : null,
    metadata.providerActual ? `Provider: ${metadata.providerActual}` : null,
    metadata.toolExecution?.tool_selected ? `Tool: ${metadata.toolExecution.tool_selected}` : null,
  ].filter((item): item is string => Boolean(item))
}

function sidebarModuleCopy(item: string, metadata: RuntimeMetadata | null) {
  const copies: Record<string, string[]> = {
    historico: [
      'Histórico local ativo: a conversa atual é persistida no navegador.',
      `Último runtime: ${metadata?.runtimeMode ?? 'sem execução registrada nesta sessão.'}`,
    ],
    memoria: [
      'Memória em modo leitura: exibindo status conhecido do runtime sem gravar dados privados.',
    ],
    simulacoes: [
      'Simulações conectadas ao painel inferior. Use a aba Simulação para ver caminhos considerados.',
      `Caminhos disponíveis: ${metadata?.matchedTools?.length ?? mockRuntimeState.pathsConsidered}`,
    ],
    insights: [
      'Insights derivados dos metadados disponíveis.',
      `Failure class atual: ${metadata?.failureClass ?? 'none'}`,
    ],
    logs: [
      'Logs apontam para a superfície de observabilidade do runtime.',
    ],
    'configuracoes-ia': [
      'Configurações IA estão em modo seguro nesta branch.',
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
  const activeSidebarItem = useRuntimeConsoleStore((state) => state.activeSidebarItem)
  const activeTab = useRuntimeConsoleStore((state) => state.activeTab)
  const uiNotice = useRuntimeConsoleStore((state) => state.uiNotice)
  const clearUiNotice = useRuntimeConsoleStore((state) => state.clearUiNotice)
  const selectBottomTab = useRuntimeConsoleStore((state) => state.selectBottomTab)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)

  const moduleCopy = useMemo(() => sidebarModuleCopy(activeSidebarItem, lastMetadata), [activeSidebarItem, lastMetadata])
  const latestUserPrompt = messages.findLast((message) => message.role === 'user')?.content ?? 'Como criar um SaaS?'
  const runtimeActive = loading || requestState === 'loading'

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

          <OmniMessageList
            hasMessages={messages.length > 0}
            emptyState={
              <div className="text-center text-sm text-slate-400">
                Nenhuma mensagem ainda. Comece uma conversa.
              </div>
            }
          >
            <AnimatePresence initial={false}>
              {visibleMessages.map((message, index) => {
                const isUser = message.role === 'user'
                if (isUser) {
                  return <OmniUserMessage key={message.id} message={message} />
                }
                return (
                  <OmniAssistantMessage
                    key={message.id}
                    message={message}
                    getBadges={messageBadges}
                    onCopy={(content) => {
                      navigator.clipboard.writeText(content).catch(() => {})
                      setUiNotice('Resposta copiada para a área de transferência.')
                    }}
                    onRetry={() => {
                      setUiNotice('Reenvio manual ainda não implementado nesta branch.')
                    }}
                  />
                )
              })}
            </AnimatePresence>
          </OmniMessageList>
        </div>

        <OmniComposer
          canSend={canSend}
          error={error}
          loading={loading}
          onChange={onChange}
          onSubmit={onSubmit}
          value={input}
          before={<OmniAttachmentButton onClick={() => setUiNotice('Anexos ainda não estão conectados ao runtime nesta branch.')} />}
          after={
            <button
              aria-label="Entrada por voz"
              className="rounded-full border border-white/12 bg-white/[0.05] p-2 text-slate-200 transition hover:text-white active:translate-y-px"
              onClick={() => setUiNotice('Microfone ainda não está conectado a um runtime de voz nesta branch.')}
              type="button"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 18a3 3 0 0 0 3-3V8a3 3 0 1 0-6 0v7a3 3 0 0 0 3 3Z" /><path d="M19 11v4a7 7 0 0 1-14 0v-4M12 22v-3" /></svg>
            </button>
          }
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
                    type="button"
                  >
                    {tab.label}
                  </button>
                )
              })}
            </div>
            <button
              className={`rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-200 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`}
              onClick={() => setUiNotice('Logs detalhados vivem na rota de observabilidade.')}
              type="button"
            >
              Logs
            </button>
          </div>

          {(uiNotice || moduleCopy) ? (
            <div className="mb-3 rounded-[22px] border border-white/8 bg-black/15 px-4 py-2.5">
              <div className="grid gap-2 text-sm text-slate-200/80">
                {uiNotice ? (
                  <OmniSystemNotice variant="info" onDismiss={clearUiNotice}>
                    {uiNotice}
                  </OmniSystemNotice>
                ) : null}
                {moduleCopy ? (
                  <div className="rounded-2xl border border-white/8 bg-white/[0.035] px-3 py-2.5">
                    <div className="mb-2 text-xs uppercase tracking-[0.24em] text-neon-cyan/80">
                      {activeSidebarItem.replaceAll('-', ' ')}
                    </div>
                    {moduleCopy.slice(0, 1).map((line) => (
                      <div key={line} className="flex items-start gap-3">
                        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-neon-cyan" />
                        <span>{line}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
        </OmniComposer>
      </div>
    </div>
  )
}
