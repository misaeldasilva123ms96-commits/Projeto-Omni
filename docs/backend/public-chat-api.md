# Public chat API — `POST /api/v1/chat` (Phase 11)

**Scope:** Versioned public chat envelope, request/response contract, and how it relates to legacy `POST /chat`.  
**Implementation:** `backend/rust/src/main.rs` (`public_v1_chat`, `call_python`, `build_python_stdin_json`), Python stdout sanitization in `backend/python/main.py`.  
**Related:** [`chat-session-contract.md`](chat-session-contract.md), [`python-bridge-contract.md`](python-bridge-contract.md), [`public-api-roadmap.md`](public-api-roadmap.md).

---

## 1. Scope

`POST /api/v1/chat` exists to give product clients a **stable, explicitly versioned** HTTP contract (`api_version` in the JSON body) while **reusing the same Rust → Python subprocess path** as `POST /chat`. It does **not** replace `/chat`: legacy clients keep calling `/chat` unchanged.

**OIL** is not exposed on this endpoint; any internal mapping stays inside Python.

---

## 2. Request contract — `POST /api/v1/chat`

`Content-Type: application/json`

| Field | Required | Type | Notes |
| ----- | -------- | ---- | ----- |
| `message` | Yes | string | User text; empty after trim → `400`. |
| `client_session_id` | No | string | Same normalization as `/chat` (trim, drop empty, max 256 scalar chars); forwarded on the stdin bridge when present. |
| `client_context` | No | object | Optional product hints. Only safe, grounded keys are forwarded on stdin today (see [`python-bridge-contract.md`](python-bridge-contract.md)). |

**Example**

```json
{
  "message": "Olá",
  "client_session_id": "sessao-ui-abc",
  "client_context": {
    "source": "frontend"
  }
}
```

Clients may send only `{ "message": "..." }`.

---

## 3. Response contract

Top-level JSON object:

| Field | Type | Notes |
| ----- | ---- | ----- |
| `api_version` | string | Constant `"1"` for this document revision. |
| `response` | string | Assistant text (same extraction rules as `/chat`). |
| `session_id` | string | Legacy field: adapter placeholder (`python-session`, `mock-session`) until a future phase maps a real orchestrator id here. **Do not** treat as the UI conversation id. |
| `source` | string | e.g. `python-subprocess`, `mock-env`. |
| `runtime_session_version` | number | Rust runtime epoch (aligned with `/health` / `GET /api/v1/status`). |
| `client_session_id` | string | **Omitted** unless the request included one — then echoed after normalization. |
| `matched_commands` | string[] | As today; may be empty. |
| `matched_tools` | string[] | As today; may be empty. |
| `stop_reason` | string \| null | e.g. `completed`, `mock_completed`. |
| `usage` | object \| null | Optional token / usage JSON when supplied (e.g. mock path). |
| `conversation_id` | string | **Omitted** unless Python stdout JSON (after sanitization) contained a **truthful** orchestrator/server id — see §3.1. Never synthesized by Rust. |

All fields except `api_version` mirror the legacy `ChatResponse` shape so parsers can share logic.

### 3.1 Optional `conversation_id`

When the Python layer emits a structured object that includes `server_conversation_id` or `conversation_id` (non-empty, bounded, sanity-checked), the sanitizer may copy a single canonical **`conversation_id`** into stdout JSON. Rust merges that value **additively** into the HTTP response. If absent, the field is omitted (not `null`), to keep payloads small.

---

## 4. Legacy compatibility — `POST /chat`

- **Path:** `POST /chat` remains the primary legacy entrypoint.
- **Request:** `ChatRequest` — `message` (required), optional `client_session_id` only.
- **Response:** Same `ChatResponse` fields as today, plus optional `conversation_id` when truthfully available (additive JSON field).
- **Semantics:** No removed fields; existing clients that ignore unknown fields continue to work; clients that strictly validate JSON may need to allow optional `conversation_id` (standard forward-compatible practice).

---

## 5. Migration notes (frontend)

1. **No rush:** Keep calling `/chat` until product wants versioning or stricter schemas.
2. **When adopting v1:** Switch URL to `POST /api/v1/chat`, send the same `message` / `client_session_id`, optionally add `client_context.source`.
3. **Parse envelope:** Read `api_version` and the flattened chat fields from one object (no nested `data` wrapper by design).
4. **Session identity:** Continue to use UI-owned `client_session_id` for UX; treat `response.session_id` as legacy adapter metadata until documented otherwise; prefer optional `conversation_id` when present for server-acknowledged store keys.

---

## 6. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 11 | `POST /api/v1/chat`, `PublicChatResponseV1`, stdin `client_context`, optional `conversation_id` merge from Python stdout. |
