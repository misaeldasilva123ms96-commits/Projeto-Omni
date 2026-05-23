type View = 'chat' | 'dashboard' | 'observability'

type AppHeaderProps = {
  activeView: View
  apiBaseUrl: string
  onChangeView: (view: View) => void
}

export function AppHeader({
  activeView,
  apiBaseUrl,
  onChangeView,
}: AppHeaderProps) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Omni Runtime Platform</p>
        <h1>Professional interface for the Rust, Python and Node cognitive stack.</h1>
      </div>

      <div className="topbar-actions">
        <nav className="nav-tabs" aria-label="Primary">
          <button
            className={activeView === 'chat' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => onChangeView('chat')}
            type="button"
          >
            Chat
          </button>
          <button
            className={activeView === 'dashboard' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => onChangeView('dashboard')}
            type="button"
          >
            Dashboard
          </button>
          <button
            className={activeView === 'observability' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => onChangeView('observability')}
            type="button"
          >
            Observability
          </button>
        </nav>
        <div className="status-chip">
          <span className="status-dot" />
          {apiBaseUrl || 'API not configured'}
        </div>
      </div>
    </header>
  )
}
