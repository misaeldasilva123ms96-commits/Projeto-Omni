import type { ToolExecutionDiagnostic } from '../../types'
import { RuntimeLinkAction } from './RuntimeLinkAction'

type RuntimeToolsTabProps = {
  data: ToolExecutionDiagnostic[]
  executionHref: string | null
}

function ToolCard({ tool }: { tool: ToolExecutionDiagnostic }) {
  const statusLabel = tool.tool_succeeded
    ? 'Success'
    : tool.tool_failed
      ? 'Failed'
      : tool.tool_denied
        ? 'Denied'
        : tool.tool_attempted
          ? 'Attempted'
          : 'Pending'

  const statusColor = tool.tool_succeeded
    ? 'text-emerald-300'
    : tool.tool_failed
      ? 'text-red-300'
      : tool.tool_denied
        ? 'text-amber-300'
        : 'text-slate-400'

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium text-white">
            {tool.tool_selected || 'Unknown tool'}
          </div>
          <div className={`mt-1 text-xs ${statusColor}`}>
            {statusLabel}
          </div>
        </div>
        {tool.tool_latency_ms != null ? (
          <span className="text-xs text-slate-400">{tool.tool_latency_ms}ms</span>
        ) : null}
      </div>
      {tool.tool_failure_reason ? (
        <p className="mt-2 text-xs text-red-200/80">{tool.tool_failure_reason}</p>
      ) : null}
    </div>
  )
}

export function RuntimeToolsTab({ data, executionHref }: RuntimeToolsTabProps) {
  if (!data.length) {
    return (
      <div>
        <p className="text-sm text-slate-400">não disponível</p>
        <RuntimeLinkAction
          href={executionHref}
          label="Ver execução"
          unavailableLabel="observabilidade indisponível"
        />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {data.map((tool, index) => (
        <ToolCard key={index} tool={tool} />
      ))}
      <RuntimeLinkAction
        href={executionHref}
        label="Ver execução"
        unavailableLabel="observabilidade indisponível"
      />
    </div>
  )
}
