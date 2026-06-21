import type { ReactNode } from 'react'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'
import { OmniButton } from './OmniButton'

export type OmniEmptyStateTone = 'neutral' | 'warning' | 'danger' | 'success'

export type OmniEmptyStateProps = {
  title: string
  description?: string
  eyebrow?: string
  icon?: ReactNode
  children?: ReactNode
  actionLabel?: string
  onAction?: () => void
  tone?: OmniEmptyStateTone
  framed?: boolean
  className?: string
}

const toneClasses: Record<OmniEmptyStateTone, string> = {
  neutral: 'text-slate-400',
  warning: 'text-amber-300',
  danger: 'text-red-300',
  success: 'text-emerald-300',
}

export function OmniEmptyState({
  title,
  description,
  eyebrow,
  icon,
  children,
  actionLabel,
  onAction,
  tone = 'neutral',
  framed = false,
  className = '',
}: OmniEmptyStateProps) {
  const safeTitle = redactRuntimeDebugText(title)
  const safeDescription = description ? redactRuntimeDebugText(description) : null
  const safeEyebrow = eyebrow ? redactRuntimeDebugText(eyebrow) : null
  const safeActionLabel = actionLabel ? redactRuntimeDebugText(actionLabel) : null

  return (
    <section
      className={`omni-empty-state flex flex-col items-center justify-center py-10 text-center ${
        framed ? 'empty-state' : ''
      } ${className}`.trim()}
      data-tone={tone}
      role="status"
    >
      {safeEyebrow ? <p className="eyebrow">{safeEyebrow}</p> : null}
      {icon ? (
        <div className={`mb-4 flex h-12 w-12 items-center justify-center ${toneClasses[tone]}`} aria-hidden="true">
          {icon}
        </div>
      ) : null}
      <h2 className={framed ? '' : 'text-sm font-medium text-slate-300'}>
        {safeTitle || 'Estado indisponível'}
      </h2>
      {safeDescription ? (
        <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">{safeDescription}</p>
      ) : null}
      {safeActionLabel && onAction ? (
        <OmniButton className="mt-4" onClick={onAction} variant="primary">
          {safeActionLabel}
        </OmniButton>
      ) : null}
      {children}
    </section>
  )
}
