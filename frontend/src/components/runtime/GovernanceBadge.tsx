import type { GovernanceSummary } from '../../types'
import { OmniBadge } from '../ui/OmniBadge'

type GovernanceBadgeProps = {
  governance: GovernanceSummary | null | undefined
  className?: string
}

const DECISION_LABELS: Record<string, string> = {
  allowed: 'Allowed',
  blocked: 'Blocked',
  requires_approval: 'Pending',
  unknown: 'Unknown',
}

const DECISION_TONES: Record<string, 'success' | 'danger' | 'warning' | 'muted'> = {
  allowed: 'success',
  blocked: 'danger',
  requires_approval: 'warning',
  unknown: 'muted',
}

export function GovernanceBadge({ governance, className = '' }: GovernanceBadgeProps) {
  if (!governance) {
    return null
  }

  const decision = governance.decision ?? 'unknown'
  const label = DECISION_LABELS[decision] ?? decision
  const tone = DECISION_TONES[decision] ?? 'muted'
  const title = governance.reason
    ? `Policy: ${governance.policy ?? '—'}\nReason: ${governance.reason}`
    : undefined

  return (
    <OmniBadge tone={tone} className={className} title={title}>
      <span>Gov: {label}</span>
    </OmniBadge>
  )
}
