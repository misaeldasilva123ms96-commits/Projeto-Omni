import type { RuntimeMetadata, ToolExecutionDiagnostic } from '../types'
import {
  normalizeGovernanceStatus,
  type RuntimeGovernanceStatus,
} from './governanceTypes'
import {
  normalizeProviderStatus,
  type RuntimeProviderStatus,
} from './providerTypes'
import {
  redactRuntimeDebugText,
  sanitizeRuntimeDebugPayload,
} from './runtimeDebugSanitizer'
import {
  firstValidTokenCount,
  normalizeTokenUsage,
} from './tokenUsage'

export const RUNTIME_MODES = [
  'FULL_COGNITIVE_RUNTIME',
  'PARTIAL_COGNITIVE',
  'MATCHER_SHORTCUT',
  'RULE_BASED_INTENT',
  'SAFE_FALLBACK',
  'NODE_RUNNER_FAILED',
  'PROVIDER_UNAVAILABLE',
  'UNKNOWN',
] as const

export type RuntimeMode = (typeof RUNTIME_MODES)[number]

export type RuntimeSummaryContract = {
  runtime_mode: RuntimeMode
  runtime_reason: string | null
  provider_attempted: boolean | null
  provider_succeeded: boolean | null
  fallback_triggered: boolean | null
  tool_invoked: boolean | null
  governance_decision: string | null
  tokens_in: number | null
  tokens_out: number | null
  total_tokens: number | null
  latency_ms: number | null
  request_id: string | null
  trace_id: string | null
  created_at: string | null
}

export type RuntimeOilSkeleton = {
  input: unknown
  decision: unknown
  execution: unknown
  observation: unknown
  evaluation: unknown
}

export type RuntimeMemoryStatus = {
  status: string | null
  matched_tools: string[]
  matched_commands: string[]
}

export type RuntimeInspectorData = {
  summary: RuntimeSummaryContract
  governance: RuntimeGovernanceStatus | null
  tools: ToolExecutionDiagnostic[]
  provider: RuntimeProviderStatus | null
  providers: RuntimeProviderStatus[]
  memory: RuntimeMemoryStatus | null
  oil: RuntimeOilSkeleton | null
  logs: Record<string, unknown> | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? redactRuntimeDebugText(value) : null
}

function optionalTimestamp(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value)
    ? value
    : redactRuntimeDebugText(value)
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

function optionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function firstBoolean(...values: unknown[]): boolean | null {
  for (const value of values) {
    const normalized = optionalBoolean(value)
    if (normalized !== null) return normalized
  }
  return null
}

function normalizeOil(value: unknown): RuntimeOilSkeleton | null {
  if (!isRecord(value)) return null
  const safe = sanitizeRuntimeDebugPayload(value)

  return {
    input: safe.input ?? null,
    decision: safe.decision ?? null,
    execution: safe.execution ?? null,
    observation: safe.observation ?? null,
    evaluation: safe.evaluation ?? null,
  }
}

export function normalizeRuntimeMode(value: unknown): RuntimeMode {
  return typeof value === 'string' && (RUNTIME_MODES as readonly string[]).includes(value)
    ? value as RuntimeMode
    : 'UNKNOWN'
}

