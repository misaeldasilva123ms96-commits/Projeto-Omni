import { useCallback, useEffect, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { TokenUsageChart } from '../components/tokens/TokenUsageChart'
import { TokenUsageOverview } from '../components/tokens/TokenUsageOverview'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { ErrorNotice } from '../components/ui/ErrorNotice'
import { OmniEmptyState } from '../components/ui/OmniEmptyState'
import { PageHero } from '../components/ui/PageHero'
import { fetchTokenUsage } from '../lib/omniData'
import type { ChatMode, ConversationSummary, TokenUsageSummary } from '../types'
import { redactRuntimeDebugText } from '../lib/runtimeDebugSanitizer'

type TokenUsagePageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function TokenUsagePage({ mode, onChangeMode, onChangeView, renderShell, view }: TokenUsagePageProps) {
  const [summary, setSummary] = useState<TokenUsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setError(null)

    fetchTokenUsage()
      .then((data) => {
        if (!cancelled) {
          setSummary(data)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error
            ? redactRuntimeDebugText(err.message)
            : 'Falha ao carregar uso de tokens')
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
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

  const content = useCallback(() => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-16 text-sm text-slate-400">
          Carregando uso de tokens...
        </div>
      )
    }

    if (error) {
      return <ErrorNotice message={error} className="mx-auto mt-8 max-w-lg" />
    }

    if (!summary) {
      return (
        <OmniEmptyState
          description="O uso de tokens aparecerá após algumas requisições."
          icon={(
            <svg className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
              <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Z" />
              <path d="M12 6v6l4 2" />
            </svg>
          )}
          title="Nenhum dado de uso disponível."
        />
      )
    }

    return (
      <>
        <TokenUsageOverview summary={summary} className="mb-6" />
        <TokenUsageChart summary={summary} />
      </>
    )
  }, [loading, error, summary])

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Monitoramento"
          title="Uso de Tokens"
          subtitle="Acompanhe o consumo de tokens por requisição e ao longo do tempo"
          className="mb-6"
        />

        {content()}
      </div>,
    { sidebar },
  )
}
