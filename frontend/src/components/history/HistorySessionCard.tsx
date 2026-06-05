import type { ConversationSummary } from '../../types'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniStatusDot } from '../ui/OmniStatusDot'

type HistorySessionCardProps = {
  session: ConversationSummary
  active?: boolean
  onClick?: () => void
  className?: string
}

const modeLabels: Record<string, string> = {
  chat: 'Chat',
  pesquisa: 'Pesquisa',
  codigo: 'Código',
  agente: 'Agente',
}

const modeColors: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
  chat: 'info',
  pesquisa: 'success',
  codigo: 'warning',
  agente: 'danger',
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffDays === 0) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    if (diffDays === 1) return 'Ontem'
    if (diffDays < 7) return `${diffDays} dias atrás`
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  } catch {
    return ''
  }
}

export function HistorySessionCard({ session, active = false, onClick, className = '' }: HistorySessionCardProps) {
  return (
    <button
      className={`group flex w-full items-start gap-3 rounded-2xl border px-3 py-2.5 text-left transition ${
        active
          ? 'border-neon-purple/30 bg-neon-purple/10'
          : 'border-white/6 bg-white/[0.02] hover:border-white/12 hover:bg-white/[0.05]'
      } ${className}`.trim()}
      onClick={onClick}
      type="button"
    >
      <OmniStatusDot tone={session.messageCount > 0 ? 'success' : 'inactive'} />

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-slate-100">
            {session.title}
          </span>
          <span className="shrink-0 text-[11px] text-slate-400">{formatDate(session.updatedAt)}</span>
        </div>

        <div className="mt-1 flex items-center gap-2">
          <OmniBadge tone={modeColors[session.mode] ?? 'muted'}>
            {modeLabels[session.mode] ?? session.mode}
          </OmniBadge>
          <span className="text-[11px] text-slate-500">
            {session.messageCount} {session.messageCount === 1 ? 'mensagem' : 'mensagens'}
          </span>
        </div>
      </div>
    </button>
  )
}
