# Omni Documentation

This directory is the **canonical home** for Omni documentation. The repository root keeps short entrypoints; extended runtime, audit, training, and release material lives here.

## Start here

| Area | Path |
|------|------|
| Current root roadmap/status index | [../ROADMAP.md](../ROADMAP.md) |
| Product vision and product-maturity roadmap | [product/vision.md](product/vision.md), [product/roadmap.md](product/roadmap.md) |
| Architecture (runtime, layers, contracts) | [architecture/](architecture/) |
| Runtime truth and bridge contract | [architecture/runtime-modes.md](architecture/runtime-modes.md), [architecture/bridge-response-contract.md](architecture/bridge-response-contract.md) |
| Current testing matrix | [operations/testing.md](operations/testing.md) |
| Public demo readiness | [release/PUBLIC_DEMO_READINESS.md](release/PUBLIC_DEMO_READINESS.md) |
| Training readiness | [training/TRAINING_READINESS.md](training/TRAINING_READINESS.md) |
| Known limitations | [audit/KNOWN_LIMITATIONS.md](audit/KNOWN_LIMITATIONS.md) |
| Phase history and current maturity | [phases/README.md](phases/README.md) |
| Governance and safety posture | [governance/](governance/) |
| Evolution and improvement pipelines | [evolution/](evolution/) |
| Operations (observability, tests, runtime behavior) | [operations/](operations/) |
| Setup (dev, env, deploy) | [setup/](setup/) |
| Frontend ↔ Rust API (compatibility matrix) | [frontend/integration-matrix.md](frontend/integration-matrix.md) |
| Backend public API evolution | [backend/public-api-roadmap.md](backend/public-api-roadmap.md) |
| Legacy reports, models, and phase notes (archived from root) | [reports/repository-archive/](reports/repository-archive/) |

## Repository root (minimal)

The root keeps short, stable entrypoints only:

- `README.md` — positioning and navigation
- `ROADMAP.md` — current roadmap/status index with links into audit, architecture, training, release, and product docs
- `CHANGELOG.md` — release history
- `GOVERNANCE.md` — non-negotiable rules + link to `docs/governance/`
- `LICENSE`

There is no required root `ARCHITECTURE.md` entrypoint in the current audited tree. Use `docs/architecture/` for architecture material.

## Contributing

See [setup/contributing.md](setup/contributing.md).
