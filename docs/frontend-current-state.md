# Omni Frontend Current State

**Audit branch:** `ui/omni-cockpit-audit`
**Audited baseline:** `origin/main` at `4ff18e1`
**Audit date:** 2026-06-17
**Scope:** read-only inspection of `frontend/src`

## Executive summary

The frontend is a React 19 and TypeScript 6 application built with Vite 8. It
already contains a substantial Omni Cockpit implementation: a responsive shell,
sidebar, modular chat, runtime truth topbar, tabbed Runtime Inspector, safe debug
viewer, provider settings, token usage, projects, history, governance, memory,
agents, observability, and lab views.

The next frontend work should therefore be consolidation and contract alignment,
not a greenfield cockpit rewrite. The main technical gaps are:

- shell ownership is duplicated because `App` wraps every view in `OmniShell`
  while most pages render another `OmniShell`;
- routing is a manual `window.history` switch rather than a route configuration;
- several feature pages have their own empty conversation/sidebar context;
- cockpit data mixes HTTP contracts, Supabase reads, localStorage fallbacks, and
  UI-only state without a single documented data boundary;
- some runtime fields are visible only after a chat response and are not backed
  by a durable session/event model;
- the design system and theme provider exist, but fixed dark utility classes and
  duplicated legacy CSS limit real light-theme coverage;
- provider configuration exists in both `/settings` and `/provider-center`;
- some controls are placeholders or incomplete, such as memory editing, lab
  execution, attachment/stop behavior, and some sidebar modules;
- tests cover important units and surfaces, but not the complete navigation and
  end-to-end cockpit workflow.

Runtime Truth is already the correct product differentiator and must remain
visible and trustworthy before further visual polish.

## Directory map

```text
frontend/src/
  app/
    App.tsx                    manual view resolution and history navigation
  components/
    agents/                    agent cards, forms, and lists
    chat/                      legacy and Omni chat composition
    dashboard/                 dashboard metrics and signals
    governance/                governance decision list
    history/                   filters, session cards, and session detail
    lab/                       local lab console
    layout/                    legacy/deprecated layout components
    memory/                    memory cards and list
    observability/             operational and cognitive telemetry panels
    projects/                  project CRUD surfaces
    providers/                 provider overview and credential cards
    runtime/                   Runtime Truth badges and inspector tabs
    safety/                    sanitized JSON/debug presentation
    shell/                     Omni shell, sidebar, topbar, inspector, mobile nav
    status/                    runtime and cognitive status composition
    tokens/                    token summary and chart
    ui/                        Omni primitives plus older shared primitives
  features/
    chat/                      chat transport facade
    observability/             observability exports
    runtime/                   wire-to-UI runtime mapping
    settings/                  provider settings UI and hook
  hooks/                       auth, telemetry, observability, live metrics
  lib/
    api/                       HTTP client, endpoints, adapters
    puter/                     guarded Free Mode/Puter development contracts
    omniData.ts                Supabase and localStorage feature data
    runtimeDebugSanitizer.ts   debug redaction
    supabase.ts                Supabase client
  pages/                       top-level application views
  state/
    runtimeConsoleStore.ts     Zustand cockpit UI/runtime state
  types/
    api/                       wire contracts
    ui/                        UI-facing contracts
  main.tsx                     React entrypoint
  styles.css                   Tailwind theme plus legacy/custom CSS
```

## Main frontend entrypoints

### `frontend/src/main.tsx`

- mounts React through `createRoot`;
- enables `React.StrictMode`;
- wraps the app with `ErrorBoundary`;
- installs `OmniThemeProvider`;
- imports the global `styles.css`.

### `frontend/src/app/App.tsx`

- owns the current view and chat mode;
- maps `window.location.pathname` to a `View` union;
- updates history with `window.history.pushState`;
- listens for `popstate`;
- renders the selected page;
- wraps the selected page in an outer `OmniShell`.

Most selected pages also create their own `OmniShell`. This nested-shell
composition is the main layout architecture issue to resolve in a future branch.

## Current routes and views

Routing is implemented without React Router.

| Path | View | Main surface |
|---|---|---|
| `/` | `chat` | `ChatPage` |
| `/dashboard` | `dashboard` | `DashboardPage` |
| `/history` | `history` | `ChatPage` with `HistoryPanel` |
| `/observability` | `observability` | `ObservabilityAuthGate` |
| `/projects` | `projects` | `ProjectsPage` |
| `/provider-center` | `provider-center` | `ProviderCenterPage` |
| `/token-usage` | `token-usage` | `TokenUsagePage` |
| `/agents` | `agents` | `AgentsPage` |
| `/governance` | `governance` | `GovernanceCenterPage` |
| `/memory-center` | `memory-center` | `MemoryCenterPage` |
| `/lab-mode` | `lab-mode` | `LabModePage` |
| `/settings` | `settings` | legacy `SettingsView` |
| guarded Puter path | `puter-dev` | `PuterDevRoutePage` when both flags allow it |

