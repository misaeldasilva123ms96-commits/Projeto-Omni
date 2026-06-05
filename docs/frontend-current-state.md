# Omni Frontend — Current State

**Branch:** `main` (consolidated from `ui/omni-cockpit-audit`)
**Date:** 2026-06-05
**Status:** Frontend cockpit audit complete — all 19 phases merged

---

## 1. Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 19.2.7 |
| Language | TypeScript | 6.0.3 |
| Build | Vite | 8.0.14 |
| Styling | Tailwind CSS | 4.3.0 + PostCSS |
| State | Zustand | 5.0.12 |
| Animation | framer-motion | 12.38.0 |
| Charts | recharts | 3.8.1 |
| Testing | Vitest | 4.1.7 |
| Testing lib | @testing-library/react | 16.3.2 |
| HTTP | fetch (native) | — |
| Backend | Supabase JS SDK | 2.101.1 |

## 2. Directory Structure

```
frontend/src/
├── app/
│   └── App.tsx                        — root component, views, routing
├── components/
│   ├── chat/
│   │   ├── ChatPanel.tsx              — main chat area
│   │   ├── ChatHeader.tsx             — chat header
│   │   ├── Composer.tsx               — message input
│   │   ├── EmptyState.tsx             — chat empty state
│   │   ├── MessageBubble.tsx          — individual message
│   │   ├── OmniChatPanel.tsx          — enhanced chat wrapper (Phase 6)
│   │   ├── OmniComposer.tsx           — enhanced composer (Phase 6)
│   │   ├── OmniMessageList.tsx        — message list (Phase 6)
│   │   ├── OmniUserMessage.tsx        — user message component (Phase 6)
│   │   ├── OmniAssistantMessage.tsx   — assistant msg with badges (Phase 6)
│   │   ├── OmniSystemNotice.tsx       — system notice (Phase 6)
│   │   ├── OmniAttachmentButton.tsx   — attachment button (Phase 6)
│   │   ├── OmniSendButton.tsx         — send button (Phase 6)
│   │   ├── OmniStopButton.tsx         — stop button (Phase 6)
│   │   ├── OmniChatPanel.test.tsx     — Phase 6 tests
│   │   ├── OmniAssistantMessage.test.tsx
│   │   ├── OmniComposer.test.tsx
│   │   ├── OmniSendButton.test.tsx
│   │   ├── ChatPanel.test.tsx
│   │   └── MessageBubble.test.tsx
│   ├── shell/
│   │   ├── OmniShell.tsx              — unified 3-column layout (Phase 1)
│   │   ├── OmniSidebar.tsx            — collapsible sidebar (Phase 1)
│   │   ├── OmniTopbar.tsx             — persistent top status bar (Phase 1)
│   │   ├── OmniRightInspector.tsx     — right panel container (Phase 1)
│   │   ├── OmniMobileNav.tsx          — mobile nav drawer (Phase 1)
│   │   ├── OmniShell.test.tsx
│   │   ├── OmniSidebar.test.tsx
│   │   ├── OmniTopbar.test.tsx
│   │   ├── OmniRightInspector.test.tsx
│   │   └── OmniMobileNav.test.tsx
│   ├── ui/
│   │   ├── OmniThemeProvider.tsx      — theme context + persistence (Phase 5)
│   │   ├── OmniButton.tsx             — 4 variants (Phase 5)
│   │   ├── OmniCard.tsx               — base card surface (Phase 5)
│   │   ├── OmniBadge.tsx              — status badge (Phase 5)
│   │   ├── OmniPanel.tsx              — glass panel (Phase 5)
│   │   ├── OmniTabs.tsx               — accessible tabs (Phase 5)
│   │   ├── OmniTooltip.tsx            — tooltip (Phase 5)
│   │   ├── OmniStatusDot.tsx          — status indicator (Phase 5)
│   │   ├── OmniSkeleton.tsx           — loading skeleton (Phase 5)
│   │   ├── ActionButton.tsx
│   │   ├── Card.tsx
│   │   ├── DataScopeBadge.tsx
│   │   ├── EmptyState.tsx
│   │   ├── ErrorNotice.tsx
│   │   ├── LoadingState.tsx
│   │   ├── MetricRow.tsx
│   │   ├── PageHero.tsx
│   │   ├── PanelCard.tsx
│   │   ├── SectionHeader.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── OmniButton.test.tsx
│   │   ├── OmniCard.test.tsx
│   │   ├── OmniBadge.test.tsx
│   │   ├── OmniTabs.test.tsx
│   │   ├── OmniSkeleton.test.tsx
│   │   └── OmniThemeProvider.test.tsx
│   ├── runtime/
│   │   ├── RuntimeStatusBadge.tsx      — runtime mode badge (Phase 2)
│   │   ├── ProviderStatusBadge.tsx     — provider badge (Phase 2)
│   │   ├── GovernanceBadge.tsx         — governance decision (Phase 2)
│   │   ├── TokenUsageMeter.tsx         — token usage bar (Phase 2)
│   │   ├── PlanBadge.tsx               — plan badge (Phase 2)
│   │   ├── RuntimeTruthBar.tsx         — composite topbar bar (Phase 2)
│   │   ├── RuntimeInspectorPanel.tsx   — tabbed inspector (Phase 3)
│   │   ├── RuntimeSummaryTab.tsx       — summary tab (Phase 3)
│   │   ├── RuntimeGovernanceTab.tsx    — governance tab (Phase 3)
│   │   ├── RuntimeToolsTab.tsx         — tools tab (Phase 3)
│   │   ├── RuntimeProviderTab.tsx      — provider tab (Phase 3)
│   │   ├── RuntimeMemoryTab.tsx        — memory tab (Phase 3)
│   │   ├── RuntimeOilTab.tsx           — OIL tab (Phase 3)
│   │   ├── RuntimeLogsTab.tsx          — safe logs tab (Phase 3)
│   │   ├── RuntimeStatusBadge.test.tsx
│   │   ├── RuntimeTruthBar.test.tsx
│   │   ├── RuntimeInspectorPanel.test.tsx
│   │   └── RuntimeSummaryTab.test.tsx
│   ├── safety/
│   │   ├── SafeJsonViewer.tsx          — tree view with redaction (Phase 4)
│   │   ├── SafeDebugPanel.tsx          — structured debug panel (Phase 4)
│   │   ├── RedactedField.tsx           — redacted value display (Phase 4)
│   │   ├── SafeJsonViewer.test.tsx
│   │   └── RedactedField.test.tsx
│   ├── providers/
│   │   ├── ProviderCard.tsx
│   │   ├── ProviderStatusBadge.tsx
│   │   └── ProviderSettingsPanel.tsx   — provider settings (Phase 8+)
│   ├── tokens/
│   │   └── TokenBudgetWarning.tsx      — token budget warning (Phase 8+)
│   ├── history/
│   │   ├── HistoryPanel.tsx            — full history view (Phase 7)
│   │   ├── HistoryFilters.tsx          — filter bar (Phase 7)
│   │   ├── HistorySessionCard.tsx      — session card (Phase 7)
│   │   ├── HistorySessionDetail.tsx    — expanded session (Phase 7)
│   │   ├── HistoryPanel.test.tsx
│   │   └── HistorySessionCard.test.tsx
│   ├── projects/
│   │   ├── OmniProjectsPanel.tsx       — CRUD project list (Phase 8+)
│   │   ├── OmniProjectCard.tsx         — project card (Phase 8+)
│   │   ├── OmniProjectForm.tsx         — create/edit form (Phase 8+)
│   │   └── OmniProjectsPanel.test.tsx
│   ├── governance/
│   │   ├── GovernanceCenterPanel.tsx   — governance viewer (Phase 8+)
│   │   ├── GovernancePolicyCard.tsx    — policy card (Phase 8+)
│   │   └── GovernanceCenterPanel.test.tsx
│   ├── memory/
│   │   ├── MemoryCenterPanel.tsx       — memory viewer (Phase 8+)
│   │   ├── MemoryEntryCard.tsx         — memory entry (Phase 8+)
│   │   └── MemoryCenterPanel.test.tsx
│   ├── agents/
│   │   ├── AgentsCenterPanel.tsx       — agent management (Phase 8+)
│   │   ├── OmniAgentCard.tsx           — agent card (Phase 8+)
│   │   └── AgentsCenterPanel.test.tsx
│   ├── lab/
│   │   ├── LabModePanel.tsx            — sandbox mode (Phase 8+)
│   │   └── LabModePanel.test.tsx
│   ├── layout/
│   │   ├── AppShell.tsx                — legacy (deprecated, importable)
│   │   ├── Layout.tsx                  — legacy (deprecated, importable)
│   │   ├── Sidebar.tsx                 — legacy (deprecated, importable)
│   │   ├── ModeSwitcher.tsx
│   │   ├── Layout.test.tsx
│   │   └── Sidebar.test.tsx
│   ├── status/
│   │   ├── RuntimePanel.tsx
│   │   ├── StatusPanel.tsx
│   │   ├── CognitivePanel.tsx
│   │   ├── RuntimeDebugSection.tsx
│   │   ├── RuntimeStatusSection.tsx
│   │   ├── ExecutionSignalsSection.tsx
│   │   ├── MilestoneStateSection.tsx
│   │   ├── StrategyStateSection.tsx
│   │   ├── ObservabilitySummarySection.tsx
│   │   ├── CognitiveSectionHeader.tsx
│   │   ├── FutureModuleCard.tsx
│   │   ├── RuntimePanel.test.tsx
│   │   └── RuntimeDebugSection.test.tsx
│   ├── observability/
│   │   ├── GoalStatePanel.tsx
│   │   ├── LearningSignalsPanel.tsx
│   │   ├── OperationalTimeline.tsx
│   │   ├── SimulationMemoryPanel.tsx
│   │   └── SpecialistTraceViewer.tsx
│   ├── dashboard/
│   │   ├── MetricCard.tsx
│   │   └── SignalList.tsx
│   ├── AppHeader.tsx
│   ├── ConversationPanel.tsx
│   ├── ErrorBoundary.tsx
│   ├── MarkdownRenderer.tsx
│   ├── MessageList.tsx
│   ├── ObservabilityAuthGate.tsx
│   └── SystemBadges.tsx
├── pages/
│   ├── ChatPage.tsx
│   ├── DashboardPage.tsx
│   ├── ObservabilityPage.tsx
│   ├── SettingsPage.tsx
│   ├── ProviderCenterPage.tsx          — provider management page (Phase 8+)
│   ├── TokenUsagePage.tsx              — token usage page (Phase 8+)
│   ├── ProjectsPage.tsx                — projects CRUD page (Phase 8+)
│   ├── GovernanceCenterPage.tsx        — governance page (Phase 8+)
│   ├── MemoryCenterPage.tsx            — memory page (Phase 8+)
│   ├── AgentsCenterPage.tsx            — agents page (Phase 8+)
│   ├── LabModePage.tsx                 — lab/sandbox page (Phase 8+)
│   ├── HistoryPage.tsx                 — history page (Phase 7)
│   ├── PuterDevRoutePage.tsx
│   ├── ChatPage.test.tsx
│   └── PuterDevRoutePage.test.tsx
├── features/
│   ├── chat/index.ts
│   ├── runtime/index.ts
│   ├── observability/index.ts
│   ├── sessions/
│   ├── projects/
│   │   ├── types.ts
│   │   └── useProjects.ts
│   ├── governance/
│   │   └── useGovernance.ts
│   └── settings/
│       ├── index.ts
│       ├── types.ts
│       ├── ProviderCard.tsx
│       ├── ProviderStatusBadge.tsx
│       └── hooks/useProviders.ts
├── hooks/
│   ├── useCognitiveTelemetry.ts
│   ├── useLiveRuntimeMetrics.ts
│   ├── useObservabilitySnapshot.ts
│   ├── useObservabilityStream.ts
│   ├── useRequireAuth.ts
│   ├── useTypewriter.ts
│   ├── useOmniChat.ts
│   ├── useOmniTheme.ts
│   ├── useRuntimeInspector.ts
│   ├── useTokenUsage.ts
│   └── useProjects.ts
├── lib/
│   ├── api.ts                    — barrel exports
│   ├── env.ts                    — env var resolution
│   ├── omniData.ts               — Supabase sync helpers
│   ├── runtimeDebugSanitizer.ts  — debug payload sanitizer
│   ├── runtimeDebugSanitizer.test.ts
│   ├── supabase.ts               — Supabase client
│   ├── api/
│   │   ├── chat.ts               — POST /api/v1/chat + legacy fallback
│   │   ├── client.ts             — HTTP client, timeout, auth headers
│   │   ├── health.ts             — GET /health
│   │   ├── runtime.ts            — telemetry fetchers
│   │   ├── operator.ts           — operator JWT endpoints
│   │   ├── observability.ts      — observability endpoints
│   │   ├── adapters.ts           — wire → UI adapters
│   │   └── wireChatHealth.ts     — health classification
│   └── ui/
│       └── glow.ts               — glow effect helpers
├── state/
│   ├── runtimeConsoleStore.ts    — Zustand store
│   ├── runtimeConsoleStore.test.ts
│   ├── omniShellStore.ts         — OmniShell UI state (Phase 1)
│   └── omniShellStore.test.ts
├── types/
│   ├── types.ts                  — core types
│   ├── api/wire.ts               — wire-specific types
│   ├── ui/
│   │   ├── chat.ts               — UiChatResponse
│   │   ├── runtime.ts            — UiRuntimeStatus
│   │   ├── telemetry.ts          — telemetry UI types
│   │   └── observability.ts
│   └── observability.ts
├── test/
│   └── setup.ts
├── main.tsx                      — entry point
├── styles.css                    — all styles (Tailwind + custom CSS)
├── vite-env.d.ts
└── env.d.ts
```

