/**
 * Chat transport — `POST /chat` (Rust → Python subprocess).
 *
 * Wire contract: `message` required; optional `client_session_id` echoed by Rust when present
 * (see `docs/backend/chat-session-contract.md`).
 */
import type { ChatApiResponse } from '../../types'
import { parseWireChatPayload } from './adapters'
import {
  API_BASE_URL,
  buildConfigurationError,
  fetchWithTimeout,
  parseResponseBody,
} from './client'

export type ChatClientContext = {
  /** Local UI session id; sent as `client_session_id` when set (optional on wire). */
  sessionId?: string
}

export async function sendOmniMessage(
  message: string,
  clientContext?: ChatClientContext,
): Promise<ChatApiResponse> {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const trimmed = message.trim()
  if (!trimmed) {
    throw new Error('Message must not be empty.')
  }

  const body: Record<string, string> = { message: trimmed }
  const sid = clientContext?.sessionId?.trim()
  if (sid) {
    body.client_session_id = sid
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(
      text.trim()
        ? `Omni request failed (${res.status}): ${text}`
        : `Omni request failed with status ${res.status}.`,
    )
  }

  const payload = await parseResponseBody(res)
  return parseWireChatPayload(payload)
}
