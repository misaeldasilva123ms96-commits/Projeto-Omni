export type ChatRole = 'user' | 'assistant' | 'system'

export type SyncChatStatus = 'active' | 'idle' | 'completed' | 'failed'

export type ChatMode = 'chat' | 'pesquisa' | 'codigo' | 'agente'

export type ChatUsage = {
  input_tokens?: number
  output_tokens?: number
}

export type RuntimeMetadata = {
  sessionId?: string
  source?: string
  matchedCommands: string[]
  matchedTools: string[]
  stopReason?: string
  /** When backend returns `cognitive_runtime_inspection.execution_tier` (degraded vs real). */
  executionTier?: string
  usage?: ChatUsage
  /** From `POST /chat` (`runtime_session_version`); Rust runtime epoch, not UI session. */
  runtimeSessionVersion?: number
  /** Server/orchestrator id when returned on the wire; not the UI-owned session key. */
  conversationId?: string
  /** `api_version` when the response came from `POST /api/v1/chat`. */
  chatApiVersion?: string
}

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  metadata?: RuntimeMetadata
  requestState?: 'completed' | 'failed'
}

export type ChatApiResponse = {
  response: string
  session_id?: string
  /** Echo of request `client_session_id` when the server returned it (Phase 7). */
  client_session_id?: string
  source?: string
  matched_commands?: string[]
  matched_tools?: string[]
  stop_reason?: string
  usage?: ChatUsage
  /** Rust runtime epoch; aligns with `GET /api/v1/status.runtime_session_version` / `/health`. */
  runtime_session_version?: number
  /** Truthful server/orchestrator conversation id when present (Phase 11+). */
  conversation_id?: string
  /** Present on `POST /api/v1/chat` responses (`api_version` in JSON). */
  api_version?: string
  /** Rust/Python cognitive envelope when present; never fabricate client-side. */
  cognitive_runtime_inspection?: Record<string, unknown>
}

export type ChatRequestState = 'idle' | 'loading' | 'error'

export type ConversationSummary = {
  id: string
  title: string
  updatedAt: string
  messageCount: number
  mode: ChatMode
}

/** Product-safe public snapshot (`GET /api/v1/status`). */
export type PublicStatusResponseV1 = {
  api_version: string
  status: string
  runtime_mode: string
  rust_service: string
  python_status: string
  node_status: string
  runtime_session_version: number
  timestamp_ms: number
}

/** `GET /api/v1/runtime/signals/summary` — reduced counts + latest run preview (Phase 8). */
export type PublicRuntimeSignalsSummaryV1 = {
  api_version: string
  status: string
  recent_signal_sample_size: number
  recent_signal_count: number
  recent_mode_transition_count: number
  latest_run_id: string
  latest_plan_kind: string
  latest_run_message_preview: string
  timestamp_ms: number
}

/** `GET /api/v1/milestones/summary` — checkpoint counts only (Phase 8). */
export type PublicMilestonesSummaryV1 = {
  api_version: string
  status: string
  latest_run_id: string
  completed_milestone_count: number
  blocked_milestone_count: number
  patch_set_count: number
  checkpoint_status: string
  timestamp_ms: number
}

/** `GET /api/v1/strategy/summary` — version + safe scalars (Phase 8). */
export type PublicStrategySummaryV1 = {
  api_version: string
  status: string
  strategy_version: number
  recent_change_log_count: number
  create_plan_weight: number | null
  timestamp_ms: number
}

export type HealthResponse = {
  status: string
  rust_service: string
  runtime_mode: string
  runtime_session_version: number
  timestamp_ms: number
  python: {
    configured_bin: string
    entry: string
    entry_exists: boolean
    observable: boolean
    last_status: string
    last_error?: string | null
    last_checked_ms?: number | null
  }
  node: {
    configured_bin: string
    entry: string
    entry_exists: boolean
    observable: boolean
    last_status: string
    last_error?: string | null
    last_checked_ms?: number | null
  }
}

export type RuntimeSignalsResponse = {
  status: string
  recent_signals: Record<string, unknown>[]
  recent_mode_transitions: Record<string, unknown>[]
  latest_run_summary: Record<string, unknown>
}

export type SwarmLogResponse = {
  status: string
  events: Record<string, unknown>[]
  total_events: number
}

export type StrategyStateResponse = {
  status: string
  strategy_state: Record<string, unknown>
  recent_changes: Record<string, unknown>[]
}

export type MilestonesResponse = {
  status: string
  latest_run_id?: string | null
  milestone_state: {
    milestones?: Array<Record<string, unknown>>
    completed_milestones?: number
    blocked_milestones?: number
  }
  patch_sets: Array<Record<string, unknown>>
  checkpoint_status: Record<string, unknown>
  execution_state: Record<string, unknown>
}

export type PrSummariesResponse = {
  status: string
  summaries: Array<Record<string, unknown>>
}

/** Where richer (non-summary) runtime rows came from for this request. */
export type RichTelemetryDetailSource = 'operator' | 'internal'

/** `GET /api/v1/operator/runtime/signals` — JWT; redacted audit projection. */
export type OperatorRuntimeSignalsV1 = {
  api_version: string
  status: string
  timestamp_ms: number
  recent_signal_sample_size: number
  recent_signals: Record<string, unknown>[]
  recent_mode_transitions: Record<string, unknown>[]
  latest_run_summary: Record<string, unknown>
}

/** `GET /api/v1/operator/strategy/changes` — JWT; no full rules blob. */
export type OperatorStrategyChangesV1 = {
  api_version: string
  status: string
  timestamp_ms: number
  strategy_version: number
  recent_changes: Record<string, unknown>[]
}

/** `GET /api/v1/operator/milestones` — JWT; bounded patch_sets + redacted JSON. */
export type OperatorMilestonesV1 = {
  api_version: string
  status: string
  timestamp_ms: number
  latest_run_id?: string | null
  checkpoint_status: Record<string, unknown>
  milestone_state: Record<string, unknown>
  patch_sets: Array<Record<string, unknown>>
  patch_sets_total: number
  patch_sets_returned: number
  execution_state: Record<string, unknown>
}
