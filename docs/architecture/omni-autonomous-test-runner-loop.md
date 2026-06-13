# Omni Autonomous Test Runner Loop

The Omni Autonomous Test Runner Loop is the validation orchestration layer
between autonomy policy and future repair phases.

Phase 18 builds on the Phase 17 Sandbox Command Runner. It does not contain its
own command execution boundary; every validation command goes through the
runner, which still calls the Safe Command Execution Gate.

## Flow

1. Receive a structured loop request.
2. Normalize and redact request metadata.
3. Enforce loop mode, max command count, timeout, and safety flags.
4. Plan only allowed validation command families.
5. Call the Phase 17 runner for each dry-run or sandbox-readonly command.
6. Stop on first failure when configured.
7. Classify failures conservatively.
8. Return recommended next action metadata.
9. Emit aggregate Runtime Truth.

## Boundaries

- No direct process execution.
- No code editing or repair.
- No Git mutation.
- No branch, commit, push, PR creation, PR merge, or auto-merge.
- No network/provider/MCP integration.
- No Vault writing.
- No background tasks, retries, recursion, or infinite loop behavior.

Future phases may consume the classification output to propose repair plans,
but this phase only reports validation state.
