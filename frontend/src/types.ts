export type ChatRole = 'user' | 'assistant'
export type FeedbackValue = 'up' | 'down'

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  turnId?: string
  sessionId?: string
  feedback?: FeedbackValue | null
}

export type ChatApiRequest = {
  message: string
  user_id?: string
  session_id?: string
}

export type ChatApiResponse = {
  response: string
  session_id: string
  source: string
  turn_id?: string
  user_id?: string
  evolution_version?: number
}

export type FeedbackApiRequest = {
  turn_id: string
  value: FeedbackValue
  text?: string
  user_id?: string
  session_id?: string
}
