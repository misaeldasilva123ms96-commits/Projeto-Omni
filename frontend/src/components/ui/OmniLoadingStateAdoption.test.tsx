import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AgentsList } from '../agents/AgentsList'
import { ProjectsList } from '../projects/ProjectsList'

const projectProps = {
  onArchive: vi.fn(),
  onCreate: vi.fn(),
  onDelete: vi.fn(),
  onUpdate: vi.fn(),
}

const agentProps = {
  onCreate: vi.fn(),
  onDelete: vi.fn(),
  onToggleStatus: vi.fn(),
  onUpdate: vi.fn(),
}

describe('Omni loading-state adoption', () => {
  it('keeps Projects loading distinct from empty content', () => {
    const { rerender } = render(<ProjectsList {...projectProps} loading projects={[]} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando projetos...')
    expect(screen.queryByText('Nenhum projeto ainda.')).not.toBeInTheDocument()

    rerender(<ProjectsList {...projectProps} loading={false} projects={[]} />)
    expect(screen.queryByText('Carregando projetos...')).not.toBeInTheDocument()
    expect(screen.getByText('Nenhum projeto ainda.')).toBeInTheDocument()
  })

  it('keeps Agents loading distinct from empty content', () => {
    const { rerender } = render(<AgentsList {...agentProps} agents={[]} loading />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando agentes...')
    expect(screen.queryByText('Nenhum agente ainda.')).not.toBeInTheDocument()

    rerender(<AgentsList {...agentProps} agents={[]} loading={false} />)
    expect(screen.queryByText('Carregando agentes...')).not.toBeInTheDocument()
    expect(screen.getByText('Nenhum agente ainda.')).toBeInTheDocument()
  })
})
