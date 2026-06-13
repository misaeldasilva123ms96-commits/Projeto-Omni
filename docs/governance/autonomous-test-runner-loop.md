# Autonomous Test Runner Loop

Phase 18 adds the Autonomous Test Runner Loop for Projeto Omni. The loop
orchestrates allowed validation commands through the Phase 17 Sandbox Command
Runner and aggregates results into Runtime Truth evidence.

This phase does not execute commands directly. It does not edit code, repair
code, mutate Git, create branches, create commits, push, open pull requests,
merge pull requests, call providers, use MCP, use network commands, or write to
the Vault.

## Modes

- `disabled`: default. Blocks validation loop execution.
- `dry_run`: builds the validation plan and asks the Phase 17 runner to classify
  commands without starting a process.
- `sandbox_readonly`: runs only allowed validation commands through the Phase 17
  runner.
- `blocked`: blocks all loop execution.

## Allowed Validation Families

The loop may plan test, build, lint, typecheck, format-check, JSON validation,
compile-check, Git inspection, and version commands that are also accepted by
the Phase 17 runner.

Git write commands, PR commands, merge and rebase commands, network commands,
provider/MCP commands, deploy commands, secret-reading commands, and destructive
commands are blocked.

## Failure Classification

Failures are classified conservatively as tests, build, lint, typecheck,
format, blocked command, timed out command, missing command, invalid command,
secret detection, unsafe command, or unknown failure.

Failure classification is informational only. This phase may return a textual
recommendation such as `create_repair_plan`, but actual repair belongs to a
later governed phase.

## Runtime Truth

Each loop result includes aggregate Runtime Truth with event type
`sandbox.test_runner.loop`. It records requested/planned/executed/blocked
command counts, child runner evidence, failure state, timeout state, partial
execution, governance decision, and human intervention requirements.

Network use, provider calls, MCP use, Vault writes, Git mutation, main mutation,
code edits, PR creation, and PR merge remain false.

## Public Demo Boundary

Public demos must not enable unrestricted autonomous loops. Demo flows may show
dry-run planning, blocked states, failure classification, redaction, and
Runtime Truth evidence.
