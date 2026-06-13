# Safe Command Execution Gate

Phase 16 adds the Safe Command Execution Gate for Projeto Omni. The gate
classifies command requests for future governed sandbox execution.

This phase does not execute commands. It does not call operating-system
execution APIs, mutate Git, create branches, commit, push, open pull requests,
merge pull requests, call providers, use MCP, call networks, write files, or
write to the Vault.

## Modes

- `disabled`: default mode. All command requests are blocked.
- `dry_run_policy_only`: safe commands may be classified as future eligible, but
  execution remains disabled.
- `sandbox_allowed`: safe commands may be marked eligible for future sandbox
  execution by a separate runner. This phase still does not execute them.
- `blocked`: all command requests are blocked.

## Future Eligible Categories

Read-safe commands include Git inspection, local test commands, static
validation, JSON validation, compile checks, and version checks.

Branch-write commands may become future eligible only in `sandbox_allowed` mode,
only for non-main branches, and only when no exception trigger is present.

Runtime Truth and sandbox isolation are mandatory before any future execution.

## Blocked Categories

The gate blocks:

- push to `main`;
- force push;
- merge and rebase commands;
- PR merge commands;
- network commands;
- secret access;
- production deploy commands;
- billing commands;
- destructive filesystem commands;
- privileged container commands;
- unknown or high-risk commands.

Human intervention is required for exception triggers, including network access,
secret reads, production targeting, destructive intent, main mutation, force
push, merge commands, skipped tests, CI/security reduction, or unknown commands.

## Public Demo Boundary

Public demos must not enable unrestricted command execution. They may show
classification results, blocked states, and future eligibility only.
