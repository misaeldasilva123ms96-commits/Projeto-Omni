# Operator telemetry adoption (Phase 14)

**Scope:** How the frontend prefers **`GET /api/v1/operator/*`** when a Supabase session exists, and falls back to **`/internal/*`** otherwise.  
**Code:** `frontend/src/lib/api/operator.ts`, `frontend/src/lib/api/runtime.ts` (`loadCognitiveTelemetryBundle`), `frontend/src/hooks/useCognitiveTelemetry.ts`, `frontend/src/pages/DashboardPage.tsx`, cognitive status sections.  
**Backend:** [`docs/backend/operator-telemetry-api.md`](../backend/operator-telemetry-api.md).

---

## 1. Adoption strategy

1. **`loadCognitiveTelemetryBundle()`** loads public summaries in parallel (unchanged): `/api/v1/status`, `/api/v1/runtime/signals/summary`, `/api/v1/milestones/summary`, `/api/v1/strategy/summary`.
2. For **richer** rows it calls:
   - `tryFetchOperatorRuntimeSignals()` → `/api/v1/operator/runtime/signals`
   - `tryFetchOperatorStrategyChanges()` → `/api/v1/operator/strategy/changes`
   - `tryFetchOperatorMilestones()` → `/api/v1/operator/milestones`  
   Each uses **`getSupabaseAuthHeaders()`** + **`getJsonWithAuth`**.
3. If any operator call fails (no session, expired JWT, 401/404/500, network), the helper returns **`null`** and the bundle loader uses the existing **`/internal/*`** fetch for that slice only.

Swarm log and PR summaries **still use `/internal/*` in the bundle loader** until a follow-up wires **`GET /api/v1/operator/swarm`** and **`GET /api/v1/operator/pr-digest`** (available on the API from Phase 15).

---

## 2. Fallback rules

| Condition | Behavior |
| --------- | -------- |
| No `access_token` from Supabase | Operator `tryFetch*` returns `null` immediately (catch on `getSupabaseAuthHeaders`). |
| Operator HTTP error | `tryFetch*` catches and returns `null`; **internal** fetch runs for that resource. |
| Mixed outcomes | Each of the three rich resources is independent: e.g. operator milestones + internal runtime signals if only one operator call succeeds. |

Public summaries **never** fall back to internal or operator — they stay on public v1 routes.

---

## 3. Source classes in UI

| `DataScopeBadge` variant | Meaning |
| ------------------------ | ------- |
| **live** | Public v1 summaries (`/api/v1/status`, `/api/v1/*/summary`). |
| **operator** | Redacted JWT operator projection (`/api/v1/operator/*`). |
| **internal** | Legacy unauthenticated internal route (`/internal/*`). |
| **protected** | Observability snapshot/stream (separate hook / page). |

Cognitive sections:

- **ExecutionSignalsSection** — runtime signals row uses **operator** or **internal**; swarm block stays **internal**.
- **StrategyStateSection** / **MilestoneStateSection** — detail header switches between **operator** and **internal** based on provenance.

---

## 4. Remaining internal dependencies

| Data | Why still internal |
| ---- | ------------------- |
| **Swarm log** | Backend **`/api/v1/operator/swarm`** exists (Phase 15); frontend bundle not switched yet. |
| **PR summaries** | Backend **`/api/v1/operator/pr-digest`** exists (Phase 15); frontend bundle not switched yet. |
| **Rich runtime / strategy / milestones** | Only when operator fetch returned `null` (no auth or error). |

---

## 5. Next migration opportunities

- Extend **`loadCognitiveTelemetryBundle`** to try **`/api/v1/operator/swarm`** and **`/api/v1/operator/pr-digest`** with the same try/`null`/internal pattern as runtime signals (Phase 15 backend is ready).
- **Drop `/internal/*` fetches** from the browser once all rich slices have operator (or public) replacements and proxies enforce JWT at the edge.
- Optional **env flag** to force internal-only (debug) mirroring `VITE_OMNI_CHAT_LEGACY_ONLY`.

---

## 6. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 14 | `loadCognitiveTelemetryBundle`, operator try/fetch helpers, UI provenance badges + copy. |
| Phase 15 (backend) | `GET /api/v1/operator/swarm`, `GET /api/v1/operator/pr-digest` — frontend adoption pending. |
