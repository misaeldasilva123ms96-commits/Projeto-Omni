import { useEffect, useState } from 'react'
import {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicMilestonesSummaryV1,
  fetchPublicRuntimeSignalsSummaryV1,
  fetchPublicRuntimeStatusV1,
  fetchPublicStrategySummaryV1,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
  publicMilestonesSummaryV1ToUi,
  publicRuntimeSignalsSummaryV1ToUi,
  publicStrategySummaryV1ToUi,
} from '../features/runtime'
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicStatusResponseV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types/api/wire'
import type { UiMilestonesSummary, UiRuntimeSignalsSummary, UiStrategySummary } from '../types/ui/telemetry'

export type CognitiveTelemetryState = {
  /** Preferred product-safe runtime snapshot (`GET /api/v1/status`). */
  publicRuntime: PublicStatusResponseV1 | null
  /** Public summary (`GET /api/v1/runtime/signals/summary`). */
  publicSignalsSummary: UiRuntimeSignalsSummary | null
  /** Public summary (`GET /api/v1/milestones/summary`). */
  publicMilestonesSummary: UiMilestonesSummary | null
  /** Public summary (`GET /api/v1/strategy/summary`). */
  publicStrategySummary: UiStrategySummary | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
  strategyState: StrategyStateResponse | null
  swarmLog: SwarmLogResponse | null
  loading: boolean
  error: string | null
}

const EMPTY: CognitiveTelemetryState = {
  publicRuntime: null,
  publicSignalsSummary: null,
  publicMilestonesSummary: null,
  publicStrategySummary: null,
  milestones: null,
  prSummaries: null,
  runtimeSignals: null,
  strategyState: null,
  swarmLog: null,
  loading: false,
  error: null,
}

/**
 * Bundles the same internal + health reads used by the dashboard, for cognitive side rails.
 * Refetches when `apiReady` or `refreshToken` change (e.g. after a chat turn completes).
 */
export function useCognitiveTelemetry(apiReady: boolean, refreshToken: number | string = 0) {
  const [state, setState] = useState<CognitiveTelemetryState>(EMPTY)

  useEffect(() => {
    if (!apiReady) {
      setState(EMPTY)
      return
    }

    let cancelled = false
    setState((previous) => ({ ...previous, loading: true, error: null }))

    Promise.all([
      fetchPublicRuntimeStatusV1(),
      fetchPublicRuntimeSignalsSummaryV1(),
      fetchPublicMilestonesSummaryV1(),
      fetchPublicStrategySummaryV1(),
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(
        ([
          publicRuntime,
          publicSignalsWire,
          publicMilestonesWire,
          publicStrategyWire,
          runtimeSignals,
          swarmLog,
          strategyState,
          milestones,
          prSummaries,
        ]) => {
          if (cancelled) {
            return
          }
          setState({
            publicRuntime,
            publicSignalsSummary: publicRuntimeSignalsSummaryV1ToUi(publicSignalsWire),
            publicMilestonesSummary: publicMilestonesSummaryV1ToUi(publicMilestonesWire),
            publicStrategySummary: publicStrategySummaryV1ToUi(publicStrategyWire),
            milestones,
            prSummaries,
            runtimeSignals,
            strategyState,
            swarmLog,
            loading: false,
            error: null,
          })
        })
      .catch((err) => {
        if (!cancelled) {
          setState({
            ...EMPTY,
            loading: false,
            error: err instanceof Error ? err.message : 'Telemetry failed to load.',
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [apiReady, refreshToken])

  return state
}
