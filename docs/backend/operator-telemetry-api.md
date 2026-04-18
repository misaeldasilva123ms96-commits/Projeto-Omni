# Operator telemetry API (Phase 13)

**Scope:** Authenticated, versioned read endpoints for **operator-grade** telemetry — richer than public `/api/v1/*/summary` routes, **redacted** compared to raw `/internal/*`.  
**Implementation:** `backend/rust/src/main.rs` (routes under `/api/v1/operator/*`, `operator_redact_json`, `fusion_latest_checkpoint`).  
**Auth:** Same Supabase JWT middleware as `/api/observability/*` and `/api/control/*` (`require_supabase_auth` in `observability_auth.rs`).  
**Related:** [`public-api-roadmap.md`](public-api-roadmap.md), [`public-telemetry-contracts.md`](public-telemetry-contracts.md).

---

## 1. Purpose — three layers

| Layer | Audience | Auth | Content |
| ----- | -------- | ---- | ------- |
| **Public product telemetry** | Browser / product UI | None | Counts, short previews, no paths (`/api/v1/status`, `/api/v1/*/summary`, `/api/v1/chat`). |
| **Operator telemetry (this doc)** | Signed-in operators / internal dashboards | **Supabase JWT** (Bearer) | Bounded JSON derived from the same files as `/internal/*`, passed through **redaction** (paths, secrets, depth/array limits). |
| **Internal-only routes** | Same network as API; **no JWT today** | None on the route | Full `Value` payloads as implemented historically (`/internal/*`). **Unchanged** in Phase 13. |

Operator routes exist so the **frontend can migrate** off unconditional `/internal/*` fetches toward **JWT-gated** reads without exposing those shapes on the public internet.

---

## 2. Implemented authenticated endpoints

All require:

- Header: `Authorization: Bearer <Supabase access_token>`
- Env: same as observability — `SUPABASE_JWT_SECRET`, `SUPABASE_URL` (or `VITE_SUPABASE_URL`) for issuer validation.

### `GET /api/v1/operator/runtime/signals`

| | |
| --- | --- |
| **Source** | Same files as `GET /internal/runtime-signals`: `.logs/fusion-runtime/execution-audit.jsonl` (last 20 lines), `run-summaries.jsonl` (latest line). |
| **Response** | `api_version`, `status`, `timestamp_ms`, `recent_signal_sample_size` (20), `recent_signals` (redacted array), `recent_mode_transitions` (subset of audit lines with `event_type == runtime.mode.transition`, redacted), `latest_run_summary` (redacted object). |
| **Redactions** | Per-value `operator_redact_json`: strip sensitive keys (`password`, `api_key`, `access_token`, …), replace obvious filesystem paths in strings, blank `env` objects, cap recursion depth, cap array length and string length. |

### `GET /api/v1/operator/strategy/changes`

| | |
| --- | --- |
| **Source** | `brain/evolution/strategy_log.json` → `changes` array (same family as `/internal/strategy-state`); `strategy_state.json` read **only** for scalar `version`. |
| **Response** | `api_version`, `status`, `timestamp_ms`, `strategy_version`, `recent_changes` (up to **12** newest entries, each redacted). **Does not** return the full `strategy_state` rules blob. |
| **Redactions** | Same `operator_redact_json` on each change entry. |

### `GET /api/v1/operator/milestones`

| | |
| --- | --- |
| **Source** | Same checkpoint resolution as `GET /internal/milestones`: latest `run-summaries.jsonl` → `checkpoints/<run_id>.json` → `engineering_data`. |
| **Response** | `api_version`, `status`, `timestamp_ms`, `latest_run_id`, `checkpoint_status` (small scalar object: status, next_step_index, total_actions), `milestone_state` (redacted), `patch_sets` (at most **5** entries, redacted), `patch_sets_total`, `patch_sets_returned`, `execution_state` (redacted). |
| **Redactions** | `patch_sets` truncated; nested structures passed through `operator_redact_json`. |

---

## 3. Deferred endpoints (grounded, not implemented here)

| Candidate | Reason deferred |
| --------- | ---------------- |
| `GET /api/v1/operator/runtime/signals/paged` | Needs cursor/query contract + product review. |
| `GET /api/v1/operator/swarm/events` | Swarm log events are unstructured `Value` — schema + redaction policy TBD (see roadmap). |
| `GET /api/v1/operator/pr-summaries` | PR / merge payloads need operator UX review; can wrap existing `run-summaries` projection with redaction in a follow-up. |
| `GET /api/v1/operator/strategy/state` | Full `strategy_state` remains high-risk; public summary stays on `/api/v1/strategy/summary`. |

---

## 4. Frontend migration opportunities

| Current internal usage | Suggested migration |
| ----------------------- | -------------------- |
| `GET /internal/runtime-signals` (dashboard / cognitive rail) | Prefer `GET /api/v1/operator/runtime/signals` when JWT available; keep public **summary** for unauthenticated headline widgets. |
| `GET /internal/strategy-state` (recent changes only) | Prefer `GET /api/v1/operator/strategy/changes` for change list; keep `/api/v1/strategy/summary` for version/weight headline. |
| `GET /internal/milestones` | Prefer `GET /api/v1/operator/milestones` when detail is needed with auth; keep `/api/v1/milestones/summary` for counts. |

`/internal/*` remains for **backward compatibility** until the frontend switches callers.

---

## 5. Security notes

1. **JWT:** Validation matches observability — HS256, issuer `SUPABASE_URL/auth/v1`, expiry enforced.
2. **No RBAC inside Omni today:** any valid Supabase user token that passes validation can call operator routes. Finer roles (admin vs viewer) are a **future** concern.
3. **Redaction is best-effort:** operator payloads are safer than raw internal dumps but not a substitute for network policy; do not expose the Rust API unfirewalled to the public internet without an edge gateway.
4. **Logs:** HTTP logs use `sanitize_uri_for_logs` for observability-style paths; operator routes use standard Bearer handling (no token in query).

---

## 6. Changelog

| Phase | Change |
| ----- | ------ |
| Phase 13 | `/api/v1/operator/runtime/signals`, `/api/v1/operator/strategy/changes`, `/api/v1/operator/milestones` + `operator_redact_json` + docs. |
