import { useCallback, useId, useState } from 'react'

type OmniComposerProps = {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  canSend: boolean
  loading?: boolean
  placeholder?: string
  className?: string
  /**
   * If true, shows a stop button instead of send while loading.
   */
  onStop?: () => void
  /**
   * Custom elements to render before the textarea (e.g. attachment button).
   */
  before?: React.ReactNode
  /**
   * Custom elements to render after the textarea (e.g. voice button).
   */
  after?: React.ReactNode
  error?: string | null
  children?: React.ReactNode
}

export function OmniComposer({
  value,
  onChange,
  onSubmit,
  canSend,
  loading = false,
  placeholder = 'Digite uma mensagem...',
  className = '',
  onStop,
  before,
  after,
  error,
  children,
}: OmniComposerProps) {
  const [focused, setFocused] = useState(false)
  const textareaId = useId()
  const errorId = `${textareaId}-error`

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        if (canSend) {
          onSubmit()
        }
      }
    },
    [canSend, onSubmit],
  )

  return (
    <div className={`rounded-[24px] border border-[rgba(180,109,255,0.16)] bg-[linear-gradient(180deg,rgba(14,15,34,0.8),rgba(10,11,27,0.74))] p-2 shadow-[0_20px_48px_rgba(0,0,0,0.34)] backdrop-blur-xl ${className}`.trim()}>
      {children ? <div className="mb-3">{children}</div> : null}

      <div
        className={`flex items-center gap-2 rounded-[22px] border bg-[rgba(7,8,22,0.78)] px-2.5 py-1.5 transition-all duration-300 ${focused ? 'border-neon-cyan/40 shadow-[0_0_0_1px_rgba(81,246,255,0.18),0_0_22px_rgba(81,246,255,0.16)]' : 'border-white/10'}`}
      >
        {before}

        <textarea
          aria-describedby={error ? errorId : undefined}
          aria-invalid={Boolean(error)}
          aria-label="Mensagem para o Omni"
          className="flex-1 resize-none rounded-[20px] border border-neon-purple/20 bg-[rgba(11,15,34,0.92)] px-4 py-2 text-sm text-white outline-none placeholder:text-violet-200/40 transition-all duration-300"
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setFocused(false)}
          onFocus={() => setFocused(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          value={value}
          rows={1}
        />

        {after}

        {loading && onStop ? (
          <button
            aria-label="Interromper resposta"
            className="rounded-full border border-red-400/30 bg-red-500/20 px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] text-red-200 transition hover:bg-red-500/30 active:translate-y-px"
            onClick={onStop}
            type="button"
          >
            Stop
          </button>
        ) : (
          <button
            aria-label={loading ? 'Enviando mensagem' : 'Enviar mensagem'}
            className={`rounded-full px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] transition ${
              canSend
                ? 'bg-[linear-gradient(135deg,rgba(181,109,255,0.92),rgba(78,164,255,0.92))] text-white hover:scale-[1.01] active:translate-y-px shadow-[0_0_20px_rgba(123,97,255,0.18)]'
                : 'cursor-not-allowed bg-white/[0.08] text-slate-400'
            }`}
            disabled={!canSend || loading}
            onClick={onSubmit}
            type="button"
          >
            {loading ? '...' : 'Enviar'}
          </button>
        )}
      </div>

      {error ? (
        <div className="mt-1.5 flex justify-end text-sm">
          <div id={errorId} role="alert" className="max-w-[420px] text-right text-[11px] leading-4 text-rose-300">
            {error}
          </div>
        </div>
      ) : null}
    </div>
  )
}
