# Environment alias migration

`OMNI_*` is the canonical environment-variable namespace. The misspelled
`OMINI_*` namespace remains a compatibility surface during this migration; it
is not a second configuration namespace for new deployments.

## Resolution contract

All migrated readers apply this order:

1. a non-empty canonical `OMNI_*` value;
2. a non-empty declared compatibility alias;
3. the documented default.

If both names are set, the canonical value wins even when it represents a
false boolean. Empty strings are treated as unset. Python path settings that
predate both prefixes retain their explicit unprefixed alias (for example,
`BASE_DIR`) in the order returned by `legacy_env_names()`.

New code and deployment examples must use `OMNI_*`. Compatibility readers must
never expose environment values in logs, counters, diagnostics, or errors.

## Usage measurement

Two complementary signals are available:

- `python scripts/audit_env_aliases.py` produces a deterministic repository
  inventory grouped by runtime source, tests, documentation, and configuration.
  `--check` rejects alias-only runtime references and active `OMINI_*`
  assignments in `.env.example`.
- Python `env_alias_usage_snapshot()` and Node `envAliasUsageSnapshot()` expose
  process-local counts for legacy reads and canonical overrides. Rows contain
  names and counters only, never values. Counters reset when the process exits
  and are not exposed through the public API.
- Rust emits structured `deprecated_env_alias_used` and
  `env_alias_canonical_override` warning events containing variable names only.

The static check runs in Runtime CI through `npm run validate:env-aliases`.

## Migration window

This PR is the inventory and measurement stage. It removes no compatibility
alias. Removal may be proposed only after all of the following are true:

- at least 180 days and two tagged releases have elapsed after this telemetry
  contract reaches `main`;
- supported deployments report zero legacy reads for 30 consecutive days;
- `.env.example`, active deployment manifests, phases 39–40 documentation, and
  operator runbooks use canonical names;
- a release note announces the exact aliases and release where removal occurs.

Until those gates are met, `OMINI_*` remains supported. A removal must be a
separate breaking-change PR with rollback instructions; there is currently no
scheduled removal release.

## Current families

The inventory covers runtime mode and binaries, Rust/Python/Node persistent
services, public-demo and security gates, provider routing, intent and matcher
controls, encrypted credential storage, E2E configuration, and phases 39–40
evolution controls. Historical reports remain searchable evidence and are not
rewritten solely to change old variable spellings.
