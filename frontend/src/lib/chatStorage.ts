import type { ChatMessage, ChatRequestState, RuntimeMetadata } from '../types'
import { readMigratedStorage, removeMigratedStorage, writeMigratedStorage } from './storageKeyMigration'

export const CHAT_STORAGE_KEY = 'omni-chat-state-v3'
export const LEGACY_CHAT_STORAGE_KEY = 'omini-chat-state-v3'
export const CHAT_STORAGE_VERSION = 4

const MAX_STORAGE_BYTES = 1_000_000
const MAX_MESSAGES = 200
const MAX_INPUT_CHARS = 16_000
const MAX_MESSAGE_CHARS = 64_000
const MAX_ID_CHARS = 256
const MAX_METADATA_DEPTH = 6
const MAX_METADATA_KEYS = 200
const MAX_METADATA_ARRAY = 200
const SAFE_ID = /^[A-Za-z0-9._:-]+$/

export type StoredChatMessage = ChatMessage & {
  isLoading?: boolean
  isNew?: boolean
}

export type StoredChatState = {
  version?: number
  input: string
  lastMetadata: RuntimeMetadata | null
  messages: StoredChatMessage[]
  requestState: ChatRequestState
  sessionId: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function boundedString(value: unknown, maxChars: number): string | undefined {
  if (typeof value !== 'string' || value.length > maxChars) return undefined
  return value
}

function validId(value: unknown): string | undefined {
  const candidate = boundedString(value, MAX_ID_CHARS)?.trim()
  if (!candidate || !SAFE_ID.test(candidate)) return undefined
  return candidate
}

function sanitizeJsonValue(value: unknown, depth = 0): unknown {
  if (value === null || typeof value === 'boolean') return value
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined
  if (typeof value === 'string') return value.slice(0, MAX_MESSAGE_CHARS)
  if (depth >= MAX_METADATA_DEPTH) return undefined
  if (Array.isArray(value)) {
    return value
      .slice(0, MAX_METADATA_ARRAY)
      .map(item => sanitizeJsonValue(item, depth + 1))
      .filter(item => item !== undefined)
  }
  if (!isRecord(value)) return undefined

  const sanitized: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(value).slice(0, MAX_METADATA_KEYS)) {
    if (key === '__proto__' || key === 'prototype' || key === 'constructor') continue
    const next = sanitizeJsonValue(item, depth + 1)
    if (next !== undefined) sanitized[key] = next
  }
  return sanitized
}

function sanitizeMetadata(value: unknown): RuntimeMetadata | null {
  const sanitized = sanitizeJsonValue(value)
  if (!isRecord(sanitized)) return null

  const matchedCommands = Array.isArray(sanitized.matchedCommands)
    ? sanitized.matchedCommands.filter(item => typeof item === 'string').slice(0, 100)
    : []
  const matchedTools = Array.isArray(sanitized.matchedTools)
    ? sanitized.matchedTools.filter(item => typeof item === 'string').slice(0, 100)
    : []
  return {
    ...sanitized,
    matchedCommands,
    matchedTools,
  } as RuntimeMetadata
}

function sanitizeMessage(value: unknown): StoredChatMessage | null {
  if (!isRecord(value)) return null
  const id = validId(value.id)
  const role = value.role
  const content = boundedString(value.content, MAX_MESSAGE_CHARS)
  const createdAt = boundedString(value.createdAt, 64)
  if (
    !id
    || !['user', 'assistant', 'system'].includes(String(role))
    || content === undefined
    || !createdAt
    || !Number.isFinite(Date.parse(createdAt))
  ) {
    return null
  }

  const requestState = ['completed', 'failed', 'degraded'].includes(String(value.requestState))
    ? value.requestState as ChatMessage['requestState']
    : undefined
  const metadata = sanitizeMetadata(value.metadata)
  return {
    id,
    role: role as ChatMessage['role'],
    content,
    createdAt: new Date(createdAt).toISOString(),
    ...(metadata ? { metadata } : {}),
    ...(requestState ? { requestState } : {}),
    isLoading: false,
    isNew: false,
  }
}

