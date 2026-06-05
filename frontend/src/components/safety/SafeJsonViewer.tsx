import { sanitizeRuntimeDebugPayload } from '../../lib/runtimeDebugSanitizer'
import { RedactedField } from './RedactedField'

type SafeJsonViewerProps = {
  data: unknown
  className?: string
  maxDepth?: number
}

function JsonTree({ value, depth, maxDepth }: { value: unknown; depth: number; maxDepth: number }) {
  if (depth > maxDepth) {
    return <span className="text-slate-500">[max depth]</span>
  }

  if (value === null) {
    return <span className="text-slate-500">null</span>
  }

  if (value === undefined) {
    return <span className="text-slate-500">undefined</span>
  }

  if (typeof value === 'string') {
    return <span className="text-emerald-300/90">&quot;{value}&quot;</span>
  }

  if (typeof value === 'number') {
    return <span className="text-amber-300">{value}</span>
  }

  if (typeof value === 'boolean') {
    return <span className="text-sky-300">{String(value)}</span>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-slate-500">[]</span>
    }
    return (
      <div className="space-y-1">
        {value.map((item, index) => (
          <div key={index} className="flex gap-2">
            <span className="text-slate-500 select-none">{index}:</span>
            <JsonTree value={item} depth={depth + 1} maxDepth={maxDepth} />
          </div>
        ))}
      </div>
    )
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) {
      return <span className="text-slate-500">{'{}'}</span>
    }
    return (
      <div className="space-y-1">
        {entries.map(([key, val]) => (
          <div key={key} className="flex gap-2">
            <span className="text-blue-300/80 select-none">{key}:</span>
            <JsonTree value={val} depth={depth + 1} maxDepth={maxDepth} />
          </div>
        ))}
      </div>
    )
  }

  return <span className="text-slate-400">{String(value)}</span>
}

export function SafeJsonViewer({ data, className = '', maxDepth = 6 }: SafeJsonViewerProps) {
  const safe = sanitizeRuntimeDebugPayload(data)

  if (!safe || Object.keys(safe).length === 0) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div
      className={`max-h-96 overflow-auto rounded-2xl border border-white/10 bg-black/35 p-3 font-mono text-[11px] leading-5 ${className}`.trim()}
    >
      <JsonTree value={safe} depth={0} maxDepth={maxDepth} />
    </div>
  )
}
