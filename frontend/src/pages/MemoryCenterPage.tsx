import { useCallback, useEffect, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { MemoryList } from '../components/memory/MemoryList'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { OmniCard } from '../components/ui/OmniCard'
import { PageHero } from '../components/ui/PageHero'
import { deleteMemoryEntry, fetchMemoryEntries, updateMemoryEntry } from '../lib/omniData'
import type { ChatMode, ConversationSummary, MemoryEntry } from '../types'

type MemoryCenterPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function MemoryCenterPage({ mode, onChangeMode, onChangeView, renderShell, view }: MemoryCenterPageProps) {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchMemoryEntries()
      .then((data) => {
        if (!cancelled) {
          setEntries(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const refresh = useCallback(() => {
    fetchMemoryEntries().then(setEntries).catch(() => {})
  }, [])

  const stats = {
    total: entries.length,
    pinned: entries.filter((e) => e.isPinned).length,
    working: entries.filter((e) => e.memoryType === 'working').length,
    episodic: entries.filter((e) => e.memoryType === 'episodic').length,
    semantic: entries.filter((e) => e.memoryType === 'semantic').length,
    procedural: entries.filter((e) => e.memoryType === 'procedural').length,
  }

  const handleTogglePin = useCallback(async (id: string) => {
    const entry = entries.find((e) => e.id === id)
    if (!entry) return
    await updateMemoryEntry(id, { isPinned: !entry.isPinned })
    refresh()
  }, [entries, refresh])

  const handleDelete = useCallback(async (id: string) => {
    await deleteMemoryEntry(id)
    refresh()
  }, [refresh])

  const handleEdit = useCallback((entry: MemoryEntry) => {
    console.log('Edit memory entry:', entry.id)
  }, [])

  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Memória do Runtime"
          title="Centro de Memória"
          subtitle="Inspecione entradas de memória do runtime — working, episódica, semântica e procedural"
          className="mb-6"
        />

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Total</p>
            <p className="mt-2 text-2xl font-semibold text-white">{stats.total}</p>
            <p className="mt-1 text-xs text-slate-400">Entradas de memória</p>
          </OmniCard>

          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Fixadas</p>
            <p className="mt-2 text-2xl font-semibold text-amber-300">{stats.pinned}</p>
            <p className="mt-1 text-xs text-slate-400">Entradas importantes</p>
          </OmniCard>

          <OmniCard variant="panel">
            <p className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Distribuição</p>
            <p className="mt-2 text-sm text-slate-300">
              W:{stats.working} E:{stats.episodic} S:{stats.semantic} P:{stats.procedural}
            </p>
            <p className="mt-1 text-xs text-slate-400">Working / Episódica / Semântica / Procedural</p>
          </OmniCard>
        </div>

        <MemoryList
          entries={entries}
          loading={loading}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onTogglePin={handleTogglePin}
        />
      </div>,
    { sidebar },
  )
}
