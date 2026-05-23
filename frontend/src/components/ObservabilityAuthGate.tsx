import { useState } from 'react'
import { ObservabilityPage } from '../pages/ObservabilityPage'
import { PUBLIC_APP_URL, canUseSupabase } from '../lib/env'
import { supabase } from '../lib/supabase'
import { useRequireAuth } from '../hooks/useRequireAuth'
import type { ChatMode } from '../types'

type View = 'chat' | 'dashboard' | 'observability'

type ObservabilityAuthGateProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

export function ObservabilityAuthGate(props: ObservabilityAuthGateProps) {
  const { session, loading } = useRequireAuth()
  const [authError, setAuthError] = useState<string | null>(null)

  const handleSignIn = async () => {
    setAuthError(null)
    const redirectTo = `${PUBLIC_APP_URL}/observability`
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo,
      },
    })

    if (error) {
      setAuthError(error.message)
    }
  }

  if (loading) {
    return (
      <section className="dashboard-page">
        <section className="panel-card hero-card dashboard-hero">
          <div>
            <p className="eyebrow">Operator authentication</p>
            <h2>Checking your Supabase session before opening observability.</h2>
            <p className="subtitle">The panel stays hidden until operator access is confirmed.</p>
          </div>
          <div className="hero-meta">
            <span className="status-pill">Loading</span>
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
            <p className="eyebrow">Operator authentication</p>
            <h2>Observability panel requires operator access. Sign in to continue.</h2>
            <p className="subtitle">
              Access to live cognitive traces and memory snapshots is restricted to authenticated operators.
            </p>
          </div>
          <div className="hero-meta">
            <button
              className="ghost-button status-pill active"
              disabled={!canUseSupabase()}
              onClick={() => {
                void handleSignIn()
              }}
              type="button"
            >
              Sign in with Google
            </button>
            {authError ? <span className="status-pill danger">{authError}</span> : null}
          </div>
        </section>
      </section>
    )
  }

  return <ObservabilityPage {...props} />
}