export function createClientId(prefix = ''): string {
  const cryptoApi = globalThis.crypto
  let randomPart = ''
  if (typeof cryptoApi?.randomUUID === 'function') {
    randomPart = cryptoApi.randomUUID()
  } else if (typeof cryptoApi?.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    cryptoApi.getRandomValues(bytes)
    randomPart = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
  } else {
    randomPart = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`
  }
  return prefix ? `${prefix}-${randomPart.slice(0, 32)}` : randomPart
}

export function buildEmptyChatState(): StoredChatState {
  return {
    input: '',
    lastMetadata: null,
    messages: [],
    requestState: 'idle',
    sessionId: createClientId('sessao'),
  }
}

export function loadStoredChatState(): StoredChatState {
  const baseState = buildEmptyChatState()
  let raw: string | null = null
  try {
    raw = readMigratedStorage(CHAT_STORAGE_KEY, LEGACY_CHAT_STORAGE_KEY)
  } catch {
    return baseState
  }
  if (!raw) return baseState
  if (new TextEncoder().encode(raw).byteLength > MAX_STORAGE_BYTES) {
    try {
      removeMigratedStorage(CHAT_STORAGE_KEY, LEGACY_CHAT_STORAGE_KEY)
    } catch {
      // Storage can be unavailable while the in-memory chat remains usable.
    }
    return baseState
  }

  try {
    const parsed: unknown = JSON.parse(raw)
    if (!isRecord(parsed)) throw new TypeError('chat storage must be an object')
    if (
      parsed.version !== undefined
      && (!Number.isInteger(parsed.version) || Number(parsed.version) < 1 || Number(parsed.version) > CHAT_STORAGE_VERSION)
    ) {
      throw new TypeError('unsupported chat storage version')
    }

    const messages = Array.isArray(parsed.messages)
      ? parsed.messages.slice(-MAX_MESSAGES).map(sanitizeMessage).filter((item): item is StoredChatMessage => Boolean(item))
      : []
    const sessionId = validId(parsed.sessionId) ?? baseState.sessionId
    const requestState = parsed.requestState === 'error' ? 'error' : 'idle'
    return {
      version: typeof parsed.version === 'number' ? parsed.version : undefined,
      input: boundedString(parsed.input, MAX_INPUT_CHARS) ?? '',
      lastMetadata: sanitizeMetadata(parsed.lastMetadata),
      messages,
      requestState,
      sessionId,
    }
  } catch {
    try {
      removeMigratedStorage(CHAT_STORAGE_KEY, LEGACY_CHAT_STORAGE_KEY)
    } catch {
      // Storage can be unavailable while the in-memory chat remains usable.
    }
    return baseState
  }
}

export function persistStoredChatState(state: StoredChatState): void {
  const snapshot: StoredChatState = {
    version: CHAT_STORAGE_VERSION,
    input: state.input.slice(0, MAX_INPUT_CHARS),
    lastMetadata: sanitizeMetadata(state.lastMetadata),
    messages: state.messages.slice(-MAX_MESSAGES).map(({ isLoading: _isLoading, isNew: _isNew, ...message }) => message),
    requestState: state.requestState === 'error' ? 'error' : 'idle',
    sessionId: validId(state.sessionId) ?? createClientId('sessao'),
  }
  try {
    const serialized = JSON.stringify(snapshot)
    if (new TextEncoder().encode(serialized).byteLength <= MAX_STORAGE_BYTES) {
      writeMigratedStorage(CHAT_STORAGE_KEY, LEGACY_CHAT_STORAGE_KEY, serialized)
    }
  } catch {
    // Quota and privacy-mode failures must not interrupt the active conversation.
  }
}
