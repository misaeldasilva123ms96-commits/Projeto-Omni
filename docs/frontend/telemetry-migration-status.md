# Frontend telemetry migration status (Phase 9)

Tracks adoption of **public v1 summary** endpoints vs **`/internal/*`** for dashboard and cognitive rail. Backend contracts: [`../backend/public-telemetry-contracts.md`](../backend/public-telemetry-contracts.md).

---

## 1. Public telemetry now adopted

| Public endpoint | Fetcher (`lib/api/runtime.ts`) | UI surfaces |
| ----------------- | ------------------------------ | ----------- |
| `GET /api/v1/runtime/signals/summary` | `fetchPublicRuntimeSignalsSummaryV1` → `publicRuntimeSignalsSummaryV1ToUi` | **Dashboard** — “Runtime summary” metric card (run id, plan kind, message preview, signal + transition counts). **Cognitive** — `RuntimeStatusSection` “Signals summary” block. |
| `GET /api/v1/milestones/summary` | `fetchPublicMilestonesSummaryV1` → `publicMilestonesSummaryV1ToUi` | **Dashboard** — “Milestones” metric card (counts, checkpoint status). **Cognitive** — `MilestoneStateSection` “Milestones (public summary)” block. |
| `GET /api/v1/strategy/summary` | `fetchPublicStrategySummaryV1` → `publicStrategySummaryV1ToUi` | **Dashboard** — “Strategy state” card (version, plan weight, change log count) plus one internal-only row for history limit. **Cognitive** — `StrategyStateSection` “Strategy (public summary)” block. |

**Data plumbing:** `useCognitiveTelemetry` and `DashboardPage` each run a single `Promise.all` that includes the three summary fetches alongside existing internal reads.

---

## 2. Remaining internal dependencies

| Area | Endpoint(s) | Why kept |
| ---- | ----------- | -------- |
| Runtime event lists, mode transition lists | `/internal/runtime-signals` | Raw `recent_signals` / `recent_mode_transitions` JSON for `SignalList` and `ExecutionSignalsSection`. |
| Swarm events | `/internal/swarm-log` | Unstructured events; no public summary in wave 1. |
| Strategy history + change payloads | `/internal/strategy-state` | `memory_rules`, full `strategy_state`, and `recent_changes` samples for internal-labeled rows. |
| Milestone list body | `/internal/milestones` | Record count for “Milestone detail (internal)”; full milestone arrays still internal-only. |
| PR summaries list | `/internal/pr-summaries` | Reviewer-facing objects; no public replacement yet. |

---

## 3. Migration rationale

| Decision | Rationale |
| -------- | --------- |
| Summary cards → public | Headline metrics are stable, bounded, and documented on the wire; reduces coupling to raw internal JSON for the same numbers. |
| Lists and execution rail → internal | Public wave 1 deliberately omits raw arrays; fidelity for operators still requires internal reads. |
| Strategy “history limit” stays internal | Not part of `PublicStrategySummaryV1`; exposing it would require expanding the public contract. |
| Cognitive split headers (`live` vs `internal`) | Preserves honest provenance labels from Phase 4. |

---

## 4. Next migration opportunities

| When | Action |
| ---- | ------ |
| Backend ships paged `/api/v1/runtime/signals` | Point `SignalList` at allowlisted fields; keep internal as fallback during rollout. |
| Public swarm / PR summary shapes | Replace internal list cards after redaction policy is fixed. |
| JWT on public telemetry | Move summary reads behind gateway or auth without changing UI field names. |

---

## 5. Related docs

- [`public-api-adoption.md`](public-api-adoption.md) — `/api/v1/status` and chat correlation.
- [`integration-matrix.md`](integration-matrix.md) — full route matrix.
