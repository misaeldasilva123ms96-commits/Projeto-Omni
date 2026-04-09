export type ChatRole = 'user' | 'assistant' | 'system'

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
  usage?: ChatUsage
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
  source?: string
  matched_commands?: string[]
  matched_tools?: string[]
  stop_reason?: string
  usage?: ChatUsage
}

export type ChatRequestState = 'idle' | 'loading' | 'error'

export type ConversationSummary = {
  id: string
  title: string
  updatedAt: string
  messageCount: number
  mode: ChatMode
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
