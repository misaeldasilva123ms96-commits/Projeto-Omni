import { pathForView, type View } from '../app/routes'
import { redactRuntimeDebugText } from './runtimeDebugSanitizer'
import type { RuntimeInspectorData } from './runtimeTypes'

const ALLOWED_QUERY_KEYS = [
  'request_id',
  'trace_id',
  'runtime_mode',
  'provider',
  'tool',
  'decision',
] as const

type AllowedQueryKey = (typeof ALLOWED_QUERY_KEYS)[number]
type RuntimeLinkView = Extract<View, 'observability' | 'provider-center' | 'governance'>
type RuntimeLinkParams = Partial<Record<AllowedQueryKey, unknown>>

export type RuntimeInspectorLinks = {
  observability: string | null
  provider: string | null
  tool: string | null
  governance: string | null
  logs: string | null
}

function safeQueryValue(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim()
  if (!normalized || normalized.length > 160 || normalized.includes('[REDACTED]')) {
    return null
  }
  return redactRuntimeDebugText(normalized) === normalized ? normalized : null
}

export function buildSafeRuntimeHref(
  view: RuntimeLinkView,
  values: RuntimeLinkParams,
): string | null {
  const params = new URLSearchParams()

  for (const key of ALLOWED_QUERY_KEYS) {
    const value = safeQueryValue(values[key])
    if (value) {
      params.set(key, value)
    }
  }

  if (!params.size) return null
  return `${pathForView(view)}?${params.toString()}`
}

export function buildRuntimeInspectorLinks(
  data: RuntimeInspectorData | null,
): RuntimeInspectorLinks {
  if (!data) {
    return {
      observability: null,
      provider: null,
      tool: null,
      governance: null,
      logs: null,
    }
  }

  const summary = data.summary
  const hasReference = Boolean(
    safeQueryValue(summary.request_id)
    || safeQueryValue(summary.trace_id),
  )
  const referenceParams: RuntimeLinkParams = {
    request_id: summary.request_id,
    trace_id: summary.trace_id,
    runtime_mode: summary.runtime_mode === 'UNKNOWN' ? null : summary.runtime_mode,
  }
  const observability = hasReference
    ? buildSafeRuntimeHref('observability', referenceParams)
    : null
  const providerName =
    data.provider?.provider_name
    ?? data.providers.find((provider) => provider.provider_name)?.provider_name
    ?? null
  const toolName =
    data.tools.find((tool) => tool.tool_selected)?.tool_selected
    ?? null
  const decision =
    data.governance?.decision
    ?? summary.governance_decision
  const governance = decision && decision !== 'unknown'
    ? buildSafeRuntimeHref('governance', { decision })
    : null

  return {
    observability,
    provider: buildSafeRuntimeHref('provider-center', { provider: providerName }),
    tool: toolName
      ? buildSafeRuntimeHref('observability', {
          ...referenceParams,
          tool: toolName,
        })
      : null,
    governance,
    logs: data.logs && observability ? observability : null,
  }
}
