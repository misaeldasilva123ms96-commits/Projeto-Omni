import { useEffect, useState } from 'react'
import {
  fetchMilestones,
  fetchPrSummaries,
  fetchPublicRuntimeStatusV1,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../features/runtime'
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicStatusResponseV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types/api/wire'

export type CognitiveTelemetryState = {
  /** Preferred product-safe runtime snapshot (`GET /api/v1/status`). */
  publicRuntime: PublicStatusResponseV1 | null
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
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(([publicRuntime, runtimeSignals, swarmLog, strategyState, milestones, prSummaries]) => {
        if (cancelled) {
          return
        }
        setState({
          publicRuntime,
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
