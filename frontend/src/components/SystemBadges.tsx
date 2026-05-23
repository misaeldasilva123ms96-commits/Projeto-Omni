import type { RuntimeMetadata } from '../types'

type SystemBadgesProps = {
  metadata?: RuntimeMetadata
}

export function SystemBadges({ metadata }: SystemBadgesProps) {
  if (!metadata) {
    return null
  }

  const usage = metadata.usage

  return (
    <div className="system-badges">
      {metadata.source ? <span className="system-badge">Fonte: {metadata.source}</span> : null}
      {metadata.sessionId ? <span className="system-badge">Sessao: {metadata.sessionId}</span> : null}
      {metadata.stopReason ? <span className="system-badge">Stop: {metadata.stopReason}</span> : null}
      {metadata.runtimeMode ? <span className="system-badge">Runtime: {metadata.runtimeMode}</span> : null}
      {metadata.runtimeReason ? <span className="system-badge">Motivo: {metadata.runtimeReason}</span> : null}
      {metadata.executionPathUsed ? (
        <span className="system-badge">Caminho: {metadata.executionPathUsed}</span>
      ) : null}
      {metadata.executionTier ? (
        <span className="system-badge">Exec tier: {metadata.executionTier}</span>
      ) : null}
      {metadata.wireHealth === 'degraded' ? (
        <span className="system-badge">Wire: degraded (not a clean success)</span>
      ) : null}
      {typeof metadata.fallbackTriggered === 'boolean' ? (
        <span className="system-badge">Fallback: {metadata.fallbackTriggered ? 'yes' : 'no'}</span>
      ) : null}
      {typeof metadata.compatibilityExecutionActive === 'boolean' ? (
        <span className="system-badge">
          Compatibility: {metadata.compatibilityExecutionActive ? 'yes' : 'no'}
        </span>
      ) : null}
      {metadata.providerActual ? (
        <span className="system-badge">Provider: {metadata.providerActual}</span>
      ) : null}
      {typeof metadata.providerFailed === 'boolean' ? (
        <span className="system-badge">Provider failed: {metadata.providerFailed ? 'yes' : 'no'}</span>
      ) : null}
      {metadata.failureClass ? (
        <span className="system-badge">Failure: {metadata.failureClass}</span>
      ) : null}
      {metadata.matchedTools.length > 0 ? (
        <span className="system-badge">Ferramentas: {metadata.matchedTools.join(', ')}</span>
      ) : null}
      {metadata.matchedCommands.length > 0 ? (
        <span className="system-badge">Comandos: {metadata.matchedCommands.join(', ')}</span>
      ) : null}
      {metadata.cognitiveRuntimeInspection ? (
        <span className="system-badge">Inspection: present</span>
      ) : null}
      {metadata.executionProvenance ? (
        <span className="system-badge">Provenance: present</span>
      ) : null}
      {usage?.input_tokens || usage?.output_tokens ? (
        <span className="system-badge">
          Tokens: {usage.input_tokens ?? 0}/{usage.output_tokens ?? 0}
        </span>
      ) : null}
    </div>
  )
}
