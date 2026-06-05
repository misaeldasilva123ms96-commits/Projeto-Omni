# Omni Cockpit — Phase Roadmap

**Branch:** `ui/omni-cockpit-audit` → **MERGED INTO `main`** via PR #295

---

## Branch Map (ALL PHASES COMPLETE)

```
Main (protected)
 └── ui/omni-cockpit-audit ◄── MERGED ✅
      │
      ├── ui/design-system            Phase 5  — ✅ COMPLETE
      ├── ui/omni-shell-foundation    Phase 1  — ✅ COMPLETE
      ├── ui/runtime-truth            Phase 2  — ✅ COMPLETE
      ├── ui/runtime-inspector        Phase 3  — ✅ COMPLETE
      ├── ui/safe-debug               Phase 4  — ✅ COMPLETE
      ├── ui/chat-experience          Phase 6  — ✅ COMPLETE
      ├── ui/history-v2               Phase 7  — ✅ COMPLETE
      ├── ui/provider-center          Phase 8+ — ✅ COMPLETE
      ├── ui/token-usage              Phase 8+ — ✅ COMPLETE
      ├── ui/projects                 Phase 8+ — ✅ COMPLETE
      ├── ui/governance-center        Phase 8+ — ✅ COMPLETE
      ├── ui/memory-center            Phase 8+ — ✅ COMPLETE
      ├── ui/agents-center            Phase 8+ — ✅ COMPLETE
      ├── ui/lab-mode                 Phase 8+ — ✅ COMPLETE
      ├── ui/mobile                   Phase 8+ — ✅ COMPLETE
      ├── ui/accessibility            Phase 8+ — ✅ COMPLETE
      ├── ui/frontend-testing         Phase 8+ — ✅ COMPLETE
      └── ui/product-polish           Phase 8+ — ✅ COMPLETE
```

All branches consolidated into `ui/lab-mode`, merged into `ui/omni-cockpit-audit` (PR #294), then into `main` (PR #295).

---

## Phase Details

### Phase 5 — Design System

| Field | Value |
|-------|-------|
| Branch | `ui/design-system` |
| Depends on | Nothing |
| Est. files created | 9 |
| Est. files modified | 3 |
| Risk level | Medium |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |
| Rollback | Revert `main.tsx`, restore `styles.css` |

### Phase 1 — Omni Shell

| Field | Value |
|-------|-------|
| Branch | `ui/omni-shell-foundation` |
| Depends on | Phase 5 (for UI components) |
| Est. files created | 5 |
| Est. files modified | 6 |
| Risk level | Medium |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |
| Rollback | Revert `App.tsx`, restore AppShell/Layout usage |

### Phase 2 — Runtime Truth

| Field | Value |
|-------|-------|
| Branch | `ui/runtime-truth` |
| Depends on | Phase 1 (for OmniTopbar) |
| Est. files created | 6 |
| Est. files modified | 3 |
| Risk level | Low |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |

### Phase 3 — Runtime Inspector

| Field | Value |
|-------|-------|
| Branch | `ui/runtime-inspector` |
| Depends on | Phase 2 (for badges used in tabs) |
| Est. files created | 8 |
| Est. files modified | 2 |
| Risk level | Low |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |

### Phase 4 — Safe Debug Layer

| Field | Value |
|-------|-------|
| Branch | `ui/safe-debug` |
| Depends on | Nothing (independent implementation) |
| Est. files created | 3 |
| Est. files modified | 2 |
| Risk level | Low |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |

### Phase 6 — Chat Experience

| Field | Value |
|-------|-------|
| Branch | `ui/chat-experience` |
| Depends on | Phase 5 (for UI components), Phase 2 (for runtime badges) |
| Est. files created | 9 |
| Est. files modified | 2 |
| Risk level | Medium |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |

### Phase 7 — History V2

| Field | Value |
|-------|-------|
| Branch | `ui/history-v2` |
| Depends on | Phase 6 (for session data structure) |
| Est. files created | 4 |
| Est. files modified | 3 |
| Risk level | Low |
| Validation | `npm run typecheck`, `npm run build`, `npm test` |

### Phase 8+ — Remaining

Each future phase follows same template. No dependencies beyond those listed.

---

## Success Criteria Per Phase

### Phase 5
- [x] Light/dark toggle works
- [x] Theme persisted in localStorage
- [x] OmniButton renders 4 variants
- [x] OmniTabs keyboard accessible
- [x] No breaking changes to existing components

### Phase 1
- [x] All views use OmniShell
- [x] Sidebar collapsible
- [x] Inspector open/close
- [x] Mobile tabs preserved
- [x] AppShell/Layout deprecated but importable

### Phase 2
- [x] Runtime mode visible in topbar
- [x] Fallback state prominent
- [x] Provider visible
- [x] Token usage visible
- [x] Governance visible when available

### Phase 3
- [x] 8 tabs in inspector
- [x] Summary tab matches current RuntimePanel
- [x] Real data displayed per tab
- [x] "não disponível" for missing data

### Phase 4
- [x] Dangerous fields → [REDACTED]
- [x] SafeJsonViewer handles nested objects
- [x] Tests pass for dangerous payloads

### Phase 6
- [x] Copy response works
- [x] Retry on failure
- [x] No hardcoded SaaS preview in empty state
- [x] Streaming preserved
- [x] Chat turn details expandable

### Phase 7
- [x] History searchable
- [x] Filters work (runtime, provider, date)
- [x] Sessions show runtime indicators
- [x] Click restores session

---

## Full Branch Checklist (Completion Gates)

All branches:
- [x] Created from parent branch (not main)
- [x] Contains only scoped changes
- [x] `npm run typecheck` passes
- [x] `npm run build` passes
- [x] `npm test` passes
- [x] No merge into main (until final PR)
- [x] No push to main (until final PR)
- [x] Report generated with: branch, files changed, validation results, risks, next phase

---

## Final Status

**Merge target:** `ui/omni-cockpit-audit` → `main` via PR #295 ✅

**Frontend audit complete.** All 19 phases implemented, tested, and merged into `main`.
- 42 test files, 370 tests — all passing
- 0 type errors (TypeScript 6.0.3)
- Build: `npm run build` passes clean
- Runtime console verification: all checks pass
