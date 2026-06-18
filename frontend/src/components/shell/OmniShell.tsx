import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useState } from 'react'
import type { ReactNode } from 'react'
import { OmniTopbar } from './OmniTopbar'
import { OmniMobileNav } from './OmniMobileNav'
import { OmniSidebarToggle } from './OmniSidebar'

type MobilePanel = 'sidebar' | 'content' | 'inspector'

export type OmniShellProps = {
  sidebar?: ReactNode
  rightPanel?: ReactNode
  topbar?: ReactNode
  children: ReactNode
  showSidebar?: boolean
  showRightPanel?: boolean
}

function Backdrop({ onClose }: { onClose: () => void }) {
  return (
    <motion.div
      aria-hidden="true"
      className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    />
  )
}

export function OmniShell({
  sidebar,
  rightPanel,
  topbar,
  children,
  showSidebar = true,
  showRightPanel = false,
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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-2xl focus:border focus:border-neon-purple/40 focus:bg-[rgba(11,13,29,0.95)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:outline-none"
      >
        Skip to main content
      </a>

      <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-75">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_10%,rgba(123,97,255,0.12),transparent_50%)]" />
        <div className="absolute inset-0 bg-[length:220px_220px] bg-[image:radial-gradient(circle,rgba(255,255,255,0.03)_1px,transparent_1px)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_90%,rgba(78,164,255,0.08),transparent_50%)]" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1480px] flex-col px-3 py-3 sm:px-4 sm:py-4 lg:px-6">
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
            <>
              <AnimatePresence>
                {mobilePanel === 'sidebar' ? (
                  <Backdrop onClose={() => setMobilePanel('content')} />
                ) : null}
              </AnimatePresence>

              <aside
                role="navigation"
                aria-label="Sidebar"
                className={`${
                  mobilePanel === 'sidebar'
                    ? 'fixed inset-y-0 left-0 z-40 w-[280px] translate-x-0 transition-transform duration-300 ease-out'
                    : 'hidden'
                } lg:sticky lg:top-4 lg:block lg:h-[calc(100vh-2rem)] lg:w-auto lg:translate-x-0 ${
                  sidebarCollapsed ? 'w-16' : ''
                }`}
              >
                {/* OmniSidebarToggle provides aria-label="Expand sidebar" and aria-label="Collapse sidebar"; this shell owns the state. */}
                {sidebarCollapsed ? (
                  <OmniSidebarToggle
                    collapsed
                    onToggle={() => setSidebarCollapsed(false)}
                  />
                ) : (
                  <div className="relative h-full">
                    <OmniSidebarToggle
                      collapsed={false}
                      onToggle={() => setSidebarCollapsed(true)}
                    />
                    {sidebar}
                  </div>
                )}
              </aside>
            </>
          ) : null}

          <main
            id="main-content"
            role="main"
            className={`${
              mobilePanel === 'content' ? 'block' : 'hidden'
            } lg:block`}
          >
            {children}
          </main>

          {hasRightPanel ? (
            <>
              <AnimatePresence>
                {mobilePanel === 'inspector' ? (
                  <Backdrop onClose={() => setMobilePanel('content')} />
                ) : null}
              </AnimatePresence>

              <aside
                role="region"
                aria-label="Runtime inspector"
                className={`${
                  mobilePanel === 'inspector'
                    ? 'fixed inset-y-0 right-0 z-40 w-[320px] translate-x-0 transition-transform duration-300 ease-out sm:w-[360px]'
                    : 'hidden'
                } lg:sticky lg:top-4 lg:block lg:h-[calc(100vh-2rem)] lg:w-auto lg:translate-x-0`}
              >
                <div className="flex h-full flex-col overflow-y-auto rounded-2xl border border-white/10 bg-[rgba(11,13,29,0.92)] p-4 backdrop-blur-xl lg:h-auto lg:rounded-none lg:border-none lg:bg-transparent lg:p-0">
                  <div className="mb-3 flex items-center justify-between lg:hidden">
                    <span className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Runtime</span>
                    <button
                      aria-label="Close inspector"
                      className="rounded-full border border-white/10 bg-white/5 p-1.5 text-slate-400 transition hover:text-white"
                      onClick={() => setMobilePanel('content')}
                      type="button"
                      title="Close inspector"
                    >
                      <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" /></svg>
                    </button>
                  </div>
                  {rightPanel}
                </div>
              </aside>
            </>
          ) : null}
        </motion.div>
      </div>
    </div>
  )
}
