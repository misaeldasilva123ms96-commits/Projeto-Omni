import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const requestTicket = vi.fn().mockResolvedValue({
  ticket: 'opaque-reference',
  expires_in_seconds: 30,
})
let authStateCallback: (
  event: string,
  session: { access_token: string } | null,
) => void = () => {}

vi.mock('../lib/api/observability', () => ({
  buildObservabilityStreamUrl: (ticket: string) =>
    `https://api.example.test/api/observability/stream?ticket=${encodeURIComponent(ticket)}&interval=2`,
  requestObservabilityStreamTicket: requestTicket,
}))

vi.mock('../lib/env', () => ({
  API_BASE_URL: 'https://api.example.test',
}))

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'session-value' } },
        error: null,
      }),
      onAuthStateChange: vi.fn((callback) => {
        authStateCallback = callback
        return {
          data: {
            subscription: {
              unsubscribe: vi.fn(),
            },
          },
        }
      }),
    },
  },
}))

const eventSourceUrls: string[] = []

class EventSourceMock {
  onerror: ((event: Event) => void) | null = null

  constructor(url: string | URL) {
    eventSourceUrls.push(String(url))
  }

  addEventListener() {}
  close() {}
}

afterEach(() => {
  eventSourceUrls.length = 0
  requestTicket.mockClear()
  requestTicket.mockResolvedValue({
    ticket: 'opaque-reference',
    expires_in_seconds: 30,
  })
  vi.unstubAllGlobals()
})

describe('useObservabilityStream', () => {
  it('opens EventSource with an opaque ticket and never with the session token', async () => {
    vi.stubGlobal('EventSource', EventSourceMock)
    const { useObservabilityStream } = await import('./useObservabilityStream')

    const { unmount } = renderHook(() => useObservabilityStream(true))

    await waitFor(() => expect(eventSourceUrls).toHaveLength(1))
    expect(requestTicket).toHaveBeenCalledWith({
      Authorization: 'Bearer session-value',
    })
    expect(eventSourceUrls[0]).toContain('ticket=opaque-reference')
    expect(eventSourceUrls[0]).not.toContain('session-value')
    expect(eventSourceUrls[0]).not.toMatch(/[?&]token=/i)

    unmount()
  })

  it('discards an in-flight ticket when the session token changes', async () => {
    let resolveFirstTicket: (value: { ticket: string, expires_in_seconds: number }) => void = () => {}
    requestTicket
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveFirstTicket = resolve
      }))
      .mockResolvedValueOnce({
        ticket: 'new-session-reference',
        expires_in_seconds: 30,
      })
    vi.stubGlobal('EventSource', EventSourceMock)
    const { useObservabilityStream } = await import('./useObservabilityStream')

    const { unmount } = renderHook(() => useObservabilityStream(true))
    await waitFor(() => expect(requestTicket).toHaveBeenCalledTimes(1))

    act(() => {
      authStateCallback('TOKEN_REFRESHED', { access_token: 'refreshed-session-value' })
    })
    resolveFirstTicket({
      ticket: 'old-session-reference',
      expires_in_seconds: 30,
    })

    await waitFor(() => expect(requestTicket).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(eventSourceUrls).toHaveLength(1))
    expect(eventSourceUrls[0]).toContain('ticket=new-session-reference')
    expect(eventSourceUrls[0]).not.toContain('old-session-reference')

    unmount()
  })
})
