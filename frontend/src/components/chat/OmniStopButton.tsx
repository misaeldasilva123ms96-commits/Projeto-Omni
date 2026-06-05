type OmniStopButtonProps = {
  onClick: () => void
  className?: string
}

export function OmniStopButton({ onClick, className = '' }: OmniStopButtonProps) {
  return (
    <button
      className={`rounded-full border border-red-400/30 bg-red-500/20 px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.24em] text-red-200 transition hover:bg-red-500/30 active:translate-y-px ${className}`.trim()}
      onClick={onClick}
      type="button"
    >
      Stop
    </button>
  )
}
