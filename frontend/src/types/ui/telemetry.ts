/**
 * UI-normalized public telemetry summaries (`/api/v1/*/summary`).
 * Populated via adapters from wire types in `types.ts`.
 */

export type UiRuntimeSignalsSummary = {
  apiVersion: string
  status: string
  recentSignalSampleSize: number
  recentSignalCount: number
  recentModeTransitionCount: number
  latestRunId: string
  latestPlanKind: string
  latestRunMessagePreview: string
  timestampMs: number
}

export type UiMilestonesSummary = {
  apiVersion: string
  status: string
  latestRunId: string
  completedMilestoneCount: number
  blockedMilestoneCount: number
  patchSetCount: number
  checkpointStatus: string
  timestampMs: number
}

export type UiStrategySummary = {
  apiVersion: string
  status: string
  strategyVersion: number
  recentChangeLogCount: number
  createPlanWeight: number | null
  timestampMs: number
}
