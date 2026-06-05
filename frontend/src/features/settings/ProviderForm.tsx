import { useState } from 'react';

const ALLOWED_PROVIDERS = ['openai', 'openrouter', 'anthropic', 'gemini', 'groq'];

const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  groq: 'Groq',
};

type ProviderFormProps = {
  submitting: boolean;
  onSave: (provider: string, apiKey: string) => Promise<void>;
};

export function ProviderForm({ submitting, onSave }: ProviderFormProps) {
  const [provider, setProvider] = useState(ALLOWED_PROVIDERS[0]);
  const [apiKey, setApiKey] = useState('');

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKey.trim()) {
      return;
    }
    await onSave(provider, apiKey.trim());
    setApiKey('');
  }

  return (
    <form className="panel-card provider-form" onSubmit={handleSubmit}>
      <h3 className="panel-title">Adicionar provedor</h3>
      <label htmlFor="provider-select">Provedor</label>
      <select
        id="provider-select"
        value={provider}
        onChange={(event) => setProvider(event.target.value)}
      >
        {ALLOWED_PROVIDERS.map((item) => (
          <option key={item} value={item}>
            {PROVIDER_DISPLAY_NAMES[item] ?? item}
          </option>
        ))}
      </select>
      <label htmlFor="provider-key">API Key</label>
      <input
        id="provider-key"
        name="api_key"
        type="password"
        autoComplete="off"
        value={apiKey}
        onChange={(event) => setApiKey(event.target.value)}
        placeholder="Informe a API Key"
        required
      />
      <button
        type="submit"
        className="primary-button"
        disabled={submitting || !apiKey.trim()}
      >
        Salvar credencial
      </button>
    </form>
  );
}

export default ProviderForm;
