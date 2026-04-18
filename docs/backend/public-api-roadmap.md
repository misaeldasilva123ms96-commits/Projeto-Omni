# Omni Public API Roadmap (Phase 5)

**Scope:** Classify the current Rust HTTP boundary, document **session semantics**, define a **versioned public path** (`/api/v1/*`), and plan migration off `/internal/*` **without** inventing goals/simulation/evolution payloads or exposing OIL prematurely.  
**Implementation touchpoints:** `backend/rust/src/main.rs`, `backend/rust/src/observability*.rs`, `backend/rust/src/run_control.rs`. **Phase 13:** authenticated operator telemetry under `/api/v1/operator/*` (see [`operator-telemetry-api.md`](operator-telemetry-api.md)).

---

## 1. Current route inventory

| Route | Method | Class | Auth today | Consumed by |
| ----- | ------ | ----- | ---------- | ------------- |
| `/health` | GET | **Public** | None | Frontend dashboard, chat cognitive rail, operators |
| `/api/v1/status` | GET | **Public (v1)** | None | New stable surface; subset of `/health` (no paths) |
| `/api/v1/runtime/signals/summary` | GET | **Public (v1)** | None | Reduced runtime telemetry (Phase 8); frontend may adopt next |
| `/api/v1/milestones/summary` | GET | **Public (v1)** | None | Reduced milestone checkpoint summary (Phase 8) |
| `/api/v1/strategy/summary` | GET | **Public (v1)** | None | Reduced strategy file summary (Phase 8) |
| `/chat` | POST | **Public (legacy user)** | None | Primary chat UI |
| `/api/v1/chat` | POST | **Public (v1)** | None | Versioned chat envelope; same subprocess as `/chat` (Phase 11) |
| `/internal/runtime-signals` | GET | **Internal** | None | Dashboard, chat cognitive rail |
| `/internal/swarm-log` | GET | **Internal** | None | Dashboard, chat cognitive rail |
| `/internal/strategy-state` | GET | **Internal** | None | Dashboard, chat cognitive rail |
| `/internal/milestones` | GET | **Internal** | None | Dashboard, chat cognitive rail |
| `/internal/pr-summaries` | GET | **Internal** | None | Dashboard, chat cognitive rail |
| `/api/observability/snapshot` | GET | **Protected** | Supabase JWT (Bearer) | Observability page, chat rail (if session) |
| `/api/observability/stream` | GET | **Protected** | JWT via `token` query | Observability page |
| `/api/observability/traces` | GET | **Protected** | Supabase JWT | Optional tooling |
| `/api/control/*` | GET/POST | **Protected** | Supabase JWT | Not wired in frontend today |
| `/api/v1/operator/runtime/signals` | GET | **Operator (v1)** | Supabase JWT (Bearer) | Redacted runtime audit + run summary (Phase 13) |
| `/api/v1/operator/strategy/changes` | GET | **Operator (v1)** | Supabase JWT | Recent strategy log entries only (Phase 13) |
| `/api/v1/operator/milestones` | GET | **Operator (v1)** | Supabase JWT | Bounded milestone checkpoint + redaction (Phase 13) |

**Legend**

- **Public** — reachable by any client that can hit the listener; not a security boundary by itself.
- **Internal** — path prefix is advisory; **no auth middleware** in Rust today — must be network-restricted.
- **Protected** — `require_supabase_auth` middleware (observability, control).
- **Operator (v1)** — same JWT middleware as **Protected**; JSON is **redacted** and bounded vs `/internal/*` (Phase 13).

**Legacy public:** `/chat` and `/health` predate `/api/v1/*`; they remain stable compatibility endpoints. **`POST /api/v1/chat`** is the versioned twin of `/chat` (additive contract; see [`public-chat-api.md`](public-chat-api.md)).

