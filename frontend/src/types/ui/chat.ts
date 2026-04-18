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
  /** Rust runtime epoch from `POST /chat` when present; aligns with public status snapshot. */
  runtimeSessionVersion?: number
  usage?: {
    inputTokens?: number
    outputTokens?: number
  }
}
