# Sandbox Command Runner

Phase 17 adds the Sandbox Command Runner for Projeto Omni. This is the first
real execution layer, but it is denied by default and limited to read-safe,
non-mutating commands.

The runner executes a command only when all of these gates pass:

- `runner_mode` is `sandbox_readonly`;
- `command_mode` is `sandbox_allowed`;
- the Phase 16 Safe Command Execution Gate allows the request;
- the gate marks the command `read_safe`;
- Runtime Truth is required;
- sandbox isolation is required;
- no secret, network, production, destructive, main-branch, or human exception
  trigger is present.

Dry-run mode classifies what would run but does not start a process. Disabled,
blocked, unknown, and policy-only command modes do not execute.

## Executable Commands

Phase 17 may execute only read-safe inspection, validation, test, build, and
version commands such as:

- `git status`;
- `git diff`;
- `git diff --check`;
- `git log`;
- `git branch --show-current`;
- `python --version`;
- `python -m pytest <safe test path>`;
- `python -m json.tool <safe json path>`;
- `python -m compileall <safe path>`;
- `pytest <safe test path>`;
- `npm --version`, `npm test`, `npm run test`, `npm run build`,
  `npm run lint`, `npm run typecheck`;
- `node --version`;
- `cargo --version`, `cargo check`, `cargo test`, `cargo clippy`,
  `cargo fmt --check`;
- `rustc --version`.

## Blocked Commands

The runner does not execute Git write commands. It blocks `git add`,
`git commit`, `git push`, `git checkout -b`, `git switch -c`, `git merge`, and
`git rebase`.

It also blocks GitHub CLI commands, network commands, provider calls, MCP
integration, deploy or billing commands, secret-reading commands, destructive
filesystem commands, privileged commands, PR creation, PR merge, and auto-merge.

## Execution Controls

The runner parses command strings into argv lists and uses `shell=False`. Shell
operators, command chaining, redirection, command substitution, path traversal,
`.env` access, hidden secret paths, and absolute paths outside the repository
or a safe test temporary directory are blocked.

The child process receives a minimal sanitized environment. Secret-like
environment variables are removed. Full environments are never printed.

Standard output and standard error are captured with byte limits and redaction.
Timeouts are enforced with a minimum of one second and a maximum of 300 seconds.

## Runtime Truth

Every runner result includes Runtime Truth evidence with event type
`sandbox.command.execution`. Evidence records whether execution was attempted,
whether a command was executed, timeout state, exit code, output truncation,
gate decision, and governance decision.

Network use, provider calls, MCP use, Vault writes, Git mutation, and main
branch mutation remain false in this phase.

## Public Demo Boundary

Public demos must not enable unrestricted command execution. Demo flows may
show dry-run decisions, blocked states, redaction, timeout handling, and
Runtime Truth evidence.
