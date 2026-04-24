/**
 * Wire → UI adapters. Centralizes parsing of Rust/Python subprocess quirks.
 */
import type {
  ChatApiResponse,
  ChatUsage,
  HealthResponse,
  MilestonesResponse,
  OperatorMilestonesV1,
  OperatorRuntimeSignalsV1,
  OperatorStrategyChangesV1,
  PublicMilestonesSummaryV1,
  PublicRuntimeSignalsSummaryV1,
  PublicStatusResponseV1,
  PublicStrategySummaryV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
} from '../../types'
import type {
  ObservabilityApiResponse,
  ObservabilityTracesResponse,
} from '../../types/observability'
import type { UiChatResponse } from '../../types/ui/chat'
import { classifyChatWireHealth, extractExecutionTier } from './wireChatHealth'
import type { UiObservabilitySnapshot, UiObservabilityTracesResult } from '../../types/ui/observability'
import type { UiRuntimeStatus } from '../../types/ui/runtime'
import type { UiMilestonesSummary, UiRuntimeSignalsSummary, UiStrategySummary } from '../../types/ui/telemetry'

export function parseWireChatPayload(payload: unknown): ChatApiResponse {
  if (typeof payload === 'string') {
    const response = payload.trim()
    if (!response) {
      throw new Error('Omni returned an empty response.')
    }
    return { response }
  }

  if (!payload || typeof payload !== 'object') {
    throw new Error('Omni returned an invalid response payload.')
  }

  let record = payload as Record<string, unknown>
  const nestedChat = record.chat
  if (
    nestedChat &&
    typeof nestedChat === 'object' &&
    !Array.isArray(nestedChat) &&
    typeof (nestedChat as Record<string, unknown>).response === 'string'
  ) {
    record = { ...record, ...(nestedChat as Record<string, unknown>) }
  }
  const response =
    typeof record.response === 'string'
      ? record.response
      : typeof record.message === 'string'
        ? record.message
        : ''

  const error = adaptRuntimeError(record.error)
  const responseText = response.trim() || error?.message?.trim() || ''

  if (!responseText) {
    throw new Error('Omni returned an empty response.')
  }

  const conversation_id =
    typeof record.conversation_id === 'string' && record.conversation_id.trim()
      ? record.conversation_id.trim()
      : undefined

  const api_version =
    typeof record.api_version === 'string' && record.api_version.trim()
      ? record.api_version.trim()
      : undefined

  const inspectionRaw = record.cognitive_runtime_inspection
  const cognitive_runtime_inspection =
    inspectionRaw && typeof inspectionRaw === 'object' && !Array.isArray(inspectionRaw)
      ? (inspectionRaw as Record<string, unknown>)
      : undefined

  const signals = adaptRuntimeSignals(record.signals)
  const runtime_reason =
    readString(record.runtime_reason)
    ?? signals?.runtime_reason
  const execution_path_used =
    readString(record.execution_path_used)
    ?? signals?.execution_path_used
  const fallback_triggered =
    readBoolean(record.fallback_triggered)
    ?? signals?.fallback_triggered
  const compatibility_execution_active =
    readBoolean(record.compatibility_execution_active)
    ?? signals?.compatibility_execution_active
  const provider_actual =
    readString(record.provider_actual)
    ?? signals?.provider_actual
  const provider_failed =
    readBoolean(record.provider_failed)
    ?? signals?.provider_failed
  const failure_class =
    readString(record.failure_class)
    ?? signals?.failure_class
  const execution_provenance = record.execution_provenance ?? signals?.execution_provenance
  const providers = Array.isArray(record.providers) ? record.providers : undefined

  return {
    response: responseText,
    session_id:
      typeof record.session_id === 'string' ? record.session_id : undefined,
    client_session_id:
      typeof record.client_session_id === 'string' ? record.client_session_id : undefined,
    source: typeof record.source === 'string' ? record.source : undefined,
    matched_commands: Array.isArray(record.matched_commands)
      ? record.matched_commands.filter(
        (item): item is string => typeof item === 'string',
      )
      : [],
    matched_tools: Array.isArray(record.matched_tools)
      ? record.matched_tools.filter(
        (item): item is string => typeof item === 'string',
      )
      : [],
    stop_reason:
      typeof record.stop_reason === 'string' ? record.stop_reason : undefined,
    usage:
      record.usage && typeof record.usage === 'object'
        ? adaptUsage(record.usage as Record<string, unknown>)
        : undefined,
    runtime_session_version:
      typeof record.runtime_session_version === 'number'
        ? record.runtime_session_version
        : undefined,
    conversation_id,
    api_version,
    cognitive_runtime_inspection,
    runtime_mode: readString(record.runtime_mode),
    runtime_reason,
    signals,
    execution_path_used,
    fallback_triggered,
    compatibility_execution_active,
    provider_actual,
    provider_failed,
    failure_class,
    execution_provenance,
    providers,
    error,
  }
}

