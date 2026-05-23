/**
 * Runtime telemetry: public v1 summaries, authenticated operator detail (`/api/v1/operator/*`),
 * and legacy `/internal/*` fallback. See `docs/frontend/operator-telemetry-adoption.md`.
 */
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicMilestonesSummaryV1,
  PublicRuntimeSignalsSummaryV1,
  PublicStatusResponseV1,
  PublicStrategySummaryV1,
  RichTelemetryDetailSource,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../../types'
import {
  operatorMilestonesV1ToMilestonesResponse,
  operatorRuntimeSignalsV1ToRuntimeSignalsResponse,
  operatorStrategyChangesV1ToStrategyStateResponse,
} from './adapters'
import { getJson } from './client'
import {
  tryFetchOperatorMilestones,
  tryFetchOperatorRuntimeSignals,
  tryFetchOperatorStrategyChanges,
} from './operator'

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

export async function fetchRuntimeSignalsPreferOperator(): Promise<{
  data: RuntimeSignalsResponse
  source: RichTelemetryDetailSource
}> {
  const op = await tryFetchOperatorRuntimeSignals()
  if (op) {
    return { data: operatorRuntimeSignalsV1ToRuntimeSignalsResponse(op), source: 'operator' }
  }
  const data = await fetchRuntimeSignals()
  return { data, source: 'internal' }
}

export async function fetchStrategyStatePreferOperator(): Promise<{
  data: StrategyStateResponse
  source: RichTelemetryDetailSource
}> {
  const op = await tryFetchOperatorStrategyChanges()
  if (op) {
    return { data: operatorStrategyChangesV1ToStrategyStateResponse(op), source: 'operator' }
  }
  const data = await fetchStrategyState()
  return { data, source: 'internal' }
}

export async function fetchMilestonesPreferOperator(): Promise<{
  data: MilestonesResponse
  source: RichTelemetryDetailSource
}> {
  const op = await tryFetchOperatorMilestones()
  if (op) {
    return { data: operatorMilestonesV1ToMilestonesResponse(op), source: 'operator' }
  }
  const data = await fetchMilestones()
  return { data, source: 'internal' }
}

export type CognitiveTelemetryBundle = {
  publicRuntime: PublicStatusResponseV1
  publicSignalsWire: PublicRuntimeSignalsSummaryV1
  publicMilestonesWire: PublicMilestonesSummaryV1
  publicStrategyWire: PublicStrategySummaryV1
  runtimeSignals: RuntimeSignalsResponse
  runtimeSignalsSource: RichTelemetryDetailSource
  swarmLog: SwarmLogResponse
  strategyState: StrategyStateResponse
  strategyStateSource: RichTelemetryDetailSource
  milestones: MilestonesResponse
  milestonesSource: RichTelemetryDetailSource
  prSummaries: PrSummariesResponse
}

/**
 * Single parallel load for dashboard + cognitive rail: public summaries always;
 * richer rows prefer operator JWT routes, then `/internal/*`.
 */
export async function loadCognitiveTelemetryBundle(): Promise<CognitiveTelemetryBundle> {
  const [
    publicRuntime,
    publicSignalsWire,
    publicMilestonesWire,
    publicStrategyWire,
    runtimeBundle,
    swarmLog,
    strategyBundle,
    milestonesBundle,
    prSummaries,
  ] = await Promise.all([
    fetchPublicRuntimeStatusV1(),
    fetchPublicRuntimeSignalsSummaryV1(),
    fetchPublicMilestonesSummaryV1(),
    fetchPublicStrategySummaryV1(),
    fetchRuntimeSignalsPreferOperator(),
    fetchSwarmLog(),
    fetchStrategyStatePreferOperator(),
    fetchMilestonesPreferOperator(),
    fetchPrSummaries(),
  ])

  return {
    publicRuntime,
    publicSignalsWire,
    publicMilestonesWire,
    publicStrategyWire,
    runtimeSignals: runtimeBundle.data,
    runtimeSignalsSource: runtimeBundle.source,
    swarmLog,
    strategyState: strategyBundle.data,
    strategyStateSource: strategyBundle.source,
    milestones: milestonesBundle.data,
    milestonesSource: milestonesBundle.source,
    prSummaries,
  }
}