Unknown paths fall back to chat instead of rendering a not-found view.

## Current shell and layout

### Implemented cockpit shell

- `OmniShell` supports optional left and right rails, desktop collapse, mobile
  panel switching, backdrops, skip navigation, and responsive grid columns.
- `OmniSidebar` wraps the existing navigation and conversation surface.
- `OmniTopbar` renders `RuntimeTruthBar` by default.
- `OmniMobileNav` switches between sidebar, content, and inspector.
- `OmniRightInspector` exists as a reusable container, while chat currently
  passes `RuntimePanel` directly as the shell right panel.

### Legacy layout

`components/layout/AppShell.tsx`, `Layout.tsx`, and related sidebar code remain
importable and tested. Some are marked deprecated, but the codebase still carries
legacy CSS and component concepts alongside the Omni shell.

### Current constraint

Shell state is distributed between local component state and the Zustand runtime
console store. Sidebar collapse, mobile panel, and inspector tab selection are
not represented by one canonical application shell state.

## Current components

### Ready for reuse

- `OmniShell`, `OmniSidebar`, `OmniTopbar`, `OmniMobileNav`;
- `OmniChatPanel`, `OmniMessageList`, `OmniComposer`, user/assistant/system
  message components;
- `RuntimeTruthBar`, runtime/provider/governance/plan badges,
  `TokenUsageMeter`;
- `RuntimeInspectorPanel` and Summary, Governance, Tools, Provider, Memory,
  OIL, and Logs tabs;
- `SafeJsonViewer`, `SafeDebugPanel`, `RedactedField`;
- `OmniButton`, `OmniCard`, `OmniBadge`, `OmniPanel`, `OmniTabs`,
  `OmniTooltip`, `OmniStatusDot`, `OmniSkeleton`;
- history, project, provider, token, governance, agent, memory, and lab
  feature components.

### Partially integrated or duplicated

- both legacy chat primitives and newer Omni chat primitives remain;
- `/settings` and `/provider-center` expose overlapping provider workflows;
- `RuntimePanel` contains action controls plus the inspector, while
  `OmniRightInspector` is not the canonical integration point;
- pages build independent sidebars with empty conversation arrays;
- `MemoryCenterPage` logs edit intent instead of implementing editing;
- some sidebar tools only load composer presets or display a notice;
- attachment and stop controls exist visually but are not complete runtime
  workflows;
- `LabConsole` is a local sandbox surface, not proof of host-isolated sandbox
  execution.

## Current chat flow

```text
ChatPage
  -> local input/session/message state
  -> sendWithRetry(maxRetries = 2)
  -> sendOmniMessage()
  -> POST /api/v1/chat
  -> fallback to POST /chat only for 404, 405, or 501
  -> parseWireChatPayload()
  -> chatApiResponseToUi()
  -> normalizeMetadata()
  -> update messages, RuntimeMetadata, Zustand runtime console, telemetry tick
  -> persist local snapshot and attempt Supabase session synchronization
```

Important behavior:

- local chat state uses `omni-chat-state-v3`, with non-destructive migration from the legacy `omini-chat-state-v3` key;
- sessions use generated client IDs and may be restored from Supabase;
- the UI retries network failures twice with a fixed delay;
- assistant text is displayed through a client-side streaming animation;
- failed structured responses can still populate safe runtime metadata;
- API-unavailable state prevents sending but allows message preparation;
- raw response debugging still includes a development `console.debug` call,
  although technical UI rendering uses the sanitizer.

## Current API and data flow

### Shared HTTP layer

`lib/api/client.ts` provides:

- `VITE_OMNI_API_URL` resolution through `lib/env.ts`;
- 45-second request timeout with `AbortController`;
- JSON/text response parsing;
- optional Supabase bearer acquisition;
- public and authenticated GET helpers.

### Chat

- `POST /api/v1/chat`;
- legacy fallback `POST /chat`;
- wire payloads are parsed by adapters before reaching UI types.

### Runtime and observability

Public routes:

- `GET /api/v1/status`;
- `GET /api/v1/runtime/signals/summary`;
- `GET /api/v1/milestones/summary`;
- `GET /api/v1/strategy/summary`;
- `GET /health`.

Authenticated operator routes:

- `GET /api/v1/operator/runtime/signals`;
- `GET /api/v1/operator/strategy/changes`;
- `GET /api/v1/operator/milestones`.

Legacy/internal fallback routes:

- `/internal/runtime-signals`;
- `/internal/swarm-log`;
- `/internal/strategy-state`;
- `/internal/milestones`;
- `/internal/pr-summaries`.

### Provider settings

`lib/api/settings.ts` uses `/api/v1/settings/providers` and provider-specific
subpaths for create/update/remove/test operations. Provider API keys are held in
component state while being edited and are sent to the backend settings API.

### Supabase and local fallback

`lib/omniData.ts` handles chat synchronization and feature data for projects,
token usage, governance, agents, and memory. Depending on authentication and
available rows, several features fall back to localStorage.

