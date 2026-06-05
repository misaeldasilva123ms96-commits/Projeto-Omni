import { useProviders } from '../pages/SettingsPage';
import ProviderCard from '../pages/SettingsPage';
import type { View } from '../types';
import type { ChatMode } from '../types';

type SettingsViewProps = {
  mode: ChatMode;
  onChangeMode: (mode: ChatMode) => void;
  onChangeView: (view: View) => void;
  view: View;
};

export function SettingsView({
  mode,
  onChangeMode,
  onChangeView,
  view,
}: SettingsViewProps) {
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

  const defaultProviders = [
    { provider: 'openai', configured: false, updated_at: null },
    { provider: 'openrouter', configured: false, updated_at: null },
    { provider: 'anthropic', configured: false, updated_at: null },
    { provider: 'gemini', configured: false, updated_at: null },
    { provider: 'groq', configured: false, updated_at: null },
  ];

  const resolvedProviders =
    providers.length > 0
      ? defaultProviders.map((defaultProvider) => {
          const match = providers.find((item) => item.provider === defaultProvider.provider);
          return match ? match : defaultProvider;
        })
      : defaultProviders;

  async function handleCreate(provider: string, apiKey: string) {
    await createProvider(provider, apiKey);
  }

  async function handleUpdate(provider: string) {
    const apiKey = window.prompt('Informe a nova API Key para atualizar este provedor:');
    if (!apiKey) return;
    await editProvider(provider, apiKey.trim());
  }

  async function handleTest(provider: string, apiKey: string) {
    await runConnectionTest(provider, apiKey);
  }

  async function handleRemove(provider: string) {
    const confirmed = window.confirm(`Remover credencial do provedor ${provider}?`);
    if (!confirmed) return;
    await removeProvider(provider);
  }

  return (
    <section className="dashboard-page settings-view">
      <header className="settings-header">
        <div>
          <p className="eyebrow">Configurações</p>
          <h2>Provedores BYOK</h2>
          <p className="subtitle">
            Gerencie credenciais e conexões com provedores de IA de forma segura.
          </p>
        </div>
      </header>
      {actionError ? (
        <div className="panel-card status-card settings-error" role="alert">
          <p>{actionError}</p>
          <button type="button" className="ghost-button" onClick={clearActionError}>
            Fechar
          </button>
        </div>
      ) : null}
      <div className="providers-section">
        {resolvedProviders.map((item) => (
          <ProviderCard
            key={item.provider}
            provider={item}
            submitting={submitting}
            loadingTestProvider={testingProvider}
            onConfigure={handleCreate as (provider: string) => void}
            onUpdate={handleUpdate}
            onRemove={handleRemove}
            onTest={handleTest}
          />
        ))}
      </div>
    </section>
  );
}

export default SettingsView;
