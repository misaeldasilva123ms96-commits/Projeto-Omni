import { create } from 'zustand'
import type { ChatMode, RuntimeMetadata } from '../types'

export type ConsoleAction = 'pesquisa' | 'pensar' | 'executar' | 'objetivos'
export type ConsoleTab = 'plano' | 'simulacao' | 'raciocinio'
export type ConsolePanelView = 'chat' | 'history' | 'memory' | 'simulation' | 'insights' | 'logs' | 'settings'
export type SidebarItem =
  | 'nova-conversa'
  | 'historico'
  | 'memoria'
  | 'simulacoes'
  | 'brainstorm'
  | 'analisar-dados'
  | 'criar-plano'
  | 'executar-tarefa'
  | 'insights'
  | 'logs'
  | 'configuracoes-ia'

export type NavItem = {
  id: SidebarItem
  label: string
  description: string
}

export type RuntimeGraphPoint = {
  label: string
  confidence: number
  execution: number
  memory: number
}

export type RuntimeConsoleMockState = {
  currentGoal: string
  goalProgress: number
  pathsConsidered: number
  rankedDecisions: string[]
  runId: string
  memoryStatus: string
  strategy: string
  confidence: number
  executionTime: string
  evolution: RuntimeGraphPoint[]
}

type RuntimeConsoleState = {
  activeAction: ConsoleAction
  activeTopAction: ConsoleAction
  activeSidebarItem: SidebarItem
  activeTab: ConsoleTab
  currentMode: ChatMode
  isSending: boolean
  lastError: string | null
  lastRuntimeMetadata: RuntimeMetadata | null
  panelView: ConsolePanelView
  selectedTool: SidebarItem | null
  uiNotice: string | null
  clearUiNotice: () => void
  resetConversation: () => void
  selectBottomTab: (tab: ConsoleTab) => void
  selectSidebarItem: (item: SidebarItem) => void
  selectTopAction: (action: ConsoleAction) => void
  setActiveAction: (action: ConsoleAction) => void
  setActiveSidebarItem: (item: SidebarItem) => void
  setActiveTab: (tab: ConsoleTab) => void
  setCurrentMode: (mode: ChatMode) => void
  setIsSending: (isSending: boolean) => void
  setLastError: (lastError: string | null) => void
  setRuntimeMetadata: (metadata: RuntimeMetadata | null) => void
  setUiNotice: (uiNotice: string | null) => void
}

export const TOP_ACTIONS: Array<{ id: ConsoleAction; label: string }> = [
  { id: 'pesquisa', label: 'Pesquisa' },
  { id: 'pensar', label: 'Pensar' },
  { id: 'executar', label: 'Executar' },
  { id: 'objetivos', label: 'Objetivos' },
]

export const BOTTOM_TABS: Array<{ id: ConsoleTab; label: string }> = [
  { id: 'plano', label: 'Plano' },
  { id: 'simulacao', label: 'Simulação' },
  { id: 'raciocinio', label: 'Raciocínio' },
]

export const CONVERSATION_ITEMS: NavItem[] = [
  { id: 'nova-conversa', label: 'Nova conversa', description: 'Abrir uma sessão cognitiva nova.' },
  { id: 'historico', label: 'Histórico', description: 'Revisar sessões e execuções passadas.' },
  { id: 'memoria', label: 'Memória', description: 'Inspecionar contexto e retenção ativa.' },
  { id: 'simulacoes', label: 'Simulações', description: 'Comparar alternativas antes da execução.' },
]

export const TOOL_ITEMS: NavItem[] = [
  { id: 'brainstorm', label: 'Brainstorm', description: 'Explorar caminhos e hipóteses.' },
  { id: 'analisar-dados', label: 'Analisar dados', description: 'Examinar sinais e métricas.' },
  { id: 'criar-plano', label: 'Criar plano', description: 'Transformar metas em passos.' },
  { id: 'executar-tarefa', label: 'Executar tarefa', description: 'Disparar ações do runtime.' },
  { id: 'insights', label: 'Insights', description: 'Destacar padrões de decisão.' },
  { id: 'logs', label: 'Logs', description: 'Abrir rastros e diagnósticos.' },
  { id: 'configuracoes-ia', label: 'Configurações IA', description: 'Ajustar políticas e perfis.' },
]

