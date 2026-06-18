import { useCallback, useEffect, useState } from 'react'
import { ObservabilityAuthGate } from '../components/ObservabilityAuthGate'
import { OmniShell } from '../components/shell/OmniShell'
import { AgentsPage } from '../pages/AgentsPage'
import { ChatPage } from '../pages/ChatPage'
import { DashboardPage } from '../pages/DashboardPage'
import { GovernanceCenterPage } from '../pages/GovernanceCenterPage'
import { LabModePage } from '../pages/LabModePage'
import { MemoryCenterPage } from '../pages/MemoryCenterPage'
import { ProjectsPage } from '../pages/ProjectsPage'
import { ProviderCenterPage } from '../pages/ProviderCenterPage'
import { PuterDevRoutePage } from '../pages/PuterDevRoutePage'
import { SettingsView } from '../pages/SettingsPage'
import { TokenUsagePage } from '../pages/TokenUsagePage'
import type { ChatMode } from '../types'
import {
  pathForView,
  resolveViewFromPath,
  type RenderOmniShell,
  type View,
} from './routes'

export function OmniApp() {
  const [view, setView] = useState<View>(() =>
    resolveViewFromPath(window.location.pathname),
  )
  const [mode, setMode] = useState<ChatMode>('chat')

  useEffect(() => {
    const handler = () => setView(resolveViewFromPath(window.location.pathname))
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const handleChangeView = useCallback((nextView: View) => {
    setView(nextView)
    const nextPath = pathForView(nextView)
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }
  }, [])

  const renderShell = useCallback<RenderOmniShell>((content, options) => (
    <OmniShell {...options}>{content}</OmniShell>
  ), [])

  const pageProps = {
    mode,
    onChangeMode: setMode,
    onChangeView: handleChangeView,
    renderShell,
    view,
  }

  if (view === 'dashboard') {
    return <DashboardPage {...pageProps} />
  }
  if (view === 'observability') {
    return <ObservabilityAuthGate {...pageProps} />
  }
  if (view === 'token-usage') {
    return <TokenUsagePage {...pageProps} />
  }
  if (view === 'agents') {
    return <AgentsPage {...pageProps} />
  }
  if (view === 'governance') {
    return <GovernanceCenterPage {...pageProps} />
  }
  if (view === 'memory-center') {
    return <MemoryCenterPage {...pageProps} />
  }
  if (view === 'lab-mode') {
    return <LabModePage {...pageProps} />
  }
  if (view === 'provider-center') {
    return <ProviderCenterPage {...pageProps} />
  }
  if (view === 'projects') {
    return <ProjectsPage {...pageProps} />
  }
  if (view === 'settings') {
    return renderShell(<SettingsView />)
  }
  if (view === 'puter-dev') {
    return renderShell(<PuterDevRoutePage />)
  }

  return <ChatPage {...pageProps} />
}
