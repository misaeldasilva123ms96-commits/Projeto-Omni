import { useCallback } from 'react'

type MobilePanel = 'sidebar' | 'content' | 'inspector'

type OmniMobileNavProps = {
  activePanel: MobilePanel
  onSelect: (panel: MobilePanel) => void
  hasSidebar: boolean
  hasRightPanel: boolean
}

const PANELS: Array<{ id: MobilePanel; label: string }> = [
  { id: 'sidebar', label: 'Tools' },
  { id: 'content', label: 'Chat' },
  { id: 'inspector', label: 'Runtime' },
]

export function OmniMobileNav({ activePanel, onSelect, hasSidebar, hasRightPanel }: OmniMobileNavProps) {
  const visiblePanels = PANELS.filter(
    (p) =>
      (p.id === 'sidebar' && hasSidebar) ||
      (p.id === 'content') ||
      (p.id === 'inspector' && hasRightPanel),
  )

  if (visiblePanels.length <= 1) {
    return null
  }

  return (
    <div className="mb-4 grid grid-cols-3 gap-2 lg:hidden">
      {PANELS.map(({ id, label }) => {
        const visible =
          (id === 'sidebar' && hasSidebar) ||
          (id === 'content') ||
          (id === 'inspector' && hasRightPanel)

        if (!visible) return null

        return (
          <button
            key={id}
            className={`rounded-2xl border px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition active:translate-y-px ${
              activePanel === id
                ? 'border-neon-purple/40 bg-neon-purple/14 text-white'
                : 'border-white/8 bg-white/[0.04] text-slate-400 hover:text-white'
            }`}
            onClick={() => onSelect(id)}
            type="button"
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
