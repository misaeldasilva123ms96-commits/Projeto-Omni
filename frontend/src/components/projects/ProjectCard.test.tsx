import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ProjectCard } from './ProjectCard'
import type { Project } from '../../types'

const baseProject: Project = {
  id: 'proj-1',
  name: 'Test Project',
  description: 'A test project description',
  status: 'active',
  mode: 'chat',
  sessionCount: 5,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: new Date().toISOString(),
}

describe('ProjectCard', () => {
  it('renders project name and description', () => {
    render(<ProjectCard project={baseProject} />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('A test project description')).toBeInTheDocument()
  })

  it('renders active badge', () => {
    render(<ProjectCard project={baseProject} />)
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('renders archived badge for archived projects', () => {
    render(<ProjectCard project={{ ...baseProject, status: 'archived' }} />)
    expect(screen.getByText('Arquivado')).toBeInTheDocument()
  })

  it('renders mode badge', () => {
    render(<ProjectCard project={baseProject} />)
    expect(screen.getByText('Chat')).toBeInTheDocument()
  })

  it('renders session count', () => {
    render(<ProjectCard project={baseProject} />)
    expect(screen.getByText(/5 sessões/)).toBeInTheDocument()
  })

  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn()
    render(<ProjectCard project={baseProject} onEdit={onEdit} />)
    const editBtn = screen.getByRole('button', { name: /editar/i })
    await userEvent.click(editBtn)
    expect(onEdit).toHaveBeenCalledWith(baseProject)
  })

  it('calls onDelete when delete button is clicked', async () => {
    const onDelete = vi.fn()
    render(<ProjectCard project={baseProject} onDelete={onDelete} />)
    const deleteBtn = screen.getByRole('button', { name: /excluir/i })
    await userEvent.click(deleteBtn)
    expect(onDelete).toHaveBeenCalledWith(baseProject)
  })

  it('calls onArchive when archive button is clicked', async () => {
    const onArchive = vi.fn()
    render(<ProjectCard project={baseProject} onArchive={onArchive} />)
    const archiveBtn = screen.getByRole('button', { name: /arquivar/i })
    await userEvent.click(archiveBtn)
    expect(onArchive).toHaveBeenCalledWith(baseProject)
  })

  it('shows activate button for archived projects', () => {
    render(<ProjectCard project={{ ...baseProject, status: 'archived' }} onArchive={vi.fn()} />)
    expect(screen.getByRole('button', { name: /ativar/i })).toBeInTheDocument()
  })
})
