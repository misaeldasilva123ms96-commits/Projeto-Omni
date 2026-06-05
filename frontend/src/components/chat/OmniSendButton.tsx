type OmniSendButtonProps = {
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  className?: string
  label?: string
}

export function OmniSendButton({ onClick, disabled = false, loading = false, className = '', label = 'Enviar' }: OmniSendButtonProps) {
  return (
    <button
      className={`rounded-full px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] transition ${
        disabled || loading
          ? 'cursor-not-allowed bg-white/[0.08] text-slate-400'
          : 'bg-[linear-gradient(135deg,rgba(181,109,255,0.92),rgba(78,164,255,0.92))] text-white hover:scale-[1.01] active:translate-y-px shadow-[0_0_20px_rgba(123,97,255,0.18)]'
      } ${className}`.trim()}
      disabled={disabled || loading}
      onClick={onClick}
      type="button"
    >
      {loading ? '...' : label}
    </button>
  )
}
