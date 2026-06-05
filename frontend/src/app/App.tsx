import { useEffect, useState } from 'react'
import { ObservabilityAuthGate } from '../components/ObservabilityAuthGate'
import { ChatPage } from '../pages/ChatPage'
import { DashboardPage } from '../pages/DashboardPage'
import {
  PUTER_DEV_ROUTE_PATH,
  PuterDevRoutePage,
  canShowPuterDevRoute,
} from '../pages/PuterDevRoutePage'
import type { ChatMode } from '../types'

export type View = 'chat' | 'dashboard' | 'observability' | 'puter-dev'

export function resolveViewFromPath(
  pathname: string,
  puterDevRouteVisible = canShowPuterDevRoute(),
): View {
  if (pathname === PUTER_DEV_ROUTE_PATH && puterDevRouteVisible) {
    return 'puter-dev'
  }
  if (pathname === '/observability') {
    return 'observability'
  }
  if (pathname === '/dashboard') {
    return 'dashboard'
  }
  return 'chat'
}

function pathForView(view: View) {
  if (view === 'observability') {
    return '/observability'
  }
  if (view === 'dashboard') {
    return '/dashboard'
  }
  if (view === 'puter-dev') {
    return PUTER_DEV_ROUTE_PATH
  }
  return '/'
}

export default function App() {
  const [view, setView] = useState<View>(() =>
    resolveViewFromPath(window.location.pathname),
  )
  const [mode, setMode] = useState<ChatMode>('chat')

  useEffect(() => {
    const handler = () => setView(resolveViewFromPath(window.location.pathname))
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const handleChangeView = (nextView: View) => {
    setView(nextView)
    const nextPath = pathForView(nextView)
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }
  }

  if (view === 'dashboard') {
    return (
      <DashboardPage
        mode={mode}
        onChangeMode={setMode}
        onChangeView={handleChangeView}
        view={view}
      />
    )
  }

  if (view === 'observability') {
    return (
      <ObservabilityAuthGate
        mode={mode}
        onChangeMode={setMode}
        onChangeView={handleChangeView}
        view={view}
      />
    )
  }

  if (view === 'puter-dev') {
    return <PuterDevRoutePage />
  }

  return (
    <ChatPage
      mode={mode}
      onChangeMode={setMode}
      onChangeView={handleChangeView}
      view={view}
    />
  )
}
