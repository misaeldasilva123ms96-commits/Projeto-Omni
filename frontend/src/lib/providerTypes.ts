import type { ProviderDiagnostic } from '../types'
import { redactRuntimeDebugText } from './runtimeDebugSanitizer'

export type RuntimeProviderStatus = {
  provider_name: string | null
  model: string | null
  attempted: boolean | null
  succeeded: boolean | null
  failure_reason: string | null
  latency_ms: number | null
  tokens_in: number | null
  tokens_out: number | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? redactRuntimeDebugText(value) : null
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

function optionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function normalizeProviderStatus(
  value: unknown,
  fallback?: ProviderDiagnostic | null,
): RuntimeProviderStatus | null {
  const record = isRecord(value) ? value : null
  if (!record && !fallback) return null

  return {
    provider_name: optionalString(record?.provider_name ?? record?.provider ?? fallback?.provider),
    model: optionalString(record?.model ?? fallback?.model),
    attempted: optionalBoolean(record?.attempted ?? fallback?.attempted),
    succeeded: optionalBoolean(record?.succeeded ?? fallback?.succeeded),
    failure_reason: optionalString(record?.failure_reason ?? fallback?.failure_reason),
    latency_ms: optionalNumber(record?.latency_ms ?? fallback?.latency_ms),
    tokens_in: optionalNumber(record?.tokens_in ?? fallback?.tokens_in),
    tokens_out: optionalNumber(record?.tokens_out ?? fallback?.tokens_out),
  }
}
