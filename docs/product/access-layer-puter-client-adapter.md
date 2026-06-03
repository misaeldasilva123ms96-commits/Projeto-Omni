# Omni Access Layer Puter Client Adapter Contract

This document describes the Phase 7A Puter client adapter contract. It is an
experimental Free Mode contract only. It does not make Puter the default
provider and does not add a real provider call.

## Location

- Contract: `backend/python/brain/runtime/access_layer/puter_client_adapter.py`
- Tests: `tests/runtime/test_puter_client_adapter.py`

## Boundary

Puter.js is browser/client-side oriented infrastructure. This phase only defines
a disabled-by-default contract that can be evaluated after the Access Snapshot
Boundary has produced a safe response.

The contract remains behind:

- PlanPolicy
- TokenQuota
- ProviderRouter
- ProviderRegistry
- PublicAccessSnapshot
- AccessSnapshotBoundary

The adapter contract must not be treated as a replacement for server-side
governance.

## Free Mode Restrictions

The Puter client adapter contract is limited to `experimental_free_provider` and
`experimental_free` provider mode. It remains experimental, requires a browser
runtime and user session, and is disabled by default.

Free mode restrictions remain unchanged:

- no tools or function calling
- no files
- no sensitive tools
- no long memory
- strict Free token limits
- no server API key required

## Not Included

This phase does not add frontend code, dependencies, automatic execution on app
load, a default provider switch, provider calls, Puter.js integration, BYOK key
storage, billing, Pro provider behavior, files, tools, long memory, or production
brain behavior changes.

The contract rejects request options that attempt to pass API keys, access
tokens, credentials, secrets, env vars, raw provider payloads, tools, or files.
In this contract-only phase, `request_options` rejects every key. Benign client
options may be introduced only in a future phase with explicit allowlist tests.
