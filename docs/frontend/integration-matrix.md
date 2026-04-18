# Omni Frontend ↔ Backend Integration Matrix

**Scope:** React/Vite frontend (`frontend/`) ↔ Rust HTTP API (`backend/rust/src/main.rs` and related modules).  
**Sources of truth:** `frontend/src/lib/api.ts` (barrel), `frontend/src/lib/api/*`, `frontend/src/lib/api/adapters.ts`, `docs/frontend/compatibility-layer.md`, `docs/frontend/public-api-adoption.md`, `docs/backend/public-api-roadmap.md`, `frontend/src/pages/*`, `backend/rust/src/main.rs`, `backend/rust/src/observability.rs`, `backend/rust/src/observability_auth.rs`.  
**Not in scope:** Supabase-backed persistence in `frontend/src/lib/omniData.ts` (separate product surface; not Omni Rust routes).

---

## Compatibility matrix

| UI Module | Data Needed | Current Endpoint | Status | Adapter Needed | Future Target API | Priority | Risk |
| --------- | ----------- | ---------------- | ------ | -------------- | ----------------- | -------- | ---- |
| Chat — assistant text | Plain or JSON string body; JSON envelope with `response` / `message` / `text` / `answer` | `POST /chat` | ✅ AVAILABLE | Normalize client-side (`parseWireChatPayload` in `lib/api/adapters.ts`); Rust rebuilds `ChatResponse` from Python stdout text, not full Python JSON object | Optional: preserve full Python JSON through Rust for richer metadata | HIGH | LOW |
| Chat — client session correlation | Optional `client_session_id` in JSON body (UI `sessionId`) | `POST /chat` | ✅ AVAILABLE | `sendOmniMessage` forwards when `ChatClientContext.sessionId` set; Rust echoes after normalize (see `docs/backend/chat-session-contract.md`) | Pass through to Python stdin when orchestrator supports it | MEDIUM | LOW |
| Chat — `session_id` in response | Stable session id from runtime | `POST /chat` | ⚠️ PARTIAL | Yes — Rust returns fixed `session_id` (`python-session` / `mock-session`) from `call_python` / mock paths, not values parsed from Python stdout | Propagate orchestrator `session_id` through Python stdout JSON or side-channel | MEDIUM | MEDIUM |
| Chat — `matched_commands`, `matched_tools`, `usage`, `stop_reason` | Enriched assistant metadata | `POST /chat` | ⚠️ PARTIAL | Yes — Rust `call_python` sets these to empty / defaults; only mock mode sets sample `usage` | Return structured `ChatResponse` parsed from Python JSON when present | MEDIUM | MEDIUM |
| Chat — `runtime_session_version` | Rust runtime epoch (aligns with `/health` and `/api/v1/status`) | `POST /chat` | ✅ AVAILABLE | `parseWireChatPayload` / `chatApiResponseToUi` / `RuntimeMetadata` | Same field on any future `/api/v1/chat` envelope | LOW | LOW |
| Runtime status (Dashboard system health card, cognitive strip) | `status`, `runtime_mode`, `python_status`, `node_status`, `runtime_session_version`, `timestamp_ms` | `GET /api/v1/status` | ✅ AVAILABLE | `publicStatusV1ToUiRuntimeStatus` | Typed OpenAPI when stabilized | HIGH | LOW |
| Runtime status (full dependency detail) | Paths, `observable`, last errors | `GET /health` | ✅ AVAILABLE | `healthResponseToUiRuntimeStatus` when used | Same | MEDIUM | LOW |
| Public status (minimal wire) | `api_version`, `status`, `runtime_mode`, `rust_service`, `python_status`, `node_status`, `runtime_session_version`, `timestamp_ms` | `GET /api/v1/status` | ✅ AVAILABLE | `fetchPublicRuntimeStatusV1` + `PublicStatusResponseV1` | Harden + rate-limit if exposed broadly | MEDIUM | LOW |
| Runtime signals (recent audit lines, mode transitions, latest run summary) | `recent_signals`, `recent_mode_transitions`, `latest_run_summary` | `GET /internal/runtime-signals` | 🧪 INTERNAL ONLY | None — shape is `serde_json::Value` arrays/object; UI treats as `Record<string, unknown>[]` | Move behind authenticated `/api/runtime/signals` if exposed publicly | MEDIUM | MEDIUM |
| Swarm / multi-agent log (Dashboard) | `events`, `total_events` | `GET /internal/swarm-log` | 🧪 INTERNAL ONLY | None — reads JSONL into `Vec<Value>` | Same as above | MEDIUM | MEDIUM |
| Strategy / reasoning state (Dashboard) | `strategy_state`, `recent_changes` | `GET /internal/strategy-state` | 🧪 INTERNAL ONLY | None | Authenticated read model endpoint | MEDIUM | MEDIUM |
| Milestones / engineering checkpoint (Dashboard) | `milestone_state`, `patch_sets`, `checkpoint_status`, `execution_state`, `latest_run_id` | `GET /internal/milestones` | 🧪 INTERNAL ONLY | None | Authenticated endpoint; align field names with milestone manager over time | MEDIUM | MEDIUM |
| PR / run summaries (Dashboard) | `summaries[]` with `run_id`, `timestamp`, `pr_summary`, `merge_readiness` | `GET /internal/pr-summaries` | 🧪 INTERNAL ONLY | None | Authenticated endpoint | LOW | MEDIUM |
| Observability — goals, timeline, traces, simulations, memory panels | Full `ObservabilitySnapshot` | `GET /api/observability/snapshot` | 🔒 PROTECTED | Map CLI JSON to `ObservabilityApiResponse` (`status`, `snapshot`, optional `error`); TS types may omit newer snapshot keys added server-side | Typed OpenAPI + generated TS models kept in sync with `ObservabilityReader` | HIGH | MEDIUM |
| Observability — live refresh | SSE `snapshot` events with JSON payload | `GET /api/observability/stream?token=…` | 🔒 PROTECTED | Parse SSE; token via query (EventSource cannot set `Authorization` header) | Same pattern or cookie-based session acceptable to security review | HIGH | MEDIUM |
| Observability — specialist traces list (dedicated fetch) | `traces: TraceSnapshot[]` | `GET /api/observability/traces?limit=` | 🔒 PROTECTED | Optional — exported in `api.ts` but **no page calls it** today; panels use `snapshot.recent_traces` only | UI module consuming `traces` or remove dead client | LOW | LOW |
| Simulation UI (Observability) | `latest_simulation`, `recent_simulations`, episodes, semantic facts, procedural pattern | Same as observability snapshot | 🔒 PROTECTED | None beyond snapshot typing | Same snapshot contract | MEDIUM | LOW |
| Goals UI (Observability) | `goal`, `goal_history` | Same snapshot | 🔒 PROTECTED | None | Same | MEDIUM | LOW |
| Learning / evolution signals (Observability) | `recent_learning_signals`, `recent_evolution_proposals`, `pending_evolution_proposal_count` | Same snapshot | 🔒 PROTECTED | None; TS types use `Record<string, unknown>` for some arrays | Stronger typing when schema stabilizes | MEDIUM | LOW |
| Operator control — runs, pause, resume, approve | JSON control-plane payloads | `GET/POST /api/control/runs…` (see Rust router) | ❌ NOT AVAILABLE | New client module + auth headers (same Supabase JWT as observability) | Hardened `/api/control/*` with RBAC | MEDIUM | LOW |
| External “Kimi plan” or third-party plan APIs | Plan documents not defined in this repo | — | ❌ NOT AVAILABLE | N/A — out of repository | Product-specific integration layer (not Omni core HTTP) | LOW | LOW |
| OIL contracts (`OILRequest` / `OILResult`) | Structured cognitive I/O | — | ❌ NOT AVAILABLE | N/A — OIL is Python-internal along orchestrator paths, not serialized on these HTTP routes | Explicit `/api/oil/...` or embedded envelope in `/chat` **only after** backend design | HIGH | HIGH |

