import { useEffect, useState } from 'react'
import {
  OBSERVABILITY_CONTEXT_KEYS,
  hasObservabilityContext,
  parseObservabilityContext,
  serializeObservabilityContext,
  type ObservabilityContext,
} from '../../lib/observabilityContext'
import {
  clearObservabilityContextHistory,
  loadObservabilityContextHistory,
  saveObservabilityContextHistory,
  type ObservabilityContextHistoryEntry,
} from '../../lib/observabilityContextHistory'

type ContextFilterControlsProps = {
  context: ObservabilityContext
  overviewPath: string
  navigate?: (path: string, replace: boolean) => void
}

function navigateToOverview(path: string, replace: boolean) {
  if (replace) {
    window.location.replace(path)
    return
  }
  window.location.assign(path)
}

export function ContextFilterControls({
  context,
  overviewPath,
  navigate = navigateToOverview,
}: ContextFilterControlsProps) {
  const [copied, setCopied] = useState(false)
  const safeContext = parseObservabilityContext(
    serializeObservabilityContext(context),
  )
  const safeQuery = serializeObservabilityContext(safeContext)
  const hasContext = hasObservabilityContext(safeContext)
  const [history, setHistory] = useState<ObservabilityContextHistoryEntry[]>(
    () => loadObservabilityContextHistory(),
  )
  const safeReference = `${overviewPath}${safeQuery}`

  useEffect(() => {
    if (!hasContext) return
    setHistory(saveObservabilityContextHistory(
      overviewPath,
      parseObservabilityContext(safeQuery),
    ))
  }, [hasContext, overviewPath, safeQuery])

  const copyReference = () => {
    if (!navigator.clipboard?.writeText) {
      setCopied(false)
      return
    }
    navigator.clipboard.writeText(safeReference)
      .then(() => setCopied(true))
      .catch(() => setCopied(false))
  }

  if (!hasContext && history.length === 0) return null

  return (
    <>
      {hasContext ? (
        <div
          className="mb-4 rounded-[22px] border border-neon-cyan/20 bg-neon-cyan/[0.06] px-4 py-3"
          role="note"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neon-cyan">
            Contexto do Runtime Inspector
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Filtros ativos aplicados somente aos dados disponíveis nesta página.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {OBSERVABILITY_CONTEXT_KEYS.map((key) =>
              safeContext[key] ? (
                <span
                  className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-xs text-slate-200"
                  key={key}
                >
                  {key}: {safeContext[key]}
                </span>
              ) : null,
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              className="ghost-button status-pill"
              onClick={() => navigate(overviewPath, true)}
              type="button"
            >
              Limpar filtros
            </button>
            <button
              className="ghost-button status-pill"
              onClick={copyReference}
              type="button"
            >
              {copied ? 'Referência copiada' : 'Copiar referência'}
            </button>
            <button
              className="ghost-button status-pill"
              onClick={() => navigate(overviewPath, false)}
              type="button"
            >
              Voltar para visão geral
            </button>
          </div>
        </div>
      ) : null}

      {history.length > 0 ? (
        <section className="mb-4 rounded-[22px] border border-white/10 bg-black/15 px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">
              Contextos recentes
            </p>
            <button
              className="ghost-button status-pill"
              onClick={() => {
                clearObservabilityContextHistory()
                setHistory([])
              }}
              type="button"
            >
              Limpar histórico
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {history.map((entry) => {
              const query = serializeObservabilityContext(entry.context)
              const label = OBSERVABILITY_CONTEXT_KEYS
                .filter((key) => entry.context[key])
                .map((key) => `${key}: ${entry.context[key]}`)
                .join(' · ')
              return (
                <button
                  className="ghost-button status-pill"
                  key={`${entry.path}${query}`}
                  onClick={() => navigate(`${entry.path}${query}`, false)}
                  type="button"
                >
                  {label}
                </button>
              )
            })}
          </div>
        </section>
      ) : null}
    </>
  )
}
