import { beforeEach, describe, expect, it } from 'vitest'
import {
  CHAT_STORAGE_KEY,
  CHAT_STORAGE_VERSION,
  LEGACY_CHAT_STORAGE_KEY,
  createClientId,
  loadStoredChatState,
  persistStoredChatState,
} from './chatStorage'

describe('chat storage schema', () => {
  beforeEach(() => localStorage.clear())

  it('restores only structurally valid messages and bounded metadata', () => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({
      version: CHAT_STORAGE_VERSION,
      input: 'draft',
      sessionId: 'sessao-safe-1',
      requestState: 'loading',
      messages: [
        {
          id: 'message-1',
          role: 'assistant',
          content: 'safe response',
          createdAt: '2026-07-14T12:00:00.000Z',
          metadata: {
            matchedCommands: ['status'],
            matchedTools: ['read_file'],
            __proto__: { polluted: true },
          },
          isLoading: true,
        },
        { id: '../bad', role: 'attacker', content: 42, createdAt: 'never' },
        null,
      ],
    }))

    const restored = loadStoredChatState()

    expect(restored.sessionId).toBe('sessao-safe-1')
    expect(restored.requestState).toBe('idle')
    expect(restored.messages).toHaveLength(1)
    expect(restored.messages[0]).toMatchObject({
      id: 'message-1',
      role: 'assistant',
      content: 'safe response',
      isLoading: false,
    })
    expect(Object.prototype).not.toHaveProperty('polluted')
  })

  it('rejects unsupported versions and oversized payloads fail closed', () => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({
      version: CHAT_STORAGE_VERSION + 1,
      sessionId: 'future-session',
    }))
    expect(loadStoredChatState().sessionId).not.toBe('future-session')
    expect(localStorage.getItem(CHAT_STORAGE_KEY)).toBeNull()

    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({
      version: CHAT_STORAGE_VERSION,
      input: 'x'.repeat(1_000_100),
      sessionId: 'oversized-session',
    }))
    expect(loadStoredChatState().sessionId).not.toBe('oversized-session')
    expect(localStorage.getItem(CHAT_STORAGE_KEY)).toBeNull()
  })

  it('persists a bounded snapshot without transient message state', () => {
    persistStoredChatState({
      input: 'draft',
      lastMetadata: null,
      messages: Array.from({ length: 205 }, (_, index) => ({
        id: `message-${index}`,
        role: 'user',
        content: `content-${index}`,
        createdAt: '2026-07-14T12:00:00.000Z',
        isLoading: true,
        isNew: true,
      })),
      requestState: 'loading',
      sessionId: 'sessao-safe-2',
    })

    const canonical = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '{}')
    const legacy = JSON.parse(localStorage.getItem(LEGACY_CHAT_STORAGE_KEY) || '{}')
    expect(canonical.messages).toHaveLength(200)
    expect(canonical.messages[0].id).toBe('message-5')
    expect(canonical.messages[0]).not.toHaveProperty('isLoading')
    expect(canonical.requestState).toBe('idle')
    expect(legacy).toEqual(canonical)
  })

  it('creates safe client ids', () => {
    expect(createClientId('sessao')).toMatch(/^sessao-[A-Za-z0-9-]+$/)
  })
})
