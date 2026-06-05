import { useCallback, useState } from 'react'
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

export function OmniSidebar(props: OmniSidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  const handleToggleCollapse = useCallback(() => {
    setCollapsed((prev) => !prev)
  }, [])

  if (collapsed) {
    return (
      <button
        className="flex w-full items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-slate-300 transition hover:text-white"
        onClick={handleToggleCollapse}
        type="button"
        title="Expand sidebar"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
      </button>
    )
  }

  return (
    <div className="relative h-full">
      <button
        className="absolute -right-3 top-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-[rgba(11,13,29,0.9)] text-slate-400 transition hover:text-white"
        onClick={handleToggleCollapse}
        type="button"
        title="Collapse sidebar"
      >
        <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6" /></svg>
      </button>
      <Sidebar {...props} />
    </div>
  )
}

export { Sidebar } from '../layout/Sidebar'
