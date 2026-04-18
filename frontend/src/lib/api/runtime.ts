/**
 * Runtime telemetry: public v1 summaries (`/api/v1/*/summary`, `/api/v1/status`) and internal reads (`/internal/*`).
 * See `docs/frontend/telemetry-migration-status.md` and `docs/frontend/integration-matrix.md`.
 */
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicMilestonesSummaryV1,
  PublicRuntimeSignalsSummaryV1,
  PublicStatusResponseV1,
  PublicStrategySummaryV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../../types'
import { getJson } from './client'

/** Preferred public runtime status (`GET /api/v1/status`). */
export function fetchPublicRuntimeStatusV1() {
  return getJson<PublicStatusResponseV1>('/api/v1/status')
}

/** Public runtime signals summary (`GET /api/v1/runtime/signals/summary`). */
export function fetchPublicRuntimeSignalsSummaryV1() {
  return getJson<PublicRuntimeSignalsSummaryV1>('/api/v1/runtime/signals/summary')
}

/** Public milestones checkpoint summary (`GET /api/v1/milestones/summary`). */
export function fetchPublicMilestonesSummaryV1() {
  return getJson<PublicMilestonesSummaryV1>('/api/v1/milestones/summary')
}

/** Public strategy file summary (`GET /api/v1/strategy/summary`). */
export function fetchPublicStrategySummaryV1() {
  return getJson<PublicStrategySummaryV1>('/api/v1/strategy/summary')
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
