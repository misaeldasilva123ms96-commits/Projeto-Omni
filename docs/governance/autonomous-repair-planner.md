# Autonomous Repair Planner

Phase 19 adds the Autonomous Repair Planner for Projeto Omni. It transforms
validation failures from the Phase 18 Autonomous Test Runner Loop into
structured repair-plan metadata.

This phase does not edit code, apply patches, write files, execute commands,
mutate Git, create branches, create commits, push, open pull requests, merge,
call providers, call agents, use MCP, use network access, or write to the
Vault.

Phase 20 consumes repair plans from this phase and may produce scoped patch
proposal metadata. Phase 20 still does not apply patches or edit files.

## Modes

- `disabled`: default. Blocks repair planning.
- `dry_run`: classifies failure input and returns what would be planned.
- `plan_only`: generates structured repair plan metadata only.
- `blocked`: blocks all repair planning.

## Repair Plan Output

The planner returns suspected files as metadata, proposed steps, validation
commands, repair category, complexity, risk level, and escalation decision.
Validation commands are metadata only and must remain compatible with the
governed command gates.

## Human Escalation

Security, governance, ADR, secret, production, billing, destructive, CI
threshold, skipped-test, unsafe command, policy-blocked, and main-branch repair
requests require human intervention.

## Runtime Truth

Each result includes Runtime Truth with event type
`sandbox.repair_planner.plan`. Evidence records the planner mode, failure
classification, repair category, complexity, risk, plan counts, and locked-down
capability flags. Code edits, file writes, Git mutation, PR creation, PR merge,
network use, provider calls, agent calls, MCP use, Vault writes, and main
mutation remain false.

## Public Demo Boundary

Public demos may show repair plans and escalation outcomes, but must not enable
autonomous repair editing yet.
