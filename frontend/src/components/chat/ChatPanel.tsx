import { AnimatePresence, motion } from 'framer-motion'
import { useMemo } from 'react'
import { MarkdownRenderer } from '../MarkdownRenderer'
import type { ChatMessage, RuntimeMetadata } from '../../types'
import {
  BOTTOM_TABS,
  TOP_ACTIONS,
  mockRuntimeState,
  useRuntimeConsoleStore,
} from '../../state/runtimeConsoleStore'

type ExtendedChatMessage = ChatMessage & {
  isLoading?: boolean
  isNew?: boolean
}

type ChatPanelProps = {
  canSend: boolean
  error: string | null
  helperText: string
  input: string
  lastMetadata: RuntimeMetadata | null
  loading: boolean
  messages: ExtendedChatMessage[]
  onChange: (value: string) => void
  onSelectPrompt: (prompt: string) => void
  onSubmit: () => void
  requestState: 'idle' | 'loading' | 'error'
  sessionId: string
}

const PROMPTS = [
  'Como criar um SaaS com validação e execução incremental?',
  'Analise o arquivo package.json e mostre riscos estruturais.',
  'Monte um plano de execução para estabilizar o provider runtime.',
]

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

function panelSummary(tab: 'plano' | 'simulacao' | 'raciocinio', metadata: RuntimeMetadata | null) {
  if (tab === 'plano') {
    return [
      `Objetivo atual: ${mockRuntimeState.currentGoal}`,
      `Estratégia dominante: ${metadata?.runtimeReason ?? mockRuntimeState.strategy}`,
      `Sessão ativa: ${metadata?.sessionId ?? 'local-runtime'}`,
    ]
  }

  if (tab === 'simulacao') {
    return metadata?.matchedTools?.length
      ? metadata.matchedTools.map((tool, index) => `${index + 1}. Caminho avaliado via ${tool}`)
      : mockRuntimeState.rankedDecisions.map((item, index) => `${index + 1}. ${item}`)
  }

  return [
    `Runtime reason: ${metadata?.runtimeReason ?? 'comparative_analysis'}`,
    `Failure class: ${metadata?.failureClass ?? 'none'}`,
    `Inspection: ${metadata?.cognitiveRuntimeInspection ? 'present' : 'not present'}`,
  ]
}

