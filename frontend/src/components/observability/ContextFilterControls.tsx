import { useState } from 'react'
import {
  OBSERVABILITY_CONTEXT_KEYS,
  hasObservabilityContext,
  parseObservabilityContext,
  serializeObservabilityContext,
  type ObservabilityContext,
} from '../../lib/observabilityContext'

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

  if (!hasObservabilityContext(safeContext)) return null

  const safeReference = `${overviewPath}${serializeObservabilityContext(safeContext)}`

  const copyReference = () => {
    if (!navigator.clipboard?.writeText) {
      setCopied(false)
      return
    }
    navigator.clipboard.writeText(safeReference)
      .then(() => setCopied(true))
      .catch(() => setCopied(false))
  }

  return (
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
  )
}
