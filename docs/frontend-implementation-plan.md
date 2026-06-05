# Omni Cockpit — Implementation Plan (COMPLETED)

**Branch:** `ui/omni-cockpit-audit` → `main` ✅
**Status:** ALL PHASES IMPLEMENTED AND MERGED

---

## Execution Order

```
Phase 5 — Design System (foundation for all UI)
  ↓
Phase 1 — Omni Shell (layout unification)
  ↓
Phase 2 — Runtime Truth (topbar badges)
  ↓
Phase 3 — Runtime Inspector (right panel tabs)
  ↓
Phase 4 — Safe Debug Layer (sanitized viewers)
  ↓
Phase 6 — Chat Experience (enhanced chat)
  ↓
Phase 7 — History V2 (session management)
  ↓
Phase 8+ — Remaining roadmap items
```

> All phases executed in order via individual branches, consolidated into `ui/lab-mode`, merged into `ui/omni-cockpit-audit` (PR #294), then into `main` (PR #295).

---

## Phase 5 — Design System

**Branch:** `ui/design-system` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/ui/
  OmniThemeProvider.tsx    — React context for theme, localStorage persistence
  OmniButton.tsx           — variants: primary/secondary/ghost/danger
  OmniCard.tsx             — base card surface with variants
  OmniBadge.tsx            — status badge (success/warning/danger/info)
  OmniPanel.tsx            — glass panel container (wraps PanelCard)
  OmniTabs.tsx             — accessible tab component
  OmniTooltip.tsx          — tooltip component
  OmniStatusDot.tsx        — colored status indicator
  OmniSkeleton.tsx         — loading skeleton component
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/styles.css` | Add `:root.light` CSS variables for `--omni-*` tokens |
| `frontend/src/main.tsx` | Wrap App with `OmniThemeProvider` |
| `frontend/src/components/ui/Card.tsx` | Add `OmniCard` as a new named export (keep Card) |

### Acceptance Criteria

- Light/dark toggle works, persisted in localStorage
- OmniButton renders 4 variants correctly
- OmniBadge shows success/warning/danger/info states
- OmniTabs is keyboard-navigable with aria attributes
- All existing components retain their appearance in dark mode

### Rollback

- Remove `OmniThemeProvider` from `main.tsx`
- Restore `styles.css` from git

---

## Phase 1 — Omni Shell

**Branch:** `ui/omni-shell-foundation` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/shell/
  OmniShell.tsx              — unified 3-column layout
  OmniSidebar.tsx            — collapsible sidebar with sections
  OmniTopbar.tsx             — persistent top status bar
  OmniRightInspector.tsx     — right panel container
  OmniMobileNav.tsx          — responsive mobile navigation
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/app/App.tsx` | Wrap all views with `OmniShell` |
| `frontend/src/pages/ChatPage.tsx` | Remove `Layout` usage; pass props to `OmniShell` |
| `frontend/src/pages/DashboardPage.tsx` | Remove `AppShell` usage; use `OmniShell` |
| `frontend/src/pages/ObservabilityPage.tsx` | Remove `AppShell` usage; use `OmniShell` |
| `frontend/src/components/layout/AppShell.tsx` | Add deprecation comment |
| `frontend/src/components/layout/Layout.tsx` | Add deprecation comment |

### Acceptance Criteria

- ChatPage renders correctly with OmniShell
- DashboardPage renders correctly with OmniShell
- ObservabilityPage renders correctly with OmniShell
- Sidebar collapses/expands
- Inspector panel opens/closes
- Mobile tabs work (preserve existing behavior)

### Rollback

- Revert `App.tsx` to use AppShell/Layout directly
- Remove `OmniShell` import from pages

---

## Phase 2 — Runtime Truth

**Branch:** `ui/runtime-truth` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/runtime/
  RuntimeStatusBadge.tsx     — runtime mode badge (Full/Partial/Fallback)
  ProviderStatusBadge.tsx    — provider badge (Local/BYOK/Managed)
  GovernanceBadge.tsx        — governance decision badge
  TokenUsageMeter.tsx        — token usage bar with quota
  PlanBadge.tsx              — plan badge (Free/BYOK/Pro/Local)
  RuntimeTruthBar.tsx        — composite bar for topbar
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/shell/OmniTopbar.tsx` | Use RuntimeTruthBar as content |
| `frontend/src/components/status/RuntimePanel.tsx` | Reuse RuntimeStatusBadge + ProviderStatusBadge |
| `frontend/src/types.ts` | Add optional `GovernanceSummary` type |

### Acceptance Criteria

- Topbar shows runtime mode with color indicator
- Fallback mode is visually prominent
- Provider shown when available
- Token usage shown as bar (not just numbers)
- Governance shown as badge when available

---

## Phase 3 — Runtime Inspector

**Branch:** `ui/runtime-inspector` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/runtime/
  RuntimeInspectorPanel.tsx   — tabbed container
  RuntimeSummaryTab.tsx       — runtime_mode, reason, fallback, provider, latency, tokens
  RuntimeGovernanceTab.tsx    — decision, category, policy, blocks
  RuntimeToolsTab.tsx         — tool name, category, status, duration, result
  RuntimeProviderTab.tsx      — provider diagnostics, fallback chain, latency
  RuntimeMemoryTab.tsx        — memory status
  RuntimeOilTab.tsx           — OIL envelope display
  RuntimeLogsTab.tsx          — safe logs display
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/status/RuntimePanel.tsx` | Replace debug toggle with tabs; keep top summary |
| `frontend/src/components/shell/OmniRightInspector.tsx` | Default to RuntimeInspectorPanel |

### Acceptance Criteria

- 8 tabs render in the inspector panel
- Summary tab shows existing RuntimePanel content
- Each tab shows real data or "não disponível"
- No sensitive data exposed in any tab

---

## Phase 4 — Safe Debug Layer

**Branch:** `ui/safe-debug` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/safety/
  SafeJsonViewer.tsx       — tree view with automatic redaction
  SafeDebugPanel.tsx       — structured debug panel
  RedactedField.tsx        — single redacted value display
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/lib/runtimeDebugSanitizer.ts` | Add `redactDebugPayload()` export |
| `frontend/src/components/runtime/RuntimeLogsTab.tsx` | Use SafeJsonViewer |

### Acceptance Criteria

- All dangerous fields show `[REDACTED]`
- SafeJsonViewer handles nested objects
- Tests cover dangerous payload patterns
- Existing sanitizer tests pass

---

## Phase 6 — Chat Experience

**Branch:** `ui/chat-experience` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/chat/
  OmniChatPanel.tsx         — enhanced wrapper
  OmniMessageList.tsx       — message list with scroll management
  OmniUserMessage.tsx       — user message component
  OmniAssistantMessage.tsx  — assistant message with badges + actions
  OmniSystemNotice.tsx      — system notice
  OmniComposer.tsx          — enhanced composer
  OmniAttachmentButton.tsx  — attachment button
  OmniSendButton.tsx        — send button with states
  OmniStopButton.tsx        — stop button
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/pages/ChatPage.tsx` | Use OmniChatPanel |
| `frontend/src/components/chat/ChatPanel.tsx` | Refactor internals |

### Acceptance Criteria

- Copy response button works
- Retry on failed messages
- Empty state shows onboarding (not hardcoded SaaS)
- Chat turn detail shows runtime info
- Streaming animation preserved

---

## Phase 7 — History V2

**Branch:** `ui/history-v2` — ✅ COMPLETED

### Files to Create

```
frontend/src/components/history/
  HistoryPanel.tsx           — full history view
  HistoryFilters.tsx         — filter bar
  HistorySessionCard.tsx     — session card with runtime indicators
  HistorySessionDetail.tsx   — expanded session view
```

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/layout/Sidebar.tsx` | Add session list with runtime indicators |
| `frontend/src/pages/ChatPage.tsx` | Load sessions from storage |

### Acceptance Criteria

- History is searchable
- Filters for runtime mode, provider, date
- Sessions show runtime indicators
- Click to restore session

---

## Phase 8+ (Completed Branches)

| Branch | Status |
|--------|--------|
| `ui/provider-center` | ✅ COMPLETED |
| `ui/token-usage` | ✅ COMPLETED |
| `ui/projects` | ✅ COMPLETED |
| `ui/governance-center` | ✅ COMPLETED |
| `ui/memory-center` | ✅ COMPLETED |
| `ui/agents-center` | ✅ COMPLETED |
| `ui/lab-mode` | ✅ COMPLETED |
| `ui/mobile` | ✅ COMPLETED |
| `ui/accessibility` | ✅ COMPLETED |
| `ui/frontend-testing` | ✅ COMPLETED (42 suites, 370 tests) |
| `ui/product-polish` | ✅ COMPLETED |

---

## Contract Addition: Governance

Add to `frontend/src/types.ts` (backward-compatible):

```typescript
export type GovernanceSummary = {
  decision: 'allowed' | 'blocked' | 'requires_approval' | 'unknown'
  category?: string
  policy?: string
  reason?: string
  riskLevel?: 'low' | 'medium' | 'high' | 'critical'
}
```

Add to `RuntimeMetadata`:

```typescript
export type RuntimeMetadata = {
  // ... existing fields
  governance?: GovernanceSummary  // NEW
}
```

Extraction helper in `lib/runtimeDebugSanitizer.ts`:

```typescript
export function extractGovernanceSummary(
  metadata: RuntimeMetadata | null
): GovernanceSummary | null {
  if (!metadata) return null
  const raw = metadata.cognitiveRuntimeInspection?.governance
  if (!raw || typeof raw !== 'object') return null
  const record = raw as Record<string, unknown>
  const decision = ['allowed', 'blocked', 'requires_approval', 'unknown']
    .includes(String(record.decision))
    ? (record.decision as GovernanceSummary['decision'])
    : 'unknown'
  return {
    decision,
    category: String(record.category ?? ''),
    policy: String(record.policy ?? ''),
    reason: String(record.reason ?? ''),
    riskLevel: record.riskLevel as GovernanceSummary['riskLevel'],
  }
}
```
