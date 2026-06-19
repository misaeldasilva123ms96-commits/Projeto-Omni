import { useCallback, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { ProviderCenterOverview } from '../components/providers/ProviderCenterOverview'
import { ProviderHealthCard } from '../components/providers/ProviderHealthCard'
import { ObservabilityContextBanner } from '../components/observability/ObservabilityContextBanner'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { ErrorNotice } from '../components/ui/ErrorNotice'
import { OmniButton } from '../components/ui/OmniButton'
import { PageHero } from '../components/ui/PageHero'
import { useProviders } from '../features/settings/hooks/useProviders'
import type { ChatMode, ConversationSummary } from '../types'
import {
  filterProvidersByContext,
  hasObservabilityContext,
  parseObservabilityContext,
  pickObservabilityContext,
} from '../lib/observabilityContext'

const DEFAULT_PROVIDERS = [
  { provider: 'openai', configured: false, updated_at: null },
  { provider: 'openrouter', configured: false, updated_at: null },
  { provider: 'anthropic', configured: false, updated_at: null },
  { provider: 'gemini', configured: false, updated_at: null },
  { provider: 'groq', configured: false, updated_at: null },
]

type ProviderCenterPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function ProviderCenterPage({ mode, onChangeMode, onChangeView, renderShell, view }: ProviderCenterPageProps) {
  const {
    actionError, clearActionError, createProvider, editProvider,
    lastTestResult, loading, providers, removeProvider,
    runConnectionTest, submitting, testingProvider,
  } = useProviders()

  const [apiKeys, setApiKeys] = useState<Record<string, string>>({})

  const resolvedProviders = providers.length > 0
    ? DEFAULT_PROVIDERS.map((defaultProvider) => {
        const match = providers.find((item) => item.provider === defaultProvider.provider)
        return match ?? defaultProvider
      })
    : DEFAULT_PROVIDERS
  const context = pickObservabilityContext(
    parseObservabilityContext(window.location.search),
    ['provider', 'request_id', 'trace_id'],
  )
  const hasContext = hasObservabilityContext(context)
  const visibleProviders = filterProvidersByContext(resolvedProviders, context)

  const handleApiKeyChange = useCallback((provider: string, value: string) => {
    setApiKeys((prev) => ({ ...prev, [provider]: value }))
  }, [])

  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Integrações"
          title="Centro de Provedores"
          subtitle="Gerencie credenciais e conexões com provedores de IA"
          className="mb-6"
        />

        <ObservabilityContextBanner context={context} />

        <ProviderCenterOverview
          providers={visibleProviders}
          lastTestResult={lastTestResult}
          className="mb-6"
        />

        {actionError ? (
          <div className="mb-4 flex items-start justify-between gap-3">
            <ErrorNotice message={actionError} className="flex-1" />
            <OmniButton variant="ghost" onClick={clearActionError}>
              OK
            </OmniButton>
          </div>
        ) : null}

        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-400">Carregando provedores...</div>
        ) : hasContext && visibleProviders.length === 0 ? (
          <div className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-8 text-center text-sm text-slate-400">
            Contexto recebido, mas não há dados disponíveis para este filtro.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {visibleProviders.map((item) => (
              <ProviderHealthCard
                key={item.provider}
                provider={item}
                testResult={lastTestResult?.provider === item.provider ? lastTestResult : null}
                submitting={submitting}
                testing={testingProvider === item.provider}
                apiKey={apiKeys[item.provider] ?? ''}
                onApiKeyChange={(value) => handleApiKeyChange(item.provider, value)}
                onSave={(apiKey) => {
                  createProvider(item.provider, apiKey).catch(() => {})
                }}
                onUpdate={(apiKey) => {
                  editProvider(item.provider, apiKey).catch(() => {})
                }}
                onRemove={() => {
                  removeProvider(item.provider).catch(() => {})
                }}
                onTest={(apiKey) => {
                  runConnectionTest(item.provider, apiKey)
                }}
              />
            ))}
          </div>
        )}
      </div>,
    { sidebar },
  )
}
