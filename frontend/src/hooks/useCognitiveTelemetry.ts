import { useEffect, useState } from 'react'
import {
  fetchHealth,
  fetchMilestones,
  fetchPrSummaries,
  fetchRuntimeSignals,
  fetchStrategyState,
  fetchSwarmLog,
} from '../features/runtime'
import type {
  HealthResponse,
  MilestonesResponse,
  PrSummariesResponse,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types/api/wire'

export type CognitiveTelemetryState = {
  health: HealthResponse | null
  milestones: MilestonesResponse | null
  prSummaries: PrSummariesResponse | null
  runtimeSignals: RuntimeSignalsResponse | null
  strategyState: StrategyStateResponse | null
  swarmLog: SwarmLogResponse | null
  loading: boolean
  error: string | null
}

const EMPTY: CognitiveTelemetryState = {
  health: null,
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
      fetchHealth(),
      fetchRuntimeSignals(),
      fetchSwarmLog(),
      fetchStrategyState(),
      fetchMilestones(),
      fetchPrSummaries(),
    ])
      .then(([health, runtimeSignals, swarmLog, strategyState, milestones, prSummaries]) => {
        if (cancelled) {
          return
        }
        setState({
          health,
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
