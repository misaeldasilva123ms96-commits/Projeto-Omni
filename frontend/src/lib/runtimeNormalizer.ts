import type { RuntimeMetadata } from '../types'
import type { UiChatResponse } from '../types/ui/chat'
import {
  normalizeRuntimeInspectorData,
  type RuntimeInspectorData,
} from './runtimeTypes'

export type RuntimeChatSnapshot = {
  metadata: RuntimeMetadata
  inspectorData: RuntimeInspectorData | null
}

function hasInspectorSource(metadata: RuntimeMetadata | null | undefined): boolean {
  if (!metadata) return false
  const inspection = metadata.cognitiveRuntimeInspection
  return Boolean(
    metadata.runtimeMode
    || metadata.runtimeReason
    || metadata.usage
    || metadata.providerActual
    || metadata.providerDiagnostics?.length
    || metadata.toolExecution
    || metadata.toolDiagnostics?.length
    || metadata.matchedTools?.length
    || metadata.matchedCommands?.length
    || (inspection && Object.keys(inspection).length > 0),
  )
}

export function normalizeStoredRuntimeMetadata(
  metadata: RuntimeMetadata | null | undefined,
): RuntimeInspectorData | null {
  try {
    if (!hasInspectorSource(metadata)) return null
    return normalizeRuntimeInspectorData(metadata)
  } catch {
    return null
  }
}

export function normalizeUiChatRuntime(
  ui: UiChatResponse,
  previousSessionId: string,
): RuntimeChatSnapshot {
  const metadata: RuntimeMetadata = {
    sessionId: ui.sessionId ?? previousSessionId,
    source: ui.source,
    matchedCommands: ui.commands ?? [],
    matchedTools: ui.tools ?? [],
    stopReason: ui.stopReason,
    executionTier: ui.executionTier,
    wireHealth: ui.wireHealth,
    runtimeSessionVersion: ui.runtimeSessionVersion,
    conversationId: ui.conversationId,
    chatApiVersion: ui.chatApiVersion,
    usage: ui.usage
      ? {
          input_tokens: ui.usage.inputTokens,
          output_tokens: ui.usage.outputTokens,
        }
      : undefined,
    runtimeMode: ui.runtimeMode,
    runtimeReason: ui.runtimeReason,
    cognitiveRuntimeInspection: ui.cognitiveRuntimeInspection,
    signals: ui.signals,
    executionPathUsed: ui.executionPathUsed,
    fallbackTriggered: ui.fallbackTriggered,
    compatibilityExecutionActive: ui.compatibilityExecutionActive,
    providerActual: ui.providerActual,
    providerFailed: ui.providerFailed,
    failureClass: ui.failureClass,
    failureReason: ui.failureReason,
    errorPublicCode: ui.errorPublicCode,
    errorPublicMessage: ui.errorPublicMessage,
    severity: ui.severity,
    retryable: ui.retryable,
    internalErrorRedacted: ui.internalErrorRedacted,
    executionProvenance: ui.executionProvenance,
    providers: ui.providers,
    providerDiagnostics: ui.providerDiagnostics,
    providerFallbackOccurred: ui.providerFallbackOccurred,
    noProviderAvailable: ui.noProviderAvailable,
    toolExecution: ui.toolExecution,
    toolDiagnostics: ui.toolDiagnostics,
    error: ui.error,
  }

  return {
    metadata,
    inspectorData: normalizeStoredRuntimeMetadata(metadata),
  }
}
