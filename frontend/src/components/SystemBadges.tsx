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
      {metadata.matchedTools.length > 0 ? (
        <span className="system-badge">Ferramentas: {metadata.matchedTools.join(', ')}</span>
      ) : null}
      {metadata.matchedCommands.length > 0 ? (
        <span className="system-badge">Comandos: {metadata.matchedCommands.join(', ')}</span>
      ) : null}
      {usage?.input_tokens || usage?.output_tokens ? (
        <span className="system-badge">
          Tokens: {usage.input_tokens ?? 0}/{usage.output_tokens ?? 0}
        </span>
      ) : null}
    </div>
  )
}
