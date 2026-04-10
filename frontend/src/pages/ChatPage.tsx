import { useEffect, useMemo, useState } from 'react'
import { AppShell } from '../components/AppShell'
import { ChatHeader } from '../components/ChatHeader'
import { Composer } from '../components/Composer'
import { MessageList } from '../components/MessageList'
import { Sidebar } from '../components/Sidebar'
import { StatusPanel } from '../components/StatusPanel'
import { fetchHealth, sendOmniMessage } from '../lib/api'
import { API_CONFIGURATION_ERROR, canUseApi } from '../lib/env'
import { bootstrapOmniUser, syncChatSessionToSupabase } from '../lib/omniData'
import type {
  ChatApiResponse,
  ChatMessage,
  ChatMode,
  ChatRequestState,
  ConversationSummary,
  HealthResponse,
  RuntimeMetadata,
  SyncChatStatus,
} from '../types'

type View = 'chat' | 'dashboard'

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
  messages: ChatMessage[]
  requestState: ChatRequestState
  sessionId: string
}

function buildSessionId() {
  return `${DEFAULT_SESSION_PREFIX}-${crypto.randomUUID().slice(0, 8)}`
}

function createMessage(
  role: ChatMessage['role'],
  content: string,
  options?: {
    metadata?: RuntimeMetadata
    requestState?: ChatMessage['requestState']
  },
): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
    metadata: options?.metadata,
    requestState: options?.requestState,
  }
}

function normalizeMetadata(response: ChatApiResponse, previousSessionId: string): RuntimeMetadata {
  return {
    sessionId: response.session_id ?? previousSessionId,
    source: response.source,
    matchedCommands: response.matched_commands ?? [],
    matchedTools: response.matched_tools ?? [],
    stopReason: response.stop_reason,
    usage: response.usage,
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
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
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
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [requestState, setRequestState] = useState<ChatRequestState>('idle')
  const [sessionId, setSessionId] = useState(buildSessionId)
  const [lastMetadata, setLastMetadata] = useState<RuntimeMetadata | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const apiReady = canUseApi()

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
    if (messages.length === 0) {
      return
    }

    const latestMessage = messages.at(-1)
    const status: SyncChatStatus =
      requestState === 'error'
        ? 'failed'
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
    if (!apiReady) {
      setHealth(null)
      return
    }

    let cancelled = false
    fetchHealth()
      .then((data) => {
        if (!cancelled) {
          setHealth(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [apiReady, requestState])

  const loading = requestState === 'loading'
  const trimmedInput = input.trim()
  const canSend = Boolean(trimmedInput) && !loading

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

  async function handleSubmit() {
    const prompt = input.trim()
    if (!prompt || loading) {
      return
    }

    if (!apiReady) {
      setRequestState('error')
      setError(API_CONFIGURATION_ERROR || 'A API do Omni nao esta configurada neste ambiente.')
      return
    }

    const previousInput = input
    setMessages((current) => [...current, createMessage('user', prompt)])
    setInput('')
    setError(null)
    setRequestState('loading')

    try {
      const data = await sendOmniMessage(prompt, { sessionId })
      const metadata = normalizeMetadata(data, sessionId)
      const responseText = data.response?.trim()

      if (!responseText) {
        throw new Error('O backend retornou uma resposta vazia.')
      }

      setSessionId(metadata.sessionId ?? sessionId)
      setLastMetadata(metadata)
      setMessages((current) => [
        ...current,
        createMessage('assistant', responseText, {
          metadata,
          requestState: 'completed',
        }),
      ])
      setRequestState('idle')
    } catch (err) {
      setInput(previousInput)
      setRequestState('error')
      setError(
        err instanceof Error
          ? err.message
          : 'Falha inesperada ao consultar o runtime.',
      )
      setMessages((current) => [
        ...current,
        createMessage(
          'assistant',
          'Nao foi possivel completar a execucao agora. Revise a configuracao da API ou tente novamente em instantes.',
          { requestState: 'failed' },
        ),
      ])
    }
  }

  function handleNewConversation() {
    const nextSessionId = buildSessionId()
    setMessages([])
    setInput('')
    setError(null)
    setLastMetadata(null)
    setRequestState('idle')
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
        <StatusPanel
          apiConfigured={apiReady}
          error={error}
          health={health}
          lastMetadata={lastMetadata}
          modeLabel={MODE_LABELS[mode]}
          requestState={requestState}
          sessionId={sessionId}
        />
      )}
    >
      <div className="chat-page">
        <ChatHeader loading={loading} mode={mode} sessionId={sessionId} />
        <section className="chat-surface panel-card">
          <MessageList
            loading={loading}
            messages={messages}
            onSelectPrompt={(prompt) => setInput(prompt)}
          />
        </section>
        <Composer
          canSend={canSend}
          error={error}
          helperText={helperText}
          loading={loading}
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
