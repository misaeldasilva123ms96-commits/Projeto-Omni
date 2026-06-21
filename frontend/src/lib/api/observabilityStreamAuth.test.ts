import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildObservabilityStreamUrl,
  requestObservabilityStreamTicket,
} from './observability'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('observability stream authentication', () => {
  it('requests a stream ticket through an authenticated POST without URL credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ticket: 'opaque-reference',
      expires_in_seconds: 30,
    }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await requestObservabilityStreamTicket({
      Authorization: 'Bearer session-value',
    })

    expect(result).toEqual({
      ticket: 'opaque-reference',
      expires_in_seconds: 30,
    })
    const [input, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(input).toMatch(/\/api\/observability\/stream-ticket$/)
    expect(input).not.toMatch(/token|authorization|session-value/i)
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({
      Accept: 'application/json',
      Authorization: 'Bearer session-value',
    })
  })

  it('builds an EventSource URL with only the opaque ticket reference', () => {
    const url = buildObservabilityStreamUrl('opaque-reference')

    expect(url).toContain('/api/observability/stream?')
    expect(url).toContain('ticket=opaque-reference')
    expect(url).toContain('interval=2')
    expect(url).not.toMatch(/[?&](?:token|authorization|api_key)=/i)
  })

  it('does not include response bodies or ticket values in request errors', async () => {
    const jwtLikeValue = ['header', 'payload', 'signature'].join('.')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ticket: 'opaque-reference',
      error: jwtLikeValue,
    }), { status: 401 })))

    await expect(requestObservabilityStreamTicket({
      Authorization: 'Bearer session-value',
    })).rejects.toThrow('Observability stream ticket request failed (401).')
  })
})
