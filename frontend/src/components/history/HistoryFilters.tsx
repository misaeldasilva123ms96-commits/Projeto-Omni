import { useMemo, useState } from 'react'
import type { ChatMode } from '../../types'
import { OmniButton, OmniInput } from '../ui'

type HistoryFiltersProps = {
  onSearchChange: (query: string) => void
  onModeFilter: (mode: ChatMode | null) => void
  onSortChange: (sort: 'newest' | 'oldest') => void
  className?: string
}

const MODE_OPTIONS: Array<{ id: ChatMode | null; label: string }> = [
  { id: null, label: 'Todos' },
  { id: 'chat', label: 'Chat' },
  { id: 'pesquisa', label: 'Pesquisa' },
  { id: 'codigo', label: 'Código' },
  { id: 'agente', label: 'Agente' },
]

export function HistoryFilters({ onSearchChange, onModeFilter, onSortChange, className = '' }: HistoryFiltersProps) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<ChatMode | null>(null)
  const [sort, setSort] = useState<'newest' | 'oldest'>('newest')

  const handleSearch = useMemo(() => {
    let timeout: ReturnType<typeof setTimeout>
    return (value: string) => {
      clearTimeout(timeout)
      timeout = setTimeout(() => onSearchChange(value), 280)
    }
  }, [onSearchChange])

  return (
    <div className={`space-y-3 ${className}`.trim()}>
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.8"
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <OmniInput
          className="py-2 pl-9 pr-3"
          onChange={(e) => {
            setQuery(e.target.value)
            handleSearch(e.target.value)
          }}
          placeholder="Buscar sessões..."
          value={query}
          type="text"
        />
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {MODE_OPTIONS.map((opt) => {
            const active = mode === opt.id
            return (
              <OmniButton
                key={opt.label}
                className={`rounded-xl px-2.5 py-1 normal-case tracking-normal ${
                  active
                    ? 'border-neon-purple/40 bg-neon-purple/15 text-white'
                    : 'border-white/8 bg-white/[0.03] text-slate-300 hover:text-white'
                }`}
                onClick={() => {
                  setMode(opt.id)
                  onModeFilter(opt.id)
                }}
                size="sm"
                style={{ fontWeight: 400, letterSpacing: 'normal', textTransform: 'none' }}
                type="button"
                variant={active ? 'secondary' : 'ghost'}
              >
                {opt.label}
              </OmniButton>
            )
          })}
        </div>

        <OmniButton
          className="rounded-xl border border-white/8 bg-white/[0.03] px-2.5 py-1 normal-case tracking-normal text-slate-300 hover:text-white"
          onClick={() => {
            const next = sort === 'newest' ? 'oldest' : 'newest'
            setSort(next)
            onSortChange(next)
          }}
          size="sm"
          style={{ fontWeight: 400, letterSpacing: 'normal', textTransform: 'none' }}
          type="button"
          title={sort === 'newest' ? 'Mais recentes primeiro' : 'Mais antigas primeiro'}
          variant="ghost"
        >
          {sort === 'newest' ? '↓ Recentes' : '↑ Antigas'}
        </OmniButton>
      </div>
    </div>
  )
}
