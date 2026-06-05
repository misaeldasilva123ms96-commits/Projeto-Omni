import type { ReactNode } from 'react'
import { OmniPanel } from '../ui/OmniPanel'

type OmniChatPanelProps = {
  children: ReactNode
  className?: string
  runtimeActive?: boolean
}

export function OmniChatPanel({ children, className = '', runtimeActive = false }: OmniChatPanelProps) {
  return (
    <OmniPanel
      className={`flex h-full min-h-0 flex-1 flex-col overflow-hidden ${runtimeActive ? 'omni-runtime-glow' : ''} ${className}`.trim()}
      padded={false}
    >
      <div className="flex min-h-0 flex-1 flex-col p-5">
        {children}
      </div>
    </OmniPanel>
  )
}
