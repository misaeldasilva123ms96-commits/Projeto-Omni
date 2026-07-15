# Omni Current Runtime State Audit

Date: 2026-07-14

This page summarizes the public repository state after the evidence-based audit remediation cycle merged through PR #542. It describes implemented boundaries separately from paths that are present but not yet connected end to end.

## Current Implementation Status

Omni is a governed multi-runtime cognitive system. The normal public chat path is:

```txt
Rust API boundary
  -> Python BrainOrchestrator
  -> Node QueryEngine/provider runner
  -> Python public payload sanitization
  -> Rust public response
```

Node is the default JavaScript runtime. Bun is available only when explicitly selected with `OMNI_JS_RUNTIME_BIN=bun`. `OMNI_*` is the canonical configuration namespace. The deprecated `OMINI_*` aliases remain temporarily supported under the migration policy in `docs/runtime/env-alias-migration.md`; canonical values win conflicts.

## Implemented

- Rust public API boundary: `/chat`, `/api/v1/chat`, `/health`, `/api/v1/status`, and `/api/v1/runtime/runner-smoke`.
- Python `BrainOrchestrator` bridge, runtime classification, governance, learning signals, and public payload shaping.
- Node QueryEngine runner with provider routing, fallback, runtime truth, and provenance metadata.
- Provider adapters for Groq, OpenRouter, OpenAI, Anthropic, Gemini, Ollama, and LM Studio.
- DeepSeek registry metadata with unsupported/non-executable status.
- Provider diagnostics that separate configured/executable capability from cached reachable/healthy evidence.
- Session-only BYOK typed boundary with request-scoped credential overlay and fail-closed fallback policy.
- Authenticated provider-settings API and frontend Provider Center for saving, updating, deleting, and explicitly testing provider credentials.
- AES-256-GCM encrypted credential storage, keyed by authenticated user and provider.
- Redaction coverage for API keys, auth headers, key-bearing URLs, raw request/response bodies, stack traces, unsafe status text, and credential objects.
- Workspace containment for local engineering file tools, including traversal and symlink/junction escape defenses.
- Supabase JWT issuer, expiry, and audience validation for protected routes.
- Required live Rust -> Python -> Node -> Rust contract validation in CI.
- Public-safe runner smoke diagnostic endpoint.

## Experimental Or Limited

- Persistent Python and Node service modes exist as opt-in architecture paths, but subprocess mode remains the default contributor/demo path.
- Provider credentials can be managed persistently, but the normal chat runtime does not yet resolve the authenticated user's stored credential: `JSRuntimeAdapter.build_env()` calls the credential merge without a `user_id`. Session request credentials and system environment credentials remain the executable chat inputs.
- Cached provider health is created only by an explicit provider test. The router does not probe providers on every request.
- Ollama and LM Studio require explicit local URL environment variables and are not auto-probed.
- Compatibility execution remains a supported degraded path and can still be selected for conservative or ambiguous prompt families.
- Runtime truth can prove which path ran; it does not guarantee that a downstream provider or tool action succeeded.
- The runtime remains a controlled-demo/research system, not a production autonomous decision system.

## Not Implemented

- End-to-end use of authenticated stored provider credentials by the normal chat execution path.
- Billing, governance quotas, and abuse controls for hosted provider access.
- DeepSeek execution adapter.
- Automatic main promotion or autonomous repository mutation.
- A current reproducible cross-runtime load/throughput baseline; the older measurements are retained only in `docs/reports/repository-archive/PERFORMANCE_BASELINE.md`.

## Latest Audit Remediation Cycle

The current state incorporates these merged evidence-based corrections:

- #537 contained engineering tool paths inside the approved workspace.
- #538 restored cognitive execution routing for deterministic tool-capable prompts.
- #539 enforced Supabase JWT audience validation.
- #540 made a live cross-runtime contract a required CI check.
- #541 added explicit cached provider reachability and health signals.
- #542 established canonical `OMNI_*` configuration and governed legacy alias migration.

All checks attached to PRs #537-#542 completed without failure or pending status before this audit refresh.

## Validation Matrix

Recommended broad validation:

```bash
cargo test --locked --manifest-path backend/rust/Cargo.toml
npm run test:js-runtime
npm run test:python:pytest
npm run test:security
npm run validate:env-aliases
npm run validate:audit-pack
npm run validate:public-demo
```

Use frontend validation for UI/debug-surface changes:

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## Follow-Up Work

- Define and security-review how authenticated chat identity reaches Python credential resolution before wiring stored provider credentials into execution.
- Keep stored credentials fail-closed: no fallback from a user's selected credential to an owner/system key.
- Build a reproducible offline and live performance baseline before setting latency or throughput targets.
- Continue increasing non-compat execution activation and decision quality with contract-backed prompt families.
- Continue expanding cross-language tests whenever runtime truth fields or credential boundaries change.
