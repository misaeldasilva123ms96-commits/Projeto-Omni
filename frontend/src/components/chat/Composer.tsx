import { KeyboardEvent } from 'react'
import { ErrorNotice } from '../ui/ErrorNotice'
import { PanelCard } from '../ui/PanelCard'

type ComposerProps = {
  canSend: boolean
  error: string | null
  helperText: string
  loading: boolean
  onChange: (value: string) => void
  onSubmit: () => void
  value: string
}

export function Composer({
  canSend,
  error,
  helperText,
  loading,
  onChange,
  onSubmit,
  value,
}: ComposerProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter' || event.shiftKey) {
      return
    }

    event.preventDefault()
    if (canSend) {
      onSubmit()
    }
  }

  return (
    <PanelCard className="composer-shell omni-composer">
      <div className="composer">
        <textarea
          aria-label="Enviar mensagem para o Omni"
          autoFocus
          className="composer-input"
          disabled={loading}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Peca ao Omni para investigar um bug, analisar uma arquitetura ou planejar um trabalho tecnico."
          rows={4}
          spellCheck={false}
          value={value}
        />
        <div className="composer-footer">
          <div className="composer-copy">
            {error ? <ErrorNotice message={error} /> : <p className="helper-text">{helperText}</p>}
            <span className="composer-hint">Enter envia. Shift + Enter cria uma nova linha.</span>
          </div>
          <button className="send-button" disabled={!canSend} onClick={onSubmit} type="button">
            {loading ? 'Enviando...' : 'Enviar'}
          </button>
        </div>
      </div>
    </PanelCard>
  )
}
