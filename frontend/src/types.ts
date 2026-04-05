export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
}

export type ChatApiResponse = {
  response: string
  session_id: string
  source: string
}
