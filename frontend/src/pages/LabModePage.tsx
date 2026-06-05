import type { View } from '../app/App'
import { LabConsole } from '../components/lab/LabConsole'
import { OmniShell } from '../components/shell/OmniShell'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import type { ChatMode, ConversationSummary } from '../types'

type LabModePageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  view: View
}

export function LabModePage({ mode, onChangeMode, onChangeView, view }: LabModePageProps) {
  const conversations: ConversationSummary[] = []

  return (
    <OmniShell
      sidebar={(
        <OmniSidebar
          conversations={conversations}
          mode={mode}
          onChangeMode={onChangeMode}
          onSelectView={onChangeView}
          view={view}
        />
      )}
    >
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-white">Modo Laboratório</h1>
          <p className="mt-1 text-sm text-slate-400">
            Sandbox para testar prompts com diferentes modelos, provedores e configurações
          </p>
        </div>

        <LabConsole />
      </div>
    </OmniShell>
  )
}
