import type { RuntimeMetadata } from '../../types'
import { extractGovernanceSummary } from '../../lib/runtimeDebugSanitizer'
import { GovernanceBadge } from './GovernanceBadge'

type RuntimeGovernanceTabProps = {
  metadata: RuntimeMetadata | null
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value || '—'}</span>
    </div>
  )
}

export function RuntimeGovernanceTab({ metadata }: RuntimeGovernanceTabProps) {
  const governance = extractGovernanceSummary(metadata)

  if (!governance) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-4">
      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Decision</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Verdict</span>
          <GovernanceBadge governance={governance} />
        </div>
        <DetailRow label="Category" value={governance.category ?? ''} />
        <DetailRow label="Policy" value={governance.policy ?? ''} />
        <DetailRow label="Risk Level" value={governance.riskLevel ?? '—'} />
        {governance.reason ? (
          <div className="py-2.5">
            <span className="text-sm text-slate-300/70">Reason</span>
            <p className="mt-1 text-sm text-white">{governance.reason}</p>
          </div>
        ) : null}
      </section>
    </div>
  )
}
