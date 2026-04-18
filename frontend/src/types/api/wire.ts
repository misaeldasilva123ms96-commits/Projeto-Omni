/**
 * Canonical re-exports of **wire** (HTTP JSON) shapes used by `lib/api/*` and adapters.
 * UI code should prefer `types/ui/*` + adapter outputs where possible.
 *
 * Chat: `POST /api/v1/chat` returns the same flattened fields as `POST /chat` plus optional
 * `api_version` and `conversation_id` (see `docs/frontend/public-chat-adoption.md`).
 */
export type {
  ChatApiResponse,
  HealthResponse,
  MilestonesResponse,
  PrSummariesResponse,
  PublicMilestonesSummaryV1,
  PublicRuntimeSignalsSummaryV1,
  PublicStatusResponseV1,
  PublicStrategySummaryV1,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../../types.ts'

export type {
  ObservabilityApiResponse,
  ObservabilitySnapshot,
  ObservabilityTracesResponse,
} from '../observability'