function adaptUsage(record: Record<string, unknown>): ChatUsage {
  return {
    input_tokens:
      typeof record.input_tokens === 'number' ? record.input_tokens : undefined,
    output_tokens:
      typeof record.output_tokens === 'number' ? record.output_tokens : undefined,
  }
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function readBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined
}

function adaptRuntimeSignals(value: unknown): ChatApiResponse['signals'] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }
  const record = value as Record<string, unknown>
  return {
    runtime_reason: readString(record.runtime_reason),
    execution_path_used: readString(record.execution_path_used),
    fallback_triggered: readBoolean(record.fallback_triggered),
    compatibility_execution_active: readBoolean(record.compatibility_execution_active),
    provider_actual: readString(record.provider_actual),
    provider_failed: readBoolean(record.provider_failed),
    failure_class: readString(record.failure_class),
    execution_provenance: record.execution_provenance,
    node_execution_successful: readBoolean(record.node_execution_successful),
  }
}

function adaptRuntimeError(value: unknown): ChatApiResponse['error'] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }
  const record = value as Record<string, unknown>
  return {
    code: readString(record.code),
    message: readString(record.message),
    details: record.details,
  }
}

/** Maps legacy `ChatApiResponse` (still returned by `sendOmniMessage`) to UI model. */
/** Map operator runtime projection into the same shape consumed by dashboard / cognitive UI today. */
export function operatorRuntimeSignalsV1ToRuntimeSignalsResponse(
  w: OperatorRuntimeSignalsV1,
): RuntimeSignalsResponse {
  return {
    status: w.status,
    recent_signals: w.recent_signals,
    recent_mode_transitions: w.recent_mode_transitions,
    latest_run_summary: w.latest_run_summary,
  }
}

/**
 * Map operator strategy changes into `StrategyStateResponse`.
 * Full `strategy_state` rules blob is not on the operator contract — only a version marker for UI continuity.
 */
export function operatorStrategyChangesV1ToStrategyStateResponse(
  w: OperatorStrategyChangesV1,
): StrategyStateResponse {
  return {
    status: w.status,
    strategy_state: {
      version: w.strategy_version,
    },
    recent_changes: w.recent_changes,
  }
}

export function operatorMilestonesV1ToMilestonesResponse(w: OperatorMilestonesV1): MilestonesResponse {
  return {
    status: w.status,
    latest_run_id: w.latest_run_id,
    milestone_state: w.milestone_state as MilestonesResponse['milestone_state'],
    patch_sets: w.patch_sets,
    checkpoint_status: w.checkpoint_status,
    execution_state: w.execution_state,
  }
}

