import type { ReactNode } from 'react'
import { SafeJsonViewer } from './SafeJsonViewer'

type SafeDebugPanelProps = {
  title?: string
  data: unknown
  children?: ReactNode
  className?: string
  maxDepth?: number
}

export function SafeDebugPanel({ title = 'Safe Debug View', data, children, className = '', maxDepth = 6 }: SafeDebugPanelProps) {
  return (
    <section className={`rounded-[24px] border border-white/10 bg-black/15 px-4 py-3.5 ${className}`.trim()}>
      {title ? (
        <h4 className="mb-3 text-sm font-medium text-white">{title}</h4>
      ) : null}
      {children ? (
        <div className="mb-3">{children}</div>
      ) : null}
      <SafeJsonViewer data={data} maxDepth={maxDepth} />
    </section>
  )
}
