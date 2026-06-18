import type { RuntimeMemoryStatus } from '../../lib/runtimeTypes'

type RuntimeMemoryTabProps = {
  data: RuntimeMemoryStatus | null
}

export function RuntimeMemoryTab({ data }: RuntimeMemoryTabProps) {
  if (!data) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-4">
      {data.status ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Memory Status</h4>
          <p className="text-sm text-white">{data.status}</p>
        </section>
      ) : null}

      {data.matched_tools.length ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Matched Tools</h4>
          <ul className="space-y-2">
            {data.matched_tools.map((tool, index) => (
              <li key={index} className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-slate-200">
                {tool}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {data.matched_commands.length ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Matched Commands</h4>
          <ul className="space-y-2">
            {data.matched_commands.map((command, index) => (
              <li key={index} className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-slate-200">
                {command}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
