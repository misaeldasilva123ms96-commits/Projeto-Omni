import type { ProviderRecord } from '../features/settings/types'
import type { GovernanceDecision } from '../types'
import type {
  ObservabilitySnapshot,
  TimelineEvent,
  TraceSnapshot,
} from '../types/observability'
import { redactRuntimeDebugText } from './runtimeDebugSanitizer'

export const OBSERVABILITY_CONTEXT_KEYS = [
  'request_id',
  'trace_id',
  'runtime_mode',
  'provider',
  'tool',
  'decision',
] as const

export type ObservabilityContextKey = (typeof OBSERVABILITY_CONTEXT_KEYS)[number]
export type ObservabilityContext = Partial<Record<ObservabilityContextKey, string>>

const MAX_CONTEXT_VALUE_LENGTH = 80

function safeContextValue(value: string | null): string | null {
  if (!value) return null
  const normalized = value.trim()
  if (!normalized || normalized.includes('[REDACTED]')) return null
  if (redactRuntimeDebugText(normalized) !== normalized) return null
  return normalized.slice(0, MAX_CONTEXT_VALUE_LENGTH)
}

export function parseObservabilityContext(
  search: string | URLSearchParams,
): ObservabilityContext {
  const params = typeof search === 'string'
    ? new URLSearchParams(search)
    : search
  const context: ObservabilityContext = {}

  for (const key of OBSERVABILITY_CONTEXT_KEYS) {
    const value = safeContextValue(params.get(key))
    if (value) {
      context[key] = value
    }
  }

  return context
}

export function serializeObservabilityContext(
  context: ObservabilityContext,
): string {
  const params = new URLSearchParams()
  for (const key of OBSERVABILITY_CONTEXT_KEYS) {
    const value = safeContextValue(context[key] ?? null)
    if (value) params.set(key, value)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function pickObservabilityContext(
  context: ObservabilityContext,
  keys: readonly ObservabilityContextKey[],
): ObservabilityContext {
  const selected: ObservabilityContext = {}
  for (const key of keys) {
    if (context[key]) selected[key] = context[key]
  }
  return selected
}

export function hasObservabilityContext(context: ObservabilityContext): boolean {
  return OBSERVABILITY_CONTEXT_KEYS.some((key) => Boolean(context[key]))
}

function valueMatchesKey(
  value: unknown,
  targetKey: ObservabilityContextKey,
  targetValue: string,
): boolean {
  if (Array.isArray(value)) {
    return value.some((item) => valueMatchesKey(item, targetKey, targetValue))
  }
  if (!value || typeof value !== 'object') return false

  return Object.entries(value as Record<string, unknown>).some(([key, item]) => {
    const normalizedKey = key.toLowerCase()
    const keyMatches = targetKey === 'tool'
      ? ['tool', 'tool_name', 'tool_selected', 'tool_public_name'].includes(normalizedKey)
      : normalizedKey === targetKey
    if (keyMatches && typeof item === 'string' && item === targetValue) {
      return true
    }
    return valueMatchesKey(item, targetKey, targetValue)
  })
}

function traceMatches(trace: TraceSnapshot, context: ObservabilityContext): boolean {
  if (context.trace_id) return trace.trace_id === context.trace_id
  if (context.request_id) return valueMatchesKey(trace, 'request_id', context.request_id)
  if (context.tool) return valueMatchesKey(trace, 'tool', context.tool)
  if (context.runtime_mode) return valueMatchesKey(trace, 'runtime_mode', context.runtime_mode)
  return true
}

function timelineMatches(event: TimelineEvent, context: ObservabilityContext): boolean {
  if (context.trace_id) return valueMatchesKey(event, 'trace_id', context.trace_id)
  if (context.request_id) return valueMatchesKey(event, 'request_id', context.request_id)
  if (context.tool) return valueMatchesKey(event, 'tool', context.tool)
  if (context.runtime_mode) return valueMatchesKey(event, 'runtime_mode', context.runtime_mode)
  return true
}

export function filterObservabilitySnapshotByContext(
  snapshot: ObservabilitySnapshot | null,
  context: ObservabilityContext,
): { matched: boolean; snapshot: ObservabilitySnapshot | null } {
  if (!snapshot || !hasObservabilityContext(context)) {
    return { matched: Boolean(snapshot), snapshot }
  }

  const allTraces = [
    ...(snapshot.latest_trace ? [snapshot.latest_trace] : []),
    ...snapshot.recent_traces,
  ]
  const matchingTraces = allTraces
    .filter((trace, index, items) =>
      items.findIndex((item) => item.trace_id === trace.trace_id) === index,
    )
    .filter((trace) => traceMatches(trace, context))
  const matchingTimeline = snapshot.timeline.filter((event) =>
    timelineMatches(event, context),
  )
  const matched = matchingTraces.length > 0 || matchingTimeline.length > 0

  return {
    matched,
    snapshot: matched
      ? {
          ...snapshot,
          latest_trace: matchingTraces[0] ?? null,
          recent_traces: matchingTraces,
          timeline: matchingTimeline,
        }
      : snapshot,
  }
}

export function filterProvidersByContext(
  providers: ProviderRecord[],
  context: ObservabilityContext,
): ProviderRecord[] {
  if (context.provider) {
    return providers.filter((provider) => provider.provider === context.provider)
  }
  if (context.request_id || context.trace_id) return []
  if (hasObservabilityContext(context)) return []
  return providers
}

export function filterGovernanceDecisionsByContext(
  decisions: GovernanceDecision[],
  context: ObservabilityContext,
): GovernanceDecision[] {
  if (context.decision) {
    return decisions.filter((decision) => decision.decision === context.decision)
  }
  if (context.request_id) {
    return decisions.filter((decision) => decision.sessionId === context.request_id)
  }
  if (hasObservabilityContext(context)) return []
  return decisions
}
