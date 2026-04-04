import type { ChatMessage as ChatMessageType, FeedbackValue } from '../types'

type ChatMessageProps = {
  message: ChatMessageType
  onFeedback: (message: ChatMessageType, value: FeedbackValue) => void
}

function FeedbackIcon({ type }: { type: 'up' | 'down' }) {
  return type === 'up' ? (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M14 9V5.5C14 4.12 13.28 3 12.4 3c-.5 0-.93.28-1.2.72L7.9 9H5c-1.1 0-2 .9-2 2v7c0 1.1.9 2 2 2h8.2c.83 0 1.58-.5 1.9-1.27l2.54-6.18A2 2 0 0 0 17.8 11H15a1 1 0 0 1-1-1Z" fill="currentColor" />
      <path d="M19 11h2v9h-2z" fill="currentColor" />
    </svg>
  ) : (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M10 15v3.5c0 1.38.72 2.5 1.6 2.5.5 0 .93-.28 1.2-.72L16.1 15H19c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-8.2c-.83 0-1.58.5-1.9 1.27L6.36 11.45A2 2 0 0 0 6.2 13H9a1 1 0 0 1 1 1Z" fill="currentColor" />
      <path d="M3 4h2v9H3z" fill="currentColor" />
    </svg>
  )
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
            aria-label="Feedback positivo"
            className={`message-action ${message.feedback === 'up' ? 'active' : ''}`}
            onClick={() => onFeedback(message, 'up')}
            type="button"
          >
            <FeedbackIcon type="up" />
          </button>
          <button
            aria-label="Feedback negativo"
            className={`message-action ${message.feedback === 'down' ? 'active' : ''}`}
            onClick={() => onFeedback(message, 'down')}
            type="button"
          >
            <FeedbackIcon type="down" />
          </button>
        </div>
      ) : null}
    </article>
  )
}