export const mockRuntimeState: RuntimeConsoleMockState = {
  currentGoal: 'Criar uma plataforma SaaS com runtime cognitivo auditável.',
  goalProgress: 0.4,
  pathsConsidered: 3,
  rankedDecisions: [
    'Definir proposta e validar posicionamento antes de escalar.',
    'Pesquisar concorrentes e sinais de retenção.',
    'Evitar engenharia prematura sem feedback real.',
  ],
  runId: '893.7f004e65007',
  memoryStatus: 'active',
  strategy: 'comparative_analysis',
  confidence: 0.87,
  executionTime: '1.32s',
  evolution: [
    { label: '-3 anos', confidence: 0.18, execution: 0.12, memory: 0.09 },
    { label: '-2 anos', confidence: 0.66, execution: 0.47, memory: 0.2 },
    { label: '-1 ano', confidence: 0.62, execution: 0.61, memory: 0.45 },
    { label: 'Agora', confidence: 0.88, execution: 0.79, memory: 0.53 },
  ],
}

const sidebarPanelView: Record<SidebarItem, ConsolePanelView> = {
  'nova-conversa': 'chat',
  historico: 'history',
  memoria: 'memory',
  simulacoes: 'simulation',
  brainstorm: 'chat',
  'analisar-dados': 'chat',
  'criar-plano': 'chat',
  'executar-tarefa': 'chat',
  insights: 'insights',
  logs: 'logs',
  'configuracoes-ia': 'settings',
}

export const useRuntimeConsoleStore = create<RuntimeConsoleState>((set) => ({
  activeAction: 'pensar',
  activeTopAction: 'pensar',
  activeSidebarItem: 'nova-conversa',
  activeTab: 'plano',
  currentMode: 'chat',
  isSending: false,
  lastError: null,
  lastRuntimeMetadata: null,
  panelView: 'chat',
  selectedTool: null,
  uiNotice: null,
  clearUiNotice: () => set({ uiNotice: null }),
  resetConversation: () => set({
    activeSidebarItem: 'nova-conversa',
    lastError: null,
    lastRuntimeMetadata: null,
    panelView: 'chat',
    selectedTool: null,
    uiNotice: 'Nova conversa iniciada. O estado local da sessão foi limpo.',
  }),
  selectBottomTab: (activeTab) => set({ activeTab, uiNotice: null }),
  selectSidebarItem: (activeSidebarItem) => set({
    activeSidebarItem,
    panelView: sidebarPanelView[activeSidebarItem],
    selectedTool: TOOL_ITEMS.some((item) => item.id === activeSidebarItem) ? activeSidebarItem : null,
    uiNotice: activeSidebarItem === 'nova-conversa' ? null : null,
  }),
  selectTopAction: (activeAction) => set({
    activeAction,
    activeTopAction: activeAction,
    currentMode: activeAction === 'pesquisa' ? 'pesquisa' : activeAction === 'executar' ? 'agente' : 'chat',
    uiNotice: null,
  }),
  setActiveAction: (activeAction) => set({ activeAction, activeTopAction: activeAction }),
  setActiveSidebarItem: (activeSidebarItem) => set({
    activeSidebarItem,
    panelView: sidebarPanelView[activeSidebarItem],
  }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setCurrentMode: (currentMode) => set({ currentMode }),
  setIsSending: (isSending) => set({ isSending }),
  setLastError: (lastError) => set({ lastError }),
  setRuntimeMetadata: (lastRuntimeMetadata) => set({ lastRuntimeMetadata }),
  setUiNotice: (uiNotice) => set({ uiNotice }),
}))
