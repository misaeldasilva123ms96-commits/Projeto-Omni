import { SettingsView } from '../../pages/SettingsPage'
import { useRequireAuth } from '../../hooks/useRequireAuth'
import type { ChatMode } from '../../types'
import type { View } from '../../app/App'

type SettingsAuthGateProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

export function SettingsAuthGate({ mode, onChangeMode, onChangeView, view }: SettingsAuthGateProps) {
  const { session, loading } = useRequireAuth()

  if (loading) {
    return (
      <section className="dashboard-page">
        <section className="panel-card hero-card dashboard-hero">
          <div>
            <p className="eyebrow">Autenticação</p>
            <h2>Verificando sessão antes de abrir as configurações.</h2>
          </div>
          <div className="hero-meta">
            <span className="status-pill">Carregando</span>
          </div>
        </section>
      </section>
    )
  }

  if (!session) {
    return (
      <section className="dashboard-page">
        <section className="panel-card hero-card dashboard-hero">
          <div>
            <p className="eyebrow">Autenticação</p>
            <h2>Configurações de provedores exigem acesso autenticado.</h2>
          </div>
          <div className="hero-meta">
            <span className="status-pill danger">Acesso restrito</span>
          </div>
        </section>
      </section>
    )
  }

  return <SettingsView mode={mode} onChangeMode={onChangeMode} onChangeView={onChangeView} view={view} />
}
