import type { HTMLAttributes, ReactNode } from 'react'

type OmniPanelProps = {
  children: ReactNode
  className?: string
  padded?: boolean
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

export function OmniPanel({ children, className = '', padded = true, ...rest }: OmniPanelProps) {
  return (
    <div
      className={`rounded-[24px] border border-[rgba(138,160,255,0.14)] bg-[rgba(9,14,24,0.72)] shadow-[0_24px_60px_rgba(0,0,0,0.34)] backdrop-blur-[18px] ${padded ? 'p-5' : ''} ${className}`.trim()}
      {...rest}
    >
      {children}
    </div>
  )
}
