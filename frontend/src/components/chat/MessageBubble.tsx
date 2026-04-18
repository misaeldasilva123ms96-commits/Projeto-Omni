import type { ChatMessage } from '../../types'
import { useTypewriter } from '../../hooks/useTypewriter'
import { MarkdownRenderer } from '../MarkdownRenderer'

type BubbleMessage = ChatMessage & {
  isLoading?: boolean
  isNew?: boolean
}

type MessageBubbleProps = {
  message: BubbleMessage
  onTypingComplete?: (messageId: string) => void
}

const BUBBLE_ANIMATION_CSS = `
@keyframes omni-bubble-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@keyframes omni-bubble-pulse {
  0%, 100% { transform: translateY(0); opacity: 0.35; }
  50% { transform: translateY(-2px); opacity: 1; }
}
`

function safeDisplayText(content: unknown): string {
  if (typeof content === 'string') {
    const trimmed = content.trim()
    if (!trimmed) return '...'

    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        const parsed = JSON.parse(trimmed) as Record<string, unknown>
        const candidates = ['response', 'message', 'text', 'answer']
        for (const key of candidates) {
          if (typeof parsed?.[key] === 'string' && (parsed[key] as string).trim()) {
            return (parsed[key] as string).trim()
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

export function MessageBubble({ message, onTypingComplete }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant'
  const safeText = safeDisplayText(message.content)
  const shouldType = isAssistant && message.isNew && !message.isLoading
  const { displayed, isTyping } = useTypewriter(shouldType ? safeText : '', {
    onComplete: shouldType ? () => onTypingComplete?.(message.id) : undefined,
  })
  const visibleText = shouldType ? displayed : safeText

  const articleStyle = {
    alignSelf: isAssistant ? 'flex-start' : 'flex-end',
    display: 'flex',
    gap: '0.75rem',
    justifyContent: isAssistant ? 'flex-start' : 'flex-end',
    width: '100%',
  } as const

  const bubbleStyle = {
    background: isAssistant ? 'rgba(148, 163, 184, 0.14)' : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
    border: isAssistant ? '1px solid rgba(148, 163, 184, 0.18)' : '1px solid rgba(37, 99, 235, 0.3)',
    borderRadius: '1.25rem',
    boxShadow: isAssistant ? '0 10px 30px rgba(15, 23, 42, 0.08)' : '0 12px 32px rgba(37, 99, 235, 0.22)',
    color: isAssistant ? 'var(--color-text-primary, #0f172a)' : '#ffffff',
    maxWidth: 'min(720px, 82%)',
    padding: '0.95rem 1rem',
  } as const

  const avatarStyle = {
    alignItems: 'center',
    background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
    borderRadius: '999px',
    color: '#ffffff',
    display: 'inline-flex',
    flexShrink: 0,
    fontSize: '14px',
    fontWeight: 600,
    height: '30px',
    justifyContent: 'center',
    marginTop: '0.25rem',
    width: '30px',
  } as const

  return (
    <article style={articleStyle}>
      <style>{BUBBLE_ANIMATION_CSS}</style>
      {isAssistant ? (
        <div aria-hidden="true" style={avatarStyle}>
          O
        </div>
      ) : null}
      <div style={bubbleStyle}>
        <div className="message-meta" style={{ marginBottom: '0.5rem' }}>
          <span className="message-role">
            {isAssistant ? 'Omni' : message.role === 'user' ? 'Voce' : 'Sistema'}
          </span>
          <time>{new Date(message.createdAt).toLocaleTimeString('pt-BR')}</time>
        </div>
        {message.isLoading ? (
          <div aria-label="Omni respondendo" style={{ display: 'flex', gap: '0.35rem', padding: '0.2rem 0' }}>
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                style={{
                  animation: `omni-bubble-pulse 1s ease-in-out ${dot * 0.2}s infinite`,
                  background: isAssistant ? '#2563eb' : 'rgba(255,255,255,0.92)',
                  borderRadius: '999px',
                  display: 'inline-block',
                  height: '0.5rem',
                  width: '0.5rem',
                }}
              />
            ))}
          </div>
        ) : (
          <div style={{ alignItems: 'flex-end', display: 'flex', gap: '0.15rem' }}>
            <div style={{ minWidth: 0 }}>
              <MarkdownRenderer content={visibleText || '...'} />
            </div>
            {isTyping ? (
              <span
                aria-hidden="true"
                style={{
                  animation: 'omni-bubble-blink 1s step-end infinite',
                  color: isAssistant ? '#2563eb' : 'rgba(255,255,255,0.92)',
                  fontWeight: 700,
                  lineHeight: 1,
                  marginBottom: '0.25rem',
                }}
              >
                ▋
              </span>
            ) : null}
          </div>
        )}
      </div>
    </article>
  )
}
