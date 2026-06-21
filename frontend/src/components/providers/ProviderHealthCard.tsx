import type { ProviderRecord, ProviderTestResult } from '../../features/settings/types'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniButton } from '../ui/OmniButton'
import { OmniCard } from '../ui/OmniCard'
import { OmniInput } from '../ui/OmniInput'
import { OmniSuccessState } from '../ui/OmniSuccessState'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

type ProviderHealthCardProps = {
  provider: ProviderRecord
  testResult?: ProviderTestResult | null
  submitting: boolean
  testing: boolean
  onSave: (apiKey: string) => void
  onUpdate: (apiKey: string) => void
  onRemove: () => void
  onTest: (apiKey: string) => void
  className?: string
  apiKey: string
  onApiKeyChange: (value: string) => void
}

const DISPLAY_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  groq: 'Groq',
}

const PROVIDER_ICONS: Record<string, string> = {
  openai: 'bg-emerald-500',
  openrouter: 'bg-blue-500',
  anthropic: 'bg-violet-500',
  gemini: 'bg-amber-500',
  groq: 'bg-rose-500',
}

export function ProviderHealthCard({
  provider, testResult, submitting, testing, onSave, onUpdate, onRemove, onTest, className = '', apiKey, onApiKeyChange,
}: ProviderHealthCardProps) {
  const safeProviderName = redactRuntimeDebugText(provider.provider)
  const displayName = DISPLAY_NAMES[provider.provider] ?? safeProviderName
  const iconColor = PROVIDER_ICONS[provider.provider] ?? 'bg-slate-500'
  const isConfigured = provider.configured
  const canSubmit = apiKey.trim().length > 0

  const statusBadge = isConfigured
    ? <OmniBadge tone="success">Conectado</OmniBadge>
    : <OmniBadge tone="muted">Não configurado</OmniBadge>

  return (
    <OmniCard variant="default" className={className}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconColor} shadow-lg`}>
            <span className="text-sm font-bold text-white">
              {displayName.charAt(0)}
            </span>
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-white">{displayName}</h3>
            <div className="mt-0.5 flex items-center gap-2">
              {statusBadge}
              <span className="text-[11px] text-slate-500">{safeProviderName}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-violet-200/70" htmlFor={`key-${provider.provider}`}>
            API Key
          </label>
          <OmniInput
            id={`key-${provider.provider}`}
            onChange={(e) => onApiKeyChange(e.target.value)}
            placeholder={isConfigured ? 'Atualizar API Key' : 'Informe a API Key'}
            value={apiKey}
            type="password"
          />
        </div>

        {testResult ? (
          testResult.success ? (
            <OmniSuccessState description="Conexão bem-sucedida" size="compact" />
          ) : (
            <div className="rounded-2xl border border-red-400/20 bg-red-400/10 px-3 py-2 text-xs text-red-200">
              {`Falha: ${redactRuntimeDebugText(testResult.error ?? 'erro desconhecido')}`}
            </div>
          )
        ) : null}

        <div className="flex flex-wrap gap-2">
          {isConfigured ? (
            <OmniButton variant="primary" disabled={!canSubmit || submitting} onClick={() => onUpdate(apiKey)}>
              {submitting ? 'Salvando...' : 'Atualizar'}
            </OmniButton>
          ) : (
            <OmniButton variant="primary" disabled={!canSubmit || submitting} onClick={() => onSave(apiKey)}>
              {submitting ? 'Salvando...' : 'Configurar'}
            </OmniButton>
          )}
          <OmniButton variant="secondary" disabled={!canSubmit || testing} onClick={() => onTest(apiKey)}>
            {testing ? 'Testando...' : 'Testar conexão'}
          </OmniButton>
          {isConfigured ? (
            <OmniButton variant="danger" onClick={onRemove}>
              Remover
            </OmniButton>
          ) : null}
        </div>
      </div>
    </OmniCard>
  )
}
