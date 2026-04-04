import type { SessionSummary } from '../types'

type SidebarProps = {
  activeSessionId: string
  isLoading: boolean
  isOpen: boolean
  onClose: () => void
  onNewChat: () => void
  onSelectSession: (sessionId: string) => void
  onSignOut: () => void
  sessions: SessionSummary[]
  userId: string
}

export default function Sidebar({
  activeSessionId,
  isLoading,
  isOpen,
  onClose,
  onNewChat,
  onSelectSession,
  onSignOut,
  sessions,
  userId,
}: SidebarProps) {
  return (
    <>
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-panel">
          <div className="sidebar-brand">
            <div>
              <p className="sidebar-kicker">Omini AI</p>
              <h2>Galaxy Console</h2>
            </div>
            <button
              aria-label="Fechar menu"
              className="sidebar-close"
              onClick={onClose}
              type="button"
            >
              x
            </button>
          </div>

          <button className="new-chat-button" onClick={onNewChat} type="button">
            + Nova conversa
          </button>

          <div className="sidebar-section">
            <p className="sidebar-label">Histórico</p>
            <nav className="sidebar-nav">
              {isLoading ? (
                <div className="sidebar-status">Carregando conversas...</div>
              ) : sessions.length === 0 ? (
                <div className="sidebar-status">Nenhuma conversa ainda.</div>
              ) : (
                sessions.map((session) => (
                  <button
                    className={`sidebar-link session-link ${session.session_id === activeSessionId ? 'active' : ''}`}
                    key={session.session_id}
                    onClick={() => onSelectSession(session.session_id)}
                    type="button"
                  >
                    <strong>{session.title || session.preview || 'Nova conversa'}</strong>
                    <span>{session.preview || 'Sem mensagens ainda'}</span>
                  </button>
                ))
              )}
            </nav>
          </div>

          <div className="sidebar-spacer" />

          <div className="sidebar-section">
            <p className="sidebar-label">Perfil</p>
            <div className="sidebar-profile-card">
              <span className="sidebar-avatar">O</span>
              <div>
                <strong>{userId ? 'Usuário autenticado' : 'Sessão local'}</strong>
                <p>{userId || 'Entre com Supabase para memória por usuário'}</p>
              </div>
            </div>
          </div>

          <div className="sidebar-section">
            <button className="sidebar-link" type="button">
              Configurações
            </button>
            <button className="sidebar-link danger" onClick={onSignOut} type="button">
              Sair
            </button>
          </div>
        </div>
      </aside>

      <button
        aria-hidden={!isOpen}
        className={`sidebar-backdrop ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
        tabIndex={isOpen ? 0 : -1}
        type="button"
      />
    </>
  )
}
