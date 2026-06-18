# Omni Cockpit Frontend Roadmap

**Source audit:** `docs/frontend-current-state.md`
**Baseline:** `origin/main` at `4ff18e1`
**Planning date:** 2026-06-17

## Cockpit vision

The Omni Cockpit is the governed operating surface for chat, runtime truth,
provider execution, tools, governance, memory, projects, and operational
history. It must answer four questions for every meaningful interaction:

1. What did Omni return?
2. Which runtime and provider produced it?
3. Which governance and tools affected execution?
4. Which safe evidence supports the displayed result?

The frontend already contains most target surfaces. The roadmap below is an
incremental consolidation plan. It must reuse existing components and avoid
rewriting working flows without evidence.

> **Runtime Truth must be visible, accurate, and safely unavailable before any
> visual polish is considered complete.**

## Target layout

```text
+------------------------------------------------------------------+
| Omni | Runtime | Provider | Tokens | Plan | connection/status     |
+----------------+--------------------------------+----------------+
| Sidebar        | Chat / active workspace        | Inspector      |
|                |                                |                |
| New session    | Messages or selected view      | Summary        |
| History        | Composer / primary actions     | Governance     |
| Projects       |                                | Tools          |
| Providers      |                                | Provider       |
| Agents         |                                | Memory / OIL   |
| Memory         |                                | Safe logs      |
| Lab            |                                |                |
+----------------+--------------------------------+----------------+
```

Target ownership:

- one application-level `OmniShell`;
- one route/view configuration;
- one navigation state;
- one Runtime Truth model consumed by topbar and inspector;
- feature pages render workspace content, not additional application shells;
- all technical JSON passes through the safe debug boundary.

## Component status map

| Concept | Current status | Roadmap direction |
|---|---|---|
| `OmniShell` | implemented, nested in current composition | make it the single application shell |
| Sidebar | implemented | centralize navigation and session context |
| ChatPanel | implemented and modular | preserve behavior, close incomplete controls |
| Topbar | implemented with Runtime Truth | normalize unavailable and source states |
| Runtime Inspector | implemented with seven tabs | align every field to explicit contracts |
| Governance Panel | implemented in inspector and center page | unify decision/provenance model |
| Tools Panel | implemented in inspector | add reliable empty/error/evidence states |
| SafeDebugPanel | implemented | enforce as the only technical JSON renderer |
| TokenUsageMeter | implemented | connect quota/plan semantics when contracts exist |
| ProviderSettingsPanel | equivalent provider surfaces exist | consolidate duplicate settings flows |
| Projects/History | implemented | unify navigation, provenance, and active project |
| Light/Dark theme | provider and tokens exist | replace fixed dark styling incrementally |

## Phase 1 - Design System consolidation

**Suggested branch:** `ui/omni-design-system-consolidation`

**Current state:** Omni primitives and theme tokens exist alongside older shared
components, legacy CSS, fixed dark utility classes, inline SVG icons, and
overlapping card/button patterns.

**Work remaining:**

- inventory which primitives are canonical and mark legacy equivalents;
- define semantic surface, border, text, status, spacing, and radius usage;
- make light and dark themes use semantic tokens in shared cockpit surfaces;
- document icon and accessibility conventions;
- do not redesign feature behavior.

**Acceptance criteria:**

- canonical primitive list is documented and used by touched cockpit surfaces;
- dark and light modes preserve readable contrast and focus states;
- no runtime/provider/governance data logic changes;
- existing component and frontend validations remain green.

**Risk controls:**

- migrate incrementally by component family;
- avoid global CSS deletion until import and screenshot evidence exists;
- preserve existing public component props or provide compatibility wrappers.

## Phase 2 - OmniShell and Sidebar consolidation

**Suggested branch:** `ui/omni-shell-consolidation`

**Current state:** `OmniShell`, sidebar, topbar, mobile navigation, and inspector
containers exist, but pages commonly nest shells and create isolated empty
sidebar contexts.

**Work remaining:**

- make `App` the only owner of `OmniShell`;
- move sidebar and right-inspector composition to the application boundary;
- define a route/view table instead of a long render conditional;
- preserve current URLs and browser back/forward behavior;
- provide shared session/project context to every feature view;
- add an explicit not-found behavior.

