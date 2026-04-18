/**
 * Chat transport — prefers `POST /api/v1/chat`, falls back to legacy `POST /chat` when the
 * versioned route is unavailable (404/405/501). See `docs/frontend/public-chat-adoption.md`.
 *
 * Wire: `message` required; optional `client_session_id`; v1 adds optional `client_context`.
 */
import type { ChatApiResponse } from '../../types'
import { parseWireChatPayload } from './adapters'
import {
  API_BASE_URL,
  buildConfigurationError,
  fetchWithTimeout,
  parseResponseBody,
} from './client'

const CHAT_V1_PATH = '/api/v1/chat'
const CHAT_LEGACY_PATH = '/chat'

export type ChatClientContext = {
  /** Local UI session id; sent as `client_session_id` when set (optional on wire). */
  sessionId?: string
}

function legacyChatOnlyFromEnv(): boolean {
  return import.meta.env.VITE_OMNI_CHAT_LEGACY_ONLY === 'true'
}

function shouldFallbackToLegacyChat(status: number): boolean {
  return status === 404 || status === 405 || status === 501
}

async function postChatJson(path: string, body: unknown): Promise<Response> {
  return fetchWithTimeout(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

function chatHttpErrorMessage(status: number, bodyText: string): string {
  const trimmed = bodyText.trim()
  return trimmed
    ? `Omni request failed (${status}): ${trimmed}`
    : `Omni request failed with status ${status}.`
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

  const sid = clientContext?.sessionId?.trim()
  const legacyBody: Record<string, string> = { message: trimmed }
  if (sid) {
    legacyBody.client_session_id = sid
  }

  async function sendLegacy(): Promise<ChatApiResponse> {
    const res = await postChatJson(CHAT_LEGACY_PATH, legacyBody)
    if (!res.ok) {
      const text = await res.text()
      throw new Error(chatHttpErrorMessage(res.status, text))
    }
    const payload = await parseResponseBody(res)
    return parseWireChatPayload(payload)
  }

  if (legacyChatOnlyFromEnv()) {
    return sendLegacy()
  }

  const v1Body: Record<string, unknown> = {
    message: trimmed,
    client_context: { source: 'frontend' },
    ...(sid ? { client_session_id: sid } : {}),
  }

  const v1Res = await postChatJson(CHAT_V1_PATH, v1Body)
  if (v1Res.ok) {
    const payload = await parseResponseBody(v1Res)
    return parseWireChatPayload(payload)
  }

  if (shouldFallbackToLegacyChat(v1Res.status)) {
    if (import.meta.env.DEV) {
      console.debug(
        `[omni:chat] ${CHAT_V1_PATH} returned ${v1Res.status}; falling back to ${CHAT_LEGACY_PATH}`,
      )
    }
    return sendLegacy()
  }

  const text = await v1Res.text()
  throw new Error(chatHttpErrorMessage(v1Res.status, text))
}
