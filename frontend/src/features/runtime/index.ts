/**
 * Runtime + health reads for dashboard and status surfaces.
 * Public status: `fetchPublicRuntimeStatusV1`. `/internal/*` traffic is defined in `lib/api/runtime.ts` only.
 */
export { fetchHealth } from '../../lib/api/health'
export {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicRuntimeStatusV1,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../../lib/api/runtime'
export { healthResponseToUiRuntimeStatus, publicStatusV1ToUiRuntimeStatus } from '../../lib/api/adapters'
