import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MemoryCard } from './MemoryCard'
import type { MemoryEntry } from '../../types'

const baseEntry: MemoryEntry = {
  id: 'mem-1',
  memoryType: 'working',
  title: 'Working memory entry',
  summary: 'A summary of the memory',
  content: {},
  source: 'chat',
  importance: 0.9,
  tags: ['tag1', 'tag2'],
  isPinned: false,
  sessionId: 'session-1',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
}

describe('MemoryCard', () => {
  it('renders memory type badge', () => {
    render(<MemoryCard entry={baseEntry} />)
    expect(screen.getByText('Working')).toBeInTheDocument()
  })

  it('renders importance label', () => {
    render(<MemoryCard entry={baseEntry} />)
    expect(screen.getByText('Alta')).toBeInTheDocument()
  })

  it('renders medium importance for 0.5', () => {
    render(<MemoryCard entry={{ ...baseEntry, importance: 0.5 }} />)
    expect(screen.getByText('Média')).toBeInTheDocument()
  })

  it('renders baixa importance for 0.3', () => {
    render(<MemoryCard entry={{ ...baseEntry, importance: 0.3 }} />)
    expect(screen.getByText('Baixa')).toBeInTheDocument()
  })

  it('renders title and summary', () => {
    render(<MemoryCard entry={baseEntry} />)
    expect(screen.getByText('Working memory entry')).toBeInTheDocument()
    expect(screen.getByText('A summary of the memory')).toBeInTheDocument()
  })

  it('renders pin icon when pinned', () => {
    const { container } = render(<MemoryCard entry={{ ...baseEntry, isPinned: true }} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders source and tag count', () => {
    render(<MemoryCard entry={baseEntry} />)
    expect(screen.getByText(/Fonte: chat/)).toBeInTheDocument()
    expect(screen.getByText(/2 tags/)).toBeInTheDocument()
  })

  it('shows session indicator when sessionId is present', () => {
    render(<MemoryCard entry={baseEntry} />)
    expect(screen.getByText(/Sessão vinculada/)).toBeInTheDocument()
  })

  it('calls onTogglePin when pin button is clicked', async () => {
    const onTogglePin = vi.fn()
    render(<MemoryCard entry={baseEntry} onTogglePin={onTogglePin} />)
    await userEvent.click(screen.getByRole('button', { name: /fixar/i }))
    expect(onTogglePin).toHaveBeenCalledWith(baseEntry)
  })

  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn()
    render(<MemoryCard entry={baseEntry} onEdit={onEdit} />)
    await userEvent.click(screen.getByRole('button', { name: /editar/i }))
    expect(onEdit).toHaveBeenCalledWith(baseEntry)
  })

  it('calls onDelete when delete button is clicked', async () => {
    const onDelete = vi.fn()
    render(<MemoryCard entry={baseEntry} onDelete={onDelete} />)
    await userEvent.click(screen.getByRole('button', { name: /excluir/i }))
    expect(onDelete).toHaveBeenCalledWith(baseEntry)
  })

  it('shows "Desfixar" when pinned', () => {
    render(<MemoryCard entry={{ ...baseEntry, isPinned: true }} onTogglePin={vi.fn()} />)
    expect(screen.getByRole('button', { name: /desfixar/i })).toBeInTheDocument()
  })
})
