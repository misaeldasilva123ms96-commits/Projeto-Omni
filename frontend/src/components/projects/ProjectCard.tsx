import type { Project } from '../../types'
import { OmniBadge } from '../ui/OmniBadge'
import { OmniButton } from '../ui/OmniButton'

type ProjectCardProps = {
  project: Project
  onEdit?: (project: Project) => void
  onDelete?: (project: Project) => void
  onArchive?: (project: Project) => void
  className?: string
}

const modeLabels: Record<string, string> = {
  chat: 'Chat',
  pesquisa: 'Pesquisa',
  codigo: 'Código',
  agente: 'Agente',
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / 86400000)
    if (diffDays === 0) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    if (diffDays < 7) return `${diffDays} dias atrás`
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  } catch {
    return ''
  }
}

export function ProjectCard({ project, onEdit, onDelete, onArchive, className = '' }: ProjectCardProps) {
  return (
    <div className={`group rounded-3xl border border-white/10 bg-[linear-gradient(180deg,rgba(15,15,34,0.72),rgba(10,11,27,0.68))] p-5 shadow-[0_12px_32px_rgba(0,0,0,0.22)] backdrop-blur-xl transition hover:border-white/18 hover:shadow-[0_16px_40px_rgba(0,0,0,0.3)] ${className}`.trim()}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-white">{project.name}</h3>
            <OmniBadge tone={project.status === 'active' ? 'success' : 'muted'}>
              {project.status === 'active' ? 'Ativo' : 'Arquivado'}
            </OmniBadge>
          </div>

          {project.description ? (
            <p className="mt-1.5 line-clamp-2 text-sm text-slate-300/80">{project.description}</p>
          ) : null}

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <OmniBadge tone="info">{modeLabels[project.mode] ?? project.mode}</OmniBadge>
            <span>{project.sessionCount} sessões</span>
            <span>·</span>
            <span>{formatDate(project.updatedAt)}</span>
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-1.5 opacity-0 transition group-hover:opacity-100">
          {onEdit ? (
            <OmniButton variant="ghost" onClick={() => onEdit(project)}>
              Editar
            </OmniButton>
          ) : null}
          {onArchive ? (
            <OmniButton variant="ghost" onClick={() => onArchive(project)}>
              {project.status === 'active' ? 'Arquivar' : 'Ativar'}
            </OmniButton>
          ) : null}
          {onDelete ? (
            <OmniButton variant="danger" onClick={() => onDelete(project)}>
              Excluir
            </OmniButton>
          ) : null}
        </div>
      </div>
    </div>
  )
}
