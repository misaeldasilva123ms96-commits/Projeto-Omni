import type { RuntimeMetadata } from '../../types'
import { sanitizeRuntimeDebugPayload } from '../../lib/runtimeDebugSanitizer'
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
    return JSON.stringify(sanitizeRuntimeDebugPayload({ value }), null, 2)
  } catch {
    return 'unserializable'
  }
}

function safeString(value: unknown, fallback = 'n/a'): string {
  if (typeof value !== 'string' || !value.trim()) {
    return fallback
  }
  const sanitized = sanitizeRuntimeDebugPayload({ value })
  return typeof sanitized.value === 'string' ? sanitized.value : fallback
}

export function RuntimeDebugSection({ metadata }: RuntimeDebugSectionProps) {
  if (!metadata) {
    return null
  }

  const safeMetadata = sanitizeRuntimeDebugPayload(metadata) as Partial<RuntimeMetadata>
  const signalRuntimeReason = safeMetadata.signals?.runtime_reason
  const signalNodeExecutionSuccessful = safeMetadata.signals?.node_execution_successful
  const inspectionPresent = Boolean(metadata.cognitiveRuntimeInspection)
  const provenancePresent = Boolean(metadata.executionProvenance || metadata.signals?.execution_provenance)
  const providersCount = safeMetadata.providers?.length ?? 0
  const providerDiagnostics = safeMetadata.providerDiagnostics ?? safeMetadata.signals?.provider_diagnostics ?? []
  const providerFallbackOccurred =
    safeMetadata.providerFallbackOccurred ?? safeMetadata.signals?.provider_fallback_occurred
  const noProviderAvailable =
    safeMetadata.noProviderAvailable ?? safeMetadata.signals?.no_provider_available
  const toolExecution = safeMetadata.toolExecution ?? safeMetadata.signals?.tool_execution ?? null
  const toolDiagnostics = safeMetadata.toolDiagnostics ?? safeMetadata.signals?.tool_diagnostics ?? []

  return (
    <section className="status-section">
      <p className="sidebar-label">Runtime debug (last turn)</p>
      <div className="status-grid">
        <MetricRow label="Runtime mode" value={safeString(safeMetadata.runtimeMode)} />
        <MetricRow label="Runtime reason" value={safeString(safeMetadata.runtimeReason ?? signalRuntimeReason)} />
        <MetricRow label="Execution path" value={safeString(safeMetadata.executionPathUsed)} />
        <MetricRow label="Fallback triggered" value={boolLabel(safeMetadata.fallbackTriggered)} />
        <MetricRow
          label="Compatibility execution"
          value={boolLabel(safeMetadata.compatibilityExecutionActive)}
        />
        <MetricRow label="Provider actual" value={safeString(safeMetadata.providerActual)} />
        <MetricRow label="Provider failed" value={boolLabel(safeMetadata.providerFailed)} />
        <MetricRow label="Failure class" value={safeString(safeMetadata.failureClass)} />
        <MetricRow label="Failure reason" value={safeString(safeMetadata.failureReason)} />
        <MetricRow label="Public error code" value={safeString(safeMetadata.errorPublicCode ?? safeMetadata.error?.error_public_code ?? safeMetadata.error?.code)} />
        <MetricRow label="Public error message" value={safeString(safeMetadata.errorPublicMessage ?? safeMetadata.error?.error_public_message ?? safeMetadata.error?.message)} />
        <MetricRow label="Severity" value={safeString(safeMetadata.severity ?? safeMetadata.error?.severity)} />
        <MetricRow label="Retryable" value={boolLabel(safeMetadata.retryable ?? safeMetadata.error?.retryable)} />
        <MetricRow
          label="Internal error redacted"
          value={boolLabel(safeMetadata.internalErrorRedacted ?? safeMetadata.error?.internal_error_redacted)}
        />
        <MetricRow label="Provider fallback routing" value={boolLabel(providerFallbackOccurred)} />
        <MetricRow label="No provider available" value={boolLabel(noProviderAvailable)} />
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
        <MetricRow label="Provider diagnostics rows" value={String(providerDiagnostics.length)} />
        <MetricRow label="Tool requested" value={boolLabel(toolExecution?.tool_requested)} />
        <MetricRow label="Tool selected" value={toolExecution?.tool_selected ?? 'n/a'} />
        <MetricRow label="Tool available" value={boolLabel(toolExecution?.tool_available)} />
        <MetricRow label="Tool attempted" value={boolLabel(toolExecution?.tool_attempted)} />
        <MetricRow label="Tool succeeded" value={boolLabel(toolExecution?.tool_succeeded)} />
        <MetricRow label="Tool failed" value={boolLabel(toolExecution?.tool_failed)} />
        <MetricRow label="Tool denied" value={boolLabel(toolExecution?.tool_denied)} />
        <MetricRow label="Tool failure class" value={toolExecution?.tool_failure_class ?? 'n/a'} />
        <MetricRow label="Tool latency (ms)" value={String(toolExecution?.tool_latency_ms ?? 'n/a')} />
        <MetricRow label="Tool diagnostics rows" value={String(toolDiagnostics.length)} />
      </div>

      <div className="runtime-debug-details">
        <details className="runtime-debug-disclosure">
          <summary>Signals</summary>
          <pre>{objectPreview(safeMetadata.signals)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Cognitive runtime inspection</summary>
          <pre>{objectPreview(safeMetadata.cognitiveRuntimeInspection)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Execution provenance</summary>
          <pre>{objectPreview(safeMetadata.executionProvenance ?? safeMetadata.signals?.execution_provenance)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Provider diagnostics</summary>
          <pre>{objectPreview(providerDiagnostics)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Tool execution</summary>
          <pre>{objectPreview(toolExecution)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Tool diagnostics</summary>
          <pre>{objectPreview(toolDiagnostics)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Providers</summary>
          <pre>{objectPreview(safeMetadata.providers)}</pre>
        </details>
        <details className="runtime-debug-disclosure">
          <summary>Error</summary>
          <pre>{objectPreview(safeMetadata.error)}</pre>
        </details>
      </div>
    </section>
  )
}
