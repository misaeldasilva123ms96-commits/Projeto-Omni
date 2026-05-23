import { EmptyState as EmptyStateSurface } from '../ui/EmptyState'

const QUICK_PROMPTS = [
  'Analise este erro de arquitetura',
  'Planeje uma nova feature',
  'Pesquise um tema tecnico',
  'Melhore meu codigo',
]

type EmptyStateProps = {
  onSelectPrompt: (prompt: string) => void
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  return (
    <EmptyStateSurface
      description="O chat prioriza fluxo confiavel, estado de sessao saneado e metadados operacionais discretos."
      eyebrow="Omni"
      title="Converse com o runtime cognitivo do projeto."
    >
      <div className="quick-prompts">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            className="quick-prompt"
            onClick={() => onSelectPrompt(prompt)}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>
    </EmptyStateSurface>
  )
}