export function normalizeRuntimeInspectorData(
  metadata: RuntimeMetadata | null | undefined,
): RuntimeInspectorData {
  const inspection = isRecord(metadata?.cognitiveRuntimeInspection)
    ? metadata.cognitiveRuntimeInspection
    : {}
  const runtimeTruth = isRecord(inspection.runtime_truth)
    ? inspection.runtime_truth
    : {}
  const governanceSource = inspection.governance
    ?? (inspection.governance_decision
      || inspection.risk_level
      || typeof inspection.blocked === 'boolean'
      || inspection.reason
      || inspection.policy
      || inspection.tool_category
      || typeof inspection.requires_approval === 'boolean'
      ? {
          decision: inspection.governance_decision,
          risk_level: inspection.risk_level,
          blocked: inspection.blocked,
          reason: inspection.reason,
          policy: inspection.policy,
          tool_category: inspection.tool_category,
          requires_approval: inspection.requires_approval,
        }
      : null)
  const governance = normalizeGovernanceStatus(governanceSource)
  const selectedProvider = metadata?.providerDiagnostics?.find((provider) => provider.selected)
    ?? metadata?.providerDiagnostics?.[0]
    ?? null
  const providerSource = inspection.provider
    ?? (metadata?.providerActual || inspection.provider_actual || inspection.provider_public_name
      ? {
          provider_name:
            metadata?.providerActual
            ?? inspection.provider_actual
            ?? inspection.provider_public_name,
          attempted:
            inspection.provider_attempted
            ?? inspection.llm_provider_attempted
            ?? runtimeTruth.provider_attempted
            ?? runtimeTruth.llm_provider_attempted,
          succeeded:
            inspection.provider_succeeded
            ?? inspection.llm_provider_succeeded
            ?? runtimeTruth.provider_succeeded
            ?? runtimeTruth.llm_provider_succeeded,
          latency_ms: inspection.latency_ms,
          tokens_in: inspection.tokens_in,
          tokens_out: inspection.tokens_out,
          total_tokens: inspection.total_tokens,
        }
      : null)
  const provider = normalizeProviderStatus(providerSource, selectedProvider)
  const providers = (metadata?.providerDiagnostics ?? [])
    .map((item) => normalizeProviderStatus(item, item))
    .filter((item): item is RuntimeProviderStatus => item !== null)
  const tools = (metadata?.toolDiagnostics
    ?? (metadata?.toolExecution ? [metadata.toolExecution] : [])
  ).map((tool) => ({
    ...tool,
    tool_selected: tool.tool_selected
      ? redactRuntimeDebugText(tool.tool_selected)
      : tool.tool_selected,
    tool_failure_class: tool.tool_failure_class
      ? redactRuntimeDebugText(tool.tool_failure_class)
      : tool.tool_failure_class,
    tool_failure_reason: tool.tool_failure_reason
      ? redactRuntimeDebugText(tool.tool_failure_reason)
      : tool.tool_failure_reason,
  }))
  const memoryStatus = optionalString(inspection.memory_status)
  const matchedTools = metadata?.matchedTools ?? []
  const matchedCommands = metadata?.matchedCommands ?? []
  const governanceDecision = optionalString(
    inspection.governance_decision
    ?? (isRecord(inspection.governance) ? inspection.governance.decision : null),
  )
  const tokenUsage = normalizeTokenUsage({
    inputTokens: firstValidTokenCount(
      inspection.tokens_in,
      provider?.tokens_in,
      metadata?.usage?.input_tokens,
    ),
    outputTokens: firstValidTokenCount(
      inspection.tokens_out,
      provider?.tokens_out,
      metadata?.usage?.output_tokens,
    ),
    totalTokens: firstValidTokenCount(
      inspection.total_tokens,
      provider?.total_tokens,
      metadata?.usage?.total_tokens,
    ),
  })

  return {
    summary: {
      runtime_mode: normalizeRuntimeMode(metadata?.runtimeMode ?? inspection.runtime_mode),
      runtime_reason: optionalString(
        metadata?.runtimeReason
        ?? inspection.runtime_reason
        ?? runtimeTruth.runtime_reason,
      ),
      provider_attempted: firstBoolean(
        inspection.provider_attempted,
        inspection.llm_provider_attempted,
        runtimeTruth.provider_attempted,
        runtimeTruth.llm_provider_attempted,
        provider?.attempted,
      ),
      provider_succeeded: firstBoolean(
        inspection.provider_succeeded,
        inspection.llm_provider_succeeded,
        runtimeTruth.provider_succeeded,
        runtimeTruth.llm_provider_succeeded,
        provider?.succeeded,
      ),
      fallback_triggered: firstBoolean(
        metadata?.fallbackTriggered,
        inspection.fallback_triggered,
        runtimeTruth.fallback_triggered,
      ),
      tool_invoked: firstBoolean(
        inspection.tool_invoked,
        runtimeTruth.tool_invoked,
        metadata?.toolExecution?.tool_attempted,
      ),
      governance_decision: governanceDecision,
      tokens_in: tokenUsage.inputTokens,
      tokens_out: tokenUsage.outputTokens,
      total_tokens: tokenUsage.totalTokens,
      latency_ms: optionalNumber(inspection.latency_ms ?? provider?.latency_ms),
      request_id: optionalString(inspection.request_id),
      trace_id: optionalString(inspection.trace_id),
      created_at: optionalTimestamp(inspection.created_at),
    },
    governance,
    tools,
    provider,
    providers: providers.length ? providers : provider ? [provider] : [],
    memory: memoryStatus || matchedTools.length || matchedCommands.length
      ? {
          status: memoryStatus,
          matched_tools: matchedTools.map(redactRuntimeDebugText),
          matched_commands: matchedCommands.map(() => '[REDACTED]'),
        }
      : null,
    oil: normalizeOil(inspection.oil ?? inspection.oil_envelope),
    logs: metadata ? sanitizeRuntimeDebugPayload(metadata) : null,
  }
}
