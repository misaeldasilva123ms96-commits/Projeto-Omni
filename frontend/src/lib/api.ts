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
} from './api/adapters'
