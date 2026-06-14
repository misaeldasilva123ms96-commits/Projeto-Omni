# Omni Controlled Branch Patch Applier Architecture

Phase 21 adds the first controlled file-writing layer in the Omni autonomous resolution loop.

```text
Phase 18 validation result
  -> Phase 19 repair plan
  -> Phase 20 scoped patch proposal
  -> Phase 21 controlled branch patch application
  -> future validation and PR phases
```

The applier writes only safe scoped files inside an explicit workspace root and only when non-main branch metadata is supplied.

## Responsibilities

The Controlled Branch Patch Applier:

- Consumes Phase 20 patch proposal metadata.
- Validates branch metadata without running Git commands.
- Validates workspace and path containment.
- Blocks protected paths.
- Applies explicit bounded snippets only.
- Records pre-apply and post-apply SHA-256 hashes.
- Emits Runtime Truth for every attempt.
- Carries validation commands as metadata.
- Requires follow-up validation after a write.

## Non-Responsibilities

The applier does not:

- Discover or change branches.
- Execute commands.
- Run tests.
- Mutate Git.
- Commit, push, open PRs, merge, or rebase.
- Call providers.
- Use MCP.
- Call agents.
- Write Vault entries.
- Modify protected files.

## Patch Model

For `modify_existing`, a hunk must contain both `before_context` and `proposed_snippet`. The `before_context` must appear exactly once in the target file.

For `add_test` and `add_documentation`, the applier may append to an existing safe file. Creating a new file requires `allow_file_create = true`.

The applier blocks missing snippets, ambiguous context, missing context, high-risk hunks, protected paths, unsupported operations, oversized results, and secret-like content.

## Audit Model

The result includes:

- Files requested.
- Files considered.
- Files applied.
- Files blocked.
- Hunks requested.
- Hunks applied.
- Hunks blocked.
- Applied changes.
- Blocked changes.
- Validation command metadata.
- Pre-apply hashes.
- Post-apply hashes.
- Runtime Truth evidence.

No backup files or patch files are written by this phase.

## Security Boundary

Secret-like content is redacted and blocks application before writing. Protected scopes include `.env`, `.git`, ADR, governance, security, CI, production, deploy, billing, credential, private-key, and lockfile paths.

Main branch mutation remains blocked. The applier requires non-main branch metadata and never pushes directly to `main`.
