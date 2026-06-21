import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { OmniButton } from './OmniButton'
import { OmniCard } from './OmniCard'

export type OmniErrorStateTone = 'neutral' | 'warning' | 'danger'
export type OmniErrorStateSize = 'compact' | 'default'

export type OmniErrorStateProps = {
  title?: string
  description: string
  technicalDetail?: string
  actionLabel?: string
  onAction?: () => void
  tone?: OmniErrorStateTone
  size?: OmniErrorStateSize
  className?: string
}

const toneClasses: Record<OmniErrorStateTone, string> = {
  neutral: 'border-white/10 bg-white/[0.03] text-slate-300',
  warning: 'border-amber-300/20 bg-amber-500/[0.06] text-amber-200',
  danger: 'border-red-300/20 bg-red-500/[0.06] text-red-200',
}

const RAW_DIAGNOSTIC_PATTERN = /\b(?:stack|stacktrace|traceback|stdout|stderr)\b/i

function sanitizeTechnicalDetail(value: string | undefined): string | null {
  if (!value) return null
  if (RAW_DIAGNOSTIC_PATTERN.test(value)) return '[REDACTED]'
  return redactRuntimeDebugText(value) || null
}

export function OmniErrorState({
  title,
  description,
  technicalDetail,
  actionLabel,
  onAction,
  tone = 'danger',
  size = 'default',
  className = '',
}: OmniErrorStateProps) {
  const safeTitle = title ? redactRuntimeDebugText(title) : null
  const safeDescription = redactRuntimeDebugText(description) || 'Erro não disponível.'
  const safeTechnicalDetail = sanitizeTechnicalDetail(technicalDetail)
  const safeActionLabel = actionLabel ? redactRuntimeDebugText(actionLabel) : null
  const compact = size === 'compact'

  const content = (
    <>
      <div className={compact ? 'min-w-0 flex-1' : 'min-w-0'}>
        {safeTitle ? (
          <h2 className={compact ? 'sidebar-label' : 'text-sm font-semibold text-current'}>
            {safeTitle}
          </h2>
        ) : null}
        <p className={compact ? 'error-text' : 'mt-1 text-sm leading-6 text-slate-300'}>
          {safeDescription}
        </p>
        {safeTechnicalDetail ? (
          <p className="mt-2 break-words font-mono text-xs leading-5 text-slate-400">
            {safeTechnicalDetail}
          </p>
        ) : null}
      </div>
      {safeActionLabel && onAction ? (
        <OmniButton
          className={compact ? 'shrink-0' : 'mt-4'}
          onClick={onAction}
          variant={tone === 'danger' ? 'danger' : 'secondary'}
        >
          {safeActionLabel}
        </OmniButton>
      ) : null}
    </>
  )

  if (compact) {
    return (
      <div
        className={`omni-error-notice flex items-start justify-between gap-3 rounded-2xl border px-4 py-3 ${
          toneClasses[tone]
        } ${className}`.trim()}
        data-size={size}
        data-tone={tone}
        role="alert"
      >
        {content}
      </div>
    )
  }

  return (
    <OmniCard
      className={`mx-auto w-full max-w-xl border px-5 py-5 text-left ${toneClasses[tone]} ${className}`.trim()}
      data-size={size}
      data-tone={tone}
      role="alert"
      variant="panel"
    >
      {content}
    </OmniCard>
  )
}
