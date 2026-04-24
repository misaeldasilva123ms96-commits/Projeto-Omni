import type { ChatRequestState, RuntimeMetadata } from '../../types'
import type { UiRuntimeStatus } from '../../types/ui/runtime'
import { ErrorNotice } from '../ui/ErrorNotice'
import { MetricRow } from '../ui/MetricRow'
import { PanelCard } from '../ui/PanelCard'
import { RuntimeDebugSection } from './RuntimeDebugSection'

type StatusPanelProps = {
  apiConfigured: boolean
  error: string | null
  health: UiRuntimeStatus | null
  lastMetadata: RuntimeMetadata | null
  modeLabel: string
  requestState: ChatRequestState
  sessionId: string
}

export function StatusPanel({
  apiConfigured,
  error,
  health,
  lastMetadata,
  modeLabel,
  requestState,
  sessionId,
}: StatusPanelProps) {
  return (
    <PanelCard className="status-panel omni-status-panel">
      <section className="status-section">
        <p className="sidebar-label">Status</p>
        <div className="status-grid">
          <MetricRow label="Request" value={requestState} />
          <MetricRow label="Modo" value={modeLabel} />
          <MetricRow label="Sessao" value={sessionId} />
          <MetricRow label="API" value={apiConfigured ? 'configurada' : 'indisponivel'} />
        </div>
      </section>

      <section className="status-section">
        <p className="sidebar-label">Runtime (/api/v1/status)</p>
        <div className="status-grid">
          <MetricRow label="Rust" value={health?.rustService ?? 'desconhecido'} />
          <MetricRow label="Python" value={health?.pythonStatus ?? 'nao checado'} />
          <MetricRow label="Node" value={health?.nodeStatus ?? 'nao checado'} />
          <MetricRow label="Modo runtime" value={health?.runtimeMode ?? 'desconhecido'} />
          <MetricRow
            label="Epoch (Rust)"
            value={health != null ? String(health.sessionVersion) : 'desconhecido'}
          />
        </div>
      </section>

      <section className="status-section">
        <p className="sidebar-label">Ultima resposta</p>
        <div className="status-grid">
          <MetricRow label="Fonte" value={lastMetadata?.source ?? 'n/a'} />
          <MetricRow
            label="Epoch (chat)"
            value={lastMetadata?.runtimeSessionVersion != null ? String(lastMetadata.runtimeSessionVersion) : 'n/a'}
          />
          <MetricRow label="Stop reason" value={lastMetadata?.stopReason ?? 'n/a'} />
          <MetricRow label="Ferramentas" value={lastMetadata?.matchedTools.length ?? 0} />
          <MetricRow label="Comandos" value={lastMetadata?.matchedCommands.length ?? 0} />
          <MetricRow
            label="Tokens"
            value={(lastMetadata?.usage?.input_tokens ?? 0) + (lastMetadata?.usage?.output_tokens ?? 0)}
          />
          {lastMetadata?.chatApiVersion ? (
            <MetricRow label="Chat API" value={`v${lastMetadata.chatApiVersion}`} />
          ) : null}
          {lastMetadata?.conversationId ? (
            <MetricRow
              label="ID servidor (corr.)"
              value={lastMetadata.conversationId}
            />
          ) : null}
        </div>
      </section>

      <RuntimeDebugSection metadata={lastMetadata} />

      {error ? (
        <section className="status-section">
          <ErrorNotice message={error} title="Erro recente" />
        </section>
      ) : null}
    </PanelCard>
  )
}
