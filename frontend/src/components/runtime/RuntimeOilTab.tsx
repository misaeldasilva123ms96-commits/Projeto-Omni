import type { RuntimeOilSkeleton } from '../../lib/runtimeTypes'
import { SafeJsonViewer } from '../safety/SafeJsonViewer'

type RuntimeOilTabProps = {
  data: RuntimeOilSkeleton | null
}

export function RuntimeOilTab({ data }: RuntimeOilTabProps) {
  if (!data) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
      <h4 className="mb-3 text-sm font-medium text-white">OIL Envelope</h4>
      <SafeJsonViewer data={data} />
    </section>
  )
}
