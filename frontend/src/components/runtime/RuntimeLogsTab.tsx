import { useMemo } from 'react'
import type { RuntimeMetadata } from '../../types'
import { sanitizeRuntimeDebugPayload } from '../../lib/runtimeDebugSanitizer'

type RuntimeLogsTabProps = {
  metadata: RuntimeMetadata | null
  sessionId: string
}

export function RuntimeLogsTab({ metadata, sessionId }: RuntimeLogsTabProps) {
  const safePayload = useMemo(() => {
    if (!metadata) return null
    return sanitizeRuntimeDebugPayload({
      api_response: metadata,
      request_id: sessionId,
    })
  }, [metadata, sessionId])

  if (!safePayload) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
      <h4 className="mb-3 text-sm font-medium text-white">Safe Debug Log</h4>
      <pre className="max-h-96 overflow-auto rounded-2xl border border-white/10 bg-black/35 p-3 text-[11px] leading-5 text-slate-200/80">
        {JSON.stringify(safePayload, null, 2)}
      </pre>
    </section>
  )
}
