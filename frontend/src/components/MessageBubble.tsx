import type { ChatMessage } from '../types'
import { MarkdownRenderer } from './MarkdownRenderer'
import { SystemBadges } from './SystemBadges'

export function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message-bubble ${message.role}`}>
      <div className="message-meta">
        <span className="message-role">
          {message.role === 'user'
            ? 'Voce'
            : message.role === 'assistant'
              ? 'Omni'
              : 'Sistema'}
        </span>
        <time>{new Date(message.createdAt).toLocaleTimeString('pt-BR')}</time>
      </div>
      <MarkdownRenderer content={message.content} />
      {message.role === 'assistant' ? <SystemBadges metadata={message.metadata} /> : null}
    </article>
  )
}
