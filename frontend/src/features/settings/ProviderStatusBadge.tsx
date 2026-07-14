import { useMemo } from 'react'
import { OmniBadge } from '../../components/ui/OmniBadge'
import type { OmniBadgeTone } from '../../components/ui/OmniBadge'

const STATUS_LABELS: Record<string, string> = {
  configured: 'Configurado',
  healthy: 'Saudável',
  unhealthy: 'Não saudável',
  unreachable: 'Inacessível',
  circuit_open: 'Circuito aberto',
  adapter_unavailable: 'Adapter indisponível',
  not_configured: 'Não configurado',
}

const STATUS_TONES: Record<string, OmniBadgeTone> = {
  configured: 'info',
  healthy: 'success',
  unhealthy: 'warning',
  unreachable: 'danger',
  circuit_open: 'danger',
  adapter_unavailable: 'danger',
  not_configured: 'muted',
}

type ProviderStatusBadgeProps = {
  configured: boolean
  updatedAt?: number | null
  executable?: boolean
  reachable?: boolean | null
  healthy?: boolean | null
  healthValid?: boolean
  circuitState?: string
  lastCheckedAt?: number | null
}

export function ProviderStatusBadge({
  configured,
  updatedAt,
  executable,
  reachable,
  healthy,
  healthValid,
  circuitState,
  lastCheckedAt,
}: ProviderStatusBadgeProps) {
  const status = useMemo(() => {
    if (!configured) {
      return 'not_configured'
    }
    if (executable === false) return 'adapter_unavailable'
    if (circuitState === 'open') return 'circuit_open'
    if (healthValid && healthy) return 'healthy'
    if (healthValid && reachable === false) return 'unreachable'
    if (healthValid && healthy === false) return 'unhealthy'
    return 'configured'
  }, [circuitState, configured, executable, healthValid, healthy, reachable])

  const label = STATUS_LABELS[status] ?? status
  const tone = STATUS_TONES[status] ?? 'muted'

  const formatted = useMemo(() => {
    const timestamp = lastCheckedAt ?? updatedAt
    if (!timestamp) {
      return null
    }
    try {
      return new Date(timestamp).toLocaleString('pt-BR')
    } catch {
      return null
    }
  }, [lastCheckedAt, updatedAt])

  return (
    <OmniBadge tone={tone} title={formatted ?? ''}>
      {label}
    </OmniBadge>
  )
}

export default ProviderStatusBadge
