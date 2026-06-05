import { useCallback, useState } from 'react'
import type { ReactNode } from 'react'

type OmniRightInspectorProps = {
  children: ReactNode
  className?: string
  defaultOpen?: boolean
}

export function OmniRightInspector({ children, className = '', defaultOpen = true }: OmniRightInspectorProps) {
  const [open, setOpen] = useState(defaultOpen)

  const handleToggle = useCallback(() => {
    setOpen((prev) => !prev)
  }, [])

  if (!open) {
    return (
      <button
        className={`flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.05] px-3 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-300 transition hover:text-white ${className}`.trim()}
        onClick={handleToggle}
        type="button"
        title="Open inspector"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
        Inspector
      </button>
    )
  }

  return (
    <div className={`relative ${className}`.trim()}>
      <button
        className="absolute -left-3 top-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-[rgba(11,13,29,0.9)] text-slate-400 transition hover:text-white"
        onClick={handleToggle}
        type="button"
        title="Close inspector"
      >
        <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6" /></svg>
      </button>
      {children}
    </div>
  )
}