## 3. Views & Routing

Manual routing via `App.tsx` `resolveViewFromPath()`:

| Path | View | Component |
|------|------|-----------|
| `/` | chat | `ChatPage` (via OmniShell) |
| `/dashboard` | dashboard | `DashboardPage` (via OmniShell) |
| `/observability` | observability | `ObservabilityAuthGate` → `ObservabilityPage` (via OmniShell) |
| `/settings` | settings | `SettingsView` (via OmniShell) |
| `/provider-center` | providers | `ProviderCenterPage` (via OmniShell) |
| `/token-usage` | tokens | `TokenUsagePage` (via OmniShell) |
| `/projects` | projects | `ProjectsPage` (via OmniShell) |
| `/governance` | governance | `GovernanceCenterPage` (via OmniShell) |
| `/memory` | memory | `MemoryCenterPage` (via OmniShell) |
| `/agents` | agents | `AgentsCenterPage` (via OmniShell) |
| `/lab` | lab | `LabModePage` (via OmniShell) |
| `/history` | history | `HistoryPage` (via OmniShell) |
| `/puter-dev` | puter-dev | `PuterDevRoutePage` |

## 4. State Management

**Zustand stores:**

- `runtimeConsoleStore` — activeAction, activeSidebarItem, activeTab, currentMode, isSending, lastError, panelView, uiNotice
- `omniShellStore` — sidebar collapsed, inspector open, inspector tab, mobile panel (Phase 1)

