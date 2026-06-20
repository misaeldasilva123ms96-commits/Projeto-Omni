import { useCallback, useMemo, useRef, useState } from 'react'
import type { LabConfig, LabTest } from '../../types'
import { OmniButton } from '../ui/OmniButton'
import { OmniCard } from '../ui/OmniCard'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

const MODEL_OPTIONS = [
  { id: 'gpt-4o', label: 'GPT-4o' },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { id: 'claude-3-opus', label: 'Claude 3 Opus' },
  { id: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
  { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
  { id: 'gemini-2.0-pro', label: 'Gemini 2.0 Pro' },
  { id: 'grok-2', label: 'Grok 2' },
  { id: 'deepseek-r1', label: 'DeepSeek R1' },
]

const PROVIDER_OPTIONS = [
  { id: 'openai', label: 'OpenAI' },
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'gemini', label: 'Gemini' },
  { id: 'groq', label: 'Groq' },
  { id: 'openrouter', label: 'OpenRouter' },
]

const DEFAULT_CONFIG: LabConfig = {
  model: 'gpt-4o-mini',
  provider: 'openai',
  temperature: 0.7,
  maxTokens: 1024,
  systemPrompt: '',
}

const LAB_HISTORY_KEY = 'omini-lab-history-v1'

function loadHistory(): LabTest[] {
  try {
    const raw = localStorage.getItem(LAB_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveHistory(tests: LabTest[]) {
  try {
    localStorage.setItem(LAB_HISTORY_KEY, JSON.stringify(tests.slice(0, 100)))
  } catch {
    // ignore
  }
}

type LabConsoleProps = {
  className?: string
}

export function LabConsole({ className = '' }: LabConsoleProps) {
  const [config, setConfig] = useState<LabConfig>(DEFAULT_CONFIG)
  const [prompt, setPrompt] = useState('')
  const [sending, setSending] = useState(false)
  const [response, setResponse] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showConfig, setShowConfig] = useState(false)
  const [history, setHistory] = useState<LabTest[]>(loadHistory)
  const [showHistory, setShowHistory] = useState(false)
  const startTime = useRef(0)

  const handleSend = useCallback(async () => {
    if (!prompt.trim() || sending) return

    setSending(true)
    setError(null)
    setResponse(null)
    startTime.current = Date.now()

    try {
      const { sendOmniMessage } = await import('../../lib/api/chat')
      const res = await sendOmniMessage(prompt.trim(), {})

      const latencyMs = Date.now() - startTime.current
      const safeResponse = redactRuntimeDebugText(res.response)

      const test: LabTest = {
        id: crypto.randomUUID(),
        config: {
          ...config,
          systemPrompt: redactRuntimeDebugText(config.systemPrompt),
        },
        prompt: redactRuntimeDebugText(prompt.trim()),
        response: safeResponse,
        latencyMs,
        timestamp: new Date().toISOString(),
      }

      setResponse(safeResponse)
      setHistory((prev) => {
        const updated = [test, ...prev]
        saveHistory(updated)
        return updated
      })
    } catch (err: unknown) {
      const msg = err instanceof Error
        ? redactRuntimeDebugText(err.message)
        : 'Erro ao processar requisição'
      setError(msg)
    } finally {
      setSending(false)
    }
  }, [prompt, sending, config])

  const handleClearHistory = useCallback(() => {
    setHistory([])
    saveHistory([])
  }, [])

  const handleRestore = useCallback((test: LabTest) => {
    setConfig(test.config)
    setPrompt(test.prompt)
    setResponse(test.response)
    setShowHistory(false)
  }, [])

  const updateConfig = useCallback(<K extends keyof LabConfig>(key: K, value: LabConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }, [])

  const recentTests = useMemo(() => history.slice(0, 20), [history])

  return (
    <div className={`flex flex-col gap-4 lg:flex-row ${className}`.trim()}>
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <OmniCard variant="panel">
          <div className="flex items-center justify-between">
            <h3 className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Console</h3>
            <div className="flex items-center gap-2">
              <button
                className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition hover:border-white/20"
                onClick={() => setShowHistory((v) => !v)}
                type="button"
              >
                {showHistory ? 'Fechar' : `Histórico (${history.length})`}
              </button>
              <button
                className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition hover:border-white/20"
                onClick={() => setShowConfig((v) => !v)}
                type="button"
              >
                {showConfig ? 'Fechar' : 'Config'}
              </button>
            </div>
          </div>
        </OmniCard>

        {showConfig ? (
          <OmniCard variant="panel">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Modelo</span>
                <select
                  className="mt-1 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
                  value={config.model}
                  onChange={(e) => updateConfig('model', e.target.value)}
                >
                  {MODEL_OPTIONS.map((opt) => (
                    <option key={opt.id} className="bg-[#0a0b1b] text-white" value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Provedor</span>
                <select
                  className="mt-1 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
                  value={config.provider}
                  onChange={(e) => updateConfig('provider', e.target.value)}
                >
                  {PROVIDER_OPTIONS.map((opt) => (
                    <option key={opt.id} className="bg-[#0a0b1b] text-white" value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  Temperature: {config.temperature.toFixed(1)}
                </span>
                <input
                  className="mt-1 w-full accent-violet-500"
                  max={2}
                  min={0}
                  step={0.1}
                  type="range"
                  value={config.temperature}
                  onChange={(e) => updateConfig('temperature', Number(e.target.value))}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Max Tokens</span>
                <input
                  className="mt-1 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
                  max={8192}
                  min={64}
                  step={64}
                  type="number"
                  value={config.maxTokens}
                  onChange={(e) => updateConfig('maxTokens', Math.max(64, Math.min(8192, Number(e.target.value))))}
                />
              </label>
            </div>

            <label className="mt-4 block">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-400">System Prompt</span>
              <textarea
                className="mt-1 min-h-[60px] w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
                placeholder="Instruções de sistema para o modelo (opcional)"
                value={config.systemPrompt}
                onChange={(e) => updateConfig('systemPrompt', e.target.value)}
              />
            </label>
          </OmniCard>
        ) : null}

        <OmniCard variant="panel">
          <textarea
            className="min-h-[100px] w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
            placeholder="Digite seu prompt de teste aqui..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-slate-500">Ctrl+Enter para enviar</span>
            <OmniButton disabled={!prompt.trim() || sending} variant="primary" onClick={handleSend}>
              {sending ? 'Enviando...' : 'Enviar'}
            </OmniButton>
          </div>
        </OmniCard>

        {error ? (
          <OmniCard variant="panel">
            <p className="text-sm text-red-300">{redactRuntimeDebugText(error)}</p>
          </OmniCard>
        ) : null}

        {response ? (
          <OmniCard variant="panel">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Resposta</h3>
              <button
                className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition hover:border-white/20"
                onClick={() => { navigator.clipboard.writeText(response).catch(() => {}) }}
                type="button"
              >
                Copiar
              </button>
            </div>
            <div className="prose prose-invert max-w-none whitespace-pre-wrap text-sm text-slate-200">
              {response}
            </div>
          </OmniCard>
        ) : null}
      </div>

      {showHistory && recentTests.length > 0 ? (
        <div className="w-full shrink-0 lg:w-80">
          <OmniCard variant="panel">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs uppercase tracking-[0.25em] text-violet-200/70">Testes Recentes</h3>
              <button
                className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition hover:border-white/20"
                onClick={handleClearHistory}
                type="button"
              >
                Limpar
              </button>
            </div>

            <div className="flex max-h-[60vh] flex-col gap-2 overflow-y-auto">
              {recentTests.map((test) => (
                <button
                  key={test.id}
                  className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2.5 text-left text-xs transition hover:border-white/20"
                  onClick={() => handleRestore(test)}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-2 text-slate-400">
                    <span className="truncate font-medium text-slate-300">
                      {test.prompt.slice(0, 40)}{test.prompt.length > 40 ? '...' : ''}
                    </span>
                    <span className="shrink-0">{test.latencyMs}ms</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-500">
                    <span>{test.config.model}</span>
                    <span>·</span>
                    <span>{test.config.provider}</span>
                  </div>
                </button>
              ))}
            </div>
          </OmniCard>
        </div>
      ) : null}
    </div>
  )
}
