import { OmniBadge } from '../ui/OmniBadge'

type PlanBadgeProps = {
  plan?: string | null
  className?: string
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  byok: 'BYOK',
  pro: 'Pro',
  local: 'Local',
  managed: 'Managed',
}

const PLAN_TONES: Record<string, 'info' | 'success' | 'warning' | 'muted'> = {
  free: 'muted',
  byok: 'success',
  pro: 'warning',
  local: 'info',
  managed: 'warning',
}

export function PlanBadge({ plan, className = '' }: PlanBadgeProps) {
  if (!plan) {
    return null
  }

  const key = plan.toLowerCase()
  const label = PLAN_LABELS[key] ?? plan
  const tone = PLAN_TONES[key] ?? 'info'

  return (
    <OmniBadge tone={tone} className={className}>
      <span>{label}</span>
    </OmniBadge>
  )
}
