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
    <div className="empty-state">
      <p className="eyebrow">Omni</p>
      <h2>Converse com o runtime cognitivo do projeto.</h2>
      <p>
        O chat agora prioriza fluxo confiavel, estado de sessao saneado e
        metadados operacionais discretos.
      </p>
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
    </div>
  )
}
