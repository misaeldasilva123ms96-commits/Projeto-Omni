import type { FormEvent, KeyboardEvent } from 'react'

type ChatInputProps = {
  error: string | null
  loading: boolean
  value: string
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export default function ChatInput({
  error,
  loading,
  value,
  onChange,
  onSubmit,
}: ChatInputProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form className="chat-input-shell" onSubmit={onSubmit}>
      <div className="chat-input-panel">
        <button aria-label="Entrada por voz" className="icon-button" type="button">
          Mic
        </button>

        <textarea
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Digite uma mensagem..."
          rows={1}
          value={value}
        />

        <button aria-label="Anexar arquivo" className="icon-button" type="button">
          +
        </button>

        <button className="send-button" disabled={loading} type="submit">
          Send
        </button>
      </div>

      <div className="chat-input-footer">
        <span>
          {error ? (
            <span className="error-text">{error}</span>
          ) : (
            'Enter envia, Shift + Enter quebra linha'
          )}
        </span>
      </div>
    </form>
  )
}
