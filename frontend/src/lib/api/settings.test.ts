import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestJsonWithAuth = vi.hoisted(() => vi.fn())

vi.mock('./client', () => ({ requestJsonWithAuth }))

import { listProviders, saveProvider } from './settings'

describe('settings API client', () => {
  beforeEach(() => requestJsonWithAuth.mockReset())

  it('uses the shared authenticated client for reads', async () => {
    requestJsonWithAuth.mockResolvedValue({ providers: [{ provider: 'openai', configured: true }] })
    await expect(listProviders()).resolves.toEqual([{ provider: 'openai', configured: true }])
    expect(requestJsonWithAuth).toHaveBeenCalledWith('/api/v1/settings/providers', undefined)
  })

  it('uses uniform JSON requests for writes', async () => {
    requestJsonWithAuth.mockResolvedValue({ provider: 'openai', configured: true, updated_at: 1 })
    await saveProvider({ provider: ' OpenAI ', api_key: 'secret' })
    expect(requestJsonWithAuth).toHaveBeenCalledWith('/api/v1/settings/providers', {
      method: 'POST',
      body: JSON.stringify({ provider: 'openai', api_key: 'secret' }),
    })
  })
})
