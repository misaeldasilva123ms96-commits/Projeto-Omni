# Omni Governance

This file is the root governance entrypoint for the Omni repository.

Omni is a governed cognitive runtime under active development. The project values truthful execution evidence, safe public debugging, strict secret handling, and manual human control over production-impacting decisions.

---

## Non-Negotiable Rules

1. **No automatic merge to `main`.**
   - Main merges remain manual.
   - Agents may create branches and pull requests when authorized.
   - Agents must not merge `main`.

2. **No direct push to `main`.**
   - Work must happen on scoped branches.
   - Pull requests must describe the evidence, validations, and remaining uncertainty.

3. **No secrets in the repository.**
   - Do not commit API keys, tokens, passwords, private `.env` files, local databases, private memory stores, real user conversations, raw logs, credentials, cookies, or headers.

4. **Runtime Truth must remain honest.**
   - Do not claim full cognitive execution based only on transport success.
   - Do not hide fallback, matcher shortcuts, degraded behavior, provider failures, tool failures, or governance blocks.

5. **Sensitive capabilities are deny-by-default.**
   - Shell, network, git-sensitive, credential access, provider control, destructive actions, and other sensitive capabilities require explicit design, tests, documentation, and safe metadata boundaries.

6. **Learning is advisory unless explicitly governed.**
   - Omni must not automatically rewrite itself, mutate production behavior, or export training data without documented safety gates.

7. **Public-safe diagnostics only.**
   - Public endpoints and debug payloads must not expose raw stdout/stderr, env values, stack traces, absolute local paths, secrets, headers, provider payloads, request bodies, tokens, cookies, or personal data.

---

## Compliance Boundary

Omni must not implement or document as accepted behavior:

- MITM;
- TLS stealth;
- proxy or bypass flows;
- scraping where not explicitly permitted;
- unofficial/private endpoints;
- credential import from sensitive stores;
- evasion of provider or government protections;
- direct integration of external projects without explicit review;
- real MCP/A2A, billing, or external autonomous tool execution unless introduced through a specific governed implementation plan.

External repositories such as OmniRoute may be studied as architectural references only. Reference studies must explicitly separate adopted ideas from non-adopted sensitive flows.

---

## Branch And PR Policy

Recommended branch names:

- `docs/...` for documentation-only changes;
- `runtime/...` for runtime foundations;
- `provider/...` for provider-specific work;
- `ui/...` for frontend/Cockpit work;
- `security/...` or `hardening/...` for safety controls;
- `research/...` for read-only analysis and ADR context.

Every PR should include:

- summary;
- scope;
- files changed;
- validation run or validation skipped with reason;
- runtime/governance/security impact;
- explicit note when docs-only;
- explicit note that merge remains manual.

---

## Runtime Truth Policy

A successful HTTP response is not enough to claim the runtime succeeded cognitively.

Before claiming full runtime execution, inspect relevant evidence such as:

- `runtime_mode`;
- `runtime_reason`;
- `execution_path_used`;
- `fallback_triggered`;
- `provider_actual`;
- `provider_failed`;
- `failure_class`;
- `execution_provenance`;
- `tool_execution`;
- `provider_diagnostics`;
- governance decisions;
- runtime inspection metadata.

Fallback, matcher, compatibility, degraded, local heuristic, or blocked paths must remain visible and must not be represented as full cognitive runtime execution.

---

## Documentation Governance

Documentation must reflect the real repository state.

Update docs whenever a change affects:

- runtime contracts;
- provider routing;
- tool execution;
- governance or capability rules;
- public debug behavior;
- frontend Runtime Truth or Runtime Inspector surfaces;
- training or learning safety gates;
- repository structure;
- setup or validation commands.

When docs conflict, prefer:

1. current implementation and merged PR evidence;
2. `docs/status/current-state.md`;
3. root `README.md`, `ROADMAP.md`, and this file;
4. focused architecture/runtime/frontend docs;
5. historical and archived documents.

---

## Security And Public Debug Policy

Allowed in public docs and public endpoints:

- bounded runtime mode metadata;
- safe provider names and status summaries;
- sanitized failure classes;
- path-existence booleans without absolute local paths;
- validation summaries;
- redacted/safe diagnostic snapshots.

Not allowed:

- API keys;
- bearer tokens;
- cookies;
- headers;
- provider raw payloads;
- raw prompts if sensitive;
- user private data;
- stack traces;
- raw stdout/stderr;
- local absolute paths;
- private `.env` values;
- credentials;
- unredacted memory stores.

---

## Current Status

Omni is currently:

- suitable for runtime architecture review;
- suitable for public debugging and controlled demo validation;
- suitable for docs, tests, observability, provider diagnostics, and frontend Cockpit contributions;
- not suitable for production decision automation;
- not suitable for unattended high-impact autonomous actions;
- not suitable for uncontrolled self-improvement or ungated training export.
