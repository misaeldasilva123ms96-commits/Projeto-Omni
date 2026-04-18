# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
