import type { ChatMessage } from '../types'
import { EmptyState } from './EmptyState'
import { MessageBubble } from './MessageBubble'

type MessageListProps = {
  loading: boolean
  messages: ChatMessage[]
  onSelectPrompt: (prompt: string) => void
}

export function MessageList({
  loading,
  messages,
  onSelectPrompt,
}: MessageListProps) {
  return (
    <section className="messages">
      {messages.length === 0 ? (
        <EmptyState onSelectPrompt={onSelectPrompt} />
      ) : (
        messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))
      )}

      {loading ? (
        <article className="message-bubble assistant loading">
          <div className="message-meta">
            <span className="message-role">Omni</span>
            <span>agora</span>
          </div>
          <p className="loading-copy">Sincronizando contexto e processando resposta...</p>
        </article>
      ) : null}
    </section>
  )
}
