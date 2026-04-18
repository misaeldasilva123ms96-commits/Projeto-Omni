# Rust ↔ Python chat bridge contract (Phase 10)

**Scope:** `POST /chat` → `call_python` in `backend/rust/src/main.rs` → Python entry (`backend/python/main.py` and `backend/python/brain/runtime/main.py`).  
**Related:** [`chat-session-contract.md`](chat-session-contract.md).

---

## 1. Current bridge behavior (after Phase 10)

| Step | Behaviour |
| ---- | --------- |
| Rust | Builds JSON (see §2), writes it to the subprocess **stdin**, closes stdin. Still passes **`argv[1]` = user message** for backward compatibility. |
| Python | Reads optional stdin JSON via `brain.runtime.bridge_stdin`. **Message** is taken from JSON `message` when present and non-empty; otherwise **`sys.argv[1]`** (legacy). |
| Env | Optional correlation: `OMNI_BRIDGE_CLIENT_SESSION_ID`, `OMNI_BRIDGE_RUNTIME_SESSION_VERSION`, `OMNI_BRIDGE_REQUEST_SOURCE` (see §4). |
| Response | Python prints one JSON object on stdout (unchanged). Rust parses assistant text as before. **`ChatResponse` JSON fields are unchanged** (no new server `session_id` semantics in this phase). |

---

## 2. Structured stdin payload

**Transport:** one UTF-8 JSON object on **stdin** (no trailing junk). Max practical size enforced in Python reader (`512_000` bytes).

| Field | Required | Type | Notes |
| ----- | -------- | ---- | ----- |
| `message` | Yes (when using stdin contract) | string | Same trimmed user text as `argv[1]`. |
| `runtime_session_version` | Yes | number | Rust `AppState.runtime_session_version` (u32). |
| `request_source` | Yes | string | Constant `"rust_boundary"`. |
| `client_session_id` | No | string | Opaque UI id when the HTTP client sent one on `/chat` or `/api/v1/chat`; omitted when absent. |
| `client_context` | No | object | Optional hints from `POST /api/v1/chat` only (e.g. `{ "source": "frontend" }`); omitted when absent or empty. Ignored by older Rust binaries. |

Rust always sends the three required keys; `client_session_id` only when normalized id is present; `client_context` only when non-empty (Phase 11).

---

## 3. Backward compatibility

| Scenario | Outcome |
| -------- | ------- |
| Old Rust binary (argv only, no stdin JSON) | Python stdin empty → `resolve_entry_message` uses **`argv[1]`**; bridge env vars not set. |
| stdin unreadable / invalid JSON | Treated as empty bridge; message from **argv**. |
| `message` missing in JSON but argv set | **argv** supplies message. |
| `AI_SESSION_ID` set in environment | **`_session_id()`** keeps operator override; bridge client id ignored for session key (see §4). |

---

## 4. Session propagation model

1. **Browser** → optional `client_session_id` on `POST /chat` (Phase 7).  
2. **Rust** → normalizes, includes in stdin JSON when present.  
3. **Python `apply_bridge_env`** → sets `OMNI_BRIDGE_CLIENT_SESSION_ID` (and related env keys) before `BrainOrchestrator.run`.  
4. **`BrainOrchestrator._session_id()`** → `AI_SESSION_ID` if set; else **`OMNI_BRIDGE_CLIENT_SESSION_ID`** (truncated to 512 chars); else default `python-session`.

This is **correlation / transcript partitioning** using the client-owned id when the operator has not forced `AI_SESSION_ID`. It is **not** a cryptographic server session guarantee.

---

## 5. Optional conversation id return path (Phase 11)

When the orchestrator (or structured bridge) supplies **`server_conversation_id`** or **`conversation_id`** on the object that becomes user-visible JSON, Python may emit a canonical **`conversation_id`** on stdout (sanitized, never invented). Rust parses stdout JSON and merges **`conversation_id`** into `ChatResponse` **additively**. If absent, the HTTP field is omitted. Placeholder `session_id` strings (`python-session`, `mock-session`) remain unchanged until a later phase maps a real orchestrator id into `session_id`.

---

## 6. Relationship to `POST /api/v1/chat`

The same stdin envelope backs **`POST /api/v1/chat`**: the HTTP handler adds optional `client_context` to stdin JSON; the Python entry keeps a single parsing path (`resolve_entry_message` / `apply_bridge_env`). HTTP versioning uses `api_version` on the **response** body — see [`public-chat-api.md`](public-chat-api.md).

---

## 7. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 7 | Optional `client_session_id` on HTTP `/chat` request/response echo. |
| Phase 10 | JSON stdin to Python + env bridge + `_session_id()` precedence rules. |
| Phase 11 | Optional `client_context` on stdin from `/api/v1/chat`; optional `conversation_id` on stdout → HTTP. |