**Local state** in `ChatPage`:
- Messages array (localStorage via `omini-chat-state-v3`)
- Request state, session ID, config mode

## 5. Chat Data Flow

```
User input → ChatPage.handleSubmit()
  → sendOmniMessage(prompt, { sessionId })
    → POST /api/v1/chat (with fallback to POST /chat)
      → ChatApiResponse
        → chatApiResponseToUi() → UiChatResponse
          → normalizeMetadata() → RuntimeMetadata
            → setMessages() + setLastMetadata()
```

## 6. Theme

**Dark-first** with light mode toggle. `OmniThemeProvider` persists choice in `localStorage`. CSS variables (`--omni-*`) defined for both `:root` (dark) and `:root.light`. Toggle in OmniTopbar.

## 7. Runtime Data Types

Core type `RuntimeMetadata` contains:
```
runtimeMode, runtimeReason, executionPathUsed, fallbackTriggered,
compatibilityExecutionActive, providerActual, providerFailed,
failureClass, failureReason, providerDiagnostics, providerFallbackOccurred,
noProviderAvailable, toolExecution, toolDiagnostics, usage (input/output tokens),
cognitiveRuntimeInspection, signals, error, governance (Phase 2)
```

## 8. Debug Sanitization

`lib/runtimeDebugSanitizer.ts` redacts:
- API keys, JWT, bearer tokens, Supabase URLs
- Unix/Windows file paths
- Emails, phone numbers
- Keys containing: `stack`, `trace`, `env`, `api_key`, `token`, `jwt`, `secret`, `password`, `authorization`, `bearer`, `command`, `args`, `stdout`, `stderr`, `raw`, `payload`, `memory_content`, `provider_raw`, `tool_raw_result`

