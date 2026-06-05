import { useMemo, useState } from 'react'
import type { ChatMode, ConversationSummary } from '../../types'
import { HistoryFilters } from './HistoryFilters'
import { HistorySessionCard } from './HistorySessionCard'
import { HistorySessionDetail } from './HistorySessionDetail'

type HistoryPanelProps = {
  sessions: ConversationSummary[]
  activeSessionId?: string
  onRestoreSession: (sessionId: string) => void
  className?: string
}

export function HistoryPanel({ sessions, activeSessionId, onRestoreSession, className = '' }: HistoryPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [modeFilter, setModeFilter] = useState<ChatMode | null>(null)
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest')
  const [selectedSession, setSelectedSession] = useState<ConversationSummary | null>(null)

  const filteredSessions = useMemo(() => {
    let result = sessions

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter((s) => s.title.toLowerCase().includes(q))
    }

    if (modeFilter) {
      result = result.filter((s) => s.mode === modeFilter)
    }

    result = [...result].sort((a, b) => {
      const diff = new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      return sortOrder === 'newest' ? diff : -diff
    })

    return result
  }, [sessions, searchQuery, modeFilter, sortOrder])

  if (selectedSession) {
    return (
      <HistorySessionDetail
        session={selectedSession}
        onClose={() => setSelectedSession(null)}
        onRestore={() => {
          onRestoreSession(selectedSession.id)
          setSelectedSession(null)
        }}
        className={className}
      />
    )
  }

  return (
    <div className={`flex flex-col gap-4 ${className}`.trim()}>
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">Histórico de Sessões</h2>
        <span className="text-xs text-slate-400">{sessions.length} sessões</span>
      </div>

      <HistoryFilters
        onSearchChange={setSearchQuery}
        onModeFilter={setModeFilter}
        onSortChange={setSortOrder}
      />

      {filteredSessions.length === 0 ? (
        <div className="flex items-center justify-center py-10 text-sm text-slate-400">
          {sessions.length === 0
            ? 'Nenhuma sessão encontrada. Envie uma mensagem para começar.'
            : 'Nenhuma sessão corresponde aos filtros.'}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {filteredSessions.map((session) => (
            <HistorySessionCard
              key={session.id}
              session={session}
              active={session.id === activeSessionId}
              onClick={() => setSelectedSession(session)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
