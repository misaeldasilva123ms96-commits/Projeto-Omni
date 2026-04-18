# Omni chat session contract

**Scope:** `POST /chat` on the Rust HTTP API (`backend/rust/src/main.rs`), the browser client, and how this relates to a future versioned public chat API.  
**Related:** [`public-api-roadmap.md`](public-api-roadmap.md), [`../frontend/integration-matrix.md`](../frontend/integration-matrix.md).

---

## 1. Current reality

### Request path

1. Client sends `POST /chat` with `Content-Type: application/json`.
2. Rust deserializes into `ChatRequest` (see `main.rs`).
3. `message` is trimmed; empty messages return `400` (`InvalidRequest`).
4. Rust invokes Python via **positional argv only**: `python <entry> <message>` — no stdin JSON envelope today.
5. Python stdout is parsed for assistant text (first non-empty string among JSON keys `response` \| `message` \| `text` \| `answer`, or a fallback string). Structured fields from Python JSON are **not** merged into `ChatResponse` on the success path today.

### Response path

1. Rust builds `ChatResponse` JSON for every outcome (success, timeout, stderr, empty stdout, mock).
2. `session_id` is a **fixed placeholder** per path (`python-session`, `mock-session`) — not derived from the client and not from Python orchestrator storage.
3. `runtime_session_version` is copied from `AppState` — the same epoch surfaced on `GET /health` and `GET /api/v1/status`.
4. Optional **`client_session_id`** (Phase 7): when the client sends it, Rust **echoes** it on the response for correlation and logging; Python is still invoked with **message only**.

---

## 2. Session identity taxonomy

| Identifier | Where it lives | Meaning |
| ---------- | -------------- | ------- |
| **Client session id** (`client_session_id` on wire) | Optional on `POST /chat` request; echoed on response when present | Opaque string owned by the product UI (e.g. `sessao-…` in the React app). Used for UX continuity, `localStorage`, and Supabase sync. **Not** validated as a server-side session store key today. |
| **Backend `session_id` (response)** | `ChatResponse.session_id` | **Transport / adapter label**, not the UI conversation id. Values today: `python-session` or `mock-session`. Future: may map to orchestrator session when Python returns one. |
| **`runtime_session_version`** | `ChatResponse`, `/health`, `/api/v1/status` | **Rust runtime epoch** — monotonic-ish counter for process/runtime restarts. Use for correlating a chat turn with a health snapshot; **do not** use as end-user session identity. |
| **Trace / request id** | Not on the JSON contract | May appear in server logs (`tracing`) or reverse-proxy headers; not part of the stable chat envelope yet. |

---

## 3. Current mismatches

| Topic | Issue |
| ----- | ----- |
| **Placeholder `session_id`** | Clients may assume `session_id` is their conversation id; it is not. |
| **Python bridge** | No channel for `client_session_id` into Python without changing argv/stdin contract — intentionally deferred. |
| **Orchestrator store** | No HTTP-visible orchestrator session id is merged into responses today. |
| **Epoch vs session** | `runtime_session_version` answers “which Rust runtime generation answered?” not “which human conversation?”. |

---

## 4. Safe near-term contract (implemented / supported)

### Request (`ChatRequest`)

| Field | Required | Notes |
| ----- | -------- | ----- |
| `message` | Yes | Non-empty after trim. |
| `client_session_id` | No | Opaque string; trimmed; empty treated as absent; **max 256 UTF-8 scalar characters** (truncated server-side if longer). Ignored by the Python subprocess invocation until a future stdin/contract exists. |

Clients sending only `{ "message": "..." }` remain fully supported.

### Response (`ChatResponse`)

| Field | Notes |
| ----- | ----- |
| `response` | Assistant text. |
| `session_id` | Placeholder or future orchestrator id — **see §2; do not treat as client session.** |
| `runtime_session_version` | Rust epoch. |
| `client_session_id` | **Omitted** when the client did not send one; **echoed** when sent — round-trip correlation only. |
| `source`, `matched_commands`, `matched_tools`, `stop_reason`, `usage` | As today. |

---

## 5. Future public envelope (`/api/v1/chat` — planned)

Goals for a versioned public chat API **without** breaking `/chat`:

| Principle | Detail |
| --------- | ------ |
| **Compatibility** | `/chat` remains the legacy entry; `/api/v1/chat` may wrap the same subprocess with a stricter schema and versioning (`api_version` in body or path). |
| **Session semantics** | Explicit fields, e.g. `client_session_id` (optional), `conversation_id` (server-issued when store exists), `runtime_session_version` (epoch), distinct names to avoid conflation with placeholder `session_id`. |
| **OIL** | Not required on first `/api/v1/chat` revision; optional nested envelope only after security and payload review. |
| **Migration** | Frontend adopts v1 when ready; old clients keep `/chat`. |

Until Python accepts structured stdin or a side channel, **server-side** correlation is limited to: logging + echo + epoch.

---

## 6. Frontend migration notes

1. **Source of truth for UX session** remains the value the UI generates and persists (`sessionId` in `ChatPage`); optionally send the same value as `client_session_id` on `POST /chat` for server logs and echo verification.
2. **Prefer** `runtime_session_version` + `/api/v1/status` for runtime correlation (already in Phase 6 UI).
3. **Do not** replace UI `sessionId` with `response.session_id` until the backend documents a real orchestrator id (Phase C in roadmap).
4. **Optional** response field `client_session_id`: if present, it should match what was sent; mismatches indicate proxies or bugs worth logging client-side.

---

## 7. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 5 | `runtime_session_version` on `ChatResponse`. |
| Phase 7 | Optional `client_session_id` on request; optional echo on response; this document. |
