type RedactedFieldProps = {
  label: string
  value?: unknown
  className?: string
}

export function RedactedField({ label, value, className = '' }: RedactedFieldProps) {
  const isRedacted = value === undefined || value === null || value === '[REDACTED]'
  const safeValue = typeof value === 'string'
    ? redactRuntimeDebugText(value)
    : sanitizeRuntimeDebugPayload({ value }).value
  const displayValue = typeof safeValue === 'string'
    ? safeValue
    : JSON.stringify(safeValue)

  return (
    <div className={`flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0 ${className}`.trim()}>
      <span className="text-sm text-slate-300/70">{label}</span>
      {isRedacted ? (
        <span className="rounded-md bg-slate-700/40 px-2 py-0.5 text-xs font-mono text-amber-300/80">
          [REDACTED]
        </span>
      ) : (
        <span className="text-right text-sm font-medium text-white">
          {displayValue}
        </span>
      )}
    </div>
  )
}
import {
  redactRuntimeDebugText,
  sanitizeRuntimeDebugPayload,
} from '../../lib/runtimeDebugSanitizer'
