import { useRuntimeConsoleStore } from '../../state/runtimeConsoleStore'
import type { GovernanceSummary } from '../../types'
import { extractGovernanceSummary } from '../../lib/runtimeDebugSanitizer'
import { GovernanceBadge } from './GovernanceBadge'
import { ProviderStatusBadge } from './ProviderStatusBadge'
import { RuntimeStatusBadge } from './RuntimeStatusBadge'
import { TokenUsageMeter } from '../tokens/TokenUsageMeter'
import { normalizeTokenUsage } from '../../lib/tokenUsage'

type RuntimeTruthBarProps = {
  className?: string
}

export function RuntimeTruthBar({ className = '' }: RuntimeTruthBarProps) {
  const metadata = useRuntimeConsoleStore((state) => state.lastRuntimeMetadata)
  const inspectorData = useRuntimeConsoleStore((state) => state.lastRuntimeInspectorData)
  const requestState = useRuntimeConsoleStore((state) => state.isSending ? 'loading' : 'idle')

  const runtimeMode = metadata?.runtimeMode ?? metadata?.cognitiveRuntimeInspection?.runtime_mode as string | undefined
  const isFallback = metadata?.fallbackTriggered ?? metadata?.signals?.fallback_triggered ?? false
  const provider = metadata?.providerActual ?? metadata?.signals?.provider_actual ?? null
  const summary = inspectorData?.summary
  const usage = normalizeTokenUsage({
    inputTokens: summary?.tokens_in,
    outputTokens: summary?.tokens_out,
    totalTokens: summary?.total_tokens,
  })

  const governance: GovernanceSummary | null = extractGovernanceSummary(metadata)

  const isLoading = requestState === 'loading'

  if (!metadata && !isLoading) {
    return (
      <div className={`flex items-center gap-3 text-xs text-slate-500 ${className}`.trim()}>
        <span>Runtime idle</span>
        <TokenUsageMeter usage={usage} variant="compact" />
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-3 flex-wrap ${className}`.trim()}>
      <RuntimeStatusBadge
        mode={typeof runtimeMode === 'string' ? runtimeMode : 'Unknown'}
        fallback={isFallback}
      />
      <ProviderStatusBadge provider={provider} />
      <GovernanceBadge governance={governance} />
      <TokenUsageMeter usage={usage} variant="compact" />
    </div>
  )
}
