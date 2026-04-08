import { FormEvent, useEffect, useState } from 'react'
import { sendOmniMessage } from '../lib/api'
import { API_CONFIGURATION_ERROR, canUseApi } from '../lib/env'
import { Composer } from '../components/Composer'
import { ConversationPanel } from '../components/ConversationPanel'
import type { ChatApiResponse, ChatMessage } from '../types'

const STORAGE_KEY = 'omini-chat-history-v2'

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  }
}

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const apiReady = canUseApi()

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return
    }

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
    if (!trimmed || loading || !apiReady) {
      if (!apiReady) {
        setError(
          API_CONFIGURATION_ERROR
            || 'The Omni API is not configured for this environment.',
        )
      }
      return
    }

    setMessages((current) => [...current, createMessage('user', trimmed)])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const data = (await sendOmniMessage(trimmed)) as ChatApiResponse
      setMessages((current) => [...current, createMessage('assistant', data.response)])
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unexpected error while sending the message.',
      )
    } finally {
      setLoading(false)
    }
  }

  function clearHistory() {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
    setError(null)
  }

  return (
    <section className="page-grid chat-layout">
      <section className="panel-card hero-card">
        <div>
          <p className="eyebrow">Chat surface</p>
          <h2>Operate the live Omni runtime through the hardened Rust bridge.</h2>
          <p className="subtitle">
            This interface preserves conversation state locally, shows runtime errors
            clearly and stays aligned with the backend contract.
          </p>
        </div>
        <button className="ghost-button" onClick={clearHistory} type="button">
          Clear history
        </button>
      </section>

      <section className="panel-card chat-panel">
        <ConversationPanel loading={loading} messages={messages} />
        <Composer
          disabled={!apiReady}
          error={error}
          loading={loading}
          onChange={setInput}
          onSubmit={handleSubmit}
          value={input}
        />
      </section>
    </section>
  )
}
