import { useState } from 'react'
import type { ReactNode } from 'react'

type OmniTooltipProps = {
  content: string
  children: ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
}

const positionClasses: Record<string, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
}

export function OmniTooltip({ content, children, position = 'top' }: OmniTooltipProps) {
  const [visible, setVisible] = useState(false)

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible ? (
        <span
          role="tooltip"
          className={`pointer-events-none absolute z-50 whitespace-nowrap rounded-lg border border-white/10 bg-[rgba(11,15,34,0.96)] px-3 py-1.5 text-xs text-slate-200 shadow-xl backdrop-blur-md ${positionClasses[position]}`}
        >
          {content}
        </span>
      ) : null}
    </span>
  )
}