export function chatApiResponseToUi(res: ChatApiResponse): UiChatResponse {
  return {
    text: res.response,
    sessionId: res.session_id,
    source: res.source,
    commands: res.matched_commands ?? [],
    tools: res.matched_tools ?? [],
    stopReason: res.stop_reason,
    executionTier: extractExecutionTier(res.cognitive_runtime_inspection),
    wireHealth: classifyChatWireHealth({
      response: res.response,
      stop_reason: res.stop_reason,
      cognitive_runtime_inspection: res.cognitive_runtime_inspection,
    }),
    runtimeSessionVersion: res.runtime_session_version,
    conversationId: res.conversation_id,
    chatApiVersion: res.api_version,
    usage: res.usage
      ? {
        inputTokens: res.usage.input_tokens,
        outputTokens: res.usage.output_tokens,
      }
      : undefined,
    runtimeMode: res.runtime_mode,
    runtimeReason: res.runtime_reason,
    cognitiveRuntimeInspection: res.cognitive_runtime_inspection,
    signals: res.signals,
    executionPathUsed: res.execution_path_used ?? res.signals?.execution_path_used,
    fallbackTriggered: res.fallback_triggered ?? res.signals?.fallback_triggered,
    compatibilityExecutionActive:
      res.compatibility_execution_active ?? res.signals?.compatibility_execution_active,
    providerActual: res.provider_actual ?? res.signals?.provider_actual,
    providerFailed: res.provider_failed ?? res.signals?.provider_failed,
    failureClass: res.failure_class ?? res.signals?.failure_class,
    executionProvenance: res.execution_provenance ?? res.signals?.execution_provenance,
    providers: res.providers,
    error: res.error,
  }
}

export function publicRuntimeSignalsSummaryV1ToUi(w: PublicRuntimeSignalsSummaryV1): UiRuntimeSignalsSummary {
  return {
    apiVersion: w.api_version,
    status: w.status,
    recentSignalSampleSize: w.recent_signal_sample_size,
    recentSignalCount: w.recent_signal_count,
    recentModeTransitionCount: w.recent_mode_transition_count,
    latestRunId: w.latest_run_id,
    latestPlanKind: w.latest_plan_kind,
    latestRunMessagePreview: w.latest_run_message_preview,
    timestampMs: w.timestamp_ms,
  }
}

export function publicMilestonesSummaryV1ToUi(w: PublicMilestonesSummaryV1): UiMilestonesSummary {
  return {
    apiVersion: w.api_version,
    status: w.status,
    latestRunId: w.latest_run_id,
    completedMilestoneCount: w.completed_milestone_count,
    blockedMilestoneCount: w.blocked_milestone_count,
    patchSetCount: w.patch_set_count,
    checkpointStatus: w.checkpoint_status,
    timestampMs: w.timestamp_ms,
  }
}

export function publicStrategySummaryV1ToUi(w: PublicStrategySummaryV1): UiStrategySummary {
  return {
    apiVersion: w.api_version,
    status: w.status,
    strategyVersion: w.strategy_version,
    recentChangeLogCount: w.recent_change_log_count,
    createPlanWeight: w.create_plan_weight,
    timestampMs: w.timestamp_ms,
  }
}

/** Map versioned public status into the shared `UiRuntimeStatus` surface (observable flags not on wire — inferred). */
export function publicStatusV1ToUiRuntimeStatus(p: PublicStatusResponseV1): UiRuntimeStatus {
  return {
    overallStatus: p.status,
    rustService: p.rust_service,
    runtimeMode: p.runtime_mode,
    sessionVersion: p.runtime_session_version,
    pythonStatus: p.python_status,
    pythonObservable: true,
    nodeStatus: p.node_status,
    nodeObservable: p.node_status === 'observable',
    timestampMs: p.timestamp_ms,
  }
}

export function healthResponseToUiRuntimeStatus(health: HealthResponse): UiRuntimeStatus {
  return {
    overallStatus: health.status,
    rustService: health.rust_service,
    runtimeMode: health.runtime_mode,
    sessionVersion: health.runtime_session_version,
    pythonStatus: health.python.last_status,
    pythonObservable: health.python.observable,
    nodeStatus: health.node.last_status,
    nodeObservable: health.node.observable,
    timestampMs: health.timestamp_ms,
  }
}

/** Narrow transport envelope to UI-facing snapshot handle (shape matches reader today). */
export function observabilityApiEnvelopeToUi(resp: ObservabilityApiResponse): {
  snapshot: UiObservabilitySnapshot | null
  status: string
  error?: string
} {
  return {
    snapshot: resp.snapshot,
    status: resp.status,
    error: resp.error,
  }
}

export function observabilityTracesResponseToUi(resp: ObservabilityTracesResponse): UiObservabilityTracesResult {
  return resp
}
