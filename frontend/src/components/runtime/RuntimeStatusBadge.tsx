import { OmniBadge } from '../ui/OmniBadge'
import { OmniStatusDot } from '../ui/OmniStatusDot'

type RuntimeStatusBadgeProps = {
  mode: string
  fallback?: boolean
  degraded?: boolean
  className?: string
}

export function RuntimeStatusBadge({ mode, fallback, degraded, className = '' }: RuntimeStatusBadgeProps) {
  const isFallback = fallback === true
  const isDegraded = degraded === true || mode?.toLowerCase().includes('degraded')
  const tone = isFallback ? 'danger' : isDegraded ? 'warning' : 'success'
  const label = isFallback ? 'Fallback' : isDegraded ? 'Degraded' : mode || 'Unknown'

  return (
    <OmniBadge tone={tone} className={className}>
      <OmniStatusDot tone={tone} animate={!isFallback} />
      <span>{label}</span>
    </OmniBadge>
  )
}
