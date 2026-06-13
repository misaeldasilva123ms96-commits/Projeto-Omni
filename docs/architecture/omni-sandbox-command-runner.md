# Omni Sandbox Command Runner

The Omni Sandbox Command Runner is the controlled bridge between command policy
classification and limited local execution.

Phase 17 introduces real execution only for read-safe commands approved by the
Safe Command Execution Gate. It does not implement Git mutation, pull request
creation, pull request merge, auto-merge, provider calls, MCP integration, agent
automation, network calls, or Vault writing.

## Flow

1. Receive a structured command runner request.
2. Normalize and redact request fields.
3. Call the Safe Command Execution Gate.
4. Reject disabled, blocked, dry-run policy-only, unknown, high-risk, and
   human-exception requests.
5. Parse the command into an argv list.
6. Validate the argv against the Phase 17 executable allowlist.
7. Validate the working directory and path arguments.
8. Execute only in `sandbox_readonly` mode with `shell=False`.
9. Capture and redact bounded output.
10. Return Runtime Truth evidence.

## Safety Boundaries

- Denied by default.
- Requires `sandbox_readonly`.
- Requires `sandbox_allowed`.
- Requires gate approval.
- Requires Runtime Truth.
- Requires sandbox isolation.
- Executes only `read_safe` commands.
- Blocks Git write commands.
- Blocks network, provider, MCP, deploy, billing, secret access, destructive,
  privileged, and unknown commands.
- Does not write files or Vault notes.
- Does not mutate Git or main.
- Does not open or merge PRs.

## Runtime Truth Contract

The runner emits `sandbox.command.execution` evidence for blocked, dry-run,
timed-out, successful, and failed execution results. Governance decisions map
to `blocked`, `dry_run`, `timed_out`, `executed_success`, or
`executed_failed`.

Secret-like output is redacted and marks the evidence as secret-bearing so
human intervention is required.

## Phase 18 Orchestration

The Autonomous Test Runner Loop consumes this runner as its only execution
boundary. The loop does not parse commands into operating-system execution or
start commands directly.
