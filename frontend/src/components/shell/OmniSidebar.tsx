import type { View } from '../../app/App'
import type { ChatMode, ConversationSummary } from '../../types'
import type { SidebarItem } from '../../state/runtimeConsoleStore'
import { Sidebar } from '../layout/Sidebar'

type OmniSidebarProps = {
  activeConversationId?: string
  conversations: ConversationSummary[]
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onNewConversation?: () => void
  onRestoreSession?: (sessionId: string) => void
  onSelectView: (view: View) => void
  onSidebarItemSelected?: (item: SidebarItem) => void
  view: View
}

type OmniSidebarToggleProps = {
  collapsed: boolean
  onToggle: () => void
}

export function OmniSidebarToggle({ collapsed, onToggle }: OmniSidebarToggleProps) {
  if (collapsed) {
    return (
      <button
        aria-label="Expand sidebar"
        className="flex w-full items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-slate-300 transition hover:text-white"
        onClick={onToggle}
        type="button"
        title="Expand sidebar"
      >
        <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
      </button>
    )
  }

  return (
    <button
      aria-label="Collapse sidebar"
      className="absolute -right-3 top-4 z-10 hidden h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-[rgba(11,13,29,0.9)] text-slate-400 transition hover:text-white lg:flex"
      onClick={onToggle}
      type="button"
      title="Collapse sidebar"
    >
      <svg aria-hidden="true" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6" /></svg>
    </button>
  )
}

export function OmniSidebar(props: OmniSidebarProps) {
  return <Sidebar {...props} />
}

export { Sidebar } from '../layout/Sidebar'
