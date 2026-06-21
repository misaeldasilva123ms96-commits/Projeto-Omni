import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { OmniSkeleton } from './OmniSkeleton'

export type OmniLoadingStateSize = 'compact' | 'default'
export type OmniLoadingStateTone = 'neutral' | 'accent'

export type OmniLoadingStateProps = {
  label?: string
  description?: string
  size?: OmniLoadingStateSize
  skeletonRows?: number
  tone?: OmniLoadingStateTone
  className?: string
}

const toneClasses: Record<OmniLoadingStateTone, string> = {
  neutral: 'text-slate-400',
  accent: 'text-cyan-200',
}

function normalizeSkeletonRows(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value)) return 0
  return Math.min(8, Math.max(0, Math.floor(value)))
}

export function OmniLoadingState({
  label = 'Carregando…',
  description,
  size = 'default',
  skeletonRows,
  tone = 'neutral',
  className = '',
}: OmniLoadingStateProps) {
  const safeLabel = redactRuntimeDebugText(label) || 'Carregando…'
  const safeDescription = description ? redactRuntimeDebugText(description) : null
  const safeSkeletonRows = normalizeSkeletonRows(skeletonRows)
  const compact = size === 'compact'

  return (
    <section
      aria-busy="true"
      aria-live="polite"
      className={`omni-loading-state ${compact ? '' : 'flex w-full flex-col justify-center py-10 text-center'} ${
        toneClasses[tone]
      } ${className}`.trim()}
      data-size={size}
      data-tone={tone}
      role="status"
    >
      <div className={`flex items-center ${compact ? 'gap-2.5' : 'justify-center gap-2.5'}`}>
        <span className="omni-loading-dot shrink-0" aria-hidden="true" />
        <p className={compact ? 'loading-copy' : 'text-sm'}>{safeLabel}</p>
      </div>
      {safeDescription ? (
        <p className={`${compact ? 'ml-[18px]' : 'mx-auto'} mt-1 max-w-xl text-xs leading-5 text-slate-500`}>
          {safeDescription}
        </p>
      ) : null}
      {safeSkeletonRows > 0 ? (
        <div
          className={`mt-5 grid w-full gap-3 text-left ${
            safeSkeletonRows > 1 ? 'sm:grid-cols-2 lg:grid-cols-3' : ''
          }`}
          aria-hidden="true"
          data-testid="omni-loading-skeletons"
        >
          {Array.from({ length: safeSkeletonRows }).map((_, index) => (
            <OmniSkeleton key={index} lines={3} variant="card" />
          ))}
        </div>
      ) : null}
    </section>
  )
}
