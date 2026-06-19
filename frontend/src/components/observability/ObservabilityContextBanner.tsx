import {
  OBSERVABILITY_CONTEXT_KEYS,
  hasObservabilityContext,
  type ObservabilityContext,
} from '../../lib/observabilityContext'

type ObservabilityContextBannerProps = {
  context: ObservabilityContext
}

export function ObservabilityContextBanner({
  context,
}: ObservabilityContextBannerProps) {
  if (!hasObservabilityContext(context)) return null

  return (
    <div
      className="mb-4 rounded-[22px] border border-neon-cyan/20 bg-neon-cyan/[0.06] px-4 py-3"
      role="note"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neon-cyan">
        Contexto do Runtime Inspector
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {OBSERVABILITY_CONTEXT_KEYS.map((key) =>
          context[key] ? (
            <span
              className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-xs text-slate-200"
              key={key}
            >
              {key}: {context[key]}
            </span>
          ) : null,
        )}
      </div>
    </div>
  )
}
