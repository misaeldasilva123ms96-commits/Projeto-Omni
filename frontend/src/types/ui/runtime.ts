/**
 * Condensed runtime / dependency status for dashboard and status surfaces.
 *
 * **Minimum UI contract** (stable across refactors): `rustService`, `runtimeMode`,
 * `pythonStatus`, `nodeStatus`, optional `timestampMs` — all derived from `GET /health`.
 * Extra fields mirror the current `HealthResponse` envelope for panels that need them.
 */
export type UiRuntimeStatus = {
  overallStatus: string
  rustService: string
  runtimeMode: string
  sessionVersion: number
  pythonStatus: string
  pythonObservable: boolean
  nodeStatus: string
  nodeObservable: boolean
  timestampMs?: number
}