**Acceptance criteria:**

- exactly one topbar and shell render on every route;
- desktop and mobile navigation reach all current views;
- browser back/forward retains correct active navigation;
- chat state is not reset by ordinary feature navigation;
- no route or API behavior regression.

**Risk controls:**

- retain current `View` values and paths during consolidation;
- add route-level regression tests before removing duplicate shell ownership;
- do not introduce a routing dependency unless separately approved.

## Phase 3 - ChatPanel completion

**Suggested branch:** `ui/omni-chat-panel-completion`

**Current state:** modular Omni chat messages, composer, retry flow, local
persistence, Supabase synchronization, history restoration, and runtime metadata
mapping exist.

**Work remaining:**

- clarify supported behavior for stop and attachment controls;
- unify loading, retry, degraded, failed, and offline states;
- remove UI actions that only imply unsupported execution;
- surface message-level runtime/evidence links without duplicating raw metadata;
- keep session restoration and composer drafts stable across navigation.

**Acceptance criteria:**

- every visible control has implemented behavior or is clearly disabled;
- one user request maps to one final message outcome;
- failure preserves draft and safe structured runtime context;
- chat-to-inspector integration is covered by tests;
- no raw provider payload is rendered or logged in production UI.

**Risk controls:**

- preserve `/api/v1/chat` and legacy fallback policy;
- do not change retry budgets without runtime/API review;
- treat attachments and cancellation as separate contracts, not visual-only work.

## Phase 4 - Runtime Inspector contract alignment

**Suggested branch:** `ui/omni-runtime-inspector-contracts`

**Current state:** Summary, Governance, Tools, Provider, Memory, OIL, and Logs
tabs exist and consume `RuntimeMetadata`.

**Work remaining:**

- define one UI-facing Runtime Truth contract and field provenance;
- distinguish unknown, unavailable, not attempted, failed, and successful states;
- expose attempted provider separately from successful provider;
- show fallback, tool invocation, latency, and token fields only from trusted
  sources;
- align initial/pre-chat state with public runtime status;
- remove mock or inferred values from truth-labeled surfaces.

**Acceptance criteria:**

- every displayed truth field has a source and deterministic empty state;
- topbar and inspector cannot contradict each other;
- provider attempted/succeeded and fallback state are independently visible;
- governance and tool evidence never depend on raw unsafe payloads;
- tests cover full, degraded, fallback, unavailable, and failed scenarios.

**Risk controls:**

- adapters remain the wire-to-UI boundary;
- optional backend fields remain backward-compatible;
- no protected `/internal/*` data is exposed to unauthenticated users.

## Phase 5 - Safe Debug Layer enforcement

**Suggested branch:** `ui/omni-safe-debug-enforcement`

**Current state:** sanitizer, `SafeJsonViewer`, `SafeDebugPanel`, and
`RedactedField` exist.

**Work remaining:**

- audit all technical payload render paths and console diagnostics;
- route logs, OIL, provider diagnostics, and tool evidence through the safe
  renderer;
- define size, depth, truncation, and unsupported-value behavior;
- add redaction regression cases for new credential/provider formats;
- label redacted and unavailable values consistently.

**Acceptance criteria:**

- no component directly renders raw technical JSON;
- secrets, authorization, cookies, commands, environment values, stack traces,
  stdout/stderr, and raw provider/tool payloads are blocked;
- sanitizer tests cover nested objects, arrays, and string patterns;
- production build does not expose raw chat/provider debug output.

**Risk controls:**

- sanitize at both ingestion/presentation boundaries where practical;
- fail closed for unknown debug objects;
- never persist sanitized or unsanitized credentials as debug history.

## Phase 6 - Provider and BYOK UI consolidation

**Suggested branch:** `ui/omni-provider-byok-consolidation`

**Current state:** `/settings` and `/provider-center` overlap. Provider APIs,
credential forms, connection tests, runtime badges, and provider diagnostics
already exist.

**Work remaining:**

- choose `/provider-center` as the canonical cockpit surface;
- preserve `/settings` through redirect or compatibility navigation;
- unify configured, attempted, successful, failed, and fallback provider states;
- display credential ownership/access mode without revealing key material;
- define save, update, remove, test, loading, auth, and failure states;
- keep BYOK fail-closed policy visible when supplied by runtime contracts.

