type RuntimeLinkActionProps = {
  href: string | null
  label: string
  unavailableLabel: string
}

export function RuntimeLinkAction({
  href,
  label,
  unavailableLabel,
}: RuntimeLinkActionProps) {
  if (!href) {
    return (
      <p aria-disabled="true" className="mt-3 text-xs text-slate-500">
        {unavailableLabel}
      </p>
    )
  }

  return (
    <a
      className="mt-3 inline-flex text-xs font-medium text-neon-cyan transition hover:text-white"
      href={href}
    >
      {label}
    </a>
  )
}
