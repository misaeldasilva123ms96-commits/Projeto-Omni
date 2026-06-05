import { useMemo } from 'react';

const STATUS_LABELS: Record<string, string> = {
  connected: 'Conectado',
  invalid_credentials: 'Credenciais inválidas',
  connection_failed: 'Falha na conexão',
  not_configured: 'Não configurado',
};

const STATUS_VARIANTS: Record<string, string> = {
  connected: 'ok',
  invalid_credentials: 'danger',
  connection_failed: 'danger',
  not_configured: 'inactive',
};

type ProviderStatusBadgeProps = {
  configured: boolean;
  updatedAt?: number | null;
};

export function ProviderStatusBadge({ configured, updatedAt }: ProviderStatusBadgeProps) {
  const status = useMemo(() => {
    if (!configured) {
      return 'not_configured';
    }
    if (!updatedAt) {
      return 'connection_failed';
    }
    return 'connected';
  }, [configured, updatedAt]);

  const label = STATUS_LABELS[status] ?? status;
  const variant = STATUS_VARIANTS[status] ?? 'inactive';

  const formatted = useMemo(() => {
    if (!updatedAt) {
      return null;
    }
    try {
      return new Date(updatedAt).toLocaleString('pt-BR');
    } catch {
      return null;
    }
  }, [updatedAt]);

  return (
    <span className={`status-pill ${variant}`} title={formatted ?? ''}>
      {label}
      {formatted ? <span className="timestamp">{formatted}</span> : null}
    </span>
  );
}

export default ProviderStatusBadge;
