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

export type RuntimeAutonomyStats = {
  total_evaluations: number | null
  decisions_by_type: Record<string, number> | null
  escalation_count: number | null
  escalation_rate: number | null
  abort_safe_count: number | null
  continue_count: number | null
  retry_count: number | null
  replan_count: number | null
  pause_count: number | null
  last_decision: string | null
  last_risk_level: string | null
  last_updated_at: string | null
  advisory_mode_enabled: boolean | null
  active_session_count: number | null
}

export type RuntimeAutonomyStatus = {
  decision: string
  advisory: boolean
  reason: string | null
  risk_level: string | null
  session_id: string | null
  progress_score: number | null
  stagnation_score: number | null
  is_progress: boolean | null
  is_stagnation: boolean | null
  stagnant_attempts: number | null
  fingerprint_id: string | null
  recommended_decision_hint: string | null
  evidence_summary: string | null
  session_state_diagnostics: RuntimeAutonomySessionStateDiagnostics | null
  dry_run_retry_plan: RuntimeDryRunRetryPlan | null
}

export type RuntimeDryRunRetryPlan = {
  plan_id: string | null
  plan_type: 'dry_run_retry' | null
  advisory: boolean | null
  would_retry: boolean | null
  retry_reason: string | null
  blocked: boolean | null
  block_reasons: string[]
  retry_eligibility_score: number | null
  risk_level: string | null
  source_decision: string | null
  fingerprint_id: string | null
  stagnation_score: number | null
  progress_score: number | null
  repeated_strategy_count: number | null
  max_attempts_remaining: number | null
  evidence_summary: string | null
  created_at: string | null
}

export type RuntimeAutonomySessionStateSource =
  | 'process_local'
  | 'sqlite_hydrated'
  | 'sqlite_missing'
  | 'sqlite_unavailable'
  | 'sqlite_read_failed'
  | 'sqlite_write_failed'

export type RuntimeAutonomySessionStateDiagnostics = {
  session_state_source: RuntimeAutonomySessionStateSource | null
  session_state_persistence_enabled: boolean | null
  session_state_hydrated: boolean | null
  session_state_upserted: boolean | null
  session_state_degraded: boolean | null
  session_state_last_error_category: string | null
  session_state_updated_at: string | null
  session_state_expires_at: string | null
  session_state_fields_count: number | null
  expired_state_cleanup_supported: boolean | null
  last_cleanup_attempted_at: string | null
  last_cleanup_deleted_count: number | null
  cleanup_degraded: boolean | null
  cleanup_last_error_category: string | null
  session_state_ttl_seconds: number | null
  expired_state_count: number | null
}

export type AutonomyTimelineItem = {
  id: string
  session_id: string
  decision: string
  advisory: boolean
  risk_level: string | null
  fingerprint_id: string | null
  progress_score: number | null
  stagnation_score: number | null
  is_progress: boolean | null
  is_stagnation: boolean | null
  stagnant_attempts: number | null
  recommended_decision_hint: string | null
  evidence_summary: string | null
  strategies_attempted: string[]
  repeated_strategy_count: number | null
  timestamp: string
}

