import { FormEvent, useEffect, useMemo, useState } from 'react'
import { getBrowserSupabaseClient } from './utils/supabase/client'
import type {
  ChatApiRequest,
  ChatApiResponse,
  ChatMessage,
  FeedbackApiRequest,
  FeedbackValue,
} from './types'

const STORAGE_KEY = 'omini-chat-history'
const API_BASE_URL = import.meta.env.VITE_API_URL?.trim() || 'http://localhost:3001'

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    feedback: null,
  }
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState<string>('')
  const supabase = useMemo(() => {
    try {
      return getBrowserSupabaseClient()
    } catch {
      return null
    }
  }, [])

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return

    try {
      setMessages(JSON.parse(raw) as ChatMessage[])
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    if (!supabase) return

    supabase.auth.getSession().then(({ data }) => {
      setUserId(data.session?.user?.id ?? '')
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUserId(session?.user?.id ?? '')
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage = createMessage('user', trimmed)
    setMessages((current) => [...current, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const payload: ChatApiRequest = {
        message: trimmed,
        user_id: userId || undefined,
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
      setMessages((current) => [
        ...current,
        {
          ...createMessage('assistant', data.response),
          turnId: data.turn_id,
          sessionId: data.session_id,
        },
      ])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro inesperado ao enviar mensagem'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  async function sendFeedback(message: ChatMessage, value: FeedbackValue) {
    if (!message.turnId) {
      return
    }

    const text = value === 'down'
      ? window.prompt('Opcional: diga rapidamente o que faltou nessa resposta.', '') ?? ''
      : ''

    const payload: FeedbackApiRequest = {
      turn_id: message.turnId,
      value,
      text: text.trim() || undefined,
      user_id: userId || undefined,
      session_id: message.sessionId,
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
          item.id === message.id
            ? { ...item, feedback: value }
            : item,
        ),
      )
    } catch (err) {
      const messageText = err instanceof Error ? err.message : 'Erro ao enviar feedback'
      setError(messageText)
    }
  }

  function handleClear() {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
    setError(null)
  }

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header className="hero">
          <div>
            <p className="eyebrow">Omni AI Platform</p>
            <h1>Chat web com backend Rust e engine Python</h1>
            <p className="subtitle">
              Base pronta para evoluir para streaming, plugins, voz e uso multiusuario com Supabase.
            </p>
          </div>
          <button className="ghost-button" onClick={handleClear} type="button">
            Limpar historico
          </button>
        </header>

        <section className="messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2>Comece a conversa</h2>
              <p>Envie uma mensagem para testar a integracao completa.</p>
            </div>
          ) : (
            messages.map((message) => (
              <article key={message.id} className={`message-bubble ${message.role}`}>
                <span className="message-role">
                  {message.role === 'user' ? 'Voce' : 'Assistente'}
                </span>
                <p>{message.content}</p>
                {message.role === 'assistant' && message.turnId ? (
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={() => sendFeedback(message, 'up')}
                      disabled={message.feedback === 'up'}
                    >
                      👍
                    </button>
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={() => sendFeedback(message, 'down')}
                      disabled={message.feedback === 'down'}
                    >
                      👎
                    </button>
                  </div>
                ) : null}
              </article>
            ))
          )}

          {loading ? (
            <article className="message-bubble assistant loading">
              <span className="message-role">Assistente</span>
              <p>Processando sua mensagem...</p>
            </article>
          ) : null}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Digite sua mensagem..."
            rows={4}
          />
          <div className="composer-footer">
            {error ? <p className="error-text">{error}</p> : <span />}
            <button className="send-button" disabled={loading} type="submit">
              {loading ? 'Enviando...' : 'Enviar'}
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}

