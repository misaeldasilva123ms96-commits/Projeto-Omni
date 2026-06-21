import { useMemo } from 'react'
import { OmniBadge } from '../../components/ui/OmniBadge'
import type { OmniBadgeTone } from '../../components/ui/OmniBadge'

const STATUS_LABELS: Record<string, string> = {
  connected: 'Conectado',
  invalid_credentials: 'Credenciais inválidas',
  connection_failed: 'Falha na conexão',
  not_configured: 'Não configurado',
}

const STATUS_TONES: Record<string, OmniBadgeTone> = {
  connected: 'success',
  invalid_credentials: 'warning',
  connection_failed: 'danger',
  not_configured: 'muted',
}

type ProviderStatusBadgeProps = {
  configured: boolean
  updatedAt?: number | null
}

export function ProviderStatusBadge({ configured, updatedAt }: ProviderStatusBadgeProps) {
  const status = useMemo(() => {
    if (!configured) {
      return 'not_configured'
    }
    if (!updatedAt) {
      return 'connection_failed'
    }
    return 'connected'
  }, [configured, updatedAt])

  const label = STATUS_LABELS[status] ?? status
  const tone = STATUS_TONES[status] ?? 'muted'

  const formatted = useMemo(() => {
    if (!updatedAt) {
      return null
    }
    try {
      return new Date(updatedAt).toLocaleString('pt-BR')
    } catch {
      return null
    }
  }, [updatedAt])

  return (
    <OmniBadge tone={tone} title={formatted ?? ''}>
      {label}
    </OmniBadge>
  )
}

export default ProviderStatusBadge
