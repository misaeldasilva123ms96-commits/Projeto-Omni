import { motion } from 'framer-motion'
import type { ChatMode, ConversationSummary } from '../../types'
import {
  CONVERSATION_ITEMS,
  TOOL_ITEMS,
  useRuntimeConsoleStore,
  type SidebarItem,
} from '../../state/runtimeConsoleStore'
import { getGlowState } from '../../lib/ui/glow'

type View = 'chat' | 'dashboard' | 'observability'

type SidebarProps = {
  activeConversationId?: string
  conversations: ConversationSummary[]
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onNewConversation?: () => void
  onSelectView: (view: View) => void
  onSidebarItemSelected?: (item: SidebarItem) => void
  view: View
}

const MODE_OPTIONS: Array<{ id: ChatMode; label: string }> = [
  { id: 'chat', label: 'Chat' },
  { id: 'pesquisa', label: 'Pesquisa' },
  { id: 'codigo', label: 'Código' },
  { id: 'agente', label: 'Agente' },
]

function SidebarIcon({ item }: { item: SidebarItem }) {
  const common = 'h-4 w-4'
  switch (item) {
    case 'nova-conversa':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
    case 'historico':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 8v5l3 2" /><path d="M21 12a9 9 0 1 1-3-6.7" /></svg>
    case 'memoria':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M8 7V5a2 2 0 1 1 4 0v2" /><path d="M16 7V5a2 2 0 1 1 4 0v2" /><path d="M4 9h16v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" /></svg>
    case 'simulacoes':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M5 5h14v14H5z" /><path d="M8 15l2-3 2 2 4-5" /></svg>
    case 'brainstorm':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0-3.6 10.8c.9.7 1.6 1.7 1.6 2.9h4c0-1.2.7-2.2 1.6-2.9A6 6 0 0 0 12 3Z" /><path d="M10 21h4M9 18h6" /></svg>
    case 'analisar-dados':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M5 19V9M12 19V5M19 19v-8" /></svg>
    case 'criar-plano':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>
    case 'executar-tarefa':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m8 5 11 7-11 7V5Z" /></svg>
    case 'insights':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M4 12h4l2-5 4 10 2-5h4" /></svg>
    case 'logs':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>
    case 'configuracoes-ia':
      return <svg className={common} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7Z" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.05V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-.4-1.04 1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.05-.4H3a2 2 0 1 1 0-4h.09c.4 0 .78-.15 1.05-.4a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6c.39 0 .77-.22 1-.6.26-.3.4-.67.4-1.05V3a2 2 0 1 1 4 0v.09c0 .39.14.76.4 1.05.23.38.61.6 1 .6a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c0 .39.22.77.6 1 .3.25.67.4 1.05.4H21a2 2 0 1 1 0 4h-.09c-.39 0-.76.15-1.05.4-.38.23-.6.61-.6 1Z" /></svg>
  }
}

function handleItemSelection(
  item: SidebarItem,
  onSelectView: (view: View) => void,
  onNewConversation?: () => void,
) {
  if (item === 'nova-conversa') {
    onNewConversation?.()
    onSelectView('chat')
    return
  }
  if (item === 'historico') {
    onSelectView('dashboard')
    return
  }
  if (item === 'logs') {
    onSelectView('observability')
    return
  }
  onSelectView('chat')
}

