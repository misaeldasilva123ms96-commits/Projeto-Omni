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
            <div className="sidebar-brand-lockup">
              <div className="sidebar-logo" aria-hidden="true">
                <span className="sidebar-logo-ring" />
                <span className="sidebar-logo-core" />
              </div>
              <div>
                <p className="sidebar-kicker">Omini AI</p>
                <h2>Galaxy Console</h2>
              </div>
            </div>
            <button
              aria-label="Fechar menu"
              className="sidebar-close"
              onClick={onClose}
              type="button"
            >
              ×
            </button>
          </div>

          <button className="new-chat-button" onClick={onNewChat} type="button">
            <span className="new-chat-plus">+</span>
            <span>Nova conversa</span>
          </button>

          <div className="sidebar-section">
            <p className="sidebar-label">Histórico</p>
            <nav className="sidebar-nav">
              {isLoading ? (
                <div className="sidebar-status">Carregando conversas...</div>
              ) : sessions.length === 0 ? (
                <div className="sidebar-status">Nenhuma conversa ainda.</div>
              ) : (
                sessions.map((session, index) => (
                  <button
                    className={`sidebar-link session-link ${session.session_id === activeSessionId ? 'active' : ''}`}
                    key={session.session_id}
                    onClick={() => onSelectSession(session.session_id)}
                    type="button"
                  >
                    <span className="session-index">{String(index + 1).padStart(2, '0')}</span>
                    <div className="session-copy">
                      <strong>{session.title || session.preview || 'Nova conversa'}</strong>
                      <span>{session.preview || 'Sem mensagens ainda'}</span>
                    </div>
                  </button>
                ))
              )}
            </nav>
          </div>

          <div className="sidebar-spacer" />

          <div className="sidebar-section sidebar-bottom-links">
            <div className="sidebar-profile-card">
              <span className="sidebar-avatar">O</span>
              <div>
                <strong>{userId ? 'Usuário autenticado' : 'Sessão local'}</strong>
                <p>{userId || 'Entre com Supabase para memória por usuário'}</p>
              </div>
            </div>

            <button className="sidebar-link sidebar-action" type="button">
              Perfil
            </button>
            <button className="sidebar-link sidebar-action" type="button">
              Configurações
            </button>
            <button className="sidebar-link danger sidebar-action" onClick={onSignOut} type="button">
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
