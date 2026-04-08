import type { FormEvent } from 'react'

type ComposerProps = {
  disabled: boolean
  error: string | null
  loading: boolean
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  value: string
}

export function Composer({
  disabled,
  error,
  loading,
  onChange,
  onSubmit,
  value,
}: ComposerProps) {
  return (
    <form className="composer" onSubmit={onSubmit}>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask Omni to inspect runtime state, summarize a subsystem or debug a flow."
        rows={4}
        disabled={disabled}
      />
      <div className="composer-footer">
        {error ? <p className="error-text">{error}</p> : <span className="helper-text">Rust bridge to Python brain to Node reasoning.</span>}
        <button className="send-button" disabled={disabled || loading} type="submit">
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </form>
  )
}
