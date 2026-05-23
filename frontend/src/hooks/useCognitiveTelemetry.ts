import { useEffect, useState } from 'react'
import {
  loadCognitiveTelemetryBundle,
  publicMilestonesSummaryV1ToUi,
  publicRuntimeSignalsSummaryV1ToUi,
  publicStrategySummaryV1ToUi,
} from '../features/runtime'
import type {
  MilestonesResponse,
  PrSummariesResponse,
  PublicStatusResponseV1,
  RichTelemetryDetailSource,
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
  /** Provenance for richer rows (operator JWT vs legacy internal). */
  runtimeSignalsSource: RichTelemetryDetailSource | null
  strategyStateSource: RichTelemetryDetailSource | null
  milestonesSource: RichTelemetryDetailSource | null
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
  runtimeSignalsSource: null,
  strategyStateSource: null,
  milestonesSource: null,
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

    loadCognitiveTelemetryBundle()
      .then((bundle) => {
          if (cancelled) {
            return
          }
          setState({
            publicRuntime: bundle.publicRuntime,
            publicSignalsSummary: publicRuntimeSignalsSummaryV1ToUi(bundle.publicSignalsWire),
            publicMilestonesSummary: publicMilestonesSummaryV1ToUi(bundle.publicMilestonesWire),
            publicStrategySummary: publicStrategySummaryV1ToUi(bundle.publicStrategyWire),
            milestones: bundle.milestones,
            prSummaries: bundle.prSummaries,
            runtimeSignals: bundle.runtimeSignals,
            strategyState: bundle.strategyState,
            swarmLog: bundle.swarmLog,
            runtimeSignalsSource: bundle.runtimeSignalsSource,
            strategyStateSource: bundle.strategyStateSource,
            milestonesSource: bundle.milestonesSource,
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
