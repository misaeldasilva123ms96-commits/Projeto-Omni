/**
 * Runtime + health reads for dashboard and status surfaces.
 * All `/internal/*` traffic is defined in `lib/api/runtime.ts` only.
 */
export { fetchHealth } from '../../lib/api/health'
export {
  fetchMilestones,
  fetchPrSummaries,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../../lib/api/runtime'
export { healthResponseToUiRuntimeStatus } from '../../lib/api/adapters'
