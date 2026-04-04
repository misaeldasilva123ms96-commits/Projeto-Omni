import type { ChatMessage as ChatMessageType, FeedbackValue } from '../types'

type ChatMessageProps = {
  message: ChatMessageType
  onFeedback: (message: ChatMessageType, value: FeedbackValue) => void
}

export default function ChatMessage({
  message,
  onFeedback,
}: ChatMessageProps) {
  const isAssistant = message.role === 'assistant'

  return (
    <article className={`chat-message ${message.role}`}>
      <div className="chat-message-meta">
        <span className="chat-message-role">
          {isAssistant ? 'Omini AI' : 'Você'}
        </span>
      </div>

      <div className={`message-bubble ${message.role}`}>
        <p>{message.content}</p>
      </div>

      {isAssistant && message.turnId ? (
        <div className="message-actions">
          <button
            className={`message-action ${message.feedback === 'up' ? 'active' : ''}`}
            onClick={() => onFeedback(message, 'up')}
            type="button"
          >
            Up
          </button>
          <button
            className={`message-action ${message.feedback === 'down' ? 'active' : ''}`}
            onClick={() => onFeedback(message, 'down')}
            type="button"
          >
            Down
          </button>
        </div>
      ) : null}
    </article>
  )
}
