import type { RuntimeMetadata } from '../../types'

type RuntimeOilTabProps = {
  metadata: RuntimeMetadata | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function OilValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-500">—</span>
  }
  if (typeof value === 'string') {
    return <span className="text-slate-200">{value}</span>
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return <span className="text-slate-200">{String(value)}</span>
  }
  if (Array.isArray(value)) {
    return (
      <ul className="space-y-1">
        {value.map((item, i) => (
          <li key={i} className="text-sm text-slate-200">
            {isRecord(item) ? JSON.stringify(item) : String(item)}
          </li>
        ))}
      </ul>
    )
  }
  if (isRecord(value)) {
    return (
      <div className="space-y-1">
        {Object.entries(value).map(([k, v]) => (
          <div key={k} className="flex items-start gap-2 text-sm">
            <span className="text-slate-400">{k}:</span>
            <OilValue value={v} />
          </div>
        ))}
      </div>
    )
  }
  return <span className="text-slate-200">{String(value)}</span>
}

export function RuntimeOilTab({ metadata }: RuntimeOilTabProps) {
  const oil = metadata?.cognitiveRuntimeInspection?.oil
  const oilEnvelope = metadata?.cognitiveRuntimeInspection?.oil_envelope

  const data = oil ?? oilEnvelope ?? null

  if (!data && !metadata?.cognitiveRuntimeInspection) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  if (!data) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
      <h4 className="mb-3 text-sm font-medium text-white">OIL Envelope</h4>
      <div className="max-h-96 overflow-y-auto rounded-2xl border border-white/10 bg-black/35 p-3">
        <pre className="text-[11px] leading-5 text-slate-200/80 whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    </section>
  )
}
