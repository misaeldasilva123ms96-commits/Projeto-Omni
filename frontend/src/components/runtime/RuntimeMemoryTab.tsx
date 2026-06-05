import type { RuntimeMetadata } from '../../types'

type RuntimeMemoryTabProps = {
  metadata: RuntimeMetadata | null
}

export function RuntimeMemoryTab({ metadata }: RuntimeMemoryTabProps) {
  const memoryStatus =
    (metadata?.cognitiveRuntimeInspection?.memory_status as string | undefined)
    ?? metadata?.signals?.runtime_reason
    ?? null

  const matchedTools = metadata?.matchedTools
  const matchedCommands = metadata?.matchedCommands

  if (!memoryStatus && !matchedTools?.length && !matchedCommands?.length) {
    return <p className="text-sm text-slate-400">não disponível</p>
  }

  return (
    <div className="space-y-4">
      {memoryStatus ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Memory Status</h4>
          <p className="text-sm text-white">{memoryStatus}</p>
        </section>
      ) : null}

      {matchedTools?.length ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Matched Tools</h4>
          <ul className="space-y-2">
            {matchedTools.map((tool, index) => (
              <li key={index} className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-slate-200">
                {tool}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {matchedCommands?.length ? (
        <section className="rounded-[22px] border border-white/10 bg-black/15 px-4 py-3.5">
          <h4 className="mb-3 text-sm font-medium text-white">Matched Commands</h4>
          <ul className="space-y-2">
            {matchedCommands.map((command, index) => (
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
