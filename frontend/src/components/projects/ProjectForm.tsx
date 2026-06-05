import { useState } from 'react'
import type { ChatMode, Project } from '../../types'
import { OmniButton } from '../ui/OmniButton'

type ProjectFormProps = {
  project?: Project | null
  onSubmit: (input: { name: string; description: string; mode: ChatMode }) => void
  onCancel: () => void
  className?: string
}

const MODE_OPTIONS: Array<{ id: ChatMode; label: string }> = [
  { id: 'chat', label: 'Chat' },
  { id: 'pesquisa', label: 'Pesquisa' },
  { id: 'codigo', label: 'Código' },
  { id: 'agente', label: 'Agente' },
]

export function ProjectForm({ project, onSubmit, onCancel, className = '' }: ProjectFormProps) {
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [mode, setMode] = useState<ChatMode>(project?.mode ?? 'chat')
  const isEditing = !!project

  const canSubmit = name.trim().length > 0

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!canSubmit) return
    onSubmit({ name: name.trim(), description: description.trim(), mode })
  }

  return (
    <form
      className={`rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,34,0.88),rgba(10,11,27,0.84))] p-6 shadow-[0_18px_48px_rgba(0,0,0,0.34)] backdrop-blur-xl ${className}`.trim()}
      onSubmit={handleSubmit}
    >
      <h3 className="mb-5 text-lg font-semibold text-white">
        {isEditing ? 'Editar Projeto' : 'Novo Projeto'}
      </h3>

      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-violet-200/70" htmlFor="project-name">
            Nome
          </label>
          <input
            id="project-name"
            className="w-full rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 transition focus:border-neon-cyan/40"
            onChange={(e) => setName(e.target.value)}
            placeholder="Nome do projeto"
            value={name}
            type="text"
            autoFocus
          />
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-violet-200/70" htmlFor="project-description">
            Descrição
          </label>
          <textarea
            id="project-description"
            className="min-h-[80px] w-full resize-y rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 transition focus:border-neon-cyan/40"
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descrição opcional"
            value={description}
            rows={3}
          />
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-violet-200/70">
            Modo
          </label>
          <div className="flex flex-wrap gap-2">
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                className={`rounded-xl border px-3 py-1.5 text-xs transition ${
                  mode === opt.id
                    ? 'border-neon-purple/40 bg-neon-purple/15 text-white'
                    : 'border-white/8 bg-white/[0.03] text-slate-300 hover:text-white'
                }`}
                onClick={() => setMode(opt.id)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-3">
        <OmniButton variant="ghost" onClick={onCancel} type="button">
          Cancelar
        </OmniButton>
        <OmniButton variant="primary" disabled={!canSubmit} type="submit">
          {isEditing ? 'Salvar' : 'Criar'}
        </OmniButton>
      </div>
    </form>
  )
}