This makes the UI functional but leaves provenance inconsistent: a page may show
server data, Supabase data, derived chat metadata, or local-only data without a
uniform visible data-source contract.

## Current state management

### Zustand

`runtimeConsoleStore` holds:

- current mode and action;
- selected sidebar item and panel view;
- sending and error state;
- last runtime metadata;
- selected tool and UI notice.

### Local React state

Local state remains the dominant model for:

- app view and navigation;
- messages, session, composer, request state, and chat metadata;
- shell collapse/mobile selection;
- inspector tab;
- provider key inputs;
- feature loading, forms, filters, and dialogs.

### Browser persistence

- chat snapshot: localStorage;
- theme: localStorage;
- lab history: localStorage;
- projects, agents, and memory: localStorage fallback paths;
- authentication and some durable data: Supabase.

## Current runtime, debug, and provider visibility

### Runtime Truth

The topbar and inspector can show:

- runtime mode and reason;
- actual provider and provider failures;
- fallback state and execution path;
- governance summary;
- matched tools and commands;
- tool/provider diagnostics;
- input/output token usage;
- session and request state;
- OIL-like inspection data when supplied by the backend.

Runtime truth is strongest after a chat response. Before the first response,
several fields are absent or represented by defaults.

### Safe debug

`sanitizeRuntimeDebugPayload` removes dangerous keys and redacts recognizable:

- OpenAI-style keys;
- bearer tokens and JWTs;
- Supabase URLs;
- email addresses and phone numbers;
- common Unix and Windows locations.

`SafeJsonViewer` sanitizes again at the rendering boundary and limits tree depth.
This is the correct presentation path for technical JSON. New technical panels
must not render raw payloads directly.

### Provider visibility

Provider status exists in the Runtime Truth bar, inspector, settings view, and
provider center. The remaining gap is a single provider model that distinguishes
configured provider, attempted provider, successful provider, fallback chain,
access plan, and credential ownership without duplicated UI logic.

## Current styling and theme approach

- Tailwind CSS 4 is loaded through PostCSS.
- `styles.css` defines Omni semantic color tokens for dark and light themes.
- `OmniThemeProvider` applies `data-omni-theme` and persists the preference.
- the initial preference honors `prefers-color-scheme`.
- significant legacy/custom CSS remains in the same global file.
- many components use fixed dark Tailwind colors, translucent white borders,
  gradients, large radii, and inline SVG icons.

The theme mechanism is implemented, but light mode is not yet a complete visual
contract because fixed dark classes bypass semantic tokens.

## Current tests and build commands

The frontend package declares:

```bash
cd frontend
npm run dev
npm run build
npm run preview
npm test
npm run test:watch
npm run typecheck
```

There is no `lint` script in `frontend/package.json`.

At audit time, Vitest discovers 42 test files and 370 tests. The test command
runs Vitest and then `frontend/scripts/verify-runtime-console.mjs`.

Covered areas include:

- shell and mobile navigation;
- chat and runtime panel behavior;
- provider, project, governance, token, and agent components;
- runtime adapters and debug sanitization;
- Zustand runtime console state;
- Puter/Free Mode guarded contracts and development surfaces.

Missing high-value coverage includes:

- a full navigation test across every path;
- one end-to-end chat-to-inspector Runtime Truth scenario;
- complete light-theme visual/regression coverage;
- source/provenance labeling across Supabase and local fallbacks;
- complete provider/BYOK lifecycle and permission-state coverage.

## Risks and constraints

1. Nested `OmniShell` instances can duplicate topbars, spacing, and responsive
   state.
2. Manual routing centralizes a growing conditional tree and has no not-found
   behavior.
3. Mixed data sources can make apparently equivalent cockpit values disagree.
4. Runtime metadata depends on optional backend fields and needs explicit
   unavailable/unknown states.
5. Internal endpoint fallbacks must not expose protected telemetry publicly.
6. Provider credentials must never enter logs, Runtime Truth payloads, browser
   persistence, or debug views.
7. Global CSS contains both current and legacy systems, increasing regression
   risk.
8. Visual controls must not imply that unsupported runtime actions succeeded.
9. The current branch history named `ui/omni-cockpit-audit` was previously used
   for implementation; this audit must remain documentation-only.

## What must not be changed yet

- runtime, provider routing, governance, or backend behavior;
- public or internal API contracts;
- Supabase schema or persistence strategy;
- dependencies, build configuration, CI, deploy configuration, or environment
  files;
- credential handling or secret storage;
- existing components through refactoring during this audit;
- automatic merge, direct push to `main`, or auto-merge configuration;
- visual polish that hides or weakens Runtime Truth;
- raw technical payload rendering that bypasses the safe debug layer.

## Audit conclusion

The current frontend already proves the Omni Cockpit concept. The safe next step
is a focused shell and data-contract consolidation branch, not another broad
design-system build. That branch should make one shell own navigation and the
inspector while preserving the existing chat, runtime truth, provider, safety,
and feature components.
