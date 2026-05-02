# Publishing Checklist

This checklist is for a controlled public demo only. It is not an automatic release, automatic merge, or production deployment instruction.

## Pre-Public-Demo Checklist

- Review `docs/audit/REMEDIATION_SUMMARY.md`.
- Review `docs/audit/SECURITY_FIXES.md`.
- Review `docs/audit/RUNTIME_TRUTH_CONTRACT.md`.
- Review `docs/audit/TEST_EVIDENCE.md`.
- Review `docs/audit/KNOWN_LIMITATIONS.md`.
- Confirm `docs/release/PUBLIC_DEMO_READINESS.md` is current.
- Confirm no GitHub release or tag is being created automatically.

## Required Commands

Run before public exposure:

```bash
npm run validate:audit-pack
npm run validate:public-demo
npm run test:security
npm test
npm run test:js-runtime
npm run test:python:pytest
npm --prefix frontend run typecheck
cd backend/rust && cargo test
python -m py_compile backend/python/brain_service.py backend/python/main.py
docker compose -f docker-compose.demo.yml config
docker build -f Dockerfile.demo -t omni-demo:public-demo .
git diff --check
```

Docker build is required before public exposure.

## Environment Checklist

Required demo env:

```txt
OMNI_PUBLIC_DEMO_MODE=true
OMINI_PUBLIC_DEMO_MODE=true
OMNI_ALLOW_SHELL_TOOLS=false
OMINI_ALLOW_SHELL_TOOLS=false
OMNI_DEBUG_INTERNAL_ERRORS=false
OMINI_DEBUG_INTERNAL_ERRORS=false
OMNI_RATE_LIMIT_ENABLED=true
OMNI_RATE_LIMIT_PER_MINUTE=30
OMNI_MAX_MESSAGE_CHARS=8000
OMNI_MAX_BODY_BYTES=65536
OMNI_INTENT_CLASSIFIER=regex
OMNI_MATCHER_MODE=enabled
OMNI_PYTHON_MODE=subprocess
OMNI_NODE_MODE=subprocess
```

Do not pass provider keys, Supabase service role keys, raw env dumps, private memory files, or local logs into the public demo.

## Secret Scan And Manual Review

- Inspect `.env.example`, Dockerfile, compose, release docs, and audit docs.
- Confirm placeholder-only examples.
- Confirm public diagnostics expose status booleans only.
- Confirm no stack traces, raw payloads, provider raw responses, memory raw content, tool raw results, stdout, stderr, or raw env are shown.

## Edge Rate Limit Checklist

- Add platform/edge rate limiting before public traffic.
- Keep Rust in-memory limiter enabled.
- Add upstream request size limits if the hosting platform supports them.
- Monitor abuse and quota usage.

## RLS And Supabase Checklist

If frontend Supabase is enabled:

- Confirm public anon key usage is intentional.
- Confirm service role keys are server-only and absent from demo container env.
- Confirm Row Level Security policies match public demo scope.
- Confirm diagnostics only expose configured/present booleans.

## Runtime Checklist

- Confirm matcher shortcuts are labeled.
- Confirm fallback is not full runtime.
- Confirm provider unavailable and tool blocked states are public-safe.
- Confirm classifier mode is `regex`.
- Confirm subprocess mode is default unless intentionally testing internal service mode.

## Rollback Steps

- Remove public routing to the demo.
- Stop the demo container/service.
- Revert the release branch or deploy previous known-good branch.
- Rotate any secret that may have been exposed outside the approved secret manager.
- Re-run `npm run validate:public-demo` and `npm run test:security` before attempting again.

## Manual Merge Reminder

Any merge to `main` must be a separate, manual decision after review. Phase 15 does not merge main and does not create an automatic release.

## No Automatic Release

Do not tag, publish a GitHub release, deploy publicly, or start training as part of this checklist.
