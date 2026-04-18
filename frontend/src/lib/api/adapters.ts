/**
 * Wire → UI adapters. Centralizes parsing of Rust/Python subprocess quirks.
 */
import type { ChatApiResponse, ChatUsage, HealthResponse, PublicStatusResponseV1 } from '../../types'
import type {
  ObservabilityApiResponse,
  ObservabilityTracesResponse,
} from '../../types/observability'
import type { UiChatResponse } from '../../types/ui/chat'
import type { UiObservabilitySnapshot, UiObservabilityTracesResult } from '../../types/ui/observability'
import type { UiRuntimeStatus } from '../../types/ui/runtime'

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

  const record = payload as Record<string, unknown>
  const response =
    typeof record.response === 'string'
      ? record.response
      : typeof record.message === 'string'
        ? record.message
        : ''

  if (!response.trim()) {
    throw new Error('Omni returned an empty response.')
  }

  return {
    response,
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

/** Maps legacy `ChatApiResponse` (still returned by `sendOmniMessage`) to UI model. */
export function chatApiResponseToUi(res: ChatApiResponse): UiChatResponse {
  return {
    text: res.response,
    sessionId: res.session_id,
    source: res.source,
    commands: res.matched_commands ?? [],
    tools: res.matched_tools ?? [],
    stopReason: res.stop_reason,
    runtimeSessionVersion: res.runtime_session_version,
    usage: res.usage
      ? {
        inputTokens: res.usage.input_tokens,
        outputTokens: res.usage.output_tokens,
      }
      : undefined,
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
