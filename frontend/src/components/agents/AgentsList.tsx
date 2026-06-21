import { useState } from 'react'
import type { Agent } from '../../types'
import { OmniButton } from '../ui/OmniButton'
import { OmniEmptyState } from '../ui/OmniEmptyState'
import { AgentCard } from './AgentCard'
import { AgentForm } from './AgentForm'

type AgentsListProps = {
  agents: Agent[]
  loading: boolean
  onCreate: (input: { name: string; description: string; model: string; provider: string; tools: string[] }) => void
  onUpdate: (id: string, input: { name: string; description: string; model: string; provider: string; tools: string[] }) => void
  onDelete: (id: string) => void
  onToggleStatus: (id: string) => void
  className?: string
}

export function AgentsList({ agents, loading, onCreate, onUpdate, onDelete, onToggleStatus, className = '' }: AgentsListProps) {
  const [showForm, setShowForm] = useState(false)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)

  const handleSubmit = (input: { name: string; description: string; model: string; provider: string; tools: string[] }) => {
    if (editingAgent) {
      onUpdate(editingAgent.id, input)
      setEditingAgent(null)
    } else {
      onCreate(input)
      setShowForm(false)
    }
  }

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent)
  }

  const handleToggleStatus = (agent: Agent) => {
    onToggleStatus(agent.id)
  }

  const handleDelete = (agent: Agent) => {
    onDelete(agent.id)
  }

  if (showForm || editingAgent) {
    return (
      <div className={`mx-auto max-w-lg ${className}`.trim()}>
        <AgentForm
          agent={editingAgent}
          onSubmit={handleSubmit}
          onCancel={() => {
            setShowForm(false)
            setEditingAgent(null)
          }}
        />
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">Agentes</h2>
          <p className="mt-0.5 text-sm text-slate-400">{agents.length} agente{agents.length !== 1 ? 's' : ''}</p>
        </div>
        <OmniButton variant="primary" onClick={() => setShowForm(true)}>
          Novo Agente
        </OmniButton>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-sm text-slate-400">Carregando agentes...</div>
      ) : agents.length === 0 ? (
        <OmniEmptyState
          actionLabel="Criar Agente"
          description="Crie seu primeiro agente para automatizar tarefas."
          icon={(
            <svg className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
              <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Z" />
              <path d="M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z" />
              <path d="M12 9v3l2 2" />
            </svg>
          )}
          onAction={() => setShowForm(true)}
          title="Nenhum agente ainda."
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onToggleStatus={handleToggleStatus}
            />
          ))}
        </div>
      )}
    </div>
  )
}
