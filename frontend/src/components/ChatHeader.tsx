import type { ChatMode } from '../types'

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
    <header className="chat-header panel-card">
      <div>
        <p className="eyebrow">Omni Runtime</p>
        <h2>{MODE_LABELS[mode]} operacional para conversa com o runtime endurecido.</h2>
        <p className="subtitle">
          Interface centrada na conversa, com metadados de execução disponíveis sem
          poluir a resposta principal.
        </p>
      </div>

      <div className="chat-header-status">
        <span className={loading ? 'status-pill active' : 'status-pill'}>
          {loading ? 'Processando resposta' : 'Pronto'}
        </span>
        <span className="status-pill">Sessao {sessionId}</span>
      </div>
    </header>
  )
}
