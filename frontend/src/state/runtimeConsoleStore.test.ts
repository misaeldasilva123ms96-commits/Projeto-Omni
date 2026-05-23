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
})
