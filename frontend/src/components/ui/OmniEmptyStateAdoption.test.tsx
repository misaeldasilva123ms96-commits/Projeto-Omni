import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AgentsList } from '../agents/AgentsList'
import { HistoryPanel } from '../history/HistoryPanel'
import { ProjectsList } from '../projects/ProjectsList'

describe('Omni empty-state adoption', () => {
  it('preserves the Projects empty-state action', async () => {
    render(
      <ProjectsList
        loading={false}
        onArchive={vi.fn()}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        onUpdate={vi.fn()}
        projects={[]}
      />,
    )

    expect(screen.getByText('Nenhum projeto ainda.')).toBeInTheDocument()
    const actions = screen.getAllByRole('button', { name: 'Criar Projeto' })
    await userEvent.click(actions[0])
    expect(screen.getByRole('heading', { name: 'Novo Projeto' })).toBeInTheDocument()
  })

  it('preserves the Agents empty-state action', async () => {
    render(
      <AgentsList
        agents={[]}
        loading={false}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        onToggleStatus={vi.fn()}
        onUpdate={vi.fn()}
      />,
    )

    expect(screen.getByText('Nenhum agente ainda.')).toBeInTheDocument()
    const actions = screen.getAllByRole('button', { name: 'Criar Agente' })
    await userEvent.click(actions[0])
    expect(screen.getByRole('heading', { name: 'Novo Agente' })).toBeInTheDocument()
  })

  it('preserves the distinct empty and filtered History messages', async () => {
    const { rerender } = render(
      <HistoryPanel onRestoreSession={vi.fn()} sessions={[]} />,
    )
    expect(screen.getByText(
      'Nenhuma sessão encontrada. Envie uma mensagem para começar.',
    )).toBeInTheDocument()

    rerender(
      <HistoryPanel
        onRestoreSession={vi.fn()}
        sessions={[{
          id: 'session-1',
          title: 'Sessão de código',
          mode: 'codigo',
          messageCount: 1,
          updatedAt: '2026-06-21T00:00:00Z',
        }]}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Pesquisa' }))
    expect(screen.getByText('Nenhuma sessão corresponde aos filtros.')).toBeInTheDocument()
  })
})
