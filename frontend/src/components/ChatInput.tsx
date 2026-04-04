import type { FormEvent, KeyboardEvent } from 'react'

type ChatInputProps = {
  error: string | null
  loading: boolean
  value: string
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

function VoiceIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 15a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" fill="currentColor" />
      <path d="M18 11a1 1 0 1 0-2 0 4 4 0 1 1-8 0 1 1 0 1 0-2 0 6 6 0 0 0 5 5.91V20H9a1 1 0 0 0 0 2h6a1 1 0 1 0 0-2h-2v-3.09A6 6 0 0 0 18 11Z" fill="currentColor" />
    </svg>
  )
}

function AttachmentIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M8.5 12.5 14 7a3 3 0 1 1 4.24 4.24l-7.78 7.78a5 5 0 1 1-7.07-7.07L12 3.34" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M3 11.5 21 3l-4.5 18-5.2-6.2L3 11.5Z" fill="currentColor" />
    </svg>
  )
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
        <button aria-label="Entrada por voz" className="icon-button input-icon-button" type="button">
          <VoiceIcon />
        </button>

        <textarea
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Digite uma mensagem..."
          rows={1}
          value={value}
        />

        <button aria-label="Anexar arquivo" className="icon-button input-icon-button" type="button">
          <AttachmentIcon />
        </button>

        <button aria-label="Enviar mensagem" className="send-button" disabled={loading} type="submit">
          <SendIcon />
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
