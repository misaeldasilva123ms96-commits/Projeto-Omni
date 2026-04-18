/**
 * Internal read-only telemetry (`GET /internal/*`) — not a public product API.
 * See `docs/frontend/integration-matrix.md` for stability scope.
 */
import type {
  MilestonesResponse,
  PrSummariesResponse,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../../types'
import { getJson } from './client'

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
