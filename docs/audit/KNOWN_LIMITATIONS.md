# Known Limitations

> Historical configuration note: Any `OMINI_*` names below are preserved only as immutable audit evidence. They are obsolete and are not accepted by the current runtime, which recognizes only `OMNI_*` configuration.

## Latest Verified Status

Latest documentation audit base:

| Item | Latest verified status |
| --- | --- |
| Branch audited | `validation/rust-run-control-fix` |
| Commit audited | `9a6c527254fd01f6f07e9f9990b2156c07f34934` |
| Static audit validator | Passed in latest audit pass |
| Static public-demo validator | Passed in latest audit pass |
| Rust/Python/JS/security suites | Passed in latest audit pass |
| Docker image build/runtime smoke | Not reverified in latest audit pass |

Older audit notes may record a previous Docker build or smoke result. Treat those entries as historical unless the Docker build and runtime smoke are rerun in the target environment.

## Docker Validation

Docker image build still needs daemon-backed validation in the environment that will host any controlled demo URL. Docker runtime smoke also needs target-environment validation. Static validators and `docker compose config` are useful gates, but they do not prove the image starts, serves `/health`, accepts `/chat`, or enforces runtime policies inside the container.

## Public Traffic

Public traffic needs edge/platform rate limiting. The Rust limiter is in-memory and per process, so it is not enough for multi-instance or hostile public traffic.

## Runtime Scope

Subprocess remains default. Python and Node service modes are opt-in. In-memory circuit breaker state is process-local. Service lifecycle, cross-process health, and multi-instance coordination are not production-complete.

## Training

No training started. No real dataset export was produced. Training readiness defines schemas, validation, and dry-run export only. Fallback, matcher, tool-blocked, provider-failure, governance-blocked, unsafe, or heavily redacted records are not positive examples.

## Historical Data

Historical logs are not rewritten. Redaction applies to new learning/runtime persistence paths after the hardening phases.

## Docker And Local Environment

The demo container profile is not a production deployment profile. It uses ephemeral local storage paths and process-local controls. Provider quota management, WAF/edge controls, monitoring, retention, and platform secrets remain deployment responsibilities.

## Test Suite Limitations

Some broad wrappers can be slow or environment-sensitive. The live HTTP contract is now mandatory in its dedicated CI workflow and uses the canonical `OMNI_E2E_API_URL`; local ad-hoc execution still needs a running API and that variable (or the temporary `OMINI_E2E_API_URL` alias). Docker runtime validation depends on a working Docker daemon.

## Release Status

No production release yet. No GitHub release, public deployment, tag, automatic merge, or training run is authorized by this audit pack.
