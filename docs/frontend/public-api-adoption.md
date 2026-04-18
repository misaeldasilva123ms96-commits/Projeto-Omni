# Public API adoption (Phase 6)

This document tracks how the Omni frontend uses **stable public** HTTP surfaces versus **`/internal/*`** and legacy **`/health`**, after Phase 6 migration.

## 1. Newly adopted public API surfaces

| Surface | Method | Role in UI |
|--------|--------|------------|
| `/api/v1/status` | `GET` | **Preferred** product-safe runtime snapshot: Rust service label, runtime mode, Python/Node status strings, `runtime_session_version`, `timestamp_ms`. |

**Frontend usage**

- `frontend/src/lib/api/runtime.ts` — `fetchPublicRuntimeStatusV1()`.
- `frontend/src/hooks/useCognitiveTelemetry.ts` — first parallel fetch; state field `publicRuntime`.
- `frontend/src/pages/DashboardPage.tsx` — “System health” metric card and runtime epoch row.
- `frontend/src/components/status/RuntimeStatusSection.tsx` — live-labeled runtime rows (Rust, mode, Python, Node, runtime epoch).
- `frontend/src/pages/ChatPage.tsx` — maps `publicRuntime` → `UiRuntimeStatus` via `publicStatusV1ToUiRuntimeStatus` for the cognitive `StatusPanel` strip.
- `frontend/src/components/status/StatusPanel.tsx` — runtime section labeled as sourced from `/api/v1/status` (via the adapted `UiRuntimeStatus`).

**Adapters**

- `publicStatusV1ToUiRuntimeStatus` in `frontend/src/lib/api/adapters.ts` normalizes the public wire type into `UiRuntimeStatus`. The public payload does not include `observable` flags; `pythonObservable` is set to `true` and `nodeObservable` is inferred as `node_status === 'observable'` so existing UI shape stays stable without inventing new semantics.

## 2. Remaining internal dependencies

| Surface | Typical consumer | Why it remains |
|--------|------------------|----------------|
| `/internal/*` (runtime signals, swarm, strategy, milestones, PR summaries, etc.) | `DashboardPage`, `RuntimeStatusSection` (signals block), `StrategyStateSection`, `MilestoneStateSection`, `ExecutionSignalsSection`, `useCognitiveTelemetry` | No stable public replacement yet; richer read models and operator detail. |
| Supabase-backed observability | `useObservabilitySnapshot`, `ObservabilitySummarySection` | Auth-gated product surface; not part of the anonymous public status contract. |
| `GET /health` | `fetchHealth` in `frontend/src/lib/api/health.ts` (still exported) | **Retained** for callers that need full `HealthResponse` (paths, `observable`, errors). The main chat/dashboard status paths no longer depend on it for the default strip. |

**Source labeling**

- Cognitive copy and `DataScopeBadge` usage continue to distinguish **live/public** slices from **internal** telemetry.

## 3. Session / runtime correlation notes

- **`runtime_session_version` (Rust runtime epoch)** is **not** the UI chat session id. It is an opaque counter/version from the Rust service snapshot, aligned across:
  - `GET /api/v1/status` (`PublicStatusResponseV1.runtime_session_version`),
  - `GET /health` (`HealthResponse.runtime_session_version`),
  - `POST /chat` when the backend includes `runtime_session_version` on the JSON envelope.

- **Chat → UI**
  - Wire: `ChatApiResponse.runtime_session_version` (optional).
  - Optional **`client_session_id`**: UI sends local `sessionId` via `sendOmniMessage` when set; Rust echoes it when present. `parseWireChatPayload` preserves the wire field. Correlation only — not a server session store.
  - UI model: `UiChatResponse.runtimeSessionVersion` via `chatApiResponseToUi`.
  - Persisted assistant metadata: `RuntimeMetadata.runtimeSessionVersion` via `normalizeMetadata` on `ChatPage`.

- **Status strip**
  - `StatusPanel` shows **Epoch (Rust)** from `UiRuntimeStatus.sessionVersion` (public status adapter) and **Epoch (chat)** from the last message metadata when the last `/chat` response carried the field — useful to spot mismatch after restarts without claiming extra meaning.

## 4. Migration status

| Area | Status |
|------|--------|
| Public runtime status for dashboard + cognitive rails | **Migrated** to `GET /api/v1/status`. |
| Public telemetry summaries (signals / milestones / strategy) | **Migrated** for headline cards and cognitive summary blocks — see [`telemetry-migration-status.md`](telemetry-migration-status.md). |
| `/chat` | Same path; optional `client_session_id` echo + `runtime_session_version` in wire/UI metadata. |
| Internal telemetry blocks | **Still internal**; explicitly scoped in components. |
| `/health` | **Available**, not removed; default UI paths prefer `/api/v1/status`. |
| OIL / goals / simulation public APIs | **Not exposed**; future backend work. |

## 5. Related docs

- [`telemetry-migration-status.md`](telemetry-migration-status.md) — `/api/v1/*/summary` vs `/internal/*` on dashboard and cognitive rail (Phase 9).
- `docs/frontend/compatibility-layer.md` — adapter and wire vs UI boundaries.
- `docs/frontend/cognitive-panels.md` — panel composition and trust labeling.
