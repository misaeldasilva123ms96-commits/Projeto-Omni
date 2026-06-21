import type { RuntimeGovernanceStatus } from '../../lib/governanceTypes'
import { GovernanceBadge } from './GovernanceBadge'
import { RuntimeLinkAction } from './RuntimeLinkAction'
import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

type RuntimeGovernanceTabProps = {
  data: RuntimeGovernanceStatus | null
  governanceHref: string | null
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">
        {redactRuntimeDebugText(value) || '—'}
      </span>
    </div>
  )
}

export function RuntimeGovernanceTab({ data, governanceHref }: RuntimeGovernanceTabProps) {
  if (!data) {
    return (
      <div>
        <p className="text-sm text-slate-400">não disponível</p>
        <RuntimeLinkAction
          href={governanceHref}
          label="Ver decisão"
          unavailableLabel="sem referência disponível"
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
        <h4 className="mb-3 text-sm font-medium text-white">Decision</h4>
        <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5">
          <span className="text-sm text-slate-300/70">Verdict</span>
          <GovernanceBadge governance={{
            decision: data.decision,
            policy: data.policy ?? undefined,
            reason: data.reason ?? undefined,
          }} />
        </div>
        <DetailRow label="Category" value={data.tool_category ?? ''} />
        <DetailRow label="Policy" value={data.policy ?? ''} />
        <DetailRow label="Risk Level" value={data.risk_level} />
        <DetailRow label="Blocked" value={data.blocked === null ? 'não disponível' : data.blocked ? 'Yes' : 'No'} />
        <DetailRow
          label="Requires Approval"
          value={data.requires_approval === null ? 'não disponível' : data.requires_approval ? 'Yes' : 'No'}
        />
        {data.reason ? (
          <div className="py-2.5">
            <span className="text-sm text-slate-300/70">Reason</span>
            <p className="mt-1 text-sm text-white">
              {redactRuntimeDebugText(data.reason)}
            </p>
          </div>
        ) : null}
      </section>
      <RuntimeLinkAction
        href={governanceHref}
        label="Ver decisão"
        unavailableLabel="sem referência disponível"
      />
    </div>
  )
}
