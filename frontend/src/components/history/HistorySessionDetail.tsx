import { useEffect, useState } from 'react'
import type { ChatMessage, ConversationSummary } from '../../types'
import { fetchChatMessages } from '../../lib/omniData'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniSkeleton } from '../ui/OmniSkeleton'

type HistorySessionDetailProps = {
  session: ConversationSummary
  onRestore?: () => void
  onClose?: () => void
  className?: string
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

export function HistorySessionDetail({ session, onRestore, onClose, className = '' }: HistorySessionDetailProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchChatMessages(session.id)
      .then(setMessages)
      .catch(() => setMessages([]))
      .finally(() => setLoading(false))
  }, [session.id])

  return (
    <div className={`flex max-h-[80vh] flex-col rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,34,0.92),rgba(10,11,27,0.88))] px-5 py-4 shadow-[0_22px_50px_rgba(0,0,0,0.36)] backdrop-blur-xl ${className}`.trim()}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-white">{session.title}</h3>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
            <span>{formatDate(session.updatedAt)}</span>
            <span>·</span>
            <span>{session.messageCount} mensagens</span>
          </div>
        </div>

        <div className="flex shrink-0 gap-2">
          {onRestore ? (
            <button
              className="rounded-2xl border border-neon-cyan/30 bg-neon-cyan/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-neon-cyan transition hover:bg-neon-cyan/20"
              onClick={onRestore}
              type="button"
            >
              Restaurar
            </button>
          ) : null}
          {onClose ? (
            <button
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300 transition hover:text-white"
              onClick={onClose}
              type="button"
            >
              Fechar
            </button>
          ) : null}
        </div>
      </div>

      <div className="-mx-5 flex-1 overflow-y-auto px-5">
        {loading ? (
          <div className="space-y-3 py-4">
            {[1, 2, 3, 4].map((i) => (
              <OmniSkeleton key={i} className="h-12 w-full rounded-2xl" />
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-slate-400">
            Nenhuma mensagem encontrada para esta sessão.
          </div>
        ) : (
          <div className="space-y-3 py-2">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`rounded-2xl border px-4 py-3 ${
                  msg.role === 'user'
                    ? 'ml-8 border-blue-500/20 bg-blue-500/8'
                    : 'mr-8 border-white/8 bg-white/[0.03]'
                }`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <OmniBadge tone={msg.role === 'user' ? 'info' : 'muted'}>
                    {msg.role === 'user' ? 'Você' : 'Omni'}
                  </OmniBadge>
                  <span className="text-[10px] text-slate-500">
                    {formatDate(msg.createdAt)}
                  </span>
                </div>
                <p className="whitespace-pre-wrap text-sm text-slate-200">
                  {msg.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
