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
| `client_session_id` | No | string | Opaque UI id when client sent one on `/chat`; omitted when absent. |

Rust always sends the three required keys; `client_session_id` only when normalized id is present.

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

## 5. Future return path (not implemented)

When the orchestrator can emit a **truthful** server-issued conversation id (e.g. from `SessionStore`), Python stdout JSON could add an optional field; Rust would map it into `ChatResponse` **additively** without removing `session_id` / `client_session_id` / `runtime_session_version`. Until then, `session_id` in HTTP responses remains the existing placeholder strings where applicable.

---

## 6. Relationship to future `/api/v1/chat`

The same stdin (or equivalent) envelope can back a versioned HTTP handler: request body would mirror the stdin object plus versioning (`api_version`), while the Python entry keeps a single parsing path (`resolve_entry_message` / `apply_bridge_env`).

---

## 7. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 7 | Optional `client_session_id` on HTTP `/chat` request/response echo. |
| Phase 10 | JSON stdin to Python + env bridge + `_session_id()` precedence rules. |
