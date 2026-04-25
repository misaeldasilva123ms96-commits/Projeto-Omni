import { motion } from 'framer-motion'
import { useState } from 'react'
import type { ReactNode } from 'react'

type LayoutProps = {
  sidebar: ReactNode
  center: ReactNode
  right: ReactNode
}

export function Layout({ sidebar, center, right }: LayoutProps) {
  const [mobilePanel, setMobilePanel] = useState<'chat' | 'runtime' | 'tools'>('chat')

  return (
    <div className="min-h-screen overflow-hidden bg-cosmic-gradient text-slate-50">
      <div className="pointer-events-none absolute inset-0 opacity-75">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_12%,rgba(123,97,255,0.14),transparent_18%),radial-gradient(circle_at_80%_20%,rgba(81,246,255,0.08),transparent_14%),radial-gradient(circle_at_50%_80%,rgba(181,109,255,0.08),transparent_22%)]" />
        <div className="absolute inset-0 bg-[length:220px_220px] bg-[image:radial-gradient(rgba(255,255,255,0.16)_1px,transparent_1px)] opacity-[0.16]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_35%_36%,rgba(140,94,255,0.12),transparent_18%),radial-gradient(circle_at_64%_68%,rgba(98,121,255,0.06),transparent_22%)] opacity-90" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1580px] flex-col px-5 py-8 lg:px-10">
        <div className="mb-4 grid grid-cols-3 gap-2 lg:hidden">
          {[
            ['chat', 'Chat'],
            ['runtime', 'Runtime'],
            ['tools', 'Tools'],
          ].map(([id, label]) => (
            <button
              key={id}
              className={`rounded-2xl border px-3 py-2 text-sm transition ${
                mobilePanel === id
                  ? 'border-neon-cyan/45 bg-neon-cyan/10 text-white shadow-[0_0_18px_rgba(81,246,255,0.16)]'
                  : 'border-white/10 bg-white/[0.04] text-slate-300'
              }`}
              onClick={() => setMobilePanel(id as 'chat' | 'runtime' | 'tools')}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="grid min-h-[calc(100vh-4rem)] gap-6 lg:grid-cols-[262px_minmax(0,1fr)_316px]"
          initial={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
        >
          <aside className={`${mobilePanel === 'tools' ? 'block' : 'hidden'} min-h-0 lg:sticky lg:top-8 lg:block lg:h-[calc(100vh-4rem)]`}>
            {sidebar}
          </aside>
          <main className={`${mobilePanel === 'chat' ? 'block' : 'hidden'} min-h-0 lg:block`}>
            {center}
          </main>
          <aside className={`${mobilePanel === 'runtime' ? 'block md:fixed md:inset-y-6 md:right-6 md:z-30 md:w-[360px] md:max-w-[calc(100vw-3rem)] lg:static lg:w-auto' : 'hidden'} min-h-0 lg:sticky lg:top-8 lg:block lg:h-[calc(100vh-4rem)]`}>
            {right}
          </aside>
        </motion.div>
      </div>
    </div>
  )
}
