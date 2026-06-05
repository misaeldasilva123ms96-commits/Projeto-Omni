import { useProviders } from '../features/settings/hooks/useProviders';
import ProviderCard from '../features/settings/ProviderCard';
import ProviderStatusBadge from '../features/settings/ProviderStatusBadge';
import type { ProviderRecord } from '../features/settings/types';

const DEFAULT_PROVIDERS: ProviderRecord[] = [
  { provider: 'openai', configured: false, updated_at: null },
  { provider: 'openrouter', configured: false, updated_at: null },
  { provider: 'anthropic', configured: false, updated_at: null },
  { provider: 'gemini', configured: false, updated_at: null },
  { provider: 'groq', configured: false, updated_at: null },
];

const STATUS_MESSAGES: Record<string, string> = {
  connected: 'Provedor conectado com sucesso.',
  invalid_credentials: 'Credencial inválida. Verifique a API Key.',
  connection_failed: 'Não foi possível validar a conexão.',
  not_configured: 'Provedor não configurado.',
};

type SettingsViewProps = {
  mode: string;
  onChangeMode: (mode: string) => void;
  onChangeView: (view: string) => void;
  view: string;
};

export function SettingsView({ mode, onChangeMode, onChangeView, view }: SettingsViewProps) {
  const {
    actionError,
    clearActionError,
    createProvider,
    editProvider,
    lastTestResult,
    loading,
    providers,
    removeProvider,
    runConnectionTest,
    submitting,
    testingProvider,
  } = useProviders();

  const resolvedProviders =
    providers.length > 0
      ? DEFAULT_PROVIDERS.map((defaultProvider) => {
        const match = providers.find((item) => item.provider === defaultProvider.provider);
        if (match) {
          return match;
        }
        return defaultProvider;
      })
      : DEFAULT_PROVIDERS;

  const statusMessage = lastTestResult
    ? lastTestResult.error
      ?? STATUS_MESSAGES[lastTestResult.success ? 'connected' : 'invalid_credentials']
    : null;

  async function handleCreate(provider: string, apiKey: string) {
    await createProvider(provider, apiKey);
  }

  async function handleUpdate(provider: string) {
    const apiKey = window.prompt('Informe a nova API Key para atualizar este provedor:');
    if (!apiKey) {
      return;
    }
    await editProvider(provider, apiKey.trim());
  }

  async function handleTest(provider: string, apiKey: string) {
    await runConnectionTest(provider, apiKey);
  }

  async function handleRemove(provider: string) {
    const confirmed = window.confirm(`Remover credencial do provedor ${provider}?`);
    if (!confirmed) {
      return;
    }
    await removeProvider(provider);
  }

  return (
    <section className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Configurações</p>
          <h2>Provedores BYOK</h2>
          <p className="subtitle">
            Gerencie credenciais e conexões com provedores de IA de forma segura.
          </p>
        </div>
      </header>

      {actionError ? (
        <div className="panel-card status-card error" role="alert">
          <p>{actionError}</p>
          <button type="button" className="ghost-button" onClick={clearActionError}>
            Fechar
          </button>
        </div>
      ) : null}

      {statusMessage ? (
        <div className="panel-card status-card" role="status">
          <p>{statusMessage}</p>
        </div>
      ) : null}

      {loading ? (
        <div className="panel-card" aria-busy="true">
          <p>Carregando configurações...</p>
        </div>
      ) : (
        <div className="providers-grid">
          {resolvedProviders.map((item) => (
            <ProviderCard
              key={item.provider}
              provider={item}
              submitting={submitting}
              loadingTestProvider={testingProvider}
              onConfigure={handleCreate}
              onUpdate={handleUpdate}
              onRemove={handleRemove}
              onTest={handleTest}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default SettingsView;
