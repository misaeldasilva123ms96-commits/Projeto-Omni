import { beforeEach, describe, expect, it } from 'vitest'
import { useRuntimeConsoleStore } from './runtimeConsoleStore'

describe('runtimeConsoleStore', () => {
  beforeEach(() => {
    useRuntimeConsoleStore.setState({
      activeAction: 'pensar',
      activeSidebarItem: 'nova-conversa',
      activeTab: 'plano',
      currentMode: 'chat',
      isSending: false,
      lastError: null,
      lastRuntimeInspectorData: null,
      lastRuntimeMetadata: null,
      panelView: 'chat',
      selectedTool: null,
      uiNotice: null,
    })
  })

  it('selects top actions and maps runtime mode', () => {
    useRuntimeConsoleStore.getState().selectTopAction('pesquisa')
    expect(useRuntimeConsoleStore.getState().activeAction).toBe('pesquisa')
    expect(useRuntimeConsoleStore.getState().currentMode).toBe('pesquisa')

    useRuntimeConsoleStore.getState().selectTopAction('executar')
    expect(useRuntimeConsoleStore.getState().currentMode).toBe('agente')
  })

  it('selects sidebar state and panel view', () => {
    useRuntimeConsoleStore.getState().selectSidebarItem('memoria')
    expect(useRuntimeConsoleStore.getState().activeSidebarItem).toBe('memoria')
    expect(useRuntimeConsoleStore.getState().panelView).toBe('memory')
  })

  it('resets conversation state safely', () => {
    useRuntimeConsoleStore.getState().setRuntimeMetadata({
      matchedCommands: [],
      matchedTools: [],
      runtimeMode: 'FULL_COGNITIVE_RUNTIME',
    })
    useRuntimeConsoleStore.getState().resetConversation()
    expect(useRuntimeConsoleStore.getState().lastRuntimeMetadata).toBeNull()
    expect(useRuntimeConsoleStore.getState().activeSidebarItem).toBe('nova-conversa')
    expect(useRuntimeConsoleStore.getState().uiNotice).toContain('Nova conversa')
  })

  it('stores the latest normalized runtime inspector snapshot', () => {
    const snapshot = {
      summary: {
        runtime_mode: 'FULL_COGNITIVE_RUNTIME' as const,
        runtime_reason: 'node_execution',
        provider_attempted: true,
        provider_succeeded: true,
        fallback_triggered: false,
        tool_invoked: false,
        governance_decision: null,
        tokens_in: 10,
        tokens_out: 5,
        total_tokens: 15,
        latency_ms: 30,
        request_id: 'req-store-1',
        trace_id: null,
        created_at: null,
      },
      governance: null,
      tools: [],
      provider: null,
      providers: [],
      memory: null,
      oil: null,
      autonomy: null,
      autonomy_stats: null,
      logs: null,
    }

    useRuntimeConsoleStore.setState({ lastRuntimeInspectorData: snapshot })

    expect(useRuntimeConsoleStore.getState().lastRuntimeInspectorData).toEqual(snapshot)
    useRuntimeConsoleStore.getState().resetConversation()
    expect(useRuntimeConsoleStore.getState().lastRuntimeInspectorData).toBeNull()
  })
})
