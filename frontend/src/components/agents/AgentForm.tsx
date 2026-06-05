import { useState } from 'react'
import type { Agent } from '../../types'
import { OmniButton } from '../ui/OmniButton'

type AgentFormProps = {
  agent?: Agent | null
  onSubmit: (input: {
    name: string
    description: string
    model: string
    provider: string
    tools: string[]
  }) => void
  onCancel: () => void
  className?: string
}

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

const AVAILABLE_TOOLS = [
  { id: 'web_search', label: 'Web Search' },
  { id: 'code_interpreter', label: 'Code Interpreter' },
  { id: 'file_reader', label: 'File Reader' },
  { id: 'image_analysis', label: 'Image Analysis' },
  { id: 'memory_retrieval', label: 'Memory Retrieval' },
  { id: 'data_visualization', label: 'Data Visualization' },
  { id: 'api_caller', label: 'API Caller' },
]

export function AgentForm({ agent, onSubmit, onCancel, className = '' }: AgentFormProps) {
  const [name, setName] = useState(agent?.name ?? '')
  const [description, setDescription] = useState(agent?.description ?? '')
  const [model, setModel] = useState(agent?.model ?? 'gpt-4o')
  const [provider, setProvider] = useState(agent?.provider ?? 'openai')
  const [tools, setTools] = useState<string[]>(agent?.tools ?? [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !model || !provider) return
    onSubmit({ name: name.trim(), description: description.trim(), model, provider, tools })
  }

  const toggleTool = (toolId: string) => {
    setTools((prev) =>
      prev.includes(toolId) ? prev.filter((t) => t !== toolId) : [...prev, toolId],
    )
  }

  return (
    <form
      className={`rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,34,0.72),rgba(10,11,27,0.68))] p-6 shadow-[0_12px_32px_rgba(0,0,0,0.22)] backdrop-blur-xl ${className}`.trim()}
      onSubmit={handleSubmit}
    >
      <h2 className="mb-5 text-base font-semibold text-white">
        {agent ? 'Editar Agente' : 'Novo Agente'}
      </h2>

      <label className="mb-4 block">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Nome</span>
        <input
          className="mt-1 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
          placeholder="Ex: Assistente de Pesquisa"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </label>

      <label className="mb-4 block">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Descrição</span>
        <textarea
          className="mt-1 min-h-[72px] w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
          placeholder="Descrição do agente e seu propósito"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>

      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Modelo</span>
          <select
            className="mt-1 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none transition focus:border-violet-500/40 focus:bg-violet-500/5"
            value={model}
            onChange={(e) => setModel(e.target.value)}
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
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            {PROVIDER_OPTIONS.map((opt) => (
              <option key={opt.id} className="bg-[#0a0b1b] text-white" value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mb-5">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Ferramentas</span>
        <div className="mt-2 flex flex-wrap gap-2">
          {AVAILABLE_TOOLS.map((tool) => {
            const selected = tools.includes(tool.id)
            return (
              <button
                key={tool.id}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                  selected
                    ? 'border-violet-500/40 bg-violet-500/15 text-violet-200'
                    : 'border-white/10 bg-white/5 text-slate-400 hover:border-white/20'
                }`}
                onClick={() => toggleTool(tool.id)}
                type="button"
              >
                {tool.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex items-center justify-end gap-3">
        <OmniButton type="button" variant="ghost" onClick={onCancel}>
          Cancelar
        </OmniButton>
        <OmniButton type="submit" variant="primary">
          {agent ? 'Salvar' : 'Criar Agente'}
        </OmniButton>
      </div>
    </form>
  )
}
