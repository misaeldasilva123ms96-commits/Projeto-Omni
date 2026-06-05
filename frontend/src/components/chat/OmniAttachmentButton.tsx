type OmniAttachmentButtonProps = {
  onClick?: () => void
  disabled?: boolean
  className?: string
}

export function OmniAttachmentButton({ onClick, disabled = false, className = '' }: OmniAttachmentButtonProps) {
  return (
    <button
      aria-label="Anexar arquivo"
      className={`rounded-full border border-white/12 bg-white/[0.05] p-2 text-slate-200 transition hover:text-white active:translate-y-px disabled:opacity-40 disabled:cursor-not-allowed ${className}`.trim()}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m21.4 11.6-8.8 8.8a6 6 0 0 1-8.5-8.5l9.4-9.4a4 4 0 0 1 5.7 5.7l-9.4 9.4a2 2 0 0 1-2.8-2.8l8.8-8.8" /></svg>
    </button>
  )
}
