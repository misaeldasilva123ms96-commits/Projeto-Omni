/**
 * Internal read-only telemetry (`GET /internal/*`) — not a public product API.
 * See `docs/frontend/integration-matrix.md` for stability scope.
 */
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicStatusResponseV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../../types'
import { getJson } from './client'

/** Preferred public runtime status (`GET /api/v1/status`). */
export function fetchPublicRuntimeStatusV1() {
  return getJson<PublicStatusResponseV1>('/api/v1/status')
}

export function fetchRuntimeSignals() {
  return getJson<RuntimeSignalsResponse>('/internal/runtime-signals')
}

export function fetchSwarmLog() {
  return getJson<SwarmLogResponse>('/internal/swarm-log')
}

export function fetchStrategyState() {
  return getJson<StrategyStateResponse>('/internal/strategy-state')
}

export function fetchMilestones() {
  return getJson<MilestonesResponse>('/internal/milestones')
}

export function fetchPrSummaries() {
  return getJson<PrSummariesResponse>('/internal/pr-summaries')
}
