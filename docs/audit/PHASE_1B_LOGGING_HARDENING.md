# PHASE 1B LOGGING HARDENING — Projeto Omni

Date: 2026-04-30

Branch: hardening/logging-01b

Base branch: hardening/shell-01a

Base commit: 5aef75edee327f97793fdfe2e9bd1f6e26c19acd

Statement: Phase 1B only hardens specialist/runtime error logging and fallback exposure. Runtime architecture and provider routing behavior were not rewritten.

## Files Changed

- `features/multiagent/specialists/specialistErrorPolicy.js`
- `features/multiagent/specialists/dependencyImpactSpecialist.js`
- `features/multiagent/specialists/testSelectionSpecialist.js`
- `tests/runtime/specialistErrorPolicy.test.mjs`
- `docs/audit/PHASE_1B_LOGGING_HARDENING.md`

## Logging Paths Hardened

- `reviewDependencyImpact(...)` specialist failure and timeout fallback path.
- `selectVerificationTargets(...)` specialist failure and timeout fallback path.
- Shared specialist fallback logger used by both mapped specialist surfaces.

## Sanitizer Behavior

The centralized sanitizer returns only:

- `name`
- `message`
- `code`

The sanitizer explicitly avoids returning raw:

- stack
- cause
- path
- env
- syscall
- stdout
- stderr
- command
- raw payloads
- provider raw responses
- memory raw content

Path-like and token-like substrings in debug messages are redacted before exposure.

## Public Demo / Debug Precedence

Public demo mode always wins over internal debug mode.

Canonical flags:

- `OMNI_PUBLIC_DEMO_MODE=true`
- `OMNI_DEBUG_INTERNAL_ERRORS=true`

Compatibility aliases:

- `OMINI_PUBLIC_DEMO_MODE=true`
- `OMINI_DEBUG_INTERNAL_ERRORS=true`

Internal debug details are included only when debug mode is enabled and public demo mode is false.

## Fallback Shape

Specialist failure now returns a structured public-safe degraded fallback:

```json
{
  "invoked": true,
  "degraded": true,
  "specialist_id": "dependency_impact_specialist",
  "fallback": true,
  "error_public_code": "SPECIALIST_FAILED",
  "error_public_message": "Specialist execution failed. Using fallback.",
  "internal_error_redacted": true
}
```

When internal debug is allowed, the fallback may include:

```json
{
  "internal_debug": {
    "name": "Error",
    "message": "sanitized message",
    "code": "E_CODE"
  }
}
```

## Tests Run / Results

- `node scripts/js-runtime-launcher.mjs tests/runtime/specialistErrorPolicy.test.mjs` — PASS
- `node scripts/js-runtime-launcher.mjs tests/e2e/specialistHardening.test.mjs` — PASS
- `npm test` — PASS
- `npm run test:js-runtime` — PASS
- `npm run test:python:pytest` — TIMEOUT after 300 seconds

## Inherited Pytest Timeout Note

The `npm run test:python:pytest` timeout repeated the broad pytest timeout already observed in Phase 1A. No evidence was found that Phase 1B changes caused this timeout because Phase 1B touched only JS specialist logging/fallback surfaces and narrow JS tests passed.

## Known Limitations

- This phase hardens the mapped specialist failure paths only. Other runtime surfaces that may log raw errors remain future audit targets.
- Internal debug still includes sanitized error message text, so new sanitizer bypasses should be covered by future tests if additional specialist wrappers are added.

## Rollback

Rollback command:

```bash
git revert <phase-1b-commit>
```

## Gate 1B Status

PASSED:

- Raw specialist errors are not logged in normal mode.
- Public demo mode suppresses internal debug details.
- Debug mode uses sanitized error object only.
- Specialist fallback is structured and public-safe.
- Narrow tests were added.
- No raw stack/path/env/payload/stdout/stderr exposure is present in the hardened specialist fallback paths.
- No merge into main.

No merge into main: confirmed.
