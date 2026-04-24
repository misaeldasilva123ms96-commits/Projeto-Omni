import { useEffect, useMemo, useRef, useState } from 'react'
import { ChatHeader } from '../components/chat/ChatHeader'
import { Composer } from '../components/chat/Composer'
import { EmptyState } from '../components/chat/EmptyState'
import { MessageBubble } from '../components/chat/MessageBubble'
import { AppShell } from '../components/layout/AppShell'
import { Sidebar } from '../components/layout/Sidebar'
import { CognitivePanel } from '../components/status/CognitivePanel'
import { chatApiResponseToUi, sendOmniMessage } from '../features/chat'
import { publicStatusV1ToUiRuntimeStatus } from '../features/runtime'
import { useCognitiveTelemetry } from '../hooks/useCognitiveTelemetry'
import { useObservabilitySnapshot } from '../hooks/useObservabilitySnapshot'
import { API_CONFIGURATION_ERROR, canUseApi } from '../lib/env'
import { bootstrapOmniUser, syncChatSessionToSupabase } from '../lib/omniData'
import { supabase } from '../lib/supabase'
import { ChatRequestError } from '../lib/api/chat'
import type {
  ChatMessage,
  ChatMode,
  ChatRequestState,
  ConversationSummary,
  RuntimeMetadata,
  SyncChatStatus,
} from '../types'
import type { UiChatResponse } from '../types/ui/chat'
import type { UiRuntimeStatus } from '../types/ui/runtime'

type View = 'chat' | 'dashboard' | 'observability'

type ChatPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

const STORAGE_KEY = 'omini-chat-state-v3'
const DEFAULT_SESSION_PREFIX = 'sessao'

type StoredChatState = {
  input: string
  lastMetadata: RuntimeMetadata | null
  messages: ExtendedChatMessage[]
  requestState: ChatRequestState
  sessionId: string
}

type ExtendedChatMessage = ChatMessage & {
  isLoading?: boolean
  isNew?: boolean
}

function buildSessionId() {
  return `${DEFAULT_SESSION_PREFIX}-${crypto.randomUUID().slice(0, 8)}`
}

function createMessage(
  role: ChatMessage['role'],
  content: string,
  options?: {
    id?: string
    isLoading?: boolean
    isNew?: boolean
    metadata?: RuntimeMetadata
    requestState?: ChatMessage['requestState']
  },
): ExtendedChatMessage {
  return {
    id: options?.id ?? crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
    isLoading: options?.isLoading,
    isNew: options?.isNew,
    metadata: options?.metadata,
    requestState: options?.requestState,
  }
}

function normalizeMetadata(ui: UiChatResponse, previousSessionId: string): RuntimeMetadata {
  return {
    sessionId: ui.sessionId ?? previousSessionId,
    source: ui.source,
    matchedCommands: ui.commands,
    matchedTools: ui.tools,
    stopReason: ui.stopReason,
    executionTier: ui.executionTier,
    wireHealth: ui.wireHealth,
    runtimeSessionVersion: ui.runtimeSessionVersion,
    conversationId: ui.conversationId,
    chatApiVersion: ui.chatApiVersion,
    usage: ui.usage
      ? {
        input_tokens: ui.usage.inputTokens,
        output_tokens: ui.usage.outputTokens,
      }
      : undefined,
    runtimeMode: ui.runtimeMode,
    runtimeReason: ui.runtimeReason,
    cognitiveRuntimeInspection: ui.cognitiveRuntimeInspection,
    signals: ui.signals,
    executionPathUsed: ui.executionPathUsed,
    fallbackTriggered: ui.fallbackTriggered,
    compatibilityExecutionActive: ui.compatibilityExecutionActive,
    providerActual: ui.providerActual,
    providerFailed: ui.providerFailed,
    failureClass: ui.failureClass,
    failureReason: ui.failureReason,
    executionProvenance: ui.executionProvenance,
    providers: ui.providers,
    providerDiagnostics: ui.providerDiagnostics,
    providerFallbackOccurred: ui.providerFallbackOccurred,
    noProviderAvailable: ui.noProviderAvailable,
    toolExecution: ui.toolExecution,
    toolDiagnostics: ui.toolDiagnostics,
    error: ui.error,
  }
}

function getConversationTitle(messages: ChatMessage[]) {
  const firstUserMessage = messages.find((message) => message.role === 'user')
  if (!firstUserMessage) {
    return 'Nova conversa'
  }

  return firstUserMessage.content.slice(0, 56) || 'Nova conversa'
}

