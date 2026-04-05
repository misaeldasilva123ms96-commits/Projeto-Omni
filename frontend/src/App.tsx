import { FormEvent, useEffect, useState } from 'react'
import type { ChatApiResponse, ChatMessage } from './types'

const STORAGE_KEY = 'omini-chat-history'
const API_URL = 'http://10.0.2.2:3001/chat'

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  }
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: trimmed }),
      })

      if (!response.ok) {
        const body = await response.text()
        throw new Error(body || 'Falha ao consultar a API')
      }

      const data = (await response.json()) as ChatApiResponse
      setMessages((current) => [
        ...current,
        createMessage('assistant', data.response),
      ])
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erro inesperado ao enviar mensagem'
      setError(message)
    } finally {
      setLoading(false)
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
              Base pronta para evoluir para streaming, plugins, voz e APK Android.
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
              <article
                key={message.id}
                className={`message-bubble ${message.role}`}
              >
                <span className="message-role">
                  {message.role === 'user' ? 'Voce' : 'Assistente'}
                </span>
                <p>{message.content}</p>
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
