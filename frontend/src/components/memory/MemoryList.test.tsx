import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MemoryList } from './MemoryList'
import type { MemoryEntry } from '../../types'

const entries: MemoryEntry[] = [
  {
    id: 'mem-1',
    memoryType: 'working',
    title: 'Working entry',
    summary: 'Working summary',
    content: {},
    source: 'chat',
    importance: 0.9,
    tags: [],
    isPinned: true,
    sessionId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'mem-2',
    memoryType: 'episodic',
    title: 'Episodic entry',
    summary: 'Episodic summary',
    content: {},
    source: 'chat',
    importance: 0.5,
    tags: [],
    isPinned: false,
    sessionId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'mem-3',
    memoryType: 'semantic',
    title: 'Semantic entry',
    summary: 'Semantic summary',
    content: {},
    source: 'chat',
    importance: 0.3,
    tags: [],
    isPinned: false,
    sessionId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'mem-4',
    memoryType: 'procedural',
    title: 'Procedural entry',
    summary: 'Procedural summary',
    content: {},
    source: 'chat',
    importance: 0.3,
    tags: [],
    isPinned: true,
    sessionId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
]

describe('MemoryList', () => {
  const defaultProps = {
    entries,
    loading: false,
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onTogglePin: vi.fn(),
  }

  it('renders all entries by default', () => {
    render(<MemoryList {...defaultProps} />)
    expect(screen.getByText('Working entry')).toBeInTheDocument()
    expect(screen.getByText('Episodic entry')).toBeInTheDocument()
    expect(screen.getByText('Semantic entry')).toBeInTheDocument()
    expect(screen.getByText('Procedural entry')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<MemoryList {...defaultProps} loading={true} entries={[]} />)
    expect(screen.getByText('Carregando memória...')).toBeInTheDocument()
  })

  it('shows empty state when no entries', () => {
    render(<MemoryList {...defaultProps} entries={[]} />)
    expect(screen.getByText('Nenhuma entrada de memória ainda.')).toBeInTheDocument()
  })

  it('filters by memory type', async () => {
    render(<MemoryList {...defaultProps} />)
    await userEvent.click(screen.getByRole('button', { name: /episódica/i }))
    expect(screen.getByText('Episodic entry')).toBeInTheDocument()
    expect(screen.queryByText('Working entry')).not.toBeInTheDocument()
  })

  it('shows filtered empty state when filter has no matches', async () => {
    render(<MemoryList {...defaultProps} entries={[entries[0]]} />)
    await userEvent.click(screen.getByRole('button', { name: /episódica/i }))
    expect(screen.getByText('Nenhuma entrada deste tipo.')).toBeInTheDocument()
  })

  it('resets filter to show all when clicking "Todas"', async () => {
    render(<MemoryList {...defaultProps} />)
    await userEvent.click(screen.getByRole('button', { name: /episódica/i }))
    await userEvent.click(screen.getByRole('button', { name: /todas/i }))
    expect(screen.getByText('Working entry')).toBeInTheDocument()
    expect(screen.getByText('Episodic entry')).toBeInTheDocument()
  })

  it('sorts pinned entries first', () => {
    render(<MemoryList {...defaultProps} />)
    const cards = screen.getAllByText(/entry/)
    expect(cards[0]).toHaveTextContent('Working entry')
    expect(cards[1]).toHaveTextContent('Procedural entry')
  })

  it('renders type filter buttons', () => {
    render(<MemoryList {...defaultProps} />)
    expect(screen.getByRole('button', { name: /todas/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /working/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /episódica/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /semântica/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /procedural/i })).toBeInTheDocument()
  })
})
