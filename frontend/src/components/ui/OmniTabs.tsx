import { useCallback, useRef } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'

type OmniTab = {
  id: string
  label: string
  icon?: ReactNode
}

type OmniTabsProps = {
  tabs: OmniTab[]
  activeTab: string
  onSelect: (id: string) => void
  className?: string
}

export function OmniTabs({ tabs, activeTab, onSelect, className = '' }: OmniTabsProps) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      const currentIndex = tabs.findIndex((t) => t.id === activeTab)
      let nextIndex: number | null = null
      if (event.key === 'ArrowRight') {
        nextIndex = (currentIndex + 1) % tabs.length
      } else if (event.key === 'ArrowLeft') {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
      } else if (event.key === 'Home') {
        nextIndex = 0
      } else if (event.key === 'End') {
        nextIndex = tabs.length - 1
      }
      if (nextIndex !== null) {
        event.preventDefault()
        onSelect(tabs[nextIndex].id)
        tabRefs.current[nextIndex]?.focus()
      }
    },
    [tabs, activeTab, onSelect],
  )

  return (
    <div
      className={`flex flex-wrap gap-1.5 ${className}`.trim()}
      role="tablist"
      aria-orientation="horizontal"
      onKeyDown={handleKeyDown}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`tabpanel-${tab.id}`}
            id={`tab-${tab.id}`}
            className={`rounded-2xl border px-3 py-1.5 text-xs transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-purple ${
              isActive
                ? 'border-neon-purple/40 bg-neon-purple/14 text-white'
                : 'border-white/8 bg-white/[0.03] text-slate-300 hover:text-white'
            }`}
            onClick={() => onSelect(tab.id)}
            ref={(node) => {
              tabRefs.current[tabs.indexOf(tab)] = node
            }}
            type="button"
            tabIndex={isActive ? 0 : -1}
          >
            {tab.icon ? <span className="mr-1.5 inline-flex">{tab.icon}</span> : null}
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
