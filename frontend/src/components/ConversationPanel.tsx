import type { ChatMessage } from '../types'

type ConversationPanelProps = {
  loading: boolean
  messages: ChatMessage[]
}

export function ConversationPanel({
  loading,
  messages,
}: ConversationPanelProps) {
  return (
    <section className="messages">
      {messages.length === 0 ? (
        <div className="empty-state">
          <h2>Ready to talk to Omni</h2>
          <p>
            Use the hardened Rust bridge and inspect how the runtime responds in real
            time.
          </p>
        </div>
      ) : (
        messages.map((message) => (
          <article
            key={message.id}
            className={`message-bubble ${message.role}`}
          >
            <span className="message-role">
              {message.role === 'user' ? 'Operator' : 'Omni'}
            </span>
            <p>{message.content}</p>
          </article>
        ))
      )}

      {loading ? (
        <article className="message-bubble assistant loading">
          <span className="message-role">Omni</span>
          <p>Coordinating the runtime...</p>
        </article>
      ) : null}
    </section>
  )
}
