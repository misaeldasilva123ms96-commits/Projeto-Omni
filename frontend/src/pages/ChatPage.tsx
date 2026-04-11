import { useEffect, useMemo, useRef, useState } from 'react'
import { AppShell } from '../components/AppShell'
import { ChatHeader } from '../components/ChatHeader'
import { Composer } from '../components/Composer'
import { EmptyState } from '../components/EmptyState'
import { MessageBubble } from '../components/MessageBubble'
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

function extractResponseText(payload: unknown): string {
  if (typeof payload === 'string') {
    try {
      const parsed = JSON.parse(payload) as Record<string, unknown>
      return (
        (typeof parsed?.response === 'string' && parsed.response.trim())
        || (typeof parsed?.message === 'string' && parsed.message.trim())
        || (typeof parsed?.text === 'string' && parsed.text.trim())
        || (typeof parsed?.answer === 'string' && parsed.answer.trim())
        || payload
      )
    } catch {
      return payload
    }
  }

  if (payload !== null && typeof payload === 'object') {
    const p = payload as Record<string, unknown>
    const candidates = ['response', 'message', 'text', 'answer']
    for (const key of candidates) {
      if (typeof p[key] === 'string' && (p[key] as string).trim()) {
        return (p[key] as string).trim()
      }
    }
  }

  return ''
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
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
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
      const metadata = normalizeMetadata(data, sessionId)
      const responseText = extractResponseText(data)
      const displayText = responseText || '...'

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
              requestState: 'completed' as const,
            }
            : message
        )),
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
      setMessages((current) => current.map((message) => (
        message.id === loadingMessageId
          ? {
            ...message,
            content: 'Não consegui processar sua mensagem. Tente novamente.',
            isLoading: false,
            isNew: true,
            requestState: 'failed' as const,
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
          <section className="messages">
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
