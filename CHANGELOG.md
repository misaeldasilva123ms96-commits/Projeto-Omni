# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Professional repository documentation and contribution guides
- GitHub issue and pull request templates
- CI workflow for Python and Node validation

### Changed

- Deployment workflow now includes post-deploy health verification

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
