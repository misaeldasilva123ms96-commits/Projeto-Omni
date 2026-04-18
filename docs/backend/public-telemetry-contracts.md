# Public telemetry contracts (wave 1)

**Scope:** Versioned **GET** endpoints under `/api/v1/*` that expose **reduced** telemetry derived from the same sources as select `/internal/*` routes.  
**Non-scope:** Observability snapshot (`/api/observability/*`), OIL, goals, simulation, raw log streaming.  
**Server:** `backend/rust/src/main.rs`.

---

## 1. Scope

Public telemetry here means **aggregates and small scalar previews** suitable for operator-style dashboards **without** shipping raw JSONL rows, full strategy blobs, checkpoint payloads, or filesystem paths.

**Auth model (wave 1):** Same as `/api/v1/status` — **no JWT** on these routes today. They remain **network-policy** surfaces (bind privately or place behind a gateway) just like `/internal/*`.

---

## 2. Implemented endpoints

### `GET /api/v1/runtime/signals/summary`

| | |
| --- | --- |
| **Auth** | None (public listener) |
| **Source** | Same files as `GET /internal/runtime-signals`: `.logs/fusion-runtime/execution-audit.jsonl` (bounded tail read), `run-summaries.jsonl` (latest line). |
| **Response** | `PublicRuntimeSignalsSummaryV1` |

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `api_version` | string | `"1"` |
| `status` | string | `"ok"` |
| `recent_signal_sample_size` | number | Max audit lines read for the summary (currently 20). |
| `recent_signal_count` | number | Lines returned in that bounded read. |
| `recent_mode_transition_count` | number | Count of audit entries with `event_type == "runtime.mode.transition"` in that sample. |
| `latest_run_id` | string | From latest run summary JSON, or empty. |
| `latest_plan_kind` | string | From latest run summary, or empty. |
| `latest_run_message_preview` | string | Truncated preview (max 200 chars) of `message` on latest summary. |
| `timestamp_ms` | number | Server time when the response was built. |

### `GET /api/v1/milestones/summary`

| | |
| --- | --- |
| **Auth** | None |
| **Source** | Same derivation as `GET /internal/milestones`: latest `run-summaries.jsonl` line + matching `checkpoints/{run_id}.json` under `.logs/fusion-runtime/`. |
| **Response** | `PublicMilestonesSummaryV1` |

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `api_version` | string | `"1"` |
| `status` | string | `"ok"` |
| `latest_run_id` | string | Latest run id if present. |
| `completed_milestone_count` | number | From `engineering_data.milestone_state.completed_milestones` or `0`. |
| `blocked_milestone_count` | number | From `…blocked_milestones` or `0`. |
| `patch_set_count` | number | Length of `engineering_data.patch_sets` array. |
| `checkpoint_status` | string | String form of checkpoint `status`, or `"unknown"`. |
| `timestamp_ms` | number | Server time when built. |

### `GET /api/v1/strategy/summary`

| | |
| --- | --- |
| **Auth** | None |
| **Source** | Same files as `GET /internal/strategy-state`: `brain/evolution/strategy_state.json`, `brain/evolution/strategy_log.json`. |
| **Response** | `PublicStrategySummaryV1` |

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `api_version` | string | `"1"` |
| `status` | string | `"ok"` |
| `strategy_version` | number | `strategy_state.version` if numeric, else `0`. |
| `recent_change_log_count` | number | Length of `changes` array in strategy log, **capped at 10_000** for bounded responses. |
| `create_plan_weight` | number \| null | `strategy_state.capability_weights.create_plan` if numeric. |
| `timestamp_ms` | number | Server time when built. |

---

## 3. Planned endpoints (not implemented)

| Path | Rationale |
| ---- | --------- |
| `GET /api/v1/runtime/signals` (paged / filtered) | Needs auth, allowlisted fields, and pagination before raw events are safe. |
| `GET /api/v1/swarm/summary` | Swarm events are unstructured `Value`; need a redacted schema before a public read. |
| `GET /api/v1/pr-summaries/summary` | PR text and merge payloads may be product-sensitive; needs explicit redaction policy. |
| Authenticated mirrors of internal reads | JWT + rate limits + field allowlists (see roadmap). |

---

## 4. Redaction rules (wave 1)

| Omitted from public | Why |
| ------------------- | --- |
| Raw `recent_signals` / `recent_mode_transitions` arrays | High-cardinality, unstructured audit JSON. |
| Full `latest_run_summary` object | May grow; only id / plan kind / truncated message exposed. |
| Full `milestone_state`, `patch_sets` entries, `execution_state`, checkpoint bodies | Engineering detail; only counts + status string. |
| Full `strategy_state` JSON and `recent_changes` payloads | Tuning and history content; only version, one scalar weight, and change count. |
| File paths, bin locations, hostnames | Never in these responses. |

---

## 5. Frontend migration notes

| UI area today | Internal endpoint | Future public adoption |
| --------------- | ----------------- | ---------------------- |
| Dashboard “Runtime summary” / cognitive “Runtime signals” | `/internal/runtime-signals` | May use `GET /api/v1/runtime/signals/summary` for headline metrics first; keep internal for raw lists until v2. |
| Dashboard “Milestones” card | `/internal/milestones` | May use `GET /api/v1/milestones/summary` for counts + status strip. |
| Dashboard “Strategy state” card | `/internal/strategy-state` | May use `GET /api/v1/strategy/summary` for version + change count + single weight. |

**Phase 8 choice:** Frontend is **unchanged**; endpoints are additive for the next migration PR.

---

## 6. Related docs

- [`public-api-roadmap.md`](public-api-roadmap.md) — inventory + “Public telemetry wave 1”.
- [`../frontend/integration-matrix.md`](../frontend/integration-matrix.md) — consumer map.
