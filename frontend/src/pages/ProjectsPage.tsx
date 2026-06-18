import { useCallback, useEffect, useState } from 'react'
import type { RenderOmniShell, View } from '../app/App'
import { ProjectsList } from '../components/projects/ProjectsList'
import { OmniSidebar } from '../components/shell/OmniSidebar'
import { PageHero } from '../components/ui/PageHero'
import { createProject, deleteProject, fetchProjects, updateProject } from '../lib/omniData'
import { useRuntimeConsoleStore } from '../state/runtimeConsoleStore'
import type { ChatMode, ConversationSummary, Project } from '../types'

type ProjectsPageProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
  onChangeView: (view: View) => void
  renderShell: RenderOmniShell
  view: View
}

export function ProjectsPage({ mode, onChangeMode, onChangeView, renderShell, view }: ProjectsPageProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)

  useEffect(() => {
    setLoading(true)
    fetchProjects()
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setLoading(false))
  }, [])

  const handleRefresh = useCallback(() => {
    fetchProjects().then(setProjects).catch(() => {})
  }, [])

  const handleCreate = useCallback(async (input: { name: string; description: string; mode: ChatMode }) => {
    const result = await createProject(input)
    if (result) {
      setProjects((prev) => [result, ...prev])
      setUiNotice(`Projeto "${input.name}" criado.`)
    } else {
      setUiNotice('Não foi possível criar o projeto.')
    }
  }, [setUiNotice])

  const handleUpdate = useCallback(async (id: string, input: { name: string; description: string; mode: ChatMode }) => {
    const result = await updateProject(id, input)
    if (result) {
      setProjects((prev) => prev.map((p) => (p.id === id ? result : p)))
      setUiNotice(`Projeto "${input.name}" atualizado.`)
    } else {
      setUiNotice('Não foi possível atualizar o projeto.')
    }
  }, [setUiNotice])

  const handleDelete = useCallback(async (id: string) => {
    const ok = await deleteProject(id)
    if (ok) {
      setProjects((prev) => prev.filter((p) => p.id !== id))
      setUiNotice('Projeto excluído.')
    } else {
      setUiNotice('Não foi possível excluir o projeto.')
    }
  }, [setUiNotice])

  const handleArchive = useCallback(async (id: string) => {
    const project = projects.find((p) => p.id === id)
    if (!project) return
    const nextStatus = project.status === 'active' ? 'archived' : 'active'
    const result = await updateProject(id, { status: nextStatus })
    if (result) {
      setProjects((prev) => prev.map((p) => (p.id === id ? result : p)))
      setUiNotice(`Projeto ${nextStatus === 'active' ? 'ativado' : 'arquivado'}.`)
    } else {
      setUiNotice('Não foi possível atualizar o status do projeto.')
    }
  }, [projects, setUiNotice])

  const conversations: ConversationSummary[] = []
  const sidebar = (
    <OmniSidebar
      conversations={conversations}
      mode={mode}
      onChangeMode={onChangeMode}
      onSelectView={onChangeView}
      view={view}
    />
  )

  return renderShell(
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-y-auto px-2 py-5">
        <PageHero
          eyebrow="Gerenciamento"
          title="Centro de Projetos"
          subtitle="Organize suas sessões em projetos"
          className="mb-6"
        />
        <ProjectsList
          projects={projects}
          loading={loading}
          onCreate={handleCreate}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          onArchive={handleArchive}
        />
      </div>,
    { sidebar },
  )
}
