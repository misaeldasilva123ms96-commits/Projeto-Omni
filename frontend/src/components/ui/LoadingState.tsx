export type LoadingStateProps = {
  label?: string
  className?: string
}

export function LoadingState({ label = 'Carregando…', className = '' }: LoadingStateProps) {
  return (
    <div className={`omni-loading-state ${className}`.trim()} role="status" aria-live="polite">
      <span className="omni-loading-dot" aria-hidden />
      <p className="loading-copy">{label}</p>
    </div>
  )
}
