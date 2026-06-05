import type { ReactNode } from 'react'
import { RuntimeTruthBar } from '../runtime/RuntimeTruthBar'

type OmniTopbarProps = {
  children?: ReactNode
  className?: string
}

export function OmniTopbar({ children, className = '' }: OmniTopbarProps) {
  return (
    <header
      className={`mb-3 flex items-center justify-between rounded-[20px] border border-[rgba(138,160,255,0.1)] bg-[rgba(9,12,24,0.55)] px-4 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.2)] backdrop-blur-md ${className}`.trim()}
    >
      {children ?? <RuntimeTruthBar />}
    </header>
  )
}
