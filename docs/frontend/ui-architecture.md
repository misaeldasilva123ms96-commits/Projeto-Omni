# Omni Frontend UI Architecture (Phase 3)

**Scope:** Visual shell, reusable presentational primitives, and component geography on top of the Phase 2 API layer.  
**Companion docs:** [`compatibility-layer.md`](./compatibility-layer.md), [`integration-matrix.md`](./integration-matrix.md), [`cognitive-panels.md`](./cognitive-panels.md) (Phase 4).

---

## 1. Visual shell overview

The app uses a **three-column workspace** (`AppShell`):

| Column | Role | Typical content |
| ------ | ---- | ----------------- |
| **Left rail** (`sidebar-column`) | Navigation, mode, local session list, infra hint | `layout/Sidebar` |
| **Main** (`content-column`) | Primary task surface | `ChatPage`, `DashboardPage`, or `ObservabilityPage` body |
| **Right rail** (`status-column`, optional) | Live request/runtime context | `status/StatusPanel` (chat only today) |

`AppShell` adds semantic classes (`omni-app-shell`, `omni-workspace`, `omni-rail--nav`, `omni-main`, `omni-rail--status`) for styling without changing layout logic.

Responsive rules in `styles.css` (≤1280px / ≤1040px / ≤720px) stack the status rail and tighten padding; behavior is unchanged from Phase 2.

---

## 2. UI component hierarchy

### `components/ui/` — design primitives (presentational)

| Component | Purpose |
| --------- | ------- |
| `Card` | Base bordered surface |
| `PanelCard` | Glass panel (`.panel-card`) — default shell surface |
| `SectionHeader` | Eyebrow + title + optional subtitle (+ optional `aside`) |
| `PageHero` | Dashboard / observability hero band (uses `PanelCard` + `SectionHeader`) |
| `StatusBadge` | Pill states: `default` \| `active` \| `danger` \| `muted` |
| `MetricRow` | Label / value row for metrics and status grids |
| `EmptyState` | Generic zero-state layout |
| `LoadingState` | Inline loading affordance |
| `ErrorNotice` | Accessible alert block |
| `ActionButton` | `ghost` or `primary` (maps to existing button classes) |

Feature modules compose these primitives; they do not fetch data.

### `components/layout/`

| Component | Purpose |
| --------- | ------- |
| `AppShell` | Workspace grid |
| `Sidebar` | Brand, view nav, optional new chat, mode switcher, conversations |
| `ModeSwitcher` | Chat mode chips |

### `components/chat/`

| Component | Purpose |
| --------- | ------- |
| `ChatHeader` | Chat context + session badges |
| `Composer` | Message input + send |
| `EmptyState` | Chat onboarding + quick prompts (wraps `ui/EmptyState`) |
| `MessageBubble` | Message rendering + typewriter |

### `components/dashboard/`

| Component | Purpose |
| --------- | ------- |
| `MetricCard` | Card with `SectionHeader` + body slot |
| `SignalList` | Read-only list of `Record<string, unknown>` telemetry lines |

### `components/status/`

| Component | Purpose |
| --------- | ------- |
| `StatusPanel` | Health + last response metadata (uses `MetricRow`, `ErrorNotice`, `PanelCard`) |

### `components/observability/`

Unchanged domain panels (`GoalStatePanel`, `SimulationMemoryPanel`, etc.) — they remain the **real-data** cognitive views backed by snapshot / SSE.

---

## 3. Presentational vs behavioral split

| Presentational (no I/O) | Behavioral / stateful |
| ----------------------- | ---------------------- |
| `ui/*`, `PageHero`, `MetricRow`, `PanelCard`, `StatusBadge` | `pages/*` (effects, fetch orchestration) |
| `layout/Sidebar` (props only) | `hooks/useObservabilitySnapshot`, `useObservabilityStream` |
| `dashboard/MetricCard`, `SignalList` | `features/runtime` fetches |
| `chat/Composer`, `MessageBubble` presentation | `ChatPage` submit, retry, `localStorage`, Supabase sync |
| Observability panel **layout** | Panel **data** from hooks + real snapshot |

---

## 4. Current real data surfaces

| UI | Data source |
| -- | ----------- |
| Chat assistant text | `POST /chat` via `features/chat` |
| Status rail | `GET /health` + last chat metadata |
| Dashboard metrics | `GET /health`, `GET /internal/*` (signals, swarm, strategy, milestones, PR summaries) |
| Observability | `GET /api/observability/snapshot`, SSE stream, Supabase JWT |

No synthetic runtime payloads were added in Phase 3.

---

## 5. Future-ready extension points

1. **Main column:** New routes or sections can reuse `PageHero` + `dashboard-grid` / `observability-grid` patterns.
2. **`ui/PanelCard` + `SectionHeader`:** Consistent framing for future **goals / simulation / evolution** composite views when backend contracts exist.
3. **Right rail:** `AppShell` already supports an optional `statusPanel`; additional rails could be introduced behind the same prop pattern (avoid hard-coding a second column until needed).
4. **Design tokens:** `:root` variables (`--omni-space-*`, `--omni-radius-*`, etc.) centralize spacing and surfaces for later theming without a full design-token framework.

---

## 6. Styling notes

Global glass / gradient language remains in `styles.css`. Phase 3 adds **tokens**, **muted status pills**, **section header rhythm**, **workspace framing** (`.omni-workspace`), and small **chat / composer** refinements. Major color rebrands were intentionally avoided to limit regression risk.