## 9. Tests

**370 tests across 42 test suites** — all passing.

| Suite | Count |
|-------|-------|
| Phase 5 — Design System | 6 files: OmniButton, OmniCard, OmniBadge, OmniTabs, OmniSkeleton, OmniThemeProvider |
| Phase 1 — Shell | 5 files: OmniShell, OmniSidebar, OmniTopbar, OmniRightInspector, OmniMobileNav |
| Phase 2 — Runtime Truth | 2 files: RuntimeStatusBadge, RuntimeTruthBar |
| Phase 3 — Inspector | 2 files: RuntimeInspectorPanel, RuntimeSummaryTab |
| Phase 4 — Safety | 2 files: SafeJsonViewer, RedactedField |
| Phase 6 — Chat | 4 files: OmniChatPanel, OmniAssistantMessage, OmniComposer, OmniSendButton |
| Phase 7 — History | 2 files: HistoryPanel, HistorySessionCard |
| Phase 8+ — All feature modules | 7 files: Projects, Governance, Memory, Agents, Lab, ProviderCenter |
| State | 1 file: runtimeConsoleStore, omniShellStore |
| Legacy & existing | 11 files: ChatPage, ChatPanel, Layout, Sidebar, PuterDevRoutePage, RuntimePanel, RuntimeDebugSection, sanitizer, etc. |

## 10. Accessibility

- Skip-to-content link (first focusable element)
- ARIA landmarks: `banner`, `navigation`, `main`, `complementary`, `region`, `tabpanel`
- `aria-current="page"` on active nav items
- `aria-expanded` on collapsible sidebar
- `tablist`/`tab` roles on inspector and OmniTabs
- `aria-hidden` on decorative icons
- `role="alert"` on error notices

## 11. Mobile

- OmniMobileNav with slide-in drawer (framer-motion `AnimatePresence`)
- Backdrop overlay on sidebar open
- Responsive breakpoints at 1280px / 1040px / 720px
- Bottom tab bar for mobile navigation

## 12. Build & Lint

```bash
cd frontend
npm run dev          # vite dev server on :5173
npm run build        # vite build
npm run typecheck    # tsc --noEmit (0 errors)
npm test             # vitest run + runtime console verification (370 tests)
```
