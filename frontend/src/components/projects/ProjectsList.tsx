import { useState } from 'react'
import type { ChatMode, Project } from '../../types'
import { OmniButton } from '../ui/OmniButton'
import { OmniEmptyState } from '../ui/OmniEmptyState'
import { OmniLoadingState } from '../ui/OmniLoadingState'
import { ProjectCard } from './ProjectCard'
import { ProjectForm } from './ProjectForm'

type ProjectsListProps = {
  projects: Project[]
  loading: boolean
  onCreate: (input: { name: string; description: string; mode: ChatMode }) => void
  onUpdate: (id: string, input: { name: string; description: string; mode: ChatMode }) => void
  onDelete: (id: string) => void
  onArchive: (id: string) => void
  className?: string
}

export function ProjectsList({ projects, loading, onCreate, onUpdate, onDelete, onArchive, className = '' }: ProjectsListProps) {
  const [showForm, setShowForm] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)

  const handleSubmit = (input: { name: string; description: string; mode: ChatMode }) => {
    if (editingProject) {
      onUpdate(editingProject.id, input)
      setEditingProject(null)
    } else {
      onCreate(input)
      setShowForm(false)
    }
  }

  const handleEdit = (project: Project) => {
    setEditingProject(project)
  }

  const handleArchive = (project: Project) => {
    onArchive(project.id)
  }

  const handleDelete = (project: Project) => {
    onDelete(project.id)
  }

  if (showForm || editingProject) {
    return (
      <div className={`mx-auto max-w-lg ${className}`.trim()}>
        <ProjectForm
          project={editingProject}
          onSubmit={handleSubmit}
          onCancel={() => {
            setShowForm(false)
            setEditingProject(null)
          }}
        />
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">Projetos</h2>
          <p className="mt-0.5 text-sm text-slate-400">{projects.length} projeto{projects.length !== 1 ? 's' : ''}</p>
        </div>
        <OmniButton variant="primary" onClick={() => setShowForm(true)}>
          Novo Projeto
        </OmniButton>
      </div>

      {loading ? (
        <OmniLoadingState label="Carregando projetos..." skeletonRows={3} />
      ) : projects.length === 0 ? (
        <OmniEmptyState
          actionLabel="Criar Projeto"
          description="Crie seu primeiro projeto para organizar suas sessões."
          icon={(
            <svg className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          )}
          onAction={() => setShowForm(true)}
          title="Nenhum projeto ainda."
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onArchive={handleArchive}
            />
          ))}
        </div>
      )}
    </div>
  )
}