export function ChatPanel({
  canSend,
  error,
  helperText,
  input,
  lastMetadata,
  loading,
  messages,
  onChange,
  onSelectPrompt,
  onSubmit,
  requestState,
  sessionId,
}: ChatPanelProps) {
  const activeAction = useRuntimeConsoleStore((state) => state.activeAction)
  const activeTab = useRuntimeConsoleStore((state) => state.activeTab)
  const setActiveAction = useRuntimeConsoleStore((state) => state.setActiveAction)
  const setActiveTab = useRuntimeConsoleStore((state) => state.setActiveTab)

  const tabSummary = useMemo(() => panelSummary(activeTab, lastMetadata), [activeTab, lastMetadata])

  return (
    <div className="flex h-full min-h-[calc(100vh-3rem)] flex-col gap-5">
      <motion.div
        className="rounded-[32px] border border-white/10 bg-panel-gradient p-4 shadow-neon-blue backdrop-blur-xl"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {TOP_ACTIONS.map((action) => {
            const active = action.id === activeAction
            return (
              <button
                key={action.id}
                className={`flex items-center justify-center gap-2 rounded-[22px] border px-4 py-3 text-sm font-medium transition ${
                  active
                    ? 'border-neon-blue/60 bg-neon-blue/12 text-white shadow-neon-blue'
                    : 'border-white/8 bg-white/[0.04] text-slate-200/80 hover:border-neon-purple/30 hover:text-white'
                }`}
                onClick={() => setActiveAction(action.id)}
                type="button"
              >
                <span className="h-2.5 w-2.5 rounded-full bg-gradient-to-r from-neon-purple to-neon-cyan shadow-[0_0_16px_rgba(81,246,255,0.7)]" />
                {action.label}
              </button>
            )
          })}
        </div>
      </motion.div>

      <div className="flex min-h-0 flex-1 flex-col gap-5">
        <div className="flex items-start justify-end">
          <motion.div
            animate={{ opacity: 1, x: 0 }}
            className="max-w-[72%] rounded-[28px] border border-neon-blue/50 bg-[linear-gradient(135deg,rgba(33,64,180,0.52),rgba(18,26,74,0.96))] px-6 py-4 text-right text-[30px] font-medium tracking-tight text-white shadow-neon-blue"
            initial={{ opacity: 0, x: 18 }}
            transition={{ duration: 0.35, delay: 0.08 }}
          >
            {messages.findLast((message) => message.role === 'user')?.content ?? 'Como criar um SaaS?'}
          </motion.div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden rounded-[32px] border border-white/10 bg-panel-gradient px-5 py-5 shadow-glass-edge backdrop-blur-xl">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.35em] text-slate-400">Hoje</div>
              <div className="mt-1 text-sm text-slate-300/80">Sessão {sessionId}</div>
            </div>
            <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-300">
              {requestState}
            </div>
          </div>

          <div className="flex max-h-[calc(100vh-26rem)] min-h-[340px] flex-col gap-4 overflow-y-auto pr-2">
            <AnimatePresence initial={false}>
              {messages.length === 0 ? (
                <motion.div
                  key="empty"
                  className="grid min-h-[280px] place-items-center rounded-[28px] border border-dashed border-white/10 bg-black/10 px-6 py-10 text-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <div className="max-w-xl">
                    <div className="mb-4 text-[32px] font-semibold tracking-tight text-white">
                      Omni Cognitive Runtime
                    </div>
                    <p className="mb-6 text-base leading-7 text-slate-300/80">
                      Interface operacional para decisão, execução, observação e aprendizado. Use um prompt que force análise, planejamento ou execução real.
                    </p>
                    <div className="flex flex-wrap justify-center gap-3">
                      {PROMPTS.map((prompt) => (
                        <button
                          key={prompt}
                          className="rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-sm text-slate-100 transition hover:border-neon-purple/40 hover:bg-neon-purple/10"
                          onClick={() => onSelectPrompt(prompt)}
                          type="button"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ) : (
                messages.map((message, index) => {
                  const assistant = message.role === 'assistant'
                  const badges = messageBadges(message.metadata)
                  return (
                    <motion.article
                      key={message.id}
                      className={`flex ${assistant ? 'justify-start' : 'justify-end'}`}
                      initial={{ opacity: 0, y: 14 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.28, delay: Math.min(index * 0.04, 0.18) }}
                    >
                      <div
                        className={`max-w-[86%] rounded-[28px] border px-5 py-4 backdrop-blur-xl ${
                          assistant
                            ? 'border-white/10 bg-white/[0.04] text-slate-100 shadow-glass-edge'
                            : 'border-neon-blue/40 bg-[linear-gradient(135deg,rgba(25,58,170,0.76),rgba(15,23,60,0.94))] text-white shadow-neon-blue'
                        }`}
                      >
                        <div className="mb-3 flex items-center justify-between gap-4 text-xs uppercase tracking-[0.32em] text-slate-300/70">
                          <span>{assistant ? 'Omni Runtime' : 'Operator Input'}</span>
                          <span>{new Date(message.createdAt).toLocaleTimeString('pt-BR')}</span>
                        </div>
                        {message.isLoading ? (
                          <div className="flex items-center gap-2 py-3">
                            {[0, 1, 2].map((dot) => (
                              <span
                                key={dot}
                                className="h-2.5 w-2.5 animate-shimmer rounded-full bg-gradient-to-r from-neon-purple via-neon-blue to-neon-cyan"
                                style={{ animationDelay: `${dot * 140}ms` }}
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="space-y-4">
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
                          </div>
                        )}
                      </div>
                    </motion.article>
                  )
                })
              )}
            </AnimatePresence>
          </div>
        </div>

        <motion.div
          className="rounded-[32px] border border-white/10 bg-panel-gradient p-4 shadow-neon-purple backdrop-blur-xl"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.12 }}
        >
          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="flex flex-wrap gap-2">
              {BOTTOM_TABS.map((tab) => {
                const active = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    className={`rounded-2xl border px-4 py-2 text-sm transition ${
                      active
                        ? 'border-neon-purple/50 bg-neon-purple/14 text-white shadow-[0_0_20px_rgba(181,109,255,0.2)]'
                        : 'border-white/8 bg-white/[0.03] text-slate-300 hover:border-neon-blue/30 hover:text-white'
                    }`}
                    onClick={() => setActiveTab(tab.id)}
                    type="button"
                  >
                    {tab.label}
                  </button>
                )
              })}
            </div>
            <button
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-200 transition hover:border-neon-blue/30 hover:text-white"
              onClick={() => useRuntimeConsoleStore.getState().setActiveAction('executar')}
              type="button"
            >
              Logs
            </button>
          </div>

          <div className="mb-4 rounded-[24px] border border-white/8 bg-black/15 px-4 py-3">
            <div className="grid gap-2 text-sm text-slate-200/80">
              {tabSummary.map((line) => (
                <div key={line} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-gradient-to-r from-neon-purple to-neon-cyan shadow-[0_0_10px_rgba(81,246,255,0.6)]" />
                  <span>{line}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-[26px] border border-white/10 bg-black/15 px-4 py-3">
            <button className="rounded-full border border-white/12 bg-white/[0.05] p-3 text-slate-200 transition hover:border-neon-purple/40 hover:text-white" type="button">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 18h.01M8 10a4 4 0 1 1 8 0c0 4-4 4-4 7" /></svg>
            </button>
            <button className="rounded-full border border-white/12 bg-white/[0.05] p-3 text-slate-200 transition hover:border-neon-purple/40 hover:text-white" type="button">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 18a3 3 0 0 0 3-3V8a3 3 0 1 0-6 0v7a3 3 0 0 0 3 3Z" /><path d="M19 11v4a7 7 0 0 1-14 0v-4M12 22v-3" /></svg>
            </button>
            <textarea
              className="min-h-[64px] flex-1 resize-none rounded-[22px] border border-neon-purple/20 bg-[rgba(11,15,34,0.92)] px-5 py-4 text-base text-white outline-none placeholder:text-violet-200/40 focus:border-neon-blue/50 focus:shadow-[0_0_0_1px_rgba(78,164,255,0.18),0_0_26px_rgba(78,164,255,0.14)]"
              onChange={(event) => onChange(event.target.value)}
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
            <button className="rounded-full border border-white/12 bg-white/[0.05] p-3 text-slate-200 transition hover:border-neon-blue/40 hover:text-white" type="button">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 18a3 3 0 0 0 3-3V8a3 3 0 1 0-6 0v7a3 3 0 0 0 3 3Z" /><path d="M19 11v4a7 7 0 0 1-14 0v-4M12 22v-3" /></svg>
            </button>
            <button
              className={`rounded-full px-6 py-4 text-sm font-semibold uppercase tracking-[0.28em] transition ${
                canSend
                  ? 'bg-[linear-gradient(135deg,rgba(181,109,255,0.92),rgba(78,164,255,0.92))] text-white shadow-neon-purple hover:scale-[1.01]'
                  : 'cursor-not-allowed bg-white/[0.08] text-slate-400'
              }`}
              onClick={onSubmit}
              type="button"
            >
              {loading ? '...' : 'Enviar'}
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
            <div className="text-slate-300/70">{helperText}</div>
            {error ? <div className="text-rose-300">{error}</div> : null}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
