/**
 * Runtime + health reads for dashboard and status surfaces.
 * Public summaries, operator detail when JWT present, `/internal/*` fallback — see `docs/frontend/operator-telemetry-adoption.md`.
 */
export type { RichTelemetryDetailSource } from '../../types'
export { fetchHealth } from '../../lib/api/health'
export {
  fetchMilestones,
  fetchMilestonesPreferOperator,
  fetchPrSummaries,
  fetchPublicMilestonesSummaryV1,
  fetchPublicRuntimeSignalsSummaryV1,
  fetchPublicRuntimeStatusV1,
  fetchPublicStrategySummaryV1,
  fetchRuntimeSignals,
  fetchRuntimeSignalsPreferOperator,
  fetchStrategyState,
  fetchStrategyStatePreferOperator,
  fetchSwarmLog,
  loadCognitiveTelemetryBundle,
} from '../../lib/api/runtime'
export type { CognitiveTelemetryBundle } from '../../lib/api/runtime'
export {
  healthResponseToUiRuntimeStatus,
  publicMilestonesSummaryV1ToUi,
  publicRuntimeSignalsSummaryV1ToUi,
  publicStatusV1ToUiRuntimeStatus,
  publicStrategySummaryV1ToUi,
} from '../../lib/api/adapters'
