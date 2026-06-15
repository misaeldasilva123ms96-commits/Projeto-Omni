# Omni Autonomous Resolution Loop

The Autonomous Resolution Loop is the future end-to-end operating model for
Omni. It describes how an agent can move from task intake to reviewed outcome
when every governance gate passes.

## Future Loop

1. Analyze the task and classify risk.
2. Create a plan and identify required tests.
3. Work on a non-main branch.
4. Apply scoped edits.
5. Run approved tests.
6. Commit scoped changes.
7. Push the working branch.
8. Open a pull request.
9. Monitor CI (Phases 29–30).
10. Evaluate CI repair-loop eligibility (Phase 31).
11. Repair CI failures within scope.
12. Merge only when conditional merge gates pass.
13. Produce Runtime Truth and reports.
14. Produce a governed Vault draft for audit, if policy allows.

## Human Exception Model

Human intervention is required when any exception trigger is present:

- secret-like content;
- CI threshold changes;
- skipped tests;
- security policy changes;
- governance policy changes;
- production targets;
- billing or cost impact;
- destructive actions;
- explicit human decision requirement;
- main branch edit or push attempt;
- merge attempt with failing checks.

## Current Phase Boundary

Phase 15 does not implement the loop. It defines the policy object, the decision
object, safe flags, tests, and documentation needed before runtime execution can
be designed. Command execution, agent execution, provider calls, MCP, Vault
writes, Git mutation, PR creation, and auto-merge behavior remain unimplemented.

Phase 16 adds the Safe Command Execution Gate as a policy-only step in the
future loop. It can mark commands as future eligible, but command execution
remains disabled until a separate governed runner exists.
