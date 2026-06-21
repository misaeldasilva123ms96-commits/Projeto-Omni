import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { OmniButton } from './OmniButton'
import { OmniCard } from './OmniCard'

export type OmniSuccessStateSize = 'compact' | 'default'

export type OmniSuccessStateProps = {
  title?: string
  description: string
  actionLabel?: string
  onAction?: () => void
  size?: OmniSuccessStateSize
  className?: string
}

export function OmniSuccessState({
  title,
  description,
  actionLabel,
  onAction,
  size = 'default',
  className = '',
}: OmniSuccessStateProps) {
  const safeTitle = title ? redactRuntimeDebugText(title) : null
  const safeDescription = redactRuntimeDebugText(description) || 'Operação concluída com sucesso.'
  const safeActionLabel = actionLabel ? redactRuntimeDebugText(actionLabel) : null
  const compact = size === 'compact'

  const content = (
    <>
      <div className={compact ? 'min-w-0 flex-1' : 'min-w-0'}>
        {safeTitle ? (
          <h2 className={compact ? 'sidebar-label' : 'text-sm font-semibold text-emerald-200'}>
            {safeTitle}
          </h2>
        ) : null}
        <p className={compact ? 'success-text' : 'mt-1 text-sm leading-6 text-emerald-300'}>
          {safeDescription}
        </p>
      </div>
      {safeActionLabel && onAction ? (
        <OmniButton
          className={compact ? 'shrink-0' : 'mt-4'}
          onClick={onAction}
          variant="primary"
        >
          {safeActionLabel}
        </OmniButton>
      ) : null}
    </>
  )

  if (compact) {
    return (
      <div
        className={`flex items-start justify-between gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.06] px-4 py-3 text-emerald-200 ${className}`.trim()}
        data-size={size}
        data-testid="omni-success-state"
        role="status"
      >
        {content}
      </div>
    )
  }

  return (
    <OmniCard
      className={`mx-auto w-full max-w-xl border border-emerald-500/20 bg-emerald-500/[0.06] px-5 py-5 text-left text-emerald-200 ${className}`.trim()}
      data-size={size}
      data-testid="omni-success-state"
      role="status"
      variant="panel"
    >
      {content}
    </OmniCard>
  )
}
