import { useEffect, useState } from 'react'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { ObservabilityPage } from './pages/ObservabilityPage'
import type { ChatMode } from './types'

type View = 'chat' | 'dashboard' | 'observability'

function resolveViewFromPath(pathname: string): View {
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
  return '/'
}

export default function App() {
  const [view, setView] = useState<View>(() => resolveViewFromPath(window.location.pathname))
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
      <ObservabilityPage
        mode={mode}
        onChangeMode={setMode}
        onChangeView={handleChangeView}
        view={view}
      />
    )
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
