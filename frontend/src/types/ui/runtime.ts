/**
 * Condensed runtime / dependency status for dashboard and status surfaces.
 *
 * **Preferred public source**: `GET /api/v1/status` → `publicStatusV1ToUiRuntimeStatus`.
 * **Public telemetry summaries**: see `types/ui/telemetry.ts` and `docs/frontend/telemetry-migration-status.md`.
 * **`GET /health`**: richer Python/Node envelopes (`observable`, paths); use where internal detail is required.
 * **Minimum UI contract**: `rustService`, `runtimeMode`, `pythonStatus`, `nodeStatus`, `sessionVersion`, optional `timestampMs`.
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
