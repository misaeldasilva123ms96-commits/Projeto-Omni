# Public chat adoption — `/api/v1/chat` (Phase 12)

**Scope:** How the Omni frontend prefers the versioned chat endpoint while keeping legacy `POST /chat` as a compatibility fallback.  
**Code:** `frontend/src/lib/api/chat.ts`, `frontend/src/lib/api/adapters.ts`, `frontend/src/types.ts`, `frontend/src/types/ui/chat.ts`, `frontend/src/pages/ChatPage.tsx`, `frontend/src/components/status/StatusPanel.tsx`.  
**Backend contract:** [`docs/backend/public-chat-api.md`](../backend/public-chat-api.md).

---

## 1. Adoption strategy

1. **`sendOmniMessage`** tries **`POST /api/v1/chat`** first with the same `message` and optional `client_session_id`, plus a minimal `client_context: { source: "frontend" }` (additive on the wire).
2. On **success** (`2xx` + JSON body), the payload is normalized through **`parseWireChatPayload`** into `ChatApiResponse`, then **`chatApiResponseToUi`** into `UiChatResponse`.
3. **Explicit legacy mode:** set **`VITE_OMNI_CHAT_LEGACY_ONLY=true`** to skip v1 and call **`POST /chat`** only (rollback / older proxies).

---

## 2. Fallback behavior

If the v1 request returns **404**, **405**, or **501** (route not deployed / not allowed / not implemented), the client **automatically retries once** against **`POST /chat`** with the same body shape as before Phase 12 (`message` + optional `client_session_id` only).

Other HTTP errors (e.g. **400**, **500**) are **not** auto-fallen-back: they surface as chat errors so misconfiguration or server faults stay visible.

Network failures and timeouts still follow the **existing retry loop** in `ChatPage` (`sendWithRetry`); each attempt re-evaluates v1 → fallback.

---

## 3. Metadata model

| Field | Source | Meaning |
| ----- | ------ | ------- |
| **`runtimeSessionVersion`** (`runtime_session_version` on wire) | Both endpoints when Rust sends it | Rust **runtime epoch** — correlates with `/api/v1/status` / `/health`; not a conversation id. |
| **`conversationId`** (`conversation_id` on wire) | Either endpoint when Python returns a truthful id | **Server-side correlation** for the cognitive layer; omitted when absent. |
| **`chatApiVersion`** (`api_version` on wire) | Present on successful **`/api/v1/chat`** responses | Contract version marker (`"1"` today). |
| **`sessionId` in `RuntimeMetadata`** | Adapter maps from wire `session_id` | **Adapter / subprocess label** (e.g. `python-session`); **not** the UI-owned session key. The UI conversation id remains the React `sessionId` state and `client_session_id` on the request. |

---

## 4. Current semantics (three identifiers)

| Concept | Owned by | Used for |
| ------- | -------- | -------- |
| **UI session id** | Frontend (`sessao-…`, `localStorage`, Supabase `external_session_id`) | UX continuity, sidebar, sync; sent as **`client_session_id`**. |
| **`conversation_id` (optional)** | Backend / orchestrator when emitted | Low-noise correlation in status panel and synced metadata; **never** shown as the primary “session”. |
| **`runtime_session_version` / epoch** | Rust process | Aligns chat turns with public status / health; **not** a human conversation id. |

---

## 5. Next migration opportunities

- Drop **`VITE_OMNI_CHAT_LEGACY_ONLY`** once all deployed APIs guarantee `/api/v1/chat`.
- Remove the **404/405/501 fallback branch** when legacy `/chat` is retired (coordinate with backend deprecation policy).
- Optionally collapse **`ChatApiResponse`** / wire types once only v1 remains.
- If product wants, move **`session_id`** display out of “session” wording in the UI to “adapter / fonte” only, to reduce confusion with UI session.

---

## 6. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 12 | Prefer `/api/v1/chat`, conditional fallback to `/chat`, `conversation_id` + `api_version` in adapters and status panel. |
