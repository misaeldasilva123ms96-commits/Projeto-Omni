# Omni chat session contract

**Scope:** `POST /chat` and `POST /api/v1/chat` on the Rust HTTP API (`backend/rust/src/main.rs`), the browser client, and session semantics.  
**Related:** [`public-chat-api.md`](public-chat-api.md), [`public-api-roadmap.md`](public-api-roadmap.md), [`python-bridge-contract.md`](python-bridge-contract.md), [`../frontend/integration-matrix.md`](../frontend/integration-matrix.md).

---

## 1. Current reality

### Request path

1. Client sends `POST /chat` with `Content-Type: application/json`.
2. Rust deserializes into `ChatRequest` (see `main.rs`).
3. `message` is trimmed; empty messages return `400` (`InvalidRequest`).
4. Rust invokes Python as `python <entry> <message>` **and** writes a **JSON envelope on stdin** (Phase 10): `message`, `runtime_session_version`, `request_source`, optional `client_session_id` — see [`python-bridge-contract.md`](python-bridge-contract.md).
5. Python reads stdin when present, else falls back to argv-only message. Stdout is parsed for assistant text (first non-empty string among JSON keys `response` \| `message` \| `text` \| `answer`, or a fallback string). **Phase 11:** optional **`conversation_id`** from Python JSON is merged into `ChatResponse` when truthfully present.

### Response path

1. Rust builds `ChatResponse` JSON for every outcome (success, timeout, stderr, empty stdout, mock).
2. `session_id` is a **fixed placeholder** per path (`python-session`, `mock-session`) — not derived from the client and not from Python orchestrator storage.
3. `runtime_session_version` is copied from `AppState` — the same epoch surfaced on `GET /health` and `GET /api/v1/status`.
4. Optional **`client_session_id`** (Phase 7): when the client sends it, Rust **echoes** it on the response for correlation and logging; Rust also forwards it on the **stdin bridge** when present (Phase 10).

---

## 2. Session identity taxonomy

| Identifier | Where it lives | Meaning |
| ---------- | -------------- | ------- |
| **Client session id** (`client_session_id` on wire) | Optional on `POST /chat` request; echoed on response when present | Opaque string owned by the product UI (e.g. `sessao-…` in the React app). Used for UX continuity, `localStorage`, and Supabase sync. **Not** validated as a server-side session store key today. |
| **Backend `session_id` (response)** | `ChatResponse.session_id` | **Transport / adapter label**, not the UI conversation id. Values today: `python-session` or `mock-session`. Future: may map to orchestrator session when Python returns one. |
| **`runtime_session_version`** | `ChatResponse`, `/health`, `/api/v1/status` | **Rust runtime epoch** — monotonic-ish counter for process/runtime restarts. Use for correlating a chat turn with a health snapshot; **do not** use as end-user session identity. |
| **Optional `conversation_id` (response)** | Python stdout JSON → Rust `ChatResponse` | **Server- or orchestrator-backed id** when the cognitive layer emitted one; omitted when unknown. Distinct from placeholder `session_id` and from client-owned `client_session_id`. |
| **Trace / request id** | Not on the JSON contract | May appear in server logs (`tracing`) or reverse-proxy headers; not part of the stable chat envelope yet. |

---

## 3. Current mismatches

| Topic | Issue |
| ----- | ----- |
| **Placeholder `session_id`** | Clients may assume `session_id` is their conversation id; it is not. |
| **Python bridge** | **Phase 10:** stdin JSON + env (`OMNI_BRIDGE_*`) propagates client id and runtime epoch; orchestrator HTTP response still does not return a distinct server conversation id. |
| **Orchestrator store** | Optional **`conversation_id`** is merged when the Python sanitization path surfaces a real id from structured orchestrator output; otherwise omitted. |
| **Epoch vs session** | `runtime_session_version` answers “which Rust runtime generation answered?” not “which human conversation?”. |

---

## 4. Safe near-term contract (implemented / supported)

### Request (`ChatRequest`)

| Field | Required | Notes |
| ----- | -------- | ----- |
| `message` | Yes | Non-empty after trim. |
| `client_session_id` | No | Opaque string; trimmed; empty treated as absent; **max 256 UTF-8 scalar characters** (truncated server-side if longer). Forwarded on the **Python stdin JSON bridge** when present (Phase 10). |

Clients sending only `{ "message": "..." }` remain fully supported.

### Response (`ChatResponse`)

| Field | Notes |
| ----- | ----- |
| `response` | Assistant text. |
| `session_id` | Placeholder or future orchestrator id — **see §2; do not treat as client session.** |
| `runtime_session_version` | Rust epoch. |
| `client_session_id` | **Omitted** when the client did not send one; **echoed** when sent — round-trip correlation only. |
| `source`, `matched_commands`, `matched_tools`, `stop_reason`, `usage` | As today. |
| `conversation_id` | **Omitted** unless Python stdout contained a truthful orchestrator/server id (Phase 11). |

### `POST /api/v1/chat` (Phase 11)

Same `ChatResponse` field semantics as `/chat`, wrapped with **`api_version`: `"1"`** on the JSON body. Optional request **`client_context`** is forwarded on the stdin bridge when non-empty. Full wire contract: [`public-chat-api.md`](public-chat-api.md).

---

## 5. Versioned public envelope (`/api/v1/chat` — implemented)

| Principle | Detail |
| --------- | ------ |
| **Compatibility** | `/chat` remains the legacy entry; `/api/v1/chat` wraps the same subprocess with an explicit **`api_version`** on the response. |
| **Session semantics** | `client_session_id` (optional), `conversation_id` (optional, truthful only), `runtime_session_version` (epoch), placeholder `session_id` unchanged for adapter labeling. |
| **OIL** | Not on this HTTP surface. |
| **Migration** | Frontend adopts v1 when ready; old clients keep `/chat`. |

---

## 6. Frontend migration notes

1. **Source of truth for UX session** remains the value the UI generates and persists (`sessionId` in `ChatPage`); optionally send the same value as `client_session_id` on `POST /chat` for server logs and echo verification.
2. **Prefer** `runtime_session_version` + `/api/v1/status` for runtime correlation (already in Phase 6 UI).
3. **Do not** replace UI `sessionId` with `response.session_id`; it remains an adapter placeholder until Phase C maps a real orchestrator id there. Prefer optional **`conversation_id`** when the backend emits one.
4. **Optional** response field `client_session_id`: if present, it should match what was sent; mismatches indicate proxies or bugs worth logging client-side.

---

## 7. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 5 | `runtime_session_version` on `ChatResponse`. |
| Phase 7 | Optional `client_session_id` on request; optional echo on response; this document. |
| Phase 10 | Stdin JSON bridge to Python + env correlation; see [`python-bridge-contract.md`](python-bridge-contract.md). |
| Phase 11 | `POST /api/v1/chat`, response `api_version`, stdin `client_context`, optional `conversation_id` on `ChatResponse`; see [`public-chat-api.md`](public-chat-api.md). |
