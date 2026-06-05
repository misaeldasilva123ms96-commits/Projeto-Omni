import { motion } from 'framer-motion'
import { useCallback, useState } from 'react'
import type { ReactNode } from 'react'
import { OmniTopbar } from './OmniTopbar'
import { OmniMobileNav } from './OmniMobileNav'

type MobilePanel = 'sidebar' | 'content' | 'inspector'

type OmniShellProps = {
  sidebar?: ReactNode
  rightPanel?: ReactNode
  topbar?: ReactNode
  children: ReactNode
  showSidebar?: boolean
  showRightPanel?: boolean
  onToggleRightPanel?: () => void
}

export function OmniShell({
  sidebar,
  rightPanel,
  topbar,
  children,
  showSidebar = true,
  showRightPanel = false,
  onToggleRightPanel,
}: OmniShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('content')

  const handleMobileSelect = useCallback((panel: MobilePanel) => {
    setMobilePanel(panel)
  }, [])

  const hasSidebar = !!sidebar && showSidebar
  const hasRightPanel = !!rightPanel && showRightPanel

  return (
    <div className="min-h-screen overflow-hidden bg-cosmic-gradient text-slate-50">
      <div className="pointer-events-none absolute inset-0 opacity-75">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_10%,rgba(123,97,255,0.12),transparent_50%)]" />
        <div className="absolute inset-0 bg-[length:220px_220px] bg-[image:radial-gradient(circle,rgba(255,255,255,0.03)_1px,transparent_1px)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_90%,rgba(78,164,255,0.08),transparent_50%)]" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1480px] flex-col px-4 py-4 lg:px-6">
        <OmniTopbar>{topbar}</OmniTopbar>

        <OmniMobileNav
          activePanel={mobilePanel}
          onSelect={handleMobileSelect}
          hasSidebar={hasSidebar}
          hasRightPanel={hasRightPanel}
        />

        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="grid min-h-[calc(100vh-4rem)] gap-4"
          initial={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          style={{
            gridTemplateColumns: hasSidebar
              ? sidebarCollapsed
                ? '64px minmax(0,1fr)'
                : hasRightPanel
                  ? '246px minmax(0,1fr) 300px'
                  : '246px minmax(0,1fr)'
              : hasRightPanel
                ? 'minmax(0,1fr) 300px'
                : 'minmax(0,1fr)',
          }}
        >
          {hasSidebar ? (
            <aside
              className={`${
                mobilePanel === 'sidebar' ? 'block' : 'hidden'
              } lg:sticky lg:top-4 lg:block lg:h-[calc(100vh-2rem)] ${
                sidebarCollapsed ? 'w-16' : ''
              }`}
            >
              {sidebarCollapsed ? (
                <button
                  className="flex w-full items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-slate-300 transition hover:text-white"
                  onClick={() => setSidebarCollapsed(false)}
                  type="button"
                  title="Expand sidebar"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
                </button>
              ) : (
                <div className="relative h-full">
                  <button
                    className="absolute -right-3 top-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-[rgba(11,13,29,0.9)] text-slate-400 transition hover:text-white"
                    onClick={() => setSidebarCollapsed(true)}
                    type="button"
                    title="Collapse sidebar"
                  >
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6" /></svg>
                  </button>
                  {sidebar}
                </div>
              )}
            </aside>
          ) : null}

          <main
            className={`${
              mobilePanel === 'content' ? 'block' : 'hidden'
            } lg:block`}
          >
            {children}
          </main>

          {hasRightPanel ? (
            <aside
              className={`${
                mobilePanel === 'inspector' ? 'block md:fixed md:inset-0 md:z-40' : 'hidden'
              } lg:sticky lg:top-4 lg:block lg:h-[calc(100vh-2rem)]`}
            >
              <div className="flex items-center justify-between lg:mb-2">
                <button
                  className="rounded-full border border-white/10 bg-white/[0.05] p-1.5 text-slate-400 transition hover:text-white md:ml-auto lg:hidden"
                  onClick={() => setMobilePanel('content')}
                  type="button"
                  title="Close inspector"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              </div>
              {rightPanel}
            </aside>
          ) : null}
        </motion.div>
      </div>
    </div>
  )
}
