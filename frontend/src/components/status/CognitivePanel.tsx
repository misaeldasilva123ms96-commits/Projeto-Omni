import { useMemo } from 'react'
import type { ChatRequestState, RuntimeMetadata } from '../../types'
import type { UiRuntimeStatus } from '../../types/ui/runtime'
import type { CognitiveTelemetryState } from '../../hooks/useCognitiveTelemetry'
import type { UiObservabilitySnapshot } from '../../types/ui/observability'
import { FutureModuleCard } from './FutureModuleCard'
import { StatusPanel } from './StatusPanel'
import { RuntimeStatusSection } from './RuntimeStatusSection'
import { StrategyStateSection } from './StrategyStateSection'
import { MilestoneStateSection } from './MilestoneStateSection'
import { ExecutionSignalsSection } from './ExecutionSignalsSection'
import { ObservabilitySummarySection } from './ObservabilitySummarySection'
import { LoadingState } from '../ui/LoadingState'
import { ErrorNotice } from '../ui/ErrorNotice'

export type CognitivePanelProps = {
  apiConfigured: boolean
  chatError: string | null
  health: UiRuntimeStatus | null
  lastMetadata: RuntimeMetadata | null
  modeLabel: string
  observabilityCanRequest: boolean
  observabilityError: string | null
  observabilityLoading: boolean
  observabilitySnapshot: UiObservabilitySnapshot | null
  requestState: ChatRequestState
  sessionId: string
  telemetry: CognitiveTelemetryState
}

export function CognitivePanel({
  apiConfigured,
  chatError,
  health,
  lastMetadata,
  modeLabel,
  observabilityCanRequest,
  observabilityError,
  observabilityLoading,
  observabilitySnapshot,
  requestState,
  sessionId,
  telemetry,
}: CognitivePanelProps) {
  const telemetryHint = useMemo(
    () => (
      <p className="cognitive-trust-hint muted-copy">
        Seções abaixo usam apenas fontes reais: <strong>/health</strong>, <strong>/internal/*</strong> e snapshot
        protegido quando autenticado. Dados futuros aparecem como módulos pendentes de contrato público.
      </p>
    ),
    [],
  )

  return (
    <div className="omni-cognitive-stack">
      <StatusPanel
        apiConfigured={apiConfigured}
        error={chatError}
        health={health}
        lastMetadata={lastMetadata}
        modeLabel={modeLabel}
        requestState={requestState}
        sessionId={sessionId}
      />

      {telemetryHint}

      {!apiConfigured ? null : telemetry.loading && !telemetry.health ? (
        <LoadingState label="Sincronizando telemetria…" />
      ) : null}

      {!apiConfigured ? null : telemetry.error ? <ErrorNotice message={telemetry.error} title="Telemetria" /> : null}

      {!apiConfigured ? null : (
        <>
          <RuntimeStatusSection health={telemetry.health} runtimeSignals={telemetry.runtimeSignals} />
          <StrategyStateSection strategyState={telemetry.strategyState} />
          <MilestoneStateSection milestones={telemetry.milestones} prSummaries={telemetry.prSummaries} />
          <ExecutionSignalsSection runtimeSignals={telemetry.runtimeSignals} swarmLog={telemetry.swarmLog} />
          <ObservabilitySummarySection
            canRequest={observabilityCanRequest}
            error={observabilityError}
            loading={observabilityLoading}
            snapshot={observabilitySnapshot}
          />
        </>
      )}

      <section className="cognitive-future-grid" aria-label="Future cognitive modules">
        <FutureModuleCard
          description="Awaiting a stable public contract to expose orchestrator goals safely to the browser."
          title="Goal model"
        />
        <FutureModuleCard
          description="Awaiting public runtime read models for route simulation without leaking internal JSON."
          title="Simulation paths"
        />
        <FutureModuleCard
          description="Awaiting versioned metrics API; evolution proposals stay server-side today."
          title="Evolution metrics"
        />
        <FutureModuleCard
          description="OIL and memory envelopes are not on current HTTP routes; UI will map adapters when available."
          title="Memory context"
        />
      </section>
    </div>
  )
}