function loadStoredState(): StoredChatState {
  const baseState: StoredChatState = {
    input: '',
    lastMetadata: null,
    messages: [],
    requestState: 'idle',
    sessionId: buildSessionId(),
  }

  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return baseState
  }

  try {
    const parsed = JSON.parse(raw) as Partial<StoredChatState>
    return {
      ...baseState,
      ...parsed,
      input: typeof parsed.input === 'string' ? parsed.input : '',
      lastMetadata: parsed.lastMetadata ?? null,
      messages: Array.isArray(parsed.messages)
        ? parsed.messages.map((message) => ({
          ...message,
          isLoading: false,
          isNew: false,
        }))
        : [],
      requestState: parsed.requestState === 'loading' ? 'idle' : parsed.requestState ?? 'idle',
      sessionId: typeof parsed.sessionId === 'string' && parsed.sessionId ? parsed.sessionId : buildSessionId(),
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return baseState
  }
}

const MODE_LABELS: Record<ChatMode, string> = {
  agente: 'Agente',
  chat: 'Chat',
  codigo: 'Codigo',
  pesquisa: 'Pesquisa',
}

export function ChatPage({ mode, onChangeMode, onChangeView, view }: ChatPageProps) {
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [requestState, setRequestState] = useState<ChatRequestState>('idle')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(buildSessionId)
  const [lastMetadata, setLastMetadata] = useState<RuntimeMetadata | null>(null)
  const [telemetryTick, setTelemetryTick] = useState(0)
  const [observabilityAuth, setObservabilityAuth] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const apiReady = canUseApi()
  const telemetry = useCognitiveTelemetry(apiReady, telemetryTick)
  const healthUi: UiRuntimeStatus | null = telemetry.publicRuntime
    ? publicStatusV1ToUiRuntimeStatus(telemetry.publicRuntime)
    : null
  const {
    snapshot: observabilitySnapshot,
    loading: observabilityLoading,
    error: observabilityError,
  } = useObservabilitySnapshot(apiReady && observabilityAuth)

  useEffect(() => {
    const stored = loadStoredState()
    setInput(stored.input)
    setLastMetadata(stored.lastMetadata)
    setMessages(stored.messages)
    setRequestState(stored.requestState)
    setSessionId(stored.sessionId)
  }, [])

  useEffect(() => {
    void bootstrapOmniUser().catch((bootstrapError) => {
      console.warn('Unable to bootstrap Omni user state in Supabase.', bootstrapError)
    })
  }, [])

  useEffect(() => {
    const snapshot: StoredChatState = {
      input,
      lastMetadata,
      messages,
      requestState,
      sessionId,
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  }, [input, lastMetadata, messages, requestState, sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (messages.length === 0) {
      return
    }

    const latestMessage = messages.at(-1)
    const status: SyncChatStatus =
      requestState === 'error'
        ? 'failed'
        : latestMessage?.requestState === 'degraded'
          ? 'degraded'
          : latestMessage?.requestState === 'completed'
            ? 'completed'
            : requestState === 'loading'
              ? 'active'
              : 'idle'

    void syncChatSessionToSupabase({
      externalSessionId: sessionId,
      messages,
      metadata: lastMetadata,
      mode,
      status,
      summary: lastMetadata?.source,
      title: getConversationTitle(messages),
    }).catch((syncError) => {
      console.warn('Unable to sync chat session to Supabase.', syncError)
    })
  }, [lastMetadata, messages, mode, requestState, sessionId])

  useEffect(() => {
    let cancelled = false
    void supabase.auth.getSession().then(({ data }) => {
      if (!cancelled) {
        setObservabilityAuth(Boolean(data.session?.access_token))
      }
    })
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      setObservabilityAuth(Boolean(session?.access_token))
    })
    return () => {
      cancelled = true
      subscription.subscription.unsubscribe()
    }
  }, [])

  const loading = requestState === 'loading'
  const trimmedInput = input.trim()
  const canSend = Boolean(trimmedInput) && !isLoading

  const conversations = useMemo<ConversationSummary[]>(() => [{
    id: sessionId,
    title: getConversationTitle(messages),
    updatedAt: messages.at(-1)?.createdAt ?? new Date().toISOString(),
    messageCount: messages.length,
    mode,
  }], [messages, mode, sessionId])

  const helperText = apiReady
    ? 'Rust bridge to Python cognition and Node runtime.'
    : API_CONFIGURATION_ERROR || 'A API do Omni nao esta configurada. Voce ainda pode escrever e preparar a mensagem.'

  function sleep(ms: number) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms)
    })
  }

  async function sendWithRetry(prompt: string, options: { sessionId: string }, maxRetries = 2) {
    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
      try {
        return await sendOmniMessage(prompt, options)
      } catch (networkError) {
        if (attempt < maxRetries) {
          await sleep(1200)
          continue
        }
        throw networkError
      }
    }

    throw new Error('Failed to send message after retries.')
  }

  function markMessageAsCompleted(messageId: string) {
    setMessages((current) => current.map((message) => (
      message.id === messageId ? { ...message, isNew: false } : message
    )))
  }

  async function handleSubmit() {
    const prompt = input.trim()
    if (!prompt || isLoading) {
      return
    }

    if (!apiReady) {
      setRequestState('error')
      setError(API_CONFIGURATION_ERROR || 'A API do Omni nao esta configurada neste ambiente.')
      return
    }

    const previousInput = input
    const loadingMessageId = crypto.randomUUID()
    setMessages((current) => [
      ...current,
      createMessage('user', prompt),
      createMessage('assistant', '...', {
        id: loadingMessageId,
        isLoading: true,
        isNew: false,
      }),
    ])
    setInput('')
    setError(null)
    setRequestState('loading')
    setIsLoading(true)

    try {
      const data = await sendWithRetry(prompt, { sessionId })
      console.debug('[omni:raw]', data)
      const ui = chatApiResponseToUi(data)
      const metadata = normalizeMetadata(ui, sessionId)
      const displayText = ui.text.trim() || '...'
      const assistantOutcome = ui.wireHealth === 'degraded' ? ('degraded' as const) : ('completed' as const)

      setSessionId(metadata.sessionId ?? sessionId)
      setLastMetadata(metadata)
      setMessages((current) => [
        ...current.map((message) => (
          message.id === loadingMessageId
            ? {
              ...message,
              content: displayText,
              isLoading: false,
              isNew: true,
              requestState: assistantOutcome,
            }
            : message
        )),
      ])
      setRequestState('idle')
      setTelemetryTick((value) => value + 1)
    } catch (err) {
      setInput(previousInput)
      setRequestState('error')
      const chatErrorPayload = err instanceof ChatRequestError ? err.payload : undefined
      const failedUi = chatErrorPayload ? chatApiResponseToUi(chatErrorPayload) : undefined
      const failedMetadata = failedUi ? normalizeMetadata(failedUi, sessionId) : null
      if (failedMetadata) {
        setSessionId(failedMetadata.sessionId ?? sessionId)
        setLastMetadata(failedMetadata)
      }
      setError(
        err instanceof Error
          ? err.message
          : 'Falha inesperada ao consultar o runtime.',
      )
      setMessages((current) => current.map((message) => (
        message.id === loadingMessageId
          ? {
            ...message,
            content: failedUi?.text?.trim() || 'Não consegui processar sua mensagem. Tente novamente.',
            isLoading: false,
            isNew: true,
            requestState: 'failed' as const,
            metadata: failedMetadata ?? undefined,
          }
          : message
      )))
    } finally {
      setIsLoading(false)
    }
  }

  function handleNewConversation() {
    const nextSessionId = buildSessionId()
    setMessages([])
    setInput('')
    setError(null)
    setLastMetadata(null)
    setRequestState('idle')
    setIsLoading(false)
    setSessionId(nextSessionId)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      input: '',
      lastMetadata: null,
      messages: [],
      requestState: 'idle',
      sessionId: nextSessionId,
    } satisfies StoredChatState))
  }

  return (
    <AppShell
      sidebar={(
        <Sidebar
          activeConversationId={sessionId}
          conversations={conversations}
          mode={mode}
          onChangeMode={onChangeMode}
          onNewConversation={handleNewConversation}
          onSelectView={onChangeView}
          view={view}
        />
      )}
      statusPanel={(
        <CognitivePanel
          apiConfigured={apiReady}
          chatError={error}
          health={healthUi}
          lastMetadata={lastMetadata}
          modeLabel={MODE_LABELS[mode]}
          observabilityCanRequest={observabilityAuth}
          observabilityError={observabilityError}
          observabilityLoading={observabilityLoading}
          observabilitySnapshot={observabilityAuth ? observabilitySnapshot : null}
          requestState={requestState}
          sessionId={sessionId}
          telemetry={telemetry}
        />
      )}
    >
      <div className="chat-page omni-chat-page">
        <ChatHeader loading={loading} mode={mode} sessionId={sessionId} />
        <section className="chat-surface panel-card omni-chat-surface">
          <section className="messages omni-message-list">
            {messages.length === 0 ? (
              <EmptyState onSelectPrompt={(prompt) => setInput(prompt)} />
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onTypingComplete={markMessageAsCompleted}
                />
              ))
            )}
            <div ref={bottomRef} />
          </section>
        </section>
        <Composer
          canSend={canSend}
          error={error}
          helperText={helperText}
          loading={isLoading}
          onChange={setInput}
          onSubmit={() => {
            void handleSubmit()
          }}
          value={input}
        />
      </div>
    </AppShell>
  )
}

