# Omni Current Runtime State Audit

Date: 2026-05-21

This page summarizes the current public repository state after the provider, BYOK, diagnostics, redaction, and Node-default runtime updates merged through PR #171.

## Current Implementation Status

Omni is a governed multi-runtime cognitive system. The normal public chat path is:

```txt
Rust API boundary
  -> Python BrainOrchestrator
  -> Node QueryEngine/provider runner
  -> Python public payload sanitization
  -> Rust public response
```

Node is the default JavaScript runtime. Bun is available only when explicitly selected with `OMNI_JS_RUNTIME_BIN=bun`. The deprecated `OMINI_JS_RUNTIME_BIN` alias remains supported when `OMNI_JS_RUNTIME_BIN` is unset.

## Implemented

- Rust public API boundary: `/chat`, `/api/v1/chat`, `/health`, `/api/v1/status`, and `/api/v1/runtime/runner-smoke`.
- Python `BrainOrchestrator` bridge, runtime classification, governance, learning signals, and public payload shaping.
- Node QueryEngine runner with provider routing, fallback, runtime truth, and provenance metadata.
- Provider adapters for Groq, OpenRouter, OpenAI, Anthropic, Gemini, Ollama, and LM Studio.
- DeepSeek registry metadata with unsupported/non-executable status.
- Legacy `provider_diagnostics` array plus `provider_diagnostics_snapshot` object for complete provider state.
- Session-only BYOK typed boundary and fail-closed execution policy.
- Redaction coverage for API keys, auth headers, key-bearing URLs, raw request/response bodies, stack traces, unsafe status text, and credential objects.
- Public-safe runner smoke diagnostic endpoint.

## Experimental Or Limited

- Persistent Python and Node service modes exist as opt-in architecture paths, but subprocess mode is still the default contributor/demo path.
- BYOK is session-only. There is no encrypted persistent user credential storage and no frontend key-entry UI.
- Ollama and LM Studio require explicit local URL envs and are not auto-probed.
- The runtime remains a controlled-demo/research system, not a production autonomous decision system.

## Not Implemented

- Persistent BYOK storage.
- Tenant/user credential vault.
- Billing, governance quotas, and abuse controls for hosted provider access.
- Frontend BYOK management UI.
- DeepSeek execution adapter.
- Automatic main promotion or autonomous repository mutation.

## Recent PR Range

The current state incorporates merged PRs #157-#171:

- #157 OpenRouter adapter
- #158 OpenAI adapter
- #159 Anthropic adapter
- #160 Gemini adapter
- #161 Ollama/LM Studio local adapters
- #162 provider env propagation
- #163 provider diagnostics snapshot
- #164 session BYOK typed boundary
- #165 BYOK execution fail-closed policy
- #166 cross-language BYOK tests
- #167 provider router policy matrix tests
- #168 provider redaction matrix and status text hardening
- #169 diagnostics snapshot compatibility tests
- #170 Node default JS runtime
- #171 public-safe runner smoke diagnostic

## Validation Matrix

Recommended broad validation:

```bash
git diff --check
npm run test:js-runtime
npm run test:security
python -m pytest tests/runtime/test_bridge_pipeline.py tests/runtime/test_cognitive_orchestration.py -v
cd backend/rust && cargo test
```

Use frontend validation for UI/debug-surface changes:

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

## Follow-Up Work

- Add a frontend BYOK UX only after storage and policy decisions are explicit.
- Add encrypted persisted user credential storage as a separate security-reviewed phase.
- Add a dedicated provider diagnostics UI for the snapshot object.
- Add deployment documentation for reading `/api/v1/runtime/runner-smoke` after Render/Cloudflare deploys.
- Continue expanding cross-language tests when runtime truth fields change.