**Candidates for versioned public API:** `/health` (superseded in product copy by `/api/v1/status` for minimal fields), internal read-models (signals, milestones) **after** auth + schema hardening. **Phase 8:** first **summary** read models ship under `/api/v1/*/summary` (see [Public telemetry wave 1](#public-telemetry-wave-1) and [`public-telemetry-contracts.md`](public-telemetry-contracts.md)).

**Phase 13 — operator telemetry:** richer reads than public summaries, **JWT-required**, still **not** raw internal dumps — see [`operator-telemetry-api.md`](operator-telemetry-api.md). `/internal/*` stays for backward compatibility until the frontend migrates callers.

---

## 2. Session contract

### Current behavior

| Layer | Identifier | Semantics |
| ----- | ----------- | --------- |
| **Browser UI** | `sessionId` generated client-side (`sessao-…`) | Conversation key for `localStorage` + Supabase sync (`omniData`); may be sent as optional `client_session_id` on `POST /chat` (Phase 7). |
| **Rust `AppState`** | `runtime_session_version` | Monotonic-ish epoch from `bootstrap_runtime_session()`; same value exposed on `/health` and now on **`ChatResponse.runtime_session_version`**. |
| **`POST /chat` response** | `session_id` | **Placeholder** strings (`python-session`, `mock-session`) from subprocess / mock paths — **not** the UI session and not orchestrator store. |

### Mismatches

- UI should not treat `session_id` from chat as the UI conversation id; optional `client_session_id` on the wire is the explicit client-owned correlation field (see [`chat-session-contract.md`](chat-session-contract.md)).
- Orchestrator / Python session correlation uses the **stdin JSON bridge** (Phase 10+) plus env (`OMNI_BRIDGE_*`); a distinct **server-issued** id is optional via **`conversation_id`** when surfaced on stdout (Phase 11).

### Target model (incremental)

1. **Phase A (done in code):** Add **`runtime_session_version`** to every `ChatResponse` so the UI can correlate chat turns with the same epoch as `/health` / `GET /api/v1/status`.
2. **Phase B (Phase 7 — done):** `ChatRequest` accepts optional **`client_session_id`** (trimmed, max 256 chars); echoed on `ChatResponse` when present. **Phase 10:** forwarded on stdin JSON to Python when present.
3. **Phase C (planned):** When Python returns structured JSON including a real orchestrator session id, Rust may map it into `ChatResponse.session_id` (replacing placeholders).
4. **Phase 11 (done):** Optional truthful **`conversation_id`** on chat responses when Python stdout includes it; **`POST /api/v1/chat`** with `api_version` on the response body.

### Migration strategy

- Frontend continues to treat **UI session** as source of truth for UX; **`runtime_session_version`** is for **runtime epoch** alignment.
- Document until Phase C ships; avoid implying `session_id` is the UI conversation id.

---

## 3. Public API target endpoints

| Path | Method | Auth | Response / contract | Backing source | Maturity |
| ---- | ------ | ----- | --------------------- | ---------------- | -------- |
| `/api/v1/status` | GET | None | `PublicStatusResponseV1` (`api_version`, `status`, `runtime_mode`, `rust_service`, `python_status`, `node_status`, `runtime_session_version`, `timestamp_ms`) | Same logic as `/health` | **Implemented** |
| `/api/v1/runtime/signals/summary` | GET | None | `PublicRuntimeSignalsSummaryV1` — counts + latest run labels + truncated message preview | Same files as `/internal/runtime-signals` (bounded reads) | **Implemented** (Phase 8) |
| `/api/v1/milestones/summary` | GET | None | `PublicMilestonesSummaryV1` — counts + checkpoint status string | Same derivation as `/internal/milestones` | **Implemented** (Phase 8) |
| `/api/v1/strategy/summary` | GET | None | `PublicStrategySummaryV1` — version, change log size, optional `create_plan` weight | Same files as `/internal/strategy-state` | **Implemented** (Phase 8) |
| `/api/v1/chat` | POST | None | `api_version` + flattened `ChatResponse` (same fields as `/chat`, optional `conversation_id`) | Same `call_python` / Python entry as `/chat` | **Implemented** (Phase 11) |
| `/api/v1/operator/runtime/signals` | GET | Supabase JWT | Redacted audit lines + mode transitions + latest run summary | Same files as `/internal/runtime-signals` | **Implemented** (Phase 13) |
| `/api/v1/operator/strategy/changes` | GET | Supabase JWT | `strategy_version` + up to 12 redacted `changes` entries | `strategy_log.json` (+ version from `strategy_state.json`) | **Implemented** (Phase 13) |
| `/api/v1/operator/milestones` | GET | Supabase JWT | Checkpoint slice, capped `patch_sets`, redacted nested JSON | Same as `/internal/milestones` sources | **Implemented** (Phase 13) |
| `/api/v1/runtime/signals` | GET | TBD (likely JWT) | Paged, redacted audit events (full feed) | `.logs/fusion-runtime/*.jsonl` | **Planned** — superseded in part by operator route |
| `/api/v1/goals` | GET | TBD | — | Python goal store | **Blocked** — no safe HTTP mapping yet |
| `/api/v1/simulation/routes` | GET | TBD | — | Simulation reader | **Blocked** |
| `/api/v1/evolution/metrics` | GET | TBD | — | Evolution pipeline | **Blocked** |
| `/api/v1/oil/reason` | POST | TBD | OIL envelope | Python OIL | **Planned / high risk** — see §4 |

## Public telemetry wave 1

Additive **summary** endpoints (Phase 8) so product UIs can migrate off raw `/internal/*` **without** receiving full internal JSON. Full contracts and redaction rules: [`public-telemetry-contracts.md`](public-telemetry-contracts.md).

| Source internal | Public path | Safety / reduction | Maturity |
| ----------------- | ----------- | ------------------- | -------- |
| `GET /internal/runtime-signals` | `GET /api/v1/runtime/signals/summary` | No raw audit rows; bounded 20-line sample for counts only; latest run id / plan kind / 200-char message preview only. | **Implemented** |
| `GET /internal/milestones` | `GET /api/v1/milestones/summary` | No `milestone_state` blobs, patch bodies, or `execution_state`; scalar counts + checkpoint status string. | **Implemented** |
| `GET /internal/strategy-state` | `GET /api/v1/strategy/summary` | No full `strategy_state` or `recent_changes` entries; version + capped change-array length + single numeric weight. | **Implemented** |
| `GET /internal/swarm-log` | TBD (`/api/v1/swarm/summary` or similar) | Events are unstructured `Value` — need schema + redaction before any public path. | **Blocked** |
| `GET /internal/pr-summaries` | TBD | PR / merge payloads need product review before public exposure. | **Blocked** |

---

## 4. OIL exposure strategy

| Option | Recommendation |
| ------ | --------------- |
| Keep OIL Python-internal | **Default today** — matches repo reality. |
| Embed OIL in `/chat` | Only if product wants a single user entry; requires **versioned envelope** and size/latency governance. |
| Dedicated `/api/v1/oil/*` | Reasonable **future** path for power users; needs JWT, rate limits, schema (`OILRequest` / `OILResult`), and redaction policy **before** any implementation. |

**Decision:** Do **not** expose OIL on HTTP in this phase. `/chat` remains the default legacy conversational entrypoint; **`/api/v1/chat`** is an optional versioned alias with the same execution path.

---

## 5. Internal route migration plan

| Internal route | Risk | Migration |
| -------------- | ---- | --------- |
| `runtime-signals` | High cardinality JSON from logs | **Wave 1:** `GET /api/v1/runtime/signals/summary` for safe headline metrics; full feed still → future `/api/v1/runtime/signals` + auth |
| `swarm-log` | File-backed | Same pattern; no public summary yet |
| `strategy-state` | May contain sensitive tuning | **Wave 1:** `GET /api/v1/strategy/summary` exposes minimal scalars only; full blob stays internal until reviewed |
| `milestones` / `pr-summaries` | Engineering artifacts | **Wave 1:** `GET /api/v1/milestones/summary` for counts; PR summaries remain internal |

Frontend may keep calling `/internal/*`; **compatibility** is preserved. New `/api/v1/*/summary` routes are optional adopters.

---

## 6. Compatibility plan

1. **`/chat`** — Request body: required `message`; optional `client_session_id` (additive). Legacy `{ "message" }` only remains valid. Response includes `runtime_session_version`, optionally echoes `client_session_id`, and optionally **`conversation_id`** when truthfully available (Phase 11).
2. **`/api/v1/chat`** — Same response fields as `/chat` plus top-level **`api_version`: `"1"`**; optional request **`client_context`** (Phase 11). See [`public-chat-api.md`](public-chat-api.md).
3. **`/health`** — Unchanged JSON shape.
4. **`GET /api/v1/status`** — Additive; frontend can adopt in `lib/api` when ready without dropping `/health`.
5. **`GET /api/v1/*/summary` (telemetry wave 1)** — Additive public summaries; frontend unchanged in Phase 8.
6. **`/internal/*`** — Unchanged; no removal in this phase.

---

## 7. `/chat` request / response reference (grounded)

**Request (`ChatRequest`)**

- `message: string` (required, non-empty after trim)
- `client_session_id: string` (optional) — opaque UI id; normalized server-side; forwarded on the **stdin JSON bridge** to Python when present (Phase 10+)

**Response (`ChatResponse`)**

| Field | Meaning today |
| ----- | ------------- |
| `response` | Assistant text (extracted from Python stdout JSON keys `response` \| `message` \| `text` \| `answer`, or fallback string). |
| `session_id` | Placeholder correlation id from Rust paths (`python-session` / `mock-session`); **not** UI session. |
| `runtime_session_version` | Rust runtime epoch (matches `/health.runtime_session_version`). |
| `client_session_id` | **Omitted** unless the client sent one on the request — then echoed unchanged (after normalization). |
| `source` | `python-subprocess` \| `mock-env` \| etc. |
| `matched_commands`, `matched_tools` | Currently empty on subprocess success path; mock may differ. |
| `stop_reason` | e.g. `completed`, `mock_completed`. |
| `usage` | Optional JSON; mock supplies sample token counts. |
| `conversation_id` | **Omitted** unless Python emitted a truthful orchestrator/server id on stdout (Phase 11). |

Full semantics: [`chat-session-contract.md`](chat-session-contract.md), versioned wire: [`public-chat-api.md`](public-chat-api.md).

---

## 8. Related docs

- [`docs/backend/python-bridge-contract.md`](python-bridge-contract.md)
- [`docs/backend/public-chat-api.md`](public-chat-api.md)
- [`docs/backend/operator-telemetry-api.md`](operator-telemetry-api.md)
- [`docs/backend/chat-session-contract.md`](chat-session-contract.md)
- [`docs/backend/public-telemetry-contracts.md`](public-telemetry-contracts.md)
- [`docs/frontend/integration-matrix.md`](../frontend/integration-matrix.md)
- [`docs/frontend/compatibility-layer.md`](../frontend/compatibility-layer.md)
