import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

type LayoutProps = {
  sidebar: ReactNode
  center: ReactNode
  right: ReactNode
}

export function Layout({ sidebar, center, right }: LayoutProps) {
  return (
    <div className="min-h-screen overflow-hidden bg-cosmic-gradient text-slate-50">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_12%,rgba(123,97,255,0.16),transparent_18%),radial-gradient(circle_at_80%_20%,rgba(81,246,255,0.12),transparent_14%),radial-gradient(circle_at_50%_80%,rgba(181,109,255,0.1),transparent_22%)]" />
        <div className="absolute inset-0 bg-[length:240px_240px] bg-[image:radial-gradient(rgba(255,255,255,0.14)_1px,transparent_1px)] opacity-[0.14]" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-4 py-6 lg:px-8">
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="grid min-h-[calc(100vh-3rem)] gap-5 lg:grid-cols-[280px_minmax(0,1fr)_340px]"
          initial={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
        >
          <aside className="min-h-0 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
            {sidebar}
          </aside>
          <main className="min-h-0">
            {center}
          </main>
          <aside className="min-h-0 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
            {right}
          </aside>
        </motion.div>
      </div>
    </div>
  )
}
