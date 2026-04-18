/**
 * Omni HTTP API — barrel re-exports (Phase 2 modular layout).
 * Prefer importing from `lib/api/<domain>` in new code.
 */
export { REQUEST_TIMEOUT_MS, fetchWithTimeout, getJson, getSupabaseAuthHeaders } from './api/client'
export type { ChatClientContext } from './api/chat'
export { sendOmniMessage } from './api/chat'
export { fetchHealth } from './api/health'
export {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicMilestonesSummaryV1,
  fetchPublicRuntimeSignalsSummaryV1,
  fetchPublicRuntimeStatusV1,
  fetchPublicStrategySummaryV1,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from './api/runtime'
export { fetchObservabilitySnapshot, fetchObservabilityTraces } from './api/observability'
export {
  chatApiResponseToUi,
  healthResponseToUiRuntimeStatus,
  observabilityApiEnvelopeToUi,
  observabilityTracesResponseToUi,
  parseWireChatPayload,
  publicMilestonesSummaryV1ToUi,
  publicRuntimeSignalsSummaryV1ToUi,
  publicStatusV1ToUiRuntimeStatus,
  publicStrategySummaryV1ToUi,
} from './api/adapters'
