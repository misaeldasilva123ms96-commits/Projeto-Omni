import { useCallback } from 'react'

type MobilePanel = 'sidebar' | 'content' | 'inspector'

type OmniMobileNavProps = {
  activePanel: MobilePanel
  onSelect: (panel: MobilePanel) => void
  hasSidebar: boolean
  hasRightPanel: boolean
}

const PANEL_CONFIG: Record<MobilePanel, { label: string; icon: JSX.Element }> = {
  sidebar: {
    label: 'Menu',
    icon: (
      <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M3 12h18M3 6h18M3 18h18" />
      </svg>
    ),
  },
  content: {
    label: 'Chat',
    icon: (
      <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  inspector: {
    label: 'Runtime',
    icon: (
      <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.05V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-.4-1.04 1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.05-.4H3a2 2 0 1 1 0-4h.09c.4 0 .78-.15 1.05-.4a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6c.39 0 .77-.22 1-.6.26-.3.4-.67.4-1.05V3a2 2 0 1 1 4 0v.09c0 .39.14.76.4 1.05.23.38.61.6 1 .6a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c0 .39.22.77.6 1 .3.25.67.4 1.05.4H21a2 2 0 1 1 0 4h-.09c-.39 0-.76.15-1.05.4-.38.23-.6.61-.6 1Z" />
      </svg>
    ),
  },
}

export function OmniMobileNav({ activePanel, onSelect, hasSidebar, hasRightPanel }: OmniMobileNavProps) {
  const panels: Array<{ id: MobilePanel } & typeof PANEL_CONFIG['sidebar']> = []
  if (hasSidebar) panels.push({ id: 'sidebar', ...PANEL_CONFIG.sidebar })
  panels.push({ id: 'content', ...PANEL_CONFIG.content })
  if (hasRightPanel) panels.push({ id: 'inspector', ...PANEL_CONFIG.inspector })

  if (panels.length <= 1) {
    return null
  }

  return (
    <div
      role="tablist"
      aria-label="Panel navigation"
      className="mb-3 grid gap-2 sm:mb-4 lg:hidden"
      style={{ gridTemplateColumns: `repeat(${panels.length}, 1fr)` }}
    >
      {panels.map(({ id, label, icon }) => (
        <button
          key={id}
          role="tab"
          aria-selected={activePanel === id}
          aria-controls={id === 'content' ? 'main-content' : undefined}
          className={`flex items-center justify-center gap-2 rounded-2xl border px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition active:translate-y-px ${
            activePanel === id
              ? 'border-neon-purple/40 bg-neon-purple/14 text-white'
              : 'border-white/8 bg-white/[0.04] text-slate-400 hover:text-white'
          }`}
          onClick={() => onSelect(id)}
          type="button"
        >
          {icon}
          {label}
        </button>
      ))}
    </div>
  )
}
