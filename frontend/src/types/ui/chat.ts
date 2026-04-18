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
  usage?: {
    inputTokens?: number
    outputTokens?: number
  }
}
