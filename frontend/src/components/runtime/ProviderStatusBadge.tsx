import { OmniBadge } from '../ui/OmniBadge'

type ProviderStatusBadgeProps = {
  provider: string | null | undefined
  available?: boolean
  className?: string
}

const PROVIDER_LABELS: Record<string, string> = {
  local: 'Local',
  ollama: 'Local',
  openai: 'BYOK',
  azure: 'Managed',
  anthropic: 'BYOK',
  google: 'BYOK',
}

const PROVIDER_TONES: Record<string, 'info' | 'success' | 'warning' | 'muted'> = {
  local: 'info',
  ollama: 'info',
  openai: 'success',
  azure: 'warning',
  anthropic: 'success',
  google: 'success',
}

export function ProviderStatusBadge({ provider, available, className = '' }: ProviderStatusBadgeProps) {
  if (!provider) {
    return (
      <OmniBadge tone="muted" className={className}>
        No provider
      </OmniBadge>
    )
  }

  const key = provider.toLowerCase()
  const label = PROVIDER_LABELS[key] ?? provider
  const tone = available === false ? 'danger' : (PROVIDER_TONES[key] ?? 'info')

  return (
    <OmniBadge tone={tone} className={className}>
      <span>{label}</span>
    </OmniBadge>
  )
}
