import type { ReactNode } from 'react'

type AppShellProps = {
  children: ReactNode
  sidebar: ReactNode
  statusPanel?: ReactNode
}

export function AppShell({ children, sidebar, statusPanel }: AppShellProps) {
  return (
    <main className="app-shell">
      <div className="workspace-shell">
        <aside className="sidebar-column">{sidebar}</aside>
        <section className="content-column">{children}</section>
        {statusPanel ? <aside className="status-column">{statusPanel}</aside> : null}
      </div>
    </main>
  )
}