export function Sidebar({
  activeConversationId,
  conversations,
  mode,
  onChangeMode,
  onNewConversation,
  onSelectView,
  onSidebarItemSelected,
}: SidebarProps) {
  const activeSidebarItem = useRuntimeConsoleStore((state) => state.activeSidebarItem)
  const selectSidebarItem = useRuntimeConsoleStore((state) => state.selectSidebarItem)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)

  return (
    <motion.div
      className="flex h-full flex-col overflow-hidden rounded-[26px] border border-[rgba(180,109,255,0.18)] bg-[linear-gradient(180deg,rgba(14,16,36,0.9),rgba(11,13,29,0.84))] px-3 py-4 shadow-[0_22px_50px_rgba(0,0,0,0.36)] backdrop-blur-xl"
      initial={{ opacity: 0, x: -12 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      animate={{ opacity: 1, x: 0 }}
    >
      <div className="mb-4 rounded-[22px] border border-white/8 bg-black/15 px-3 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
        <p className="mb-2 text-[11px] uppercase tracking-[0.45em] text-violet-200/70">IA Console</p>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-full border bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.95),rgba(181,109,255,0.75)_28%,rgba(78,164,255,0.72)_58%,rgba(9,12,28,0.4)_70%)] ${getGlowState('runtime')} omni-runtime-glow`}>
              <div className="h-3 w-3 rounded-full bg-white/90 shadow-[0_0_14px_rgba(255,255,255,0.95)]" />
            </div>
            <div>
              <div className="text-[20px] font-semibold tracking-tight text-white">Omni AI</div>
              <div className="text-xs text-slate-300/70">Cognitive runtime console</div>
            </div>
          </div>
          <button className={`rounded-full border border-white/10 bg-white/5 p-2 text-slate-200/80 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`} onClick={() => setUiNotice('Seletor de perfil Omni ainda não possui múltiplos perfis nesta branch.')} type="button">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></svg>
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto pr-1">
        <section className="space-y-2">
          <h2 className="px-2 text-[15px] font-medium text-fuchsia-200">Conversa</h2>
          {CONVERSATION_ITEMS.map((item) => {
            const active = activeSidebarItem === item.id
            return (
              <motion.button
                key={item.id}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.985, y: 1 }}
                className={`group flex w-full items-center justify-between rounded-2xl border px-3 py-2.5 text-left transition ${
                  active
                    ? `bg-[linear-gradient(135deg,rgba(181,109,255,0.22),rgba(118,73,255,0.1))] text-white ${getGlowState('active')}`
                    : `border-white/5 bg-white/[0.03] text-slate-200/80 hover:bg-white/[0.06] hover:text-white ${getGlowState('hover')}`
                }`}
                onClick={() => {
                  selectSidebarItem(item.id)
                  onSidebarItemSelected?.(item.id)
                  handleItemSelection(item.id, onSelectView, onNewConversation)
                }}
                type="button"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className={`rounded-xl border p-2 ${active ? 'border-neon-purple/50 bg-neon-purple/15 text-neon-purple' : 'border-white/10 bg-white/[0.03] text-slate-300 group-hover:text-neon-cyan'}`}>
                    <SidebarIcon item={item.id} />
                  </span>
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-medium">{item.label}</div>
                  </div>
                </div>
                <svg className={`h-4 w-4 ${active ? 'text-neon-cyan' : 'text-slate-500 group-hover:text-neon-cyan'}`} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
              </motion.button>
            )
          })}
        </section>

        <section className="space-y-2 border-t border-white/8 pt-5">
          <h2 className="px-2 text-[15px] font-medium text-fuchsia-200">Ferramentas</h2>
          {TOOL_ITEMS.map((item) => {
            const active = activeSidebarItem === item.id
            return (
              <motion.button
                key={item.id}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.985, y: 1 }}
                className={`group flex w-full items-center justify-between rounded-2xl border px-3 py-2.5 text-left transition ${
                  active
                    ? `bg-white/10 text-white ${getGlowState('active')}`
                    : `border-white/5 bg-white/[0.03] text-slate-200/80 hover:bg-white/[0.06] hover:text-white ${getGlowState('hover')}`
                }`}
                onClick={() => {
                  selectSidebarItem(item.id)
                  onSidebarItemSelected?.(item.id)
                  handleItemSelection(item.id, onSelectView, onNewConversation)
                }}
                type="button"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className={`rounded-xl border p-2 ${active ? 'border-neon-blue/40 bg-neon-blue/10 text-neon-blue' : 'border-white/10 bg-white/[0.03] text-slate-300 group-hover:text-neon-blue'}`}>
                    <SidebarIcon item={item.id} />
                  </span>
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-medium">{item.label}</div>
                  </div>
                </div>
                <svg className={`h-4 w-4 ${active ? 'text-neon-cyan' : 'text-slate-500 group-hover:text-neon-cyan'}`} fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
              </motion.button>
            )
          })}
        </section>
      </div>
    </motion.div>
  )
}
