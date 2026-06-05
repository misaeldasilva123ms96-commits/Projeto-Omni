import { useState } from 'react'
import type { MemoryEntry, MemoryType } from '../../types'
import { OmniButton } from '../ui/OmniButton'
import { MemoryCard } from './MemoryCard'

type MemoryListProps = {
  entries: MemoryEntry[]
  loading: boolean
  onEdit: (entry: MemoryEntry) => void
  onDelete: (id: string) => void
  onTogglePin: (id: string) => void
  className?: string
}

const TYPE_FILTERS: Array<{ id: MemoryType | 'all'; label: string }> = [
  { id: 'all', label: 'Todas' },
  { id: 'working', label: 'Working' },
  { id: 'episodic', label: 'Episódica' },
  { id: 'semantic', label: 'Semântica' },
  { id: 'procedural', label: 'Procedural' },
]

export function MemoryList({ entries, loading, onEdit, onDelete, onTogglePin, className = '' }: MemoryListProps) {
  const [activeFilter, setActiveFilter] = useState<MemoryType | 'all'>('all')

  const filtered = activeFilter === 'all'
    ? entries
    : entries.filter((e) => e.memoryType === activeFilter)

  const pinnedFirst = [...filtered].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1
    if (!a.isPinned && b.isPinned) return 1
    return 0
  })

  return (
    <div className={className}>
      <div className="mb-4 flex flex-wrap gap-2">
        {TYPE_FILTERS.map((f) => (
          <button
            key={f.id}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              activeFilter === f.id
                ? 'border-violet-500/40 bg-violet-500/15 text-violet-200'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-white/20'
            }`}
            onClick={() => setActiveFilter(f.id)}
            type="button"
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-sm text-slate-400">Carregando memória...</div>
      ) : pinnedFirst.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <svg className="mb-4 h-12 w-12 text-slate-500" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
            <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" />
          </svg>
          <p className="text-sm text-slate-400">
            {activeFilter === 'all' ? 'Nenhuma entrada de memória ainda.' : 'Nenhuma entrada deste tipo.'}
          </p>
          <p className="mt-1 text-xs text-slate-500">As entradas de memória aparecerão à medida que o runtime for usado.</p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {pinnedFirst.map((entry) => (
            <MemoryCard
              key={entry.id}
              entry={entry}
              onEdit={() => onEdit(entry)}
              onDelete={() => onDelete(entry.id)}
              onTogglePin={() => onTogglePin(entry.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
