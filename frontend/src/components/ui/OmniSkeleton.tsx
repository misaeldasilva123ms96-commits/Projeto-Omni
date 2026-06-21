type OmniSkeletonProps = {
  className?: string
  lines?: number
  variant?: 'text' | 'card' | 'circle'
}

export function OmniSkeleton({ className = '', lines = 3, variant = 'text' }: OmniSkeletonProps) {
  const safeLines = Number.isFinite(lines) ? Math.max(1, Math.floor(lines)) : 1

  if (variant === 'circle') {
    return (
      <span
        className={`inline-block rounded-full bg-white/10 omni-skeleton ${className}`.trim()}
        aria-hidden="true"
      />
    )
  }

  if (variant === 'card') {
    return (
      <div
        className={`rounded-[24px] border border-white/8 bg-white/[0.03] p-5 ${className}`.trim()}
        aria-hidden="true"
      >
        <div className="mb-4 h-4 w-1/3 rounded-full bg-white/10 omni-skeleton" />
        <div className="space-y-2">
          {Array.from({ length: safeLines }).map((_, i) => (
            <div
              key={i}
              className={`h-3 rounded-full bg-white/10 omni-skeleton ${i === safeLines - 1 ? 'w-2/3' : 'w-full'}`}
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`.trim()} aria-hidden="true">
      {Array.from({ length: safeLines }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded-full bg-white/10 omni-skeleton ${i === safeLines - 1 ? 'w-2/3' : 'w-full'}`}
        />
      ))}
    </div>
  )
}