**Legend — Status**

- ✅ AVAILABLE — Endpoint exists; frontend uses it (or client helper exists and matches backend).
- ⚠️ PARTIAL — Endpoint exists but contract or wiring does not fully match UI intent.
- ❌ NOT AVAILABLE — No frontend consumption and/or no applicable HTTP surface in Rust for that need.
- 🔒 PROTECTED — Middleware `require_supabase_auth` (JWT Bearer or stream `token` query).
- 🧪 INTERNAL ONLY — Mounted on public router **without** auth middleware; name is “internal”, not a security boundary.

---

## Current architecture summary

1. **Base URL:** `VITE_OMNI_API_URL` (`frontend/src/lib/env.ts`) points to the Rust listener (default patterns described in frontend env docs).
2. **Unauthenticated JSON:** `GET /health`, `GET /api/v1/status`, `POST /chat`, `GET /internal/*` — browser calls with simple `fetch` (no Supabase header).
3. **Authenticated JSON / SSE:** `GET /api/observability/snapshot`, `GET /api/observability/traces`, `GET /api/observability/stream` — `Authorization: Bearer <Supabase access_token>` except SSE, which passes the same token as `?token=` (supported in `observability_auth.rs`).
4. **Observability implementation:** Rust spawns `python -m brain.runtime.observability.cli` (`observability.rs`); responses are generic `serde_json::Value` wrapped by CLI stdout shape consumed as typed JSON on the client.
5. **Chat implementation:** Rust spawns `python <entry> <message>` (positional argv only). Response text is parsed for first matching key among `response` / `message` / `text` / `answer`; structured fields on `ChatResponse` are largely **not** sourced from Python JSON today.