**Acceptance criteria:**

- one canonical provider workflow exists;
- credentials never appear in localStorage, logs, debug, or Runtime Truth;
- connection tests cannot be mistaken for saved configuration;
- provider runtime status and settings status are clearly differentiated;
- all supported providers share consistent interaction states.

**Risk controls:**

- backend credential storage remains unchanged in this frontend phase;
- secret inputs are cleared after successful operations;
- destructive removal requires explicit confirmation;
- never auto-switch BYOK providers from UI policy alone.

## Phase 7 - Token Meter and plan visibility

**Suggested branch:** `ui/omni-token-plan-meter`

**Current state:** message usage, `TokenUsageMeter`, usage overview, chart, and
plan badge components exist. Usage history is derived from available chat data.

**Work remaining:**

- distinguish per-response usage, session usage, daily usage, quota, and plan;
- display source and freshness for aggregated usage;
- connect Free/BYOK/Pro/local plan labels only when authoritative;
- define warning states without inventing quota values;
- reconcile topbar meter with token usage page totals.

**Acceptance criteria:**

- token values include scope and unit;
- missing usage is shown as unavailable, not zero;
- topbar and usage page totals agree for the same source/window;
- quota warnings appear only from an authoritative quota contract;
- tests cover absent, partial, and complete usage data.

**Risk controls:**

- no client-side enforcement presented as server enforcement;
- no pricing or billing assumptions added in this phase;
- retain backward compatibility for responses without usage.

## Phase 8 - Projects and History integration

**Suggested branch:** `ui/omni-project-history-integration`

**Current state:** project CRUD, chat history, filters, session restoration,
Supabase persistence, and local fallbacks exist.

**Work remaining:**

- define active project and session relationship;
- give all routes access to the same sidebar conversation/project context;
- display data source and synchronization state;
- add cockpit filters for runtime, fallback, tools, errors, provider, memory,
  and latency when backed by stored fields;
- make local-only and synchronized records visibly distinct.

**Acceptance criteria:**

- selecting a history item restores the expected session;
- project navigation does not lose chat state;
- filters never claim unsupported metadata;
- local/Supabase provenance and sync failures are visible;
- project deletion/archive behavior is tested and recoverable as designed.

**Risk controls:**

- no schema migration in this frontend branch;
- preserve local fallback records during synchronization failures;
- do not merge unrelated session records solely by display title.

## Phase 9 - Governance Dashboard

**Suggested branch:** `ui/omni-governance-dashboard`

**Current state:** governance badge, inspector tab, decision extraction, center
page, summary cards, and recent decision list exist.

**Work remaining:**

- define a canonical governance decision UI type and evidence reference;
- distinguish current request governance from historical aggregates;
- add policy, risk, reason, approval requirement, and source/freshness states;
- align dashboard counts with the same decision contract used by chat;
- reserve controls for future approvals without implying that UI actions can
  bypass runtime governance.

**Acceptance criteria:**

- each decision shows its scope, source, time, and evidence availability;
- blocked and requires-approval states are distinct;
- aggregate counts can be traced to visible decisions;
- no UI action weakens or overrides backend governance;
- high-risk and secret-related data remains sanitized.

**Risk controls:**

- dashboard is read-only until an approved action contract exists;
- absence of governance evidence is shown as unknown, never allowed;
- historical decisions must not be treated as current authorization.

## Cross-phase controls

- Never push directly or merge automatically to `main`.
- Use one isolated branch per phase and open a PR to `main`.
- Do not change runtime/backend contracts implicitly from frontend work.
- Do not add dependencies without a documented need and separate review.
- Keep Runtime Truth, provider provenance, governance, and debug safety tests as
  merge gates.
- Run frontend typecheck, tests, build, and `git diff --check` for every phase.
- Confirm each PR contains only its declared frontend/documentation scope.
- Preserve accessibility semantics and responsive behavior.
- Treat credentials and raw technical payloads as untrusted by default.

## Recommended next branch

The next branch should be:

```text
ui/omni-shell-consolidation
```

Reason: the design system already exists, while duplicate shell ownership
affects every route and makes later provider, token, project, history, and
governance integration harder. The branch should consolidate shell ownership
without redesigning components or changing runtime behavior.
