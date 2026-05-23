# Omni Cognitive Panels (Phase 4)

**Scope:** How the UI surfaces **real** runtime, strategy, milestone, swarm, and observability data with **honest provenance labels**, plus **non-deceptive** placeholders for future public APIs.  
**Depends on:** Phase 2 compatibility layer, Phase 3 shell (`ui-architecture.md`).

---

## 1. Real data sources powering the cognitive UI

| UI section | HTTP source | Notes |
| ---------- | ----------- | ----- |
| **Runtime health** | `GET /health` | Live dependency posture (Rust / Python / Node). |
| **Runtime signals** | `GET /internal/runtime-signals` | Recent signals, mode transitions, latest run summary JSON. |
| **Strategy / reasoning** | `GET /internal/strategy-state` | Version, memory rules, capability weights (typed loosely as records). |
| **Milestones & PR summaries** | `GET /internal/milestones`, `GET /internal/pr-summaries` | Engineering checkpoint + reviewer-style summaries. |
| **Execution / swarm** | `GET /internal/swarm-log` (+ signals above) | Cooperative agent events and counts. |
| **Observability snapshot (chat rail)** | `GET /api/observability/snapshot` | Same payload as Observability page; **only when Supabase session** has `access_token`. |
| **Chat metadata** | `POST /chat` response (adapted) | `source`, commands/tools, `stop_reason`, `usage`, best-effort `session_id`. |
| **Observability page body** | Snapshot + SSE + (optional) traces | Protected routes; unchanged architecture. |

No new routes were added in Phase 4.

---

## 2. Live vs internal vs protected vs future

| Label (`DataScopeBadge`) | Meaning |
| ------------------------ | ------- |
| **Live runtime** | Public listener today: `/health` (still requires reachable Rust instance). |
| **Internal telemetry** | `GET /internal/*` — **not** a security boundary; network policy must restrict exposure. |
| **Protected** | `GET /api/observability/*` — Supabase JWT (header or SSE query token). |
| **Future module** | UI extension point **without** live HTTP backing in this repo; explicit “awaiting contract” copy. |

Rule: **nothing labeled “Live” or “Internal” is fabricated** — empty states show `—` or zero counts from real JSON.

---

## 3. Current cognitive UI structure

* **Chat (`ChatPage`)** — Main column: conversation + composer. **Right rail:** `CognitivePanel` stacks `StatusPanel` (request + last `/chat` metadata), telemetry sections (health + internal bundles), optional observability summary when authenticated, then **four** `FutureModuleCard` placeholders.
* **Dashboard** — Existing metric grid unchanged in data terms; added **trust strip** (`DataScopeBadge` + copy) and a **future API** grid using the same `FutureModuleCard` pattern.
* **Observability** — Trust strip clarifies **Protected** scope; panels remain the real snapshot-backed components.

---

## 4. Future public API path

1. **Introduce versioned read models** (e.g. `/api/v1/runtime/status`) — implement fetch in `lib/api` (or successor) and map through **adapters** to the same section components where shapes align.
2. **Goals / simulation / evolution** — replace `FutureModuleCard` slots with real components **only** when OpenAPI or hand-written contracts exist; keep badges (`DataScopeBadge`) accurate.
3. **OIL / memory** — when Python exposes a safe HTTP envelope, add a domain module + adapter; UI sections remain composable without redesigning `AppShell`.
4. **Chat rail** — `CognitivePanel` stays the single composition point so chat + telemetry coherence survives backend moves.

---

## 5. Key frontend files

| File | Role |
| ---- | ---- |
| `hooks/useCognitiveTelemetry.ts` | Batches health + all `/internal/*` reads used on the chat cognitive rail. |
| `components/status/CognitivePanel.tsx` | Composes rail: status, telemetry sections, observability summary, future cards. |
| `components/status/*Section.tsx` | Presentational slices per domain. |
| `components/status/FutureModuleCard.tsx` | Product-grade placeholder. |
| `components/ui/DataScopeBadge.tsx` | Provenance pill. |
