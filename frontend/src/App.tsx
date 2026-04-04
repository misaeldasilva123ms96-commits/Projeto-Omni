import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import ChatInput from './components/ChatInput'
import ChatMessage from './components/ChatMessage'
import Sidebar from './components/Sidebar'
import type {
  ChatApiRequest,
  ChatApiResponse,
  ChatMessage as ChatMessageType,
  FeedbackApiRequest,
  FeedbackValue,
  SessionDetail,
  SessionSummary,
} from './types'
import { getBrowserSupabaseClient } from './utils/supabase/client'

const API_BASE_URL = import.meta.env.VITE_API_URL?.trim() || 'http://localhost:3001'

function createMessage(
  role: ChatMessageType['role'],
  content: string,
): ChatMessageType {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    feedback: null,
  }
}

function createSessionId(userId: string) {
  const token = crypto.randomUUID()
  if (!userId) {
    return `session-${token}`
  }
  return `session-${userId.replace(/[^a-zA-Z0-9_-]+/g, '-')}-${token}`
}

function buildSessionQuery(userId: string) {
  return userId ? `?user_id=${encodeURIComponent(userId)}` : ''
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const supabase = useMemo(() => {
    try {
      return getBrowserSupabaseClient()
    } catch {
      return null
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  useEffect(() => {
    if (!supabase) {
      const fallbackSessionId = createSessionId('')
      setActiveSessionId(fallbackSessionId)
      void refreshSessions('', fallbackSessionId)
      return
    }

    supabase.auth.getSession().then(({ data }) => {
      const nextUserId = data.session?.user?.id ?? ''
      setUserId(nextUserId)
      const fallbackSessionId = createSessionId(nextUserId)
      setActiveSessionId(fallbackSessionId)
      void refreshSessions(nextUserId, fallbackSessionId)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const nextUserId = session?.user?.id ?? ''
      setUserId(nextUserId)
      const fallbackSessionId = createSessionId(nextUserId)
      setActiveSessionId(fallbackSessionId)
      void refreshSessions(nextUserId, fallbackSessionId)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  async function refreshSessions(nextUserId = userId, fallbackSessionId = activeSessionId) {
    setSessionsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/sessions${buildSessionQuery(nextUserId)}`)
      if (!response.ok) {
        throw new Error(await response.text())
      }

      const data = (await response.json()) as SessionSummary[]
      setSessions(data)

      if (data.length > 0) {
        const targetSessionId = data.some((session) => session.session_id === fallbackSessionId)
          ? fallbackSessionId
          : data[0].session_id
        await loadSession(targetSessionId, nextUserId, data)
      } else {
        setMessages([])
        setActiveSessionId(fallbackSessionId || createSessionId(nextUserId))
      }
    } catch (err) {
      const messageText = err instanceof Error ? err.message : 'Erro ao carregar sessões'
      setError(messageText)
    } finally {
      setSessionsLoading(false)
    }
  }

  async function loadSession(
    sessionId: string,
    nextUserId = userId,
    knownSessions?: SessionSummary[],
  ) {
    setSessionsLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}${buildSessionQuery(nextUserId)}`,
      )
      if (!response.ok) {
        throw new Error(await response.text())
      }

      const data = (await response.json()) as SessionDetail
      setActiveSessionId(data.session_id)
      setMessages(data.messages)
      if (knownSessions) {
        setSessions(knownSessions)
      }
      setSidebarOpen(false)
    } catch (err) {
      const messageText = err instanceof Error ? err.message : 'Erro ao abrir conversa'
      setError(messageText)
    } finally {
      setSessionsLoading(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const sessionId = activeSessionId || createSessionId(userId)
    const userMessage = createMessage('user', trimmed)
    userMessage.sessionId = sessionId

    if (!activeSessionId) {
      setActiveSessionId(sessionId)
    }

    setMessages((current) => [...current, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const payload: ChatApiRequest = {
        message: trimmed,
        user_id: userId || undefined,
        session_id: sessionId,
      }

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const body = await response.text()
        throw new Error(body || 'Falha ao consultar a API')
      }

      const data = (await response.json()) as ChatApiResponse
      setActiveSessionId(data.session_id)
      setMessages((current) => [
        ...current,
        {
          ...createMessage('assistant', data.response),
          turnId: data.turn_id,
          sessionId: data.session_id,
        },
      ])
      await refreshSessions(userId, data.session_id)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erro inesperado ao enviar mensagem'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  async function sendFeedback(
    message: ChatMessageType,
    value: FeedbackValue,
  ) {
    if (!message.turnId) {
      return
    }

    const text =
      value === 'down'
        ? window.prompt(
            'Opcional: diga rapidamente o que faltou nessa resposta.',
            '',
          ) ?? ''
        : ''

    const payload: FeedbackApiRequest = {
      turn_id: message.turnId,
      value,
      text: text.trim() || undefined,
      user_id: userId || undefined,
      session_id: message.sessionId || activeSessionId,
    }

    try {
      const response = await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(await response.text())
      }

      setMessages((current) =>
        current.map((item) =>
          item.id === message.id ? { ...item, feedback: value } : item,
        ),
      )
      await refreshSessions(userId, activeSessionId)
    } catch (err) {
      const messageText =
        err instanceof Error ? err.message : 'Erro ao enviar feedback'
      setError(messageText)
    }
  }

  function handleNewChat() {
    const nextSessionId = createSessionId(userId)
    setActiveSessionId(nextSessionId)
    setMessages([])
    setError(null)
    setSidebarOpen(false)
  }

  async function handleSelectSession(sessionId: string) {
    if (sessionId === activeSessionId) {
      setSidebarOpen(false)
      return
    }
    await loadSession(sessionId)
  }

  async function handleSignOut() {
    if (!supabase) {
      return
    }

    await supabase.auth.signOut()
    setUserId('')
    setSessions([])
    setMessages([])
    setActiveSessionId(createSessionId(''))
    setSidebarOpen(false)
  }

  return (
    <main className="app-shell galaxy-theme">
      <div className="galaxy-overlay" />

      <Sidebar
        activeSessionId={activeSessionId}
        isLoading={sessionsLoading}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onSignOut={handleSignOut}
        sessions={sessions}
        userId={userId}
      />

      <section className="chat-layout">
        <header className="chat-header">
          <div className="chat-header-left">
            <button
              aria-label="Abrir menu"
              className="icon-button mobile-only"
              onClick={() => setSidebarOpen(true)}
              type="button"
            >
              Menu
            </button>
            <div>
              <p className="brand-overline">Omini AI</p>
              <h1>Assistente universal de inteligência</h1>
            </div>
          </div>

          <button className="ghost-button" onClick={handleNewChat} type="button">
            Nova conversa
          </button>
        </header>

        <section className="chat-surface">
          {sessionsLoading ? (
            <div className="empty-state">
              <div className="empty-state-orb" />
              <h2>Carregando conversa</h2>
              <p>Sincronizando histórico da sessão selecionada.</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-orb" />
              <h2>Bem-vindo ao Omini AI</h2>
              <p>
                Explore ideias, estratégias, comparações e decisões com uma
                interface pronta para um SaaS global.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onFeedback={sendFeedback}
              />
            ))
          )}

          {loading ? (
            <article className="chat-message assistant">
              <div className="chat-message-meta">
                <span className="chat-message-role">Omini AI</span>
              </div>
              <div className="message-bubble assistant loading">
                <p>Processando sua mensagem...</p>
              </div>
            </article>
          ) : null}

          <div ref={messagesEndRef} />
        </section>

        <ChatInput
          error={error}
          loading={loading}
          onChange={setInput}
          onSubmit={handleSubmit}
          value={input}
        />
      </section>
    </main>
  )
}
