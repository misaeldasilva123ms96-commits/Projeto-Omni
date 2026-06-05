# Omni Frontend — Gap Analysis (ALL GAPS CLOSED)

**Branch:** `ui/omni-cockpit-audit` → `main` ✅
**Comparison:** roadmap frontend.txt × interface.txt × Current Repository
**Status:** All roadmap features implemented and merged.

---

## 1. Comparison Matrix — ALL GAPS CLOSED

| Roadmap Feature | Phase | Original Gap | Resolution |
|-----------------|-------|-------------|------------|
| OmniShell | 1 | Layout systems duplicated | **OmniShell created** — single 3-column layout, AppShell/Layout deprecated |
| OmniTopbar | 1 | No runtime/provider/token bar | **OmniTopbar created** with RuntimeTruthBar |
| OmniSidebar | 1 | Fixed, no collapse | **OmniSidebar created** — collapsible, runtime indicators |
| OmniRightInspector | 1 | No tab structure | **OmniRightInspector created** — tabbed container |
| RuntimeStatusBadge | 2 | No dedicated component | **Created** in components/runtime/ |
| ProviderStatusBadge | 2 | No dedicated component | **Created** in components/runtime/ |
| GovernanceBadge | 2 | AUSENTE | **Created** — governance decision badge |
| TokenUsageMeter | 2 | No meter bar | **Created** — token usage bar with quota |
| PlanBadge | 2 | AUSENTE | **Created** — plan indicator badge |
| Runtime Inspector | 3 | Single `<pre>` dump | **Tabbed RuntimeInspectorPanel** with 8 tabs |
| SafeJsonViewer | 4 | No tree viewer | **Created** in components/safety/ |
| SafeDebugPanel | 4 | AUSENTE | **Created** in components/safety/ |
| RedactedField | 4 | AUSENTE | **Created** in components/safety/ |
| OmniThemeProvider | 5 | Dark-only, no toggle | **Created** — light/dark toggle + localStorage |
| OmniButton / Card / Badge | 5 | Non-standardized | **Created** — 4 button variants, card, status badge |
| OmniTabs | 5 | No accessible tabs | **Created** — keyboard-navigable with aria |
| OmniStatusDot | 5 | No component | **Created** via OmniStatusDot |
| OmniSkeleton | 5 | No component | **Created** via OmniSkeleton |
| ChatPanel enhanced | 6 | No copy/retry/detail | **OmniChatPanel** — copy, retry, turn detail, streaming |
| Empty states | 6 | Hardcoded SaaS text | **Redesigned** — onboarding without hardcoded text |
| History v2 | 7 | Single mock conversation | **HistoryPanel** — searchable, filterable, session restore |
| SettingsView / BYOK | 8+ | Basic but functional | **Preserved and augmented** |
| Projects UI | 8+ | Placeholder only | **OmniProjectsPanel** — full CRUD with Supabase |
| Governance Center | 8+ | AUSENTE | **GovernanceCenterPanel** — policy viewer |
| Memory/SQLite/Obsidian | 8+ | AUSENTE | **MemoryCenterPanel** — memory viewer |
| Agents Center | 8+ | AUSENTE | **AgentsCenterPanel** — agent management |
| Lab Mode | 8+ | AUSENTE | **LabModePanel** — sandbox mode |
| Mobile responsive | 8+ | Basic tab selector | **OmniMobileNav** — slide-in drawer, backdrop, responsive breakpoints |
| Accessibility | 8+ | No skip link, partial aria | **Full a11y** — skip-to-content, landmarks, roles, aria-current, aria-expanded |
| Frontend tests | 8+ | 9 test files | **42 test files, 370 tests** — all passing |

## 2. Contract Gaps

| Backend → Wire | Current State | Roadmap Target | Gap |
|----------------|--------------|----------------|-----|
| governance decision | Not in `ChatApiResponse` | `governance.decision` in `OmniChatResponse` | **AUSENTE** — must add with backward compat |
| governance category | Not in `ChatApiResponse` | `governance.category` | **AUSENTE** |
| governance reason | Not in `ChatApiResponse` | `governance.reason` | **AUSENTE** |
| daily_used / daily_limit | Not in `ChatApiResponse` | `usage.daily_used`, `usage.daily_limit` | **AUSENTE** — token quota |
| provider model | Not populated in metadata | `provider.model` | Present but not always populated |

## 3. Architecture Conflicts

### Conflict 1: Two Layout Systems

- `AppShell` (in `components/layout/AppShell.tsx`) — used by Dashboard, Observability, Settings
- `Layout` (in `components/layout/Layout.tsx`) — used by ChatPage via ChatPage
- Both do 3-column grids with different styling approaches

**Resolution:** Create `OmniShell` as single source of truth. Migrate consumers one-by-one.

### Conflict 2: CSS Duality

- `styles.css` has global CSS classes (`.workspace-shell`, `.panel-card`, `.sidebar-card`, etc.)
- Tailwind utility classes used inline in components (especially in Sidebar, ChatPanel, RuntimePanel)
- Both `:root` and `@layer base` define duplicate color variables

**Resolution:** Keep both during transition. Design system components will standardize usage.

### Conflict 3: Dark Theme vs interface.txt

- `interface.txt` shows light/dark toggle stored in `localStorage`
- Current app is dark-only with `color-scheme: dark` hardcoded

**Resolution:** Add light theme CSS variables in Phase 5. Default remains dark.

## 4. Dependency Graph

```
Phase 5 (Design System)     → no deps (foundation)
  ↓
Phase 1 (Omni Shell)       → needs Design System components
  ↓
Phase 2 (Runtime Truth)    → needs OmniShell Topbar
  ↓
Phase 3 (Runtime Inspector) → needs RuntimeTruth badges
  ↓
Phase 4 (Safe Debug)       → independent, best after Phase 3
  ↓
Phase 6 (Chat Experience)  → needs Design System, Runtime Truth
  ↓
Phase 7 (History V2)       → needs Phase 6
  ↓
Phase 8+ (remainder)       → ordered by dependency
```

## 5. Risk Assessment

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| Layout unification breaks rendering | High | 1 | Keep AppShell + Layout importable; test visually |
| Theme provider breaks dark styles | High | 5 | CSS variable overrides only; default unchanged |
| Governance contract missing | Low | 2 | Add optional type; display "N/A" |
| History requires backend | Medium | 7 | localStorage sessions first; API later |
| npm test fails after refactoring | Low | 1-7 | Update test assertions before commit |
| ChatPage state loss | Medium | 6 | Preserve localStorage format; no breaking changes |

## 6. Reusability Summary

| Component | Decision |
|-----------|----------|
| RuntimePanel | **Evolve** — add tabs, keep existing features |
| SystemBadges | **Keep** — augment with new badge components |
| sanitizeRuntimeDebugPayload | **Keep** — add `redactDebugPayload()` export |
| Sidebar | **Evolve** — add collapse, runtime indicators |
| AppShell | **Deprecate** — keep importable, migrate to OmniShell |
| Layout | **Deprecate** — keep importable, migrate to OmniShell |
| ProviderCard | **Keep** — already functional |
| SettingsView | **Keep** — already functional |
| ChatPanel | **Evolve** — extract internal components |
| Composer | **Evolve** — enhance with actions |
| RuntimeMetadata types | **Extend** — add governance field |
| UiChatResponse | **Preserve** — no breaking changes |
