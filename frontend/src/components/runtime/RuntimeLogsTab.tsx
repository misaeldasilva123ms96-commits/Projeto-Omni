import { SafeJsonViewer } from '../safety/SafeJsonViewer'
import { RuntimeLinkAction } from './RuntimeLinkAction'

type RuntimeLogsTabProps = {
  data: Record<string, unknown> | null
  logsHref: string | null
}

export function RuntimeLogsTab({ data, logsHref }: RuntimeLogsTabProps) {
  if (!data) {
    return (
      <div>
        <p className="text-sm text-slate-400">não disponível</p>
        <RuntimeLinkAction
          href={logsHref}
          label="Ver logs seguros"
          unavailableLabel="logs seguros indisponíveis"
        />
      </div>
    )
  }

  return (
    <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
      <h4 className="mb-3 text-sm font-medium text-white">Safe Debug Log</h4>
      <SafeJsonViewer data={data} />
      <RuntimeLinkAction
        href={logsHref}
        label="Ver logs seguros"
        unavailableLabel="logs seguros indisponíveis"
      />
    </section>
  )
}
