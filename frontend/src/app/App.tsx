import { useEffect, useState } from 'react'
import { OmniShell } from '../components/shell/OmniShell'
import { ObservabilityAuthGate } from '../components/ObservabilityAuthGate'
import { ChatPage } from '../pages/ChatPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ProjectsPage } from '../pages/ProjectsPage'
import { ProviderCenterPage } from '../pages/ProviderCenterPage'
import { TokenUsagePage } from '../pages/TokenUsagePage'
import { SettingsView } from '../pages/SettingsPage'
import {
  PUTER_DEV_ROUTE_PATH,
  PuterDevRoutePage,
  canShowPuterDevRoute,
} from '../pages/PuterDevRoutePage'
import type { ChatMode } from '../types'

export type View = 'chat' | 'dashboard' | 'history' | 'observability' | 'projects' | 'provider-center' | 'token-usage' | 'settings' | 'puter-dev'

export function resolveViewFromPath(
  pathname: string,
  puterDevRouteVisible = canShowPuterDevRoute(),
): View {
  if (pathname === PUTER_DEV_ROUTE_PATH && puterDevRouteVisible) {
    return 'puter-dev'
  }
  if (pathname === '/settings') {
    return 'settings'
  }
  if (pathname === '/observability') {
    return 'observability'
  }
  if (pathname === '/dashboard') {
    return 'dashboard'
  }
  if (pathname === '/history') {
    return 'history'
  }
  if (pathname === '/projects') {
    return 'projects'
  }
  if (pathname === '/provider-center') {
    return 'provider-center'
  }
  if (pathname === '/token-usage') {
    return 'token-usage'
  }
  return 'chat'
}

function pathForView(view: View) {
  if (view === 'settings') {
    return '/settings'
  }
  if (view === 'observability') {
    return '/observability'
  }
  if (view === 'dashboard') {
    return '/dashboard'
  }
  if (view === 'history') {
    return '/history'
  }
  if (view === 'projects') {
    return '/projects'
  }
  if (view === 'provider-center') {
    return '/provider-center'
  }
  if (view === 'token-usage') {
    return '/token-usage'
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

  return (
    <OmniShell>
      {view === 'dashboard' ? (
        <DashboardPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'observability' ? (
        <ObservabilityAuthGate
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'token-usage' ? (
        <TokenUsagePage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'provider-center' ? (
        <ProviderCenterPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'projects' ? (
        <ProjectsPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'settings' ? (
        <SettingsView
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      ) : view === 'puter-dev' ? (
        <PuterDevRoutePage />
      ) : (
        <ChatPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={handleChangeView}
          view={view}
        />
      )}
    </OmniShell>
  )
}
