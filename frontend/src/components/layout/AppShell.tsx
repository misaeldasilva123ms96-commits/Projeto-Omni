import type { ReactNode } from 'react'

type AppShellProps = {
  children: ReactNode
  sidebar: ReactNode
  statusPanel?: ReactNode
}

/**
 * Three-column Omni workspace: navigation, primary task, optional status rail.
 */
export function AppShell({ children, sidebar, statusPanel }: AppShellProps) {
  return (
    <main className="app-shell omni-app-shell">
      <div className="workspace-shell omni-workspace">
        <aside className="sidebar-column omni-rail omni-rail--nav">{sidebar}</aside>
        <section className="content-column omni-main">{children}</section>
        {statusPanel ? (
          <aside className="status-column omni-rail omni-rail--status">{statusPanel}</aside>
        ) : null}
      </div>
    </main>
  )
}
