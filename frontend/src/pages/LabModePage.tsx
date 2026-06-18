import type { RenderOmniShell, View } from '../app/App'
import { LabConsole } from '../components/lab/LabConsole'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { PageHero } from '../components/ui/PageHero'
import type { ChatMode, ConversationSummary } from '../types'

type LabModePageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function LabModePage({ mode, onChangeMode, onChangeView, renderShell, view }: LabModePageProps) {
  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Sandbox"
          title="Modo Laboratório"
          subtitle="Sandbox para testar prompts com diferentes modelos, provedores e configurações"
          className="mb-6"
        />

        <LabConsole />
      </div>,
    { sidebar },
  )
}
