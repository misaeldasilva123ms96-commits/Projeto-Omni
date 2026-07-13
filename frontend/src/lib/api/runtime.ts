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
  publicRuntime: PublicStatusResponseV1 | null
  publicSignalsWire: PublicRuntimeSignalsSummaryV1 | null
  publicMilestonesWire: PublicMilestonesSummaryV1 | null
  publicStrategyWire: PublicStrategySummaryV1 | null
  runtimeSignals: RuntimeSignalsResponse | null
  runtimeSignalsSource: RichTelemetryDetailSource | null
  swarmLog: SwarmLogResponse | null
  strategyState: StrategyStateResponse | null
  strategyStateSource: RichTelemetryDetailSource | null
  milestones: MilestonesResponse | null
  milestonesSource: RichTelemetryDetailSource | null
  prSummaries: PrSummariesResponse | null
  failedSources: string[]
}

/**
 * Single parallel load for dashboard + cognitive rail: public summaries always;
 * richer rows prefer operator JWT routes, then `/internal/*`.
 */
export async function loadCognitiveTelemetryBundle(): Promise<CognitiveTelemetryBundle> {
  const results = await Promise.allSettled([
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
  const names = [
    'runtime status', 'runtime signals summary', 'milestones summary', 'strategy summary',
    'runtime signals detail', 'swarm log', 'strategy detail', 'milestones detail', 'PR summaries',
  ]
  const failedSources = results.flatMap((result, index) => result.status === 'rejected' ? [names[index]] : [])
  if (failedSources.length === results.length) {
    throw new Error('Telemetry endpoints are unavailable.')
  }
  const value = <T,>(index: number): T | null => {
    const result = results[index]
    return result.status === 'fulfilled' ? result.value as T : null
  }
  const runtimeBundle = value<Awaited<ReturnType<typeof fetchRuntimeSignalsPreferOperator>>>(4)
  const strategyBundle = value<Awaited<ReturnType<typeof fetchStrategyStatePreferOperator>>>(6)
  const milestonesBundle = value<Awaited<ReturnType<typeof fetchMilestonesPreferOperator>>>(7)

  return {
    publicRuntime: value<PublicStatusResponseV1>(0),
    publicSignalsWire: value<PublicRuntimeSignalsSummaryV1>(1),
    publicMilestonesWire: value<PublicMilestonesSummaryV1>(2),
    publicStrategyWire: value<PublicStrategySummaryV1>(3),
    runtimeSignals: runtimeBundle?.data ?? null,
    runtimeSignalsSource: runtimeBundle?.source ?? null,
    swarmLog: value<SwarmLogResponse>(5),
    strategyState: strategyBundle?.data ?? null,
    strategyStateSource: strategyBundle?.source ?? null,
    milestones: milestonesBundle?.data ?? null,
    milestonesSource: milestonesBundle?.source ?? null,
    prSummaries: value<PrSummariesResponse>(8),
    failedSources,
  }
}
