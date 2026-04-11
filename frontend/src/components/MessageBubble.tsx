import type { ChatMessage } from '../types'
import { MarkdownRenderer } from './MarkdownRenderer'

function safeDisplayText(content: unknown): string {
  if (typeof content === 'string') {
    const trimmed = content.trim()
    if (!trimmed) return '...'

    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        const parsed = JSON.parse(trimmed) as Record<string, unknown>
        const candidates = ['response', 'message', 'text', 'answer']
        for (const key of candidates) {
          if (typeof parsed?.[key] === 'string' && parsed[key].trim()) {
            return parsed[key].trim()
          }
        }
      } catch {
        // not valid JSON, render as-is
      }
    }
    return trimmed
  }

  if (content !== null && typeof content === 'object') {
    const c = content as Record<string, unknown>
    const candidates = ['response', 'message', 'text', 'answer']
    for (const key of candidates) {
      if (typeof c[key] === 'string' && (c[key] as string).trim()) {
        return (c[key] as string).trim()
      }
    }
  }

  return '...'
}

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
      <MarkdownRenderer content={safeDisplayText(message.content)} />
    </article>
  )
}
