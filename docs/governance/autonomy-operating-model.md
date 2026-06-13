# Omni Autonomy Operating Model

Phase 15 defines the governed autonomy operating model for Projeto Omni. The
strategic goal is controlled full autonomy: agents may eventually resolve tasks
end to end when every safety gate is satisfied, while humans enter only for
exception triggers.

This phase is policy and documentation only. It does not execute commands,
execute agents, call providers, use MCP, write to the Vault, create pull
requests, merge pull requests, or mutate Git.

## Autonomy Levels

- `L0_READ_ONLY`: inspection only. No edits, commands, Git mutation, or PR work.
- `L1_ADVISORY`: analyze, plan, assess risk, propose changes, propose tests,
  review diffs, and generate reports.
- `L2_BRANCH_EDIT_PROPOSAL`: future branch edit proposal capability on a
  non-main branch only.
- `L3_TEST_COMMIT_PUSH_BRANCH`: future approved tests, scoped commits, and
  branch pushes. Direct push to main remains blocked.
- `L4_PR_OPEN_AND_CI_REPAIR`: future PR creation, check monitoring, and CI
  repair commits on the working branch. Merge is not allowed at this level.
- `L5_CONDITIONAL_AUTO_MERGE`: future PR merge only when all required gates
  pass. Checks must not be bypassed.
- `L6_SUPERVISED_SANDBOX_EXECUTION`: future allowlisted sandbox command
  execution with Runtime Truth, reports, approval gates, and escalation gates.
- `L7_FULL_AUTONOMOUS_RESOLUTION`: future task-to-merge loop with planning,
  branch work, tests, PR, CI repair, gated merge, report, and vault draft.

The default level is `L1_ADVISORY`.

## Mandatory Gates

Push to main is always blocked. Merge to main is allowed only through PR and
only when all gates pass:

- target branch is not main;
- base branch is main;
- required checks are green;
- no secret-like content is detected;
- CI thresholds were not lowered;
- tests were not skipped;
- security and governance policy were not changed by automation;
- no production, billing, or destructive action is involved;
- no human decision is explicitly required.

Security reductions, skipped tests, changed CI thresholds, secret exposure,
production changes, billing impact, destructive actions, and
governance/security policy changes require human intervention.

## Runtime Truth And Reports

Autonomous future actions require Runtime Truth evidence and a report. These
records are mandatory for auditability, but this phase only returns policy
decisions. It does not write reports to disk or to the Vault.

## Public Demo Restriction

Public demo surfaces must not enable unrestricted autonomy. Any demo mode must
remain advisory or use mocked policy decisions unless the same safety gates,
exception triggers, and audit requirements are enforced.

## Phase 15 Boundary

The autonomy policy may say a future action is allowed, but that is only a
classification decision. No runtime execution, command execution, network call,
provider call, MCP integration, Git mutation, PR mutation, or Vault write is
implemented in this phase.
