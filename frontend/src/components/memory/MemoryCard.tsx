import type { MemoryEntry } from '../../types'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniButton } from '../ui/OmniButton'

type MemoryCardProps = {
  entry: MemoryEntry
  onEdit?: (entry: MemoryEntry) => void
  onDelete?: (entry: MemoryEntry) => void
  onTogglePin?: (entry: MemoryEntry) => void
  className?: string
}

const TYPE_LABELS: Record<string, string> = {
  working: 'Working',
  episodic: 'Episódica',
  semantic: 'Semântica',
  procedural: 'Procedural',
}

const TYPE_TONES: Record<string, 'info' | 'success' | 'warning' | 'muted'> = {
  working: 'info',
  episodic: 'success',
  semantic: 'warning',
  procedural: 'muted',
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / 86400000)
    if (diffDays === 0) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    if (diffDays < 7) return `${diffDays} dias atrás`
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  } catch {
    return ''
  }
}

function importanceLabel(n: number): string {
  if (n >= 0.8) return 'Alta'
  if (n >= 0.4) return 'Média'
  return 'Baixa'
}

function importanceTone(n: number): 'success' | 'warning' | 'muted' {
  if (n >= 0.8) return 'success'
  if (n >= 0.4) return 'warning'
  return 'muted'
}

export function MemoryCard({ entry, onEdit, onDelete, onTogglePin, className = '' }: MemoryCardProps) {
  return (
    <div className={`group rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,34,0.72),rgba(10,11,27,0.68))] p-5 shadow-[0_12px_32px_rgba(0,0,0,0.22)] backdrop-blur-xl transition hover:border-white/18 hover:shadow-[0_16px_40px_rgba(0,0,0,0.3)] ${className}`.trim()}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <OmniBadge tone={TYPE_TONES[entry.memoryType] ?? 'muted'}>
              {TYPE_LABELS[entry.memoryType] ?? entry.memoryType}
            </OmniBadge>
            <OmniBadge tone={importanceTone(entry.importance)}>
              {importanceLabel(entry.importance)}
            </OmniBadge>
            {entry.isPinned ? (
              <svg className="h-3.5 w-3.5 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" />
              </svg>
            ) : null}
          </div>

          {entry.title ? (
            <h3 className="mt-2 truncate text-sm font-semibold text-white">{entry.title}</h3>
          ) : null}

          {entry.summary ? (
            <p className="mt-1 line-clamp-2 text-sm text-slate-300/80">{entry.summary}</p>
          ) : null}

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            {entry.source ? <span>Fonte: {entry.source}</span> : null}
            {entry.tags.length > 0 ? (
              <span>{entry.tags.length} tag{entry.tags.length !== 1 ? 's' : ''}</span>
            ) : null}
            {entry.sessionId ? <span>· Sessão vinculada</span> : null}
            <span>· {formatDate(entry.createdAt)}</span>
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-1.5 opacity-0 transition group-hover:opacity-100">
          {onTogglePin ? (
            <OmniButton variant="ghost" onClick={() => onTogglePin(entry)}>
              {entry.isPinned ? 'Desfixar' : 'Fixar'}
            </OmniButton>
          ) : null}
          {onEdit ? (
            <OmniButton variant="ghost" onClick={() => onEdit(entry)}>
              Editar
            </OmniButton>
          ) : null}
          {onDelete ? (
            <OmniButton variant="danger" onClick={() => onDelete(entry)}>
              Excluir
            </OmniButton>
          ) : null}
        </div>
      </div>
    </div>
  )
}
