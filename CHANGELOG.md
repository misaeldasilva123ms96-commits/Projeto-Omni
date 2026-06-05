# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

#### Frontend Cockpit Audit — All 19 Phases (PRs #294, #295)
- **Phase 5 — Design System:** OmniThemeProvider (light/dark toggle, localStorage), OmniButton (4 variants), OmniCard, OmniBadge, OmniPanel, OmniTabs (accessible), OmniTooltip, OmniStatusDot, OmniSkeleton
- **Phase 1 — Omni Shell:** OmniShell (unified 3-column layout), OmniSidebar (collapsible), OmniTopbar (status bar), OmniRightInspector (tabbed container), OmniMobileNav (responsive drawer)
- **Phase 2 — Runtime Truth:** RuntimeStatusBadge, ProviderStatusBadge, GovernanceBadge, TokenUsageMeter, PlanBadge, RuntimeTruthBar
- **Phase 3 — Runtime Inspector:** RuntimeInspectorPanel with 8 tabs (Summary, Runtime, Governance, Provider, Tools, Memory, OIL, Safe Logs)
- **Phase 4 — Safe Debug:** SafeJsonViewer (tree view with redaction), SafeDebugPanel, RedactedField
- **Phase 6 — Chat Experience:** OmniChatPanel, OmniComposer, OmniMessageList, OmniUserMessage, OmniAssistantMessage (with copy/retry/badges), OmniSystemNotice, OmniAttachmentButton, OmniSendButton, OmniStopButton
- **Phase 7 — History V2:** HistoryPanel (searchable), HistoryFilters, HistorySessionCard, HistorySessionDetail
- **Phase 8+ — Provider Center:** ProviderCenterPage, ProviderSettingsPanel
- **Phase 8+ — Token Usage:** TokenUsagePage, TokenBudgetWarning
- **Phase 8+ — Projects CRUD:** OmniProjectsPanel, OmniProjectCard, OmniProjectForm, useProjects (Supabase-backed)
- **Phase 8+ — Governance:** GovernanceCenterPanel, GovernancePolicyCard
- **Phase 8+ — Memory:** MemoryCenterPanel, MemoryEntryCard, Supabase persistence
- **Phase 8+ — Agents:** AgentsCenterPanel, OmniAgentCard
- **Phase 8+ — Lab Mode:** LabModePanel (sandbox)
- **Phase 8+ — Mobile:** OmniMobileNav with backdrop overlay, AnimatePresence drawer, responsive breakpoints
- **Phase 8+ — Accessibility:** Skip-to-content link, ARIA landmarks/labels/roles, aria-current, aria-expanded, tablist/tab roles
- **Phase 8+ — Tests:** 33 new test suites (now 42 total, 370 tests)
- **Phase 8+ — Product Polish:** PageHero headers on 7 pages, ErrorNotice, OmniButton replacements, rounded-3xl cards, consistent border radius

- Current-state runtime audit documentation for the provider/BYOK/diagnostics work through PR #171.
- Runtime provider documentation covering Groq, OpenRouter, OpenAI, Anthropic, Gemini, Ollama, LM Studio, DeepSeek metadata, and `local-heuristic`.
- Session-only BYOK documentation with fail-closed policy and privacy boundaries.
- Public-safe runtime diagnostics documentation for `provider_diagnostics_snapshot` and `GET /api/v1/runtime/runner-smoke`.
- `.env.example` placeholders for current provider model envs, OpenRouter, local provider config, and JS runtime selection.
- Professional `docs/` tree: architecture, governance, evolution, operations, setup, product, and phase index (`docs/README.md`, `docs/phases/README.md`).
- Archive of legacy root Markdown reports under `docs/reports/repository-archive/` (git history preserved via `git mv`).
- Professional repository documentation and contribution guides
- GitHub issue and pull request templates
- CI workflow for Python and Node validation
- Governed evolution proposal baseline (Phase 30.17)
- Deterministic proposal validation loop with history tracking (Phase 30.18)
- Governed bounded patch application path with rollback safety (Phase 30.19)
- Evolution control-plane closure helpers and contract normalization (Phase 30.20)

### Changed

- Root documentation minimalism: long-form Markdown moved from repository root into `docs/` (contributing guide at `docs/setup/contributing.md`; GitHub entry via `.github/CONTRIBUTING.md`).
- `README.md`, `ARCHITECTURE.md`, and `ROADMAP.md` updated for **Phase 40** positioning and cross-links.
- Deployment workflow now includes post-deploy health verification
- Governed evolution observability block aligned with proposal/validation/application/rollback lifecycle summaries
- Runtime governance/evolution documentation refreshed for Phase 30.20 repository maturity

## [1.0.0] - 2026-04-03

### Added

- Rust bridge with subprocess-based Python runtime integration
- Python brain orchestrator with hybrid memory, sessions, and transcripts
- Node reasoning runner with formal payload validation
- Internal multi-agent swarm with router, planner, executor, critic, and memory agents
- Evolution layer with response scoring, pattern analysis, strategy snapshots, and rollback support
- Docker and GitHub Actions deployment foundation

### Changed

- Repository structure consolidated around production-ready runtime layers

### Fixed

- Removed absolute Windows runtime paths from production code paths

### Removed

- Legacy duplicated runtime directories in the Python backend
