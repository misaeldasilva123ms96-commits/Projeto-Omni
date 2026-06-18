import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChatPanel } from '../components/chat/ChatPanel'
import { HistoryPanel } from '../components/history/HistoryPanel'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { RuntimePanel } from '../components/status/RuntimePanel'
import { chatApiResponseToUi, sendOmniMessage } from '../features/chat'
import { publicStatusV1ToUiRuntimeStatus } from '../features/runtime'
import { useCognitiveTelemetry } from '../hooks/useCognitiveTelemetry'
import { ChatRequestError } from '../lib/api/chat'
import { API_CONFIGURATION_ERROR, canUseApi } from '../lib/env'
import { bootstrapOmniUser, fetchChatMessages, fetchChatSessions, syncChatSessionToSupabase } from '../lib/omniData'
import {
  normalizeStoredRuntimeMetadata,
  normalizeUiChatRuntime,
} from '../lib/runtimeNormalizer'
import { useRuntimeConsoleStore, type SidebarItem } from '../state/runtimeConsoleStore'
import type { RenderOmniShell, View } from '../app/App'
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
import type { RuntimeInspectorData } from '../lib/runtimeTypes'

type ChatPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
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

const SIDEBAR_PROMPTS: Partial<Record<SidebarItem, { mode: ChatMode; prompt: string }>> = {
  brainstorm: {
    mode: 'chat',
    prompt: 'Faça um brainstorm estruturado com hipóteses, riscos e próximos passos.',
  },
  'analisar-dados': {
    mode: 'pesquisa',
    prompt: 'Analise os dados disponíveis e destaque padrões, riscos e lacunas.',
  },
  'criar-plano': {
    mode: 'agente',
    prompt: 'Crie um plano de execução incremental com etapas, critérios de validação e riscos.',
  },
  'executar-tarefa': {
    mode: 'agente',
    prompt: 'Prepare a execução desta tarefa, identifique ações necessárias e confirme limitações.',
  },
}

