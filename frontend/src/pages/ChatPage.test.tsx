import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from './ChatPage'

const mocks = vi.hoisted(() => ({
  sendOmniMessage: vi.fn(),
}))

vi.mock('../features/chat', () => ({
  sendOmniMessage: mocks.sendOmniMessage,
  chatApiResponseToUi: (response: {
    response: string
    runtime_mode?: string
    runtime_reason?: string
    execution_path_used?: string
    provider_actual?: string
  }) => ({
    text: response.response,
    runtimeMode: response.runtime_mode,
    runtimeReason: response.runtime_reason,
    executionPathUsed: response.execution_path_used,
    providerActual: response.provider_actual,
    wireHealth: 'ok',
  }),
}))

vi.mock('../features/runtime', () => ({
  publicStatusV1ToUiRuntimeStatus: vi.fn(() => null),
}))

vi.mock('../components/status/RuntimePanel', () => ({
  RuntimePanel: () => <aside data-testid="runtime-panel">Runtime panel</aside>,
}))

vi.mock('../hooks/useCognitiveTelemetry', () => ({
  useCognitiveTelemetry: () => ({ publicRuntime: null }),
}))

vi.mock('../lib/env', () => ({
  API_BASE_URL: 'http://127.0.0.1:3001',
  API_CONFIGURATION_ERROR: null,
  PUBLIC_APP_URL: 'http://127.0.0.1:4173',
  PUBLIC_APP_URL_CONFIGURATION_ERROR: '',
  SUPABASE_ANON_KEY: 'test-key',
  SUPABASE_CONFIGURATION_ERROR: '',
  SUPABASE_URL: 'http://127.0.0.1:54321',
  canUseApi: () => true,
  canUseSupabase: () => true,
}))

vi.mock('../lib/omniData', () => ({
  bootstrapOmniUser: vi.fn(() => Promise.resolve()),
  syncChatSessionToSupabase: vi.fn(() => Promise.resolve()),
}))

describe('ChatPage runtime chat integration', () => {
  beforeEach(() => {
    localStorage.clear()
    mocks.sendOmniMessage.mockReset()
  })

  it('handles API success and streams assistant response', async () => {
    mocks.sendOmniMessage.mockResolvedValue({
      response: 'Resposta do runtime Omni.',
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      runtime_reason: 'node_execution',
      execution_path_used: 'node_execution',
      provider_actual: 'openai',
    })

    render(<ChatPage mode="chat" onChangeMode={vi.fn()} onChangeView={vi.fn()} view="chat" />)

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Olá Omni')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    expect(mocks.sendOmniMessage).toHaveBeenCalledWith('Olá Omni', expect.any(Object))
    await waitFor(() => expect(screen.getByText(/Resposta do runtime Omni/i)).toBeInTheDocument(), { timeout: 4000 })
    expect(screen.getByText(/Mode: FULL_COGNITIVE_RUNTIME/i)).toBeInTheDocument()
  }, 10_000)

  it('handles API error safely', async () => {
    mocks.sendOmniMessage.mockRejectedValue(new Error('backend offline'))

    render(<ChatPage mode="chat" onChangeMode={vi.fn()} onChangeView={vi.fn()} view="chat" />)

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Falhe com segurança')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    await waitFor(() => expect(screen.getByText(/backend offline/i)).toBeInTheDocument(), { timeout: 4000 })
    expect(screen.getByText(/Não consegui processar sua mensagem/i)).toBeInTheDocument()
  }, 10_000)
})
