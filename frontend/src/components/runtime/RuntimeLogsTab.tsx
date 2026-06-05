import { useMemo } from 'react'
import type { RuntimeMetadata } from '../../types'
import { SafeJsonViewer } from '../safety/SafeJsonViewer'

type RuntimeLogsTabProps = {
  metadata: RuntimeMetadata | null
  sessionId: string
}

export function RuntimeLogsTab({ metadata, sessionId }: RuntimeLogsTabProps) {
  const safePayload = useMemo(() => {
    if (!metadata) return null
    return {
      api_response: metadata,
      request_id: sessionId,
    }
  }, [metadata, sessionId])

  if (!safePayload) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
      <h4 className="mb-3 text-sm font-medium text-white">Safe Debug Log</h4>
      <SafeJsonViewer data={safePayload} />
    </section>
  )
}
