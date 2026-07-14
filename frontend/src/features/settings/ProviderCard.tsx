import { useState } from 'react';
import type { ProviderRecord } from './types';
import { ProviderStatusBadge } from './ProviderStatusBadge';

type ProviderCardProps = {
  provider: ProviderRecord;
  submitting: boolean;
  loadingTestProvider: string | null;
  onConfigure: (provider: string, apiKey: string) => void;
  onUpdate: (provider: string, apiKey: string) => void;
  onRemove: (provider: string) => void;
  onTest: (provider: string, apiKey: string) => void;
};

const DISPLAY_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  groq: 'Groq',
};

export function ProviderCard({
  provider,
  submitting,
  loadingTestProvider,
  onConfigure,
  onUpdate,
  onRemove,
  onTest,
}: ProviderCardProps) {
  const [apiKey, setApiKey] = useState('');
  const [confirmRemove, setConfirmRemove] = useState(false);

  const displayName = DISPLAY_NAMES[provider.provider] ?? provider.provider;

  function handleTest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKey.trim()) {
      return;
    }
    onTest(provider.provider, apiKey.trim());
  }

  function handleConfigure(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKey.trim()) {
      return;
    }
    onConfigure(provider.provider, apiKey.trim());
  }

  function handleUpdate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKey.trim()) {
      return;
    }
    onUpdate(provider.provider, apiKey.trim());
  }

  function handleRemove() {
    onRemove(provider.provider);
  }

  return (
    <section className="panel-card provider-card" aria-label={displayName}>
      <header className="provider-header">
        <div>
          <h3 className="provider-name">{displayName}</h3>
          <span className="provider-id">{provider.provider}</span>
        </div>
        <ProviderStatusBadge
          configured={provider.configured}
          updatedAt={provider.updated_at}
          executable={provider.executable}
          reachable={provider.reachable}
          healthy={provider.healthy}
          healthValid={provider.health_valid}
          circuitState={provider.circuit_state}
          lastCheckedAt={provider.last_checked_at}
        />
      </header>

      <form className="provider-form" onSubmit={provider.configured ? handleUpdate : handleConfigure}>
        <label htmlFor={`provider-key-${provider.provider}`}>API Key</label>
        <input
          id={`provider-key-${provider.provider}`}
          name="api_key"
          type="password"
          autoComplete="off"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder={provider.configured ? 'Atualizar API Key' : 'Informe a API Key'}
          required
        />
        <div className="provider-actions">
          <button
            type="submit"
            className="primary-button"
            disabled={submitting || !apiKey.trim()}
          >
            {provider.configured ? 'Atualizar' : 'Configurar'}
          </button>
          <button
            type="button"
            className="ghost-button"
            disabled={submitting || !apiKey.trim()}
            onClick={() => onTest(provider.provider, apiKey.trim())}
          >
            {loadingTestProvider === provider.provider ? 'Testando...' : 'Testar conexão'}
          </button>
          {provider.configured ? (
            <button
              type="button"
              className="ghost-button danger"
              disabled={submitting}
              onClick={handleRemove}
            >
              Remover
            </button>
          ) : null}
        </div>
      </form>

      {confirmRemove ? (
        <div className="provider-confirm" role="alert">
          <p>Remover esta credencial?</p>
          <div className="provider-actions">
            <button
              type="button"
              className="ghost-button danger"
              disabled={submitting}
              onClick={handleRemove}
            >
              Confirmar remoção
            </button>
            <button
              type="button"
              className="ghost-button"
              disabled={submitting}
              onClick={() => setConfirmRemove(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default ProviderCard;