export type RuntimeInspectorData = {
  summary: RuntimeSummaryContract
  governance: RuntimeGovernanceStatus | null
  tools: ToolExecutionDiagnostic[]
  provider: RuntimeProviderStatus | null
  providers: RuntimeProviderStatus[]
  memory: RuntimeMemoryStatus | null
  oil: RuntimeOilSkeleton | null
  autonomy: RuntimeAutonomyStatus | null
  autonomy_stats: RuntimeAutonomyStats | null
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

const AUTONOMY_SESSION_STATE_SOURCES = new Set([
  'process_local',
  'sqlite_hydrated',
  'sqlite_missing',
  'sqlite_unavailable',
  'sqlite_read_failed',
  'sqlite_write_failed',
])

export function normalizeAutonomySessionStateDiagnostics(
  value: unknown,
): RuntimeAutonomySessionStateDiagnostics | null {
  if (!isRecord(value)) return null
  const rawSource = optionalString(value.session_state_source)
  const source = rawSource && AUTONOMY_SESSION_STATE_SOURCES.has(rawSource)
    ? rawSource as RuntimeAutonomySessionStateSource
    : null
  return {
    session_state_source: source,
    session_state_persistence_enabled: optionalBoolean(value.session_state_persistence_enabled),
    session_state_hydrated: optionalBoolean(value.session_state_hydrated),
    session_state_upserted: optionalBoolean(value.session_state_upserted),
    session_state_degraded: optionalBoolean(value.session_state_degraded),
    session_state_last_error_category: optionalString(value.session_state_last_error_category),
    session_state_updated_at: optionalTimestamp(value.session_state_updated_at),
    session_state_expires_at: optionalTimestamp(value.session_state_expires_at),
    session_state_fields_count: optionalNumber(value.session_state_fields_count),
    expired_state_cleanup_supported: optionalBoolean(value.expired_state_cleanup_supported),
    last_cleanup_attempted_at: optionalTimestamp(value.last_cleanup_attempted_at),
    last_cleanup_deleted_count: optionalNumber(value.last_cleanup_deleted_count),
    cleanup_degraded: optionalBoolean(value.cleanup_degraded),
    cleanup_last_error_category: optionalString(value.cleanup_last_error_category),
    session_state_ttl_seconds: optionalNumber(value.session_state_ttl_seconds),
    expired_state_count: optionalNumber(value.expired_state_count),
  }
}

export function normalizeDryRunRetryPlan(value: unknown): RuntimeDryRunRetryPlan | null {
  if (!isRecord(value)) return null
  const rawPlanType = optionalString(value.plan_type)
  const planType = rawPlanType === 'dry_run_retry' ? rawPlanType : null
  const rawBlockReasons = Array.isArray(value.block_reasons)
    ? value.block_reasons
      .filter((reason): reason is string => typeof reason === 'string')
      .slice(0, 12)
      .map(redactRuntimeDebugText)
    : []

  return {
    plan_id: optionalString(value.plan_id),
    plan_type: planType,
    advisory: optionalBoolean(value.advisory),
    would_retry: optionalBoolean(value.would_retry),
    retry_reason: optionalString(value.retry_reason),
    blocked: optionalBoolean(value.blocked),
    block_reasons: rawBlockReasons,
    retry_eligibility_score: optionalNumber(value.retry_eligibility_score),
    risk_level: optionalString(value.risk_level),
    source_decision: optionalString(value.source_decision),
    fingerprint_id: optionalString(value.fingerprint_id),
    stagnation_score: optionalNumber(value.stagnation_score),
    progress_score: optionalNumber(value.progress_score),
    repeated_strategy_count: optionalNumber(value.repeated_strategy_count),
    max_attempts_remaining: optionalNumber(value.max_attempts_remaining),
    evidence_summary: optionalString(value.evidence_summary),
    created_at: optionalTimestamp(value.created_at),
  }
}

export function normalizeAutonomyStatus(value: unknown): RuntimeAutonomyStatus | null {
  if (!isRecord(value)) return null
  return {
    decision: optionalString(value.decision) ?? 'UNKNOWN',
    advisory: typeof value.advisory === 'boolean' ? value.advisory : false,
    reason: optionalString(value.reason),
    risk_level: optionalString(value.risk_level),
    session_id: optionalString(value.session_id),
    progress_score: optionalNumber(value.progress_score),
    stagnation_score: optionalNumber(value.stagnation_score),
    is_progress: optionalBoolean(value.is_progress),
    is_stagnation: optionalBoolean(value.is_stagnation),
    stagnant_attempts: optionalNumber(value.stagnant_attempts),
    fingerprint_id: optionalString(value.fingerprint_id),
    recommended_decision_hint: optionalString(value.recommended_decision_hint),
    evidence_summary: optionalString(value.evidence_summary),
    session_state_diagnostics: normalizeAutonomySessionStateDiagnostics(value.session_state_diagnostics),
    dry_run_retry_plan: normalizeDryRunRetryPlan(value.dry_run_retry_plan),
  }
}

export function normalizeAutonomyStats(value: unknown): RuntimeAutonomyStats | null {
  if (!isRecord(value)) return null
  const decisions_by_type_raw = value.decisions_by_type
  const decisions_by_type: Record<string, number> | null =
    isRecord(decisions_by_type_raw)
      ? Object.fromEntries(
          Object.entries(decisions_by_type_raw)
            .filter(([_, v]) => typeof v === 'number' && Number.isFinite(v)),
        ) as Record<string, number>
      : null
  return {
    total_evaluations: optionalNumber(value.total_evaluations),
    decisions_by_type,
    escalation_count: optionalNumber(value.escalation_count),
    escalation_rate: optionalNumber(value.escalation_rate),
    abort_safe_count: optionalNumber(value.abort_safe_count),
    continue_count: optionalNumber(value.continue_count),
    retry_count: optionalNumber(value.retry_count),
    replan_count: optionalNumber(value.replan_count),
    pause_count: optionalNumber(value.pause_count),
    last_decision: optionalString(value.last_decision),
    last_risk_level: optionalString(value.last_risk_level),
    last_updated_at: optionalTimestamp(value.last_updated_at),
    advisory_mode_enabled: optionalBoolean(value.advisory_mode_enabled),
    active_session_count: optionalNumber(value.active_session_count),
  }
}

export function normalizeAutonomyTimelineItem(
  value: unknown,
  messageId: string,
  sessionId: string,
  timestamp: string,
): AutonomyTimelineItem | null {
  if (!isRecord(value) || typeof messageId !== 'string' || typeof sessionId !== 'string') return null
  const decision = optionalString(value.decision)
  if (!decision) return null
  const rawStrategies: string[] = Array.isArray(value.strategies_attempted)
    ? value.strategies_attempted.filter((s): s is string => typeof s === 'string').map(redactRuntimeDebugText)
    : []
  return {
    id: `${messageId}`,
    session_id: sessionId,
    decision,
    advisory: typeof value.advisory === 'boolean' ? value.advisory : false,
    risk_level: optionalString(value.risk_level),
    fingerprint_id: optionalString(value.fingerprint_id),
    progress_score: optionalNumber(value.progress_score),
    stagnation_score: optionalNumber(value.stagnation_score),
    is_progress: optionalBoolean(value.is_progress),
    is_stagnation: optionalBoolean(value.is_stagnation),
    stagnant_attempts: optionalNumber(value.stagnant_attempts),
    recommended_decision_hint: optionalString(value.recommended_decision_hint),
    evidence_summary: optionalString(value.evidence_summary),
    strategies_attempted: rawStrategies,
    repeated_strategy_count: optionalNumber(value.repeated_strategy_count),
    timestamp,
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
  const autonomy = normalizeAutonomyStatus(inspection.autonomy_evaluation)
  const autonomy_stats = normalizeAutonomyStats(inspection.autonomy_controller_stats)

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
    autonomy,
    autonomy_stats,
    logs: metadata ? sanitizeRuntimeDebugPayload(metadata) : null,
  }
}
