# Omni Frontend Compatibility Layer

**Scope:** How the React/Vite client talks to the current Rust HTTP surface without coupling product UI to unstable wire JSON.  
**Companion:** [`integration-matrix.md`](./integration-matrix.md) (endpoint inventory and risk notes).  
**Implementation:** `frontend/src/app/App.tsx` (shell routing), `frontend/src/features/*` (feature-facing entrypoints), `frontend/src/lib/api/*`, `frontend/src/lib/api/adapters.ts`, `frontend/src/types/ui/*`, `frontend/src/types/api/wire.ts`.

---

## 1. Purpose

The compatibility layer exists to:

- **Isolate** raw backend payloads behind small modules (`lib/api/chat.ts`, `runtime.ts`, etc.) and **adapters** (`adapters.ts`).
- **Normalize** responses into **UI-facing models** (`UiChatResponse`, `UiRuntimeStatus`, `UiObservabilitySnapshot`, …) so pages and hooks do not depend on snake_case fields or transport envelopes.
- **Document** what is public, protected, or internal-only today so future refactors (public `/api/v1/*`, OIL, cognitive modules) can swap implementations without rewriting the shell.

No new Rust routes were added for this phase; behavior matches the pre-refactor client.

---

## 2. Current raw contracts (what the frontend consumes)

| Concern | Method / path | Wire notes |
| ------- | ------------- | ---------- |
| Chat | `POST /chat` | Request body: `{ "message": string }` only. Response: JSON object or legacy string; parser accepts `response` / `message` keys (see `parseWireChatPayload`). |
| Health | `GET /health` | `HealthResponse` in `frontend/src/types.ts` (snake_case). |
| Dashboard telemetry | `GET /internal/*` | JSON blobs with `status` plus domain fields; many arrays are effectively `Record<string, unknown>[]` on the client. |
| Observability | `GET /api/observability/snapshot`, `GET /api/observability/traces`, SSE `GET /api/observability/stream?token=…` | Envelope: `{ status, snapshot?, error? }`. SSE sends the same envelope in `snapshot` events. Bearer JWT on snapshot/traces; stream uses query token (EventSource limitation). |

Raw TypeScript aliases for these shapes are grouped in `frontend/src/types/api/wire.ts`. Domain types still live in `frontend/src/types.ts` and `frontend/src/types/observability.ts` for incremental migration.

---

## 3. Adapter strategy

1. **Transport** (`lib/api/client.ts`, domain modules): timeouts, base URL, Supabase headers where required, `getJson` for simple GETs.
2. **Parse** (`parseWireChatPayload`): coerce string bodies and missing keys into `ChatApiResponse` (internal wire model).
3. **Map to UI** (`chatApiResponseToUi`, `healthResponseToUiRuntimeStatus`, `observabilityApiEnvelopeToUi`, `observabilityTracesResponseToUi`): produce camelCase / stable structures for components.
4. **Pages** consume UI models or existing **persistence** types (`RuntimeMetadata`) built from UI chat fields, not raw HTTP types where avoidable.

Observability snapshot mapping is currently **1:1** with the reader JSON (the UI type is an alias of `ObservabilitySnapshot`) so panels keep working; the adapter still gives a single place to add defaults or field renames later.

---

## 4. Protected vs internal vs public

| Class | Examples | Intended scope |
| ----- | -------- | -------------- |
| **Public (unauthenticated today)** | `GET /health`, `POST /chat`, `GET /internal/*` | Callable from any deployment that can reach the listener. **`/internal/*` is not a security boundary** — network policy must restrict it. |
| **Protected** | `GET /api/observability/*` | Requires Supabase JWT (header or stream query per Rust middleware). Suitable for operator-facing UI behind auth. |
| **Product-safe “public API”** | Future `/api/v1/*` | Not shipped in this repo phase; UI must not assume speculative routes. |

OIL and other Python-internal contracts are **not** exposed on these HTTP routes; see the integration matrix.

---

## 5. Migration path

1. **Runtime read models:** Move internal telemetry behind authenticated, versioned HTTP (`/api/runtime/...`) when the server supports it; keep `lib/api/runtime.ts` as the only import site for dashboard fetches, swapping URLs internally.
2. **Chat:** When Rust accepts structured context (e.g. real `session_id`), extend `ChatClientContext` and the POST body in **one** module (`lib/api/chat.ts`) and update `ChatApiResponse` / `UiChatResponse` mappings.
3. **OIL / cognitive UI:** Introduce explicit HTTP envelopes when backend design exists; adapters map OIL → UI modules without leaking Python field names.
4. **OpenAPI / generated models:** Replace `types/api/wire.ts` hand-exports with generated clients while preserving adapter outputs for the shell.

---

## 6. Behavioral notes (Phase 2)

- **`POST /chat`** sends only `{ message }`. Optional UI `sessionId` is passed to `sendOmniMessage` as **client-only** context (documented on `ChatClientContext`); it is **not** serialized until the backend contract supports it.
- **Session identity:** The UI continues to generate a local conversation id; Rust may still return a placeholder `session_id` on the subprocess path — alignment remains a backend follow-up (see integration matrix).

---

## 7. File map (quick reference)

| Area | Location |
| ---- | -------- |
| App shell / view routing | `frontend/src/app/App.tsx` |
| Feature entry barrels | `frontend/src/features/chat`, `runtime`, `observability`, `sessions` |
| HTTP client helpers | `frontend/src/lib/api/client.ts` |
| Domain calls | `frontend/src/lib/api/chat.ts`, `health.ts`, `runtime.ts`, `observability.ts` |
| Wire → UI | `frontend/src/lib/api/adapters.ts` |
| Barrel re-exports | `frontend/src/lib/api.ts` |
| UI models | `frontend/src/types/ui/*.ts` |
| Wire type barrel | `frontend/src/types/api/wire.ts` |
