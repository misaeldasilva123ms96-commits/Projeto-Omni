import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AgentCard } from './AgentCard'
import type { Agent } from '../../types'

const baseAgent: Agent = {
  id: 'agent-1',
  name: 'Test Agent',
  description: 'An agent for testing',
  model: 'gpt-4',
  provider: 'openai',
  tools: ['read_file', 'search'],
  status: 'active',
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: new Date().toISOString(),
}

describe('AgentCard', () => {
  it('renders agent name and description', () => {
    render(<AgentCard agent={baseAgent} />)
    expect(screen.getByText('Test Agent')).toBeInTheDocument()
    expect(screen.getByText('An agent for testing')).toBeInTheDocument()
  })

  it('renders active badge', () => {
    render(<AgentCard agent={baseAgent} />)
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('renders inactive badge', () => {
    render(<AgentCard agent={{ ...baseAgent, status: 'inactive' }} />)
    expect(screen.getByText('Inativo')).toBeInTheDocument()
  })

  it('renders model and provider badges', () => {
    render(<AgentCard agent={baseAgent} />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('openai')).toBeInTheDocument()
  })

  it('renders tool count', () => {
    render(<AgentCard agent={baseAgent} />)
    expect(screen.getByText('2 ferramentas')).toBeInTheDocument()
  })

  it('shows "Sem ferramentas" when no tools', () => {
    render(<AgentCard agent={{ ...baseAgent, tools: [] }} />)
    expect(screen.getByText('Sem ferramentas')).toBeInTheDocument()
  })

  it('calls onToggleStatus when toggle button is clicked', async () => {
    const onToggleStatus = vi.fn()
    render(<AgentCard agent={baseAgent} onToggleStatus={onToggleStatus} />)
    await userEvent.click(screen.getByRole('button', { name: /desativar/i }))
    expect(onToggleStatus).toHaveBeenCalledWith(baseAgent)
  })

  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn()
    render(<AgentCard agent={baseAgent} onEdit={onEdit} />)
    await userEvent.click(screen.getByRole('button', { name: /editar/i }))
    expect(onEdit).toHaveBeenCalledWith(baseAgent)
  })

  it('calls onDelete when delete button is clicked', async () => {
    const onDelete = vi.fn()
    render(<AgentCard agent={baseAgent} onDelete={onDelete} />)
    await userEvent.click(screen.getByRole('button', { name: /excluir/i }))
    expect(onDelete).toHaveBeenCalledWith(baseAgent)
  })

  it('shows "Ativar" for inactive agents', () => {
    render(<AgentCard agent={{ ...baseAgent, status: 'inactive' }} onToggleStatus={vi.fn()} />)
    expect(screen.getByRole('button', { name: /ativar/i })).toBeInTheDocument()
  })
})
