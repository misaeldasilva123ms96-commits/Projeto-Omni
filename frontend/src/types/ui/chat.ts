import type { RuntimeErrorPayload, RuntimeSignals } from '../../types'

/**
 * UI-stable chat result (decoupled from wire field names like `matched_commands`).
 */
export type UiChatResponse = {
  text: string
  sessionId?: string
  source?: string
  commands: string[]
  tools: string[]
  stopReason?: string
  /** From `cognitive_runtime_inspection.execution_tier` when the backend exposes it. */
  executionTier?: string
  /** Same rules as E2E `classifyChatWireHealth` — wire-level degraded vs healthy. */
  wireHealth?: 'ok' | 'degraded'
  /** Rust runtime epoch from chat endpoints when present; aligns with public status snapshot. */
  runtimeSessionVersion?: number
  /** Backend correlation id when truthfully returned; never the UI session key. */
  conversationId?: string
  /** Version marker from `/api/v1/chat` when present (e.g. `"1"`). */
  chatApiVersion?: string
  usage?: {
    inputTokens?: number
    outputTokens?: number
  }
  runtimeMode?: string
  runtimeReason?: string
  cognitiveRuntimeInspection?: Record<string, unknown>
  signals?: RuntimeSignals
  executionPathUsed?: string
  fallbackTriggered?: boolean
  compatibilityExecutionActive?: boolean
  providerActual?: string
  providerFailed?: boolean
  failureClass?: string
  executionProvenance?: unknown
  providers?: unknown[]
  error?: RuntimeErrorPayload
}
