/**
 * Chat transport — `POST /chat` (Rust → Python subprocess).
 *
 * Wire contract: Rust `ChatRequest` only deserializes `{ "message": string }`.
 * Client context (e.g. UI session id) is accepted for callers but is not sent on the wire
 * until the backend supports it (see `docs/frontend/integration-matrix.md`).
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
  /** Local UI session id; not forwarded to Rust today. */
  sessionId?: string
}

export async function sendOmniMessage(
  message: string,
  _clientContext?: ChatClientContext,
): Promise<ChatApiResponse> {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const trimmed = message.trim()
  if (!trimmed) {
    throw new Error('Message must not be empty.')
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: trimmed }),
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