export function ChatPage({ mode, onChangeMode, onChangeView, renderShell, view }: ChatPageProps) {
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [requestState, setRequestState] = useState<ChatRequestState>('idle')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(buildSessionId)
  const [lastMetadata, setLastMetadata] = useState<RuntimeMetadata | null>(null)
  const [lastInspectorData, setLastInspectorData] = useState<RuntimeInspectorData | null>(null)
  const [telemetryTick, setTelemetryTick] = useState(0)
  const [sessions, setSessions] = useState<ConversationSummary[]>([])
  const resetRuntimeConsoleConversation = useRuntimeConsoleStore((state) => state.resetConversation)
  const setConsoleCurrentMode = useRuntimeConsoleStore((state) => state.setCurrentMode)
  const setConsoleIsSending = useRuntimeConsoleStore((state) => state.setIsSending)
  const setConsoleLastError = useRuntimeConsoleStore((state) => state.setLastError)
  const setConsoleRuntimeMetadata = useRuntimeConsoleStore((state) => state.setRuntimeMetadata)
  const setConsoleUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)
  const apiReady = canUseApi()
  const telemetry = useCognitiveTelemetry(apiReady, telemetryTick)
  const healthUi: UiRuntimeStatus | null = telemetry.publicRuntime
    ? publicStatusV1ToUiRuntimeStatus(telemetry.publicRuntime)
    : null

  useEffect(() => {
    const stored = loadStoredState()
    setInput(stored.input)
    setLastMetadata(stored.lastMetadata)
    const storedInspectorData = normalizeStoredRuntimeMetadata(stored.lastMetadata)
    setLastInspectorData(storedInspectorData)
    setConsoleRuntimeMetadata(stored.lastMetadata)
    setMessages(stored.messages)
    setRequestState(stored.requestState)
    setSessionId(stored.sessionId)
  }, [setConsoleRuntimeMetadata])

  useEffect(() => {
    void bootstrapOmniUser().catch((bootstrapError) => {
      console.warn('Unable to bootstrap Omni user state in Supabase.', bootstrapError)
    })
  }, [])

  useEffect(() => {
    fetchChatSessions().then(setSessions).catch(() => {})
  }, [sessionId])

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

  const trimmedInput = input.trim()
  const canSend = Boolean(trimmedInput) && !isLoading

  const conversations = useMemo<ConversationSummary[]>(() => {
    const active: ConversationSummary = {
      id: sessionId,
      title: getConversationTitle(messages),
      updatedAt: messages.at(-1)?.createdAt ?? new Date().toISOString(),
      messageCount: messages.length,
      mode,
    }
    const past = sessions.filter((s) => s.id !== sessionId)
    return [active, ...past]
  }, [messages, mode, sessionId, sessions])

  const handleRestoreSession = useCallback((restoreSessionId: string) => {
    if (restoreSessionId === sessionId) return
    fetchChatMessages(restoreSessionId)
      .then((loadedMessages) => {
        const extended: ExtendedChatMessage[] = loadedMessages.map((msg) => ({
          ...msg,
          isLoading: false,
          isNew: false,
        }))
        setMessages(extended)
        setSessionId(restoreSessionId)
        const restoredMetadata = [...extended].reverse().find((message) => message.metadata)?.metadata ?? null
        const restoredInspectorData = normalizeStoredRuntimeMetadata(restoredMetadata)
        setLastMetadata(restoredMetadata)
        setLastInspectorData(restoredInspectorData)
        setConsoleRuntimeMetadata(restoredMetadata)
        setError(null)
        setRequestState('idle')
        setIsLoading(false)
        setInput('')
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          input: '',
          lastMetadata: restoredMetadata,
          messages: extended,
          requestState: 'idle',
          sessionId: restoreSessionId,
        } satisfies StoredChatState))
      })
      .catch(() => {
        useRuntimeConsoleStore.getState().setUiNotice('Não foi possível restaurar esta sessão.')
      })
  }, [sessionId, setConsoleRuntimeMetadata])

  const helperText = apiReady
    ? 'Rust → Python → Node/Bun → Python → Rust. Runtime truth and execution telemetry preserved.'
    : API_CONFIGURATION_ERROR || 'A API do Omni nao esta configurada. Voce ainda pode preparar a mensagem.'

  function sleep(ms: number) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms)
    })
  }

  async function streamAssistantMessage(messageId: string, text: string, metadata: RuntimeMetadata, requestState: ChatMessage['requestState']) {
    const chunks = text.match(/.{1,28}(\s|$)/g) ?? [text]
    let streamed = ''

    for (const chunk of chunks) {
      streamed += chunk
      setMessages((current) => current.map((message) => (
        message.id === messageId
          ? {
            ...message,
            content: streamed.trimEnd(),
            isLoading: false,
            isNew: true,
            metadata,
            requestState,
          }
          : message
      )))
      await sleep(28)
    }
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
    setConsoleIsSending(true)
    setConsoleLastError(null)

    try {
      const data = await sendWithRetry(prompt, { sessionId })
      const ui = chatApiResponseToUi(data)
      const snapshot = normalizeUiChatRuntime(ui, sessionId)
      const metadata = snapshot.metadata
      const displayText = ui.text.trim() || '...'
      const assistantOutcome = ui.wireHealth === 'degraded' ? ('degraded' as const) : ('completed' as const)

      await sleep(420)
      setSessionId(metadata.sessionId ?? sessionId)
      setLastMetadata(metadata)
      setLastInspectorData(snapshot.inspectorData)
      setConsoleRuntimeMetadata(metadata)
      await streamAssistantMessage(loadingMessageId, displayText, metadata, assistantOutcome)
      setRequestState('idle')
      setTelemetryTick((value) => value + 1)
    } catch (err) {
      setInput(previousInput)
      setRequestState('error')
      const chatErrorPayload = err instanceof ChatRequestError ? err.payload : undefined
      const failedUi = chatErrorPayload ? chatApiResponseToUi(chatErrorPayload) : undefined
      const failedSnapshot = failedUi ? normalizeUiChatRuntime(failedUi, sessionId) : null
      const failedMetadata = failedSnapshot?.metadata ?? null
      if (failedMetadata) {
        setSessionId(failedMetadata.sessionId ?? sessionId)
        setLastMetadata(failedMetadata)
        setLastInspectorData(failedSnapshot?.inspectorData ?? null)
        setConsoleRuntimeMetadata(failedMetadata)
      }
      const safeError =
        err instanceof Error
          ? err.message
          : 'Falha inesperada ao consultar o runtime.'
      setError(safeError)
      setConsoleLastError(safeError)
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
      setConsoleIsSending(false)
    }
  }

  function handleNewConversation() {
    const nextSessionId = buildSessionId()
    setMessages([])
    setInput('')
    setError(null)
    setLastMetadata(null)
    setLastInspectorData(null)
    setRequestState('idle')
    setIsLoading(false)
    setSessionId(nextSessionId)
    resetRuntimeConsoleConversation()
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      input: '',
      lastMetadata: null,
      messages: [],
      requestState: 'idle',
      sessionId: nextSessionId,
    } satisfies StoredChatState))
  }

  function handleSidebarItemSelected(item: SidebarItem) {
    const preset = SIDEBAR_PROMPTS[item]
    if (preset) {
      onChangeMode(preset.mode)
      setConsoleCurrentMode(preset.mode)
      setInput(preset.prompt)
      setConsoleUiNotice(`Preset "${item}" carregado no composer. Revise e envie quando quiser executar.`)
      return
    }

    if (item === 'memoria' || item === 'simulacoes' || item === 'insights' || item === 'configuracoes-ia') {
      setConsoleUiNotice('Este módulo ainda não possui backend dedicado nesta branch, mas a navegação e o estado da interface estão funcionais.')
    }
  }

  const mainContent = view === 'history' ? (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
      <HistoryPanel
        sessions={conversations}
        activeSessionId={sessionId}
        onRestoreSession={handleRestoreSession}
      />
    </div>
  ) : (
    <ChatPanel
      canSend={canSend}
      error={error}
      input={input}
      lastMetadata={lastMetadata}
      loading={isLoading}
      messages={messages}
      onChange={setInput}
      onSubmit={() => {
        void handleSubmit()
      }}
      requestState={requestState}
      sessionId={sessionId}
    />
  )

  return renderShell(mainContent, {
    showRightPanel: view !== 'history',
    sidebar: (
      <OmniSidebar
        activeConversationId={sessionId}
        conversations={conversations}
        mode={mode}
        onChangeMode={onChangeMode}
        onNewConversation={handleNewConversation}
        onRestoreSession={handleRestoreSession}
        onSidebarItemSelected={handleSidebarItemSelected}
        onSelectView={onChangeView}
        view={view}
      />
    ),
    rightPanel: view === 'history' ? undefined : (
      <RuntimePanel
        health={healthUi}
        inspectorData={lastInspectorData}
        lastMetadata={lastMetadata}
        modeLabel={MODE_LABELS[mode]}
        requestState={requestState}
        sessionId={sessionId}
      />
    ),
  })
}
