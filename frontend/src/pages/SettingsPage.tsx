import { useProviders } from '../features/settings/hooks/useProviders';
import ProviderCard from '../features/settings/ProviderCard';
import type { ProviderRecord } from '../features/settings/types';
import { OmniErrorState } from '../components/ui/OmniErrorState';
import { OmniLoadingState } from '../components/ui/OmniLoadingState';

const DEFAULT_PROVIDERS: ProviderRecord[] = [
  { provider: 'openai', configured: false, updated_at: null },
  { provider: 'openrouter', configured: false, updated_at: null },
  { provider: 'anthropic', configured: false, updated_at: null },
  { provider: 'gemini', configured: false, updated_at: null },
  { provider: 'groq', configured: false, updated_at: null },
];

export function SettingsView() {
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

  async function handleCreate(provider: string, apiKey: string) {
    await createProvider(provider, apiKey);
  }

  async function handleUpdate(provider: string, apiKey: string) {
    await editProvider(provider, apiKey);
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
        <OmniErrorState
          actionLabel="Fechar"
          className="status-card error"
          description={actionError}
          onAction={clearActionError}
          size="compact"
        />
      ) : null}

      {loading ? (
        <OmniLoadingState label="Carregando provedores..." skeletonRows={3} />
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
