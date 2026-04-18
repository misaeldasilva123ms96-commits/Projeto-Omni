import type { ChatMode } from '../../types'
import { SectionHeader } from '../ui/SectionHeader'
import { StatusBadge } from '../ui/StatusBadge'

type ChatHeaderProps = {
  loading: boolean
  mode: ChatMode
  sessionId: string
}

const MODE_LABELS: Record<ChatMode, string> = {
  agente: 'Agente',
  chat: 'Chat',
  codigo: 'Codigo',
  pesquisa: 'Pesquisa',
}

export function ChatHeader({ loading, mode, sessionId }: ChatHeaderProps) {
  return (
    <header className="chat-header panel-card omni-chat-header">
      <SectionHeader
        eyebrow="Omni Runtime"
        subtitle="Interface centrada na conversa, com metadados de execucao discretos no painel lateral."
        title={`${MODE_LABELS[mode]} operacional`}
      />
      <div className="chat-header-status">
        <StatusBadge tone={loading ? 'active' : 'default'}>
          {loading ? 'Processando resposta' : 'Pronto'}
        </StatusBadge>
        <StatusBadge tone="muted">Sessao {sessionId}</StatusBadge>
      </div>
    </header>
  )
}
