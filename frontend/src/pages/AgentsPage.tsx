import { useCallback, useEffect, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { AgentsList } from '../components/agents/AgentsList'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { PageHero } from '../components/ui/PageHero'
import { createAgent, deleteAgent, fetchAgents, updateAgent } from '../lib/omniData'
import type { Agent, ChatMode, ConversationSummary } from '../types'

type AgentsPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function AgentsPage({ mode, onChangeMode, onChangeView, renderShell, view }: AgentsPageProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAgents()
      .then((data) => {
        if (!cancelled) {
          setAgents(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const refresh = useCallback(() => {
    fetchAgents().then(setAgents).catch(() => {})
  }, [])

  const handleCreate = useCallback(async (input: {
    name: string; description: string; model: string; provider: string; tools: string[]
  }) => {
    await createAgent(input)
    refresh()
  }, [refresh])

  const handleUpdate = useCallback(async (id: string, input: {
    name: string; description: string; model: string; provider: string; tools: string[]
  }) => {
    await updateAgent(id, input)
    refresh()
  }, [refresh])

  const handleDelete = useCallback(async (id: string) => {
    await deleteAgent(id)
    refresh()
  }, [refresh])

  const handleToggleStatus = useCallback(async (id: string) => {
    const agent = agents.find((a) => a.id === id)
    if (!agent) return
    await updateAgent(id, { status: agent.status === 'active' ? 'inactive' : 'active' })
    refresh()
  }, [agents, refresh])

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
          eyebrow="Automação"
          title="Centro de Agentes"
          subtitle="Gerencie agentes de IA, configure modelos, provedores e ferramentas"
          className="mb-6"
        />

        <AgentsList
          agents={agents}
          loading={loading}
          onCreate={handleCreate}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          onToggleStatus={handleToggleStatus}
        />
      </div>,
    { sidebar },
  )
}
