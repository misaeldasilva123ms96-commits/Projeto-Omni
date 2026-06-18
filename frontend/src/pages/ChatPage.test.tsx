import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OmniShell } from '../components/shell/OmniShell'
import type { RenderOmniShell } from '../app/App'
import { ChatPage } from './ChatPage'

const mocks = vi.hoisted(() => ({
  sendOmniMessage: vi.fn(),
  runtimePanelProps: vi.fn(),
}))

vi.mock('../features/chat', () => ({
  sendOmniMessage: mocks.sendOmniMessage,
  chatApiResponseToUi: (response: {
    response: string
    runtime_mode?: string
    runtime_reason?: string
    execution_path_used?: string
    provider_actual?: string
    cognitive_runtime_inspection?: Record<string, unknown>
    usage?: { input_tokens?: number; output_tokens?: number }
  }) => ({
    text: response.response,
    runtimeMode: response.runtime_mode,
    runtimeReason: response.runtime_reason,
    executionPathUsed: response.execution_path_used,
    providerActual: response.provider_actual,
    cognitiveRuntimeInspection: response.cognitive_runtime_inspection,
    usage: response.usage
      ? {
          inputTokens: response.usage.input_tokens,
          outputTokens: response.usage.output_tokens,
        }
      : undefined,
    commands: [],
    tools: [],
    wireHealth: 'ok',
  }),
}))

vi.mock('../features/runtime', () => ({
  publicStatusV1ToUiRuntimeStatus: vi.fn(() => null),
}))

vi.mock('../components/status/RuntimePanel', () => ({
  RuntimePanel: (props: {
    inspectorData?: {
      summary?: {
        runtime_mode?: string
        provider_attempted?: boolean | null
        request_id?: string | null
      }
    } | null
  }) => {
    mocks.runtimePanelProps(props)
    return (
      <aside data-testid="runtime-panel">
        {props.inspectorData?.summary?.runtime_mode ?? 'não disponível'}
        {' | '}
        {String(props.inspectorData?.summary?.provider_attempted ?? 'não disponível')}
        {' | '}
        {props.inspectorData?.summary?.request_id ?? 'não disponível'}
      </aside>
    )
  },
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
  fetchChatMessages: vi.fn(() => Promise.resolve([])),
  fetchChatSessions: vi.fn(() => Promise.resolve([])),
  syncChatSessionToSupabase: vi.fn(() => Promise.resolve()),
}))

describe('ChatPage runtime chat integration', () => {
  const renderShell: RenderOmniShell = (content, options) => (
    <OmniShell {...options}>{content}</OmniShell>
  )

  beforeEach(() => {
    localStorage.clear()
    mocks.sendOmniMessage.mockReset()
    mocks.runtimePanelProps.mockClear()
  })

  it('handles API success and streams assistant response', async () => {
    mocks.sendOmniMessage.mockResolvedValue({
      response: 'Resposta do runtime Omni.',
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      runtime_reason: 'node_execution',
      execution_path_used: 'node_execution',
      provider_actual: 'openai',
    })

    render(
      <ChatPage
        mode="chat"
        onChangeMode={vi.fn()}
        onChangeView={vi.fn()}
        renderShell={renderShell}
        view="chat"
      />,
    )

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Olá Omni')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    expect(mocks.sendOmniMessage).toHaveBeenCalledWith('Olá Omni', expect.any(Object))
    await waitFor(() => expect(screen.getByText(/Resposta do runtime Omni/i)).toBeInTheDocument(), { timeout: 4000 })
    expect(screen.getByText(/Mode: FULL_COGNITIVE_RUNTIME/i)).toBeInTheDocument()
  }, 10_000)

  it('handles API error safely', async () => {
    mocks.sendOmniMessage.mockRejectedValue(new Error('backend offline'))

    render(
      <ChatPage
        mode="chat"
        onChangeMode={vi.fn()}
        onChangeView={vi.fn()}
        renderShell={renderShell}
        view="chat"
      />,
    )

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Falhe com segurança')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    await waitFor(() => expect(screen.getByText(/backend offline/i)).toBeInTheDocument(), { timeout: 4000 })
    expect(screen.getByText(/Não consegui processar sua mensagem/i)).toBeInTheDocument()
  }, 10_000)

  it('binds the latest live runtime response to the inspector snapshot', async () => {
    mocks.sendOmniMessage.mockResolvedValue({
      response: 'Resposta com runtime.',
      cognitive_runtime_inspection: {
        runtime_mode: 'FULL_COGNITIVE_RUNTIME',
        runtime_reason: 'node_execution',
        llm_provider_attempted: true,
        llm_provider_succeeded: true,
        request_id: 'req-chat-live',
      },
      usage: {
        input_tokens: 21,
        output_tokens: 9,
      },
    })

    render(
      <ChatPage
        mode="chat"
        onChangeMode={vi.fn()}
        onChangeView={vi.fn()}
        renderShell={renderShell}
        view="chat"
      />,
    )

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Mostre o runtime')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    await waitFor(() => {
      expect(screen.getByTestId('runtime-panel')).toHaveTextContent(
        'FULL_COGNITIVE_RUNTIME | true | req-chat-live',
      )
    }, { timeout: 4000 })
  }, 10_000)

  it('preserves chat success when runtime inspector metadata is absent', async () => {
    mocks.sendOmniMessage.mockResolvedValue({
      response: 'Resposta sem metadados.',
    })

    render(
      <ChatPage
        mode="chat"
        onChangeMode={vi.fn()}
        onChangeView={vi.fn()}
        renderShell={renderShell}
        view="chat"
      />,
    )

    await userEvent.type(screen.getByPlaceholderText('Digite uma mensagem...'), 'Continue sem metadados')
    await userEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    await waitFor(() => expect(screen.getByText('Resposta sem metadados.')).toBeInTheDocument(), { timeout: 4000 })
    expect(screen.getByTestId('runtime-panel')).toHaveTextContent(
      'não disponível | não disponível | não disponível',
    )
  }, 10_000)
})
