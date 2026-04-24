import type { RuntimeMetadata } from '../../types'
import { MetricRow } from '../ui/MetricRow'

type RuntimeDebugSectionProps = {
  metadata: RuntimeMetadata | null
}

function boolLabel(value: boolean | undefined): string {
  if (value === true) {
    return 'yes'
  }
  if (value === false) {
    return 'no'
  }
  return 'unknown'
}

function objectPreview(value: unknown): string {
  if (value == null) {
    return 'not present'
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return 'unserializable'
  }
}

export function RuntimeDebugSection({ metadata }: RuntimeDebugSectionProps) {
  if (!metadata) {
    return null
  }

  const signalRuntimeReason = metadata.signals?.runtime_reason
  const signalNodeExecutionSuccessful = metadata.signals?.node_execution_successful
  const inspectionPresent = Boolean(metadata.cognitiveRuntimeInspection)
  const provenancePresent = Boolean(metadata.executionProvenance || metadata.signals?.execution_provenance)
  const providersCount = metadata.providers?.length ?? 0

  return (
    <section className="status-section">
      <p className="sidebar-label">Runtime debug (last turn)</p>
      <div className="status-grid">
        <MetricRow label="Runtime mode" value={metadata.runtimeMode ?? 'n/a'} />
        <MetricRow label="Runtime reason" value={metadata.runtimeReason ?? signalRuntimeReason ?? 'n/a'} />
        <MetricRow label="Execution path" value={metadata.executionPathUsed ?? 'n/a'} />
        <MetricRow label="Fallback triggered" value={boolLabel(metadata.fallbackTriggered)} />
        <MetricRow
          label="Compatibility execution"
          value={boolLabel(metadata.compatibilityExecutionActive)}
        />
        <MetricRow label="Provider actual" value={metadata.providerActual ?? 'n/a'} />
        <MetricRow label="Provider failed" value={boolLabel(metadata.providerFailed)} />
        <MetricRow label="Failure class" value={metadata.failureClass ?? 'n/a'} />
        <MetricRow
          label="Node executed successfully"
          value={boolLabel(signalNodeExecutionSuccessful)}
        />
        <MetricRow
          label="Inspection present"
          value={inspectionPresent ? 'yes' : 'no'}
        />
        <MetricRow
          label="Execution provenance present"
          value={provenancePresent ? 'yes' : 'no'}
        />
        <MetricRow label="Providers count" value={String(providersCount)} />
      </div>

      <div className="runtime-debug-details">
        <details className="runtime-debug-disclosure">
          <summary>Signals</summary>
          <pre>{objectPreview(metadata.signals)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Cognitive runtime inspection</summary>
          <pre>{objectPreview(metadata.cognitiveRuntimeInspection)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Execution provenance</summary>
          <pre>{objectPreview(metadata.executionProvenance ?? metadata.signals?.execution_provenance)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Providers</summary>
          <pre>{objectPreview(metadata.providers)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Error</summary>
          <pre>{objectPreview(metadata.error)}</pre>
        </details>
      </div>
    </section>
  )
}
