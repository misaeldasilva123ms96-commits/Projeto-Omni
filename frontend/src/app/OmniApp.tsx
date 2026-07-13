import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import type { ComponentType } from 'react'
import { OmniShell } from '../components/shell/OmniShell'
import { OmniLoadingState } from '../components/ui/OmniLoadingState'
import type { ChatMode } from '../types'
import {
  pathForView,
  resolveViewFromPath,
  type RenderOmniShell,
  type View,
} from './routes'

const lazyNamed = <T extends Record<string, unknown>, K extends keyof T>(
  loader: () => Promise<T>,
  name: K,
) => lazy(async () => ({ default: (await loader())[name] as ComponentType<any> }))

const ObservabilityAuthGate = lazyNamed(() => import('../components/ObservabilityAuthGate'), 'ObservabilityAuthGate')
const AgentsPage = lazyNamed(() => import('../pages/AgentsPage'), 'AgentsPage')
const ChatPage = lazyNamed(() => import('../pages/ChatPage'), 'ChatPage')
const DashboardPage = lazyNamed(() => import('../pages/DashboardPage'), 'DashboardPage')
const GovernanceCenterPage = lazyNamed(() => import('../pages/GovernanceCenterPage'), 'GovernanceCenterPage')
const LabModePage = lazyNamed(() => import('../pages/LabModePage'), 'LabModePage')
const MemoryCenterPage = lazyNamed(() => import('../pages/MemoryCenterPage'), 'MemoryCenterPage')
const ProjectsPage = lazyNamed(() => import('../pages/ProjectsPage'), 'ProjectsPage')
const ProviderCenterPage = lazyNamed(() => import('../pages/ProviderCenterPage'), 'ProviderCenterPage')
const PuterDevRoutePage = lazyNamed(() => import('../pages/PuterDevRoutePage'), 'PuterDevRoutePage')
const SettingsView = lazyNamed(() => import('../pages/SettingsPage'), 'SettingsView')
const TokenUsagePage = lazyNamed(() => import('../pages/TokenUsagePage'), 'TokenUsagePage')

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

  let page
  if (view === 'dashboard') page = <DashboardPage {...pageProps} />
  if (view === 'observability') {
    page = <ObservabilityAuthGate {...pageProps} />
  }
  if (view === 'token-usage') {
    page = <TokenUsagePage {...pageProps} />
  }
  if (view === 'agents') {
    page = <AgentsPage {...pageProps} />
  }
  if (view === 'governance') {
    page = <GovernanceCenterPage {...pageProps} />
  }
  if (view === 'memory-center') {
    page = <MemoryCenterPage {...pageProps} />
  }
  if (view === 'lab-mode') {
    page = <LabModePage {...pageProps} />
  }
  if (view === 'provider-center') {
    page = <ProviderCenterPage {...pageProps} />
  }
  if (view === 'projects') {
    page = <ProjectsPage {...pageProps} />
  }
  if (view === 'settings') {
    page = renderShell(<SettingsView />)
  }
  if (view === 'puter-dev') {
    page = renderShell(<PuterDevRoutePage />)
  }
  page ??= <ChatPage {...pageProps} />

  return (
    <Suspense fallback={<OmniLoadingState label="Carregando página…" />}>
      {page}
    </Suspense>
  )
}
