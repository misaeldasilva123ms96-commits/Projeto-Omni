import { API_BASE_URL } from '../lib/env'
import type { ChatMode, ConversationSummary } from '../types'
import { ModeSwitcher } from './ModeSwitcher'

type View = 'chat' | 'dashboard'

type SidebarProps = {
  activeConversationId?: string
  conversations: ConversationSummary[]
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onNewConversation?: () => void
  onSelectView: (view: View) => void
  view: View
}

export function Sidebar({
  activeConversationId,
  conversations,
  mode,
  onChangeMode,
  onNewConversation,
  onSelectView,
  view,
}: SidebarProps) {
  return (
    <div className="sidebar-card">
      <div className="sidebar-brand">
        <div className="brand-mark">O</div>
        <div>
          <p className="eyebrow">Projeto Omni</p>
          <h1>Omni Runtime</h1>
          <p className="sidebar-copy">Cognitive platform for chat, research and engineering workflows.</p>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Workspace sections">
        <button
          className={view === 'chat' ? 'sidebar-nav-button active' : 'sidebar-nav-button'}
          onClick={() => onSelectView('chat')}
          type="button"
        >
          Chat
        </button>
        <button
          className={view === 'dashboard' ? 'sidebar-nav-button active' : 'sidebar-nav-button'}
          onClick={() => onSelectView('dashboard')}
          type="button"
        >
          Runtime
        </button>
      </nav>

      {onNewConversation ? (
        <button className="new-conversation-button" onClick={onNewConversation} type="button">
          Nova conversa
        </button>
      ) : null}

      <ModeSwitcher mode={mode} onChangeMode={onChangeMode} />

      <section className="sidebar-section">
        <p className="sidebar-label">Sessoes locais</p>
        <div className="conversation-list">
          {conversations.length === 0 ? (
            <p className="sidebar-copy">A conversa ativa vai aparecer aqui quando voce começar.</p>
          ) : (
            conversations.map((conversation) => (
              <article
                key={conversation.id}
                className={conversation.id === activeConversationId ? 'conversation-item active' : 'conversation-item'}
              >
                <div className="conversation-title-row">
                  <strong>{conversation.title}</strong>
                  <span>{conversation.mode}</span>
                </div>
                <p>{conversation.messageCount} mensagens</p>
                <small>{new Date(conversation.updatedAt).toLocaleString('pt-BR')}</small>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="sidebar-section">
        <p className="sidebar-label">Infra</p>
        <div className="sidebar-detail">
          <span>API</span>
          <strong>{API_BASE_URL || 'Nao configurada'}</strong>
        </div>
      </section>
    </div>
  )
}
