# Known Limitations

## Docker Validation

Docker image build still needs daemon-backed validation before any public demo URL is shared. Phase 14 validated `docker compose config`, but image build was blocked because the local Docker daemon was unavailable.

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

Some broad wrappers can be slow or environment-sensitive. Phase 14 observed one transient Rust test failure that passed on serial and normal rerun. Docker build remains pending until Docker daemon is available.

## Release Status

No production release yet. No GitHub release, public deployment, tag, automatic merge, or training run is authorized by this audit pack.