---

## Critical gaps

| Gap | Evidence |
| --- | --- |
| **No OIL over HTTP** | OIL types live under Python `brain/runtime/language/`; Rust `/chat` does not expose `OILRequest` / `OILResult` envelopes. |
| **Chat metadata not forwarded** | `ChatRequest` in `main.rs` is `{ message }` only; UI session hints are not on the wire (see `lib/api/chat.ts` + compatibility-layer doc). |
| **Session identity mismatch** | UI generates its own `sessionId` (`ChatPage.tsx`); Rust returns static `session_id` for subprocess path — not orchestrator session store. **`runtime_session_version` on `ChatResponse` helps correlate with `/api/v1/status` / `/health` but does not replace UI session.** |
| **Internal routes are unauthenticated** | `/internal/*` registered on the same public `Router` without `require_supabase_auth` — safe only behind network policy / private bind. |
| **Control plane API unused** | `/api/control/*` exists and is protected, but **no** `frontend/src` references; no operator UI. |
| **Observability TS model drift** | Python `ObservabilityReader` / `as_dict()` can add keys (e.g. newer runtime traces); `ObservabilitySnapshot` in TS may not list them — runtime still works, typing incomplete. |
| **Kimi / external plans** | No repository endpoint; any “plan import” is future product scope, not mapped here. |

---

## Immediate safe integrations

| Integration | Notes |
| ----------- | ----- |
| **Dashboard** | System health uses `GET /api/v1/status`; detail cards use `/internal/*`. Works when API URL points to a trusted Rust instance and logs exist under workspace `.logs/fusion-runtime/`. |
| **Chat text** | `POST /chat` with `{ "message": "..." }` is the supported minimal contract. |
| **Observability (authenticated)** | Snapshot + SSE stream once Supabase session + env (`SUPABASE_JWT_SECRET`, `SUPABASE_URL` / `VITE_SUPABASE_URL` on server) are configured — already implemented. |
| **Reuse `fetchObservabilityTraces`** | Client helper ready; can power a dedicated traces view without backend change. |

---

## Dangerous assumptions to avoid

| Assumption | Reality |
| ---------- | ------- |
| “`/internal/*` is authenticated.” | **False** — no auth middleware on those routes in `main.rs`. |
| “`metadata` in `/chat` reaches Python.” | **False** — Rust struct ignores unknown fields; only `message` is used. |
| “`/chat` returns orchestrator `session_id`.” | **False** for typical subprocess path — hard-coded placeholder in Rust response builder. |
| “OIL is available to the frontend.” | **False** on current HTTP surface. |
| “`fetchObservabilityTraces` powers the Observability page.” | **False** — page uses snapshot + SSE only; traces helper is currently unused. |
| “`/api/control/*` is wired in the UI.” | **False** — no references in `frontend/src`. |

---

## Rust route inventory (reference)

**Public (no Supabase middleware on these paths)**

- `GET /health`
- `GET /api/v1/status`
- `POST /chat`
- `GET /internal/runtime-signals`
- `GET /internal/swarm-log`
- `GET /internal/strategy-state`
- `GET /internal/milestones`
- `GET /internal/pr-summaries`

**Protected (`require_supabase_auth`; Bearer or stream query token)**

- `GET /api/observability/snapshot`
- `GET /api/observability/stream`
- `GET /api/observability/traces`
- `GET /api/control/runs`
- `GET /api/control/runs/:run_id`
- `GET /api/control/runs/summary/resolution`
- `GET /api/control/runs/waiting-operator`
- `GET /api/control/runs/with-rollback`
- `POST /api/control/runs/:run_id/pause`
- `POST /api/control/runs/:run_id/resume`
- `POST /api/control/runs/:run_id/approve`

*(Duplicate definitions in `run_control.rs` tests mirror production router shapes; production routes are merged in `main.rs`.)*

---

## Document control

- **Version:** Phase 1 matrix — aligns with repository state at authoring time.  
- **Update rule:** Any new Rust route or frontend API module **must** update this file in the same change set.  
- **Owners:** Principal engineer + frontend lead for Phase 2+ UI work.
