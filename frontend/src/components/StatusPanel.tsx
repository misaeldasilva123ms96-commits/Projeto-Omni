import type { ChatRequestState, RuntimeMetadata } from '../types'
import type { UiRuntimeStatus } from '../types/ui/runtime'

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
    <div className="status-panel panel-card">
      <section className="status-section">
        <p className="sidebar-label">Status</p>
        <div className="status-grid">
          <div className="status-line">
            <span>Request</span>
            <strong>{requestState}</strong>
          </div>
          <div className="status-line">
            <span>Modo</span>
            <strong>{modeLabel}</strong>
          </div>
          <div className="status-line">
            <span>Sessao</span>
            <strong>{sessionId}</strong>
          </div>
          <div className="status-line">
            <span>API</span>
            <strong>{apiConfigured ? 'configurada' : 'indisponivel'}</strong>
          </div>
        </div>
      </section>

      <section className="status-section">
        <p className="sidebar-label">Runtime</p>
        <div className="status-grid">
          <div className="status-line">
            <span>Rust</span>
            <strong>{health?.rustService ?? 'desconhecido'}</strong>
          </div>
          <div className="status-line">
            <span>Python</span>
            <strong>{health?.pythonStatus ?? 'nao checado'}</strong>
          </div>
          <div className="status-line">
            <span>Node</span>
            <strong>{health?.nodeStatus ?? 'nao checado'}</strong>
          </div>
          <div className="status-line">
            <span>Modo runtime</span>
            <strong>{health?.runtimeMode ?? 'desconhecido'}</strong>
          </div>
        </div>
      </section>

      <section className="status-section">
        <p className="sidebar-label">Ultima resposta</p>
        <div className="status-grid">
          <div className="status-line">
            <span>Fonte</span>
            <strong>{lastMetadata?.source ?? 'n/a'}</strong>
          </div>
          <div className="status-line">
            <span>Stop reason</span>
            <strong>{lastMetadata?.stopReason ?? 'n/a'}</strong>
          </div>
          <div className="status-line">
            <span>Ferramentas</span>
            <strong>{lastMetadata?.matchedTools.length ?? 0}</strong>
          </div>
          <div className="status-line">
            <span>Comandos</span>
            <strong>{lastMetadata?.matchedCommands.length ?? 0}</strong>
          </div>
          <div className="status-line">
            <span>Tokens</span>
            <strong>
              {(lastMetadata?.usage?.input_tokens ?? 0) + (lastMetadata?.usage?.output_tokens ?? 0)}
            </strong>
          </div>
        </div>
      </section>

      {error ? (
        <section className="status-section">
          <p className="sidebar-label">Erro recente</p>
          <p className="error-text panel-error">{error}</p>
        </section>
      ) : null}
    </div>
  )
}
