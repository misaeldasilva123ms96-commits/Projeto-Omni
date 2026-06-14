# Omni Autonomous Repair Planner

The Omni Autonomous Repair Planner is the planning layer between validation
failure evidence and future governed repair execution.

Phase 19 consumes Phase 18 loop results and creates structured repair metadata.
It does not read or write project files and does not call command runners,
providers, MCP, or agents.

Phase 20 consumes this repair metadata and creates scoped patch proposal
metadata before any future governed patch application phase.

## Flow

1. Receive failure summary, classification, command results, or a Phase 18 loop
   result.
2. Normalize failure classification aliases.
3. Map failure to repair category, complexity, and risk.
4. Redact secret-like inputs.
5. Bound suspected files and validation commands to metadata only.
6. Apply escalation rules for governance, security, production, billing,
   destructive, secret, and main-branch cases.
7. Return proposed steps and Runtime Truth.

## Boundaries

- No command execution.
- No source edits or patch application.
- No file writes.
- No Git mutation.
- No PR creation or merge.
- No network, provider, MCP, or agent calls.
- No Vault writing.

Future phases may consume the plan for governed repair execution, but this
phase only produces the plan.
