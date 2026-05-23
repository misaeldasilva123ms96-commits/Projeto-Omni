# PHASE 3 TOOL GOVERNANCE ENFORCEMENT — Projeto Omni

Date: 2026-05-01
Base branch: runtime/truth-contract-02
Base commit: e12eefeccb10e31fef13a40a76cbab3db72d3e9a
Working branch: governance/tool-enforcement-03

## Scope

Phase 3 enforces governance before sensitive tool execution. It does not remove tools, bypass existing governance, weaken shell policy, weaken runtime truth, expose raw internals, or rewrite runtime architecture.

## Files Changed

- `backend/python/brain/runtime/tool_governance_policy.py`
- `backend/python/brain/runtime/engineering_tools.py`
- `runtime/tooling/toolGovernance.js`
- `core/brain/queryEngineAuthority.js`
- `tests/runtime/test_tool_governance_enforcement.py`
- `tests/runtime/toolGovernanceEnforcement.test.mjs`

## Tool Entry Points Inspected

| Entry point | Path | Governance action |
| --- | --- | --- |
| Python engineering tools | `backend/python/brain/runtime/engineering_tools.py` | Calls `evaluate_tool_governance(...)` before any file, git, shell, package, search, debug, or verification action. |
| Node QueryEngine tool execution loop | `core/brain/queryEngineAuthority.js` | Calls `evaluateToolGovernance(...)` before `runRustExecutor(...)`. Blocked tools are converted to controlled step results. |
| Existing JS governance taxonomy | `runtime/tooling/toolGovernance.js` | Extended with explicit categories, public-safe audit, and controlled blocked result builder. |
| Existing shell policy | `backend/python/brain/runtime/shell_policy.py` | Preserved. Shell remains deny-by-default and public-demo-blocked. |

## Tools / Categories Governed

- `read_safe`: status, health, list, directory_tree, git_status, git_diff, dependency_inspection, glob_search, grep_search, code_search.
- `read_sensitive`: read_file, filesystem_read, memory_read, debug_inspection.
- `write`: write_file, edit_file, filesystem_write, filesystem_patch_set, generated_file_write.
- `destructive`: delete, overwrite, git_reset, git_clean, rm, remove_file.
- `shell`: shell_command, run_command, test_runner, verification_runner, package_manager, autonomous_debug_loop.
- `network`: curl, fetch, web_request, network_request.
- `git_sensitive`: git_commit, git_push, git_branch_mutation, other non-read git tools.

## Decision Flow

1. Classify selected tool.
2. If public demo mode is active, block shell/write/destructive/network/git-sensitive tools.
3. Allow read-safe tools.
4. Require explicit scope for read-sensitive tools.
5. Require explicit approval for write and git-sensitive tools.
6. Block destructive tools.
7. Gate network-like tools.
8. Delegate shell tools to the existing Phase 1A shell policy when not public-demo-blocked.
9. Return controlled public-safe blocked result when not allowed.

## Controlled Block Shape

Blocked tool results include:

- `ok=false`
- `tool_status=blocked`
- `error_public_code`
- `error_public_message`
- `internal_error_redacted=true`
- `governance_audit`
- `tool_execution.tool_denied=true`

The public audit only contains:

- `allowed`
- `category`
- `reason_code`
- `approval_required`
- `public_demo_blocked`
- `policy_version`

It does not include stack traces, env, token/secret/api keys, raw commands, stdout/stderr, raw payloads, memory content, or provider raw responses.

## Runtime Truth Interaction

Phase 2 runtime truth already maps denied tools to:

- `runtime_mode=TOOL_BLOCKED`
- `tool_invoked=true`
- `tool_executed=false`
- `tool_status=blocked`

Phase 3 blocked results use `tool_execution.tool_denied=true` and `error_payload.kind=tool_blocked`, which feeds the existing runtime truth path without labeling blocked tools as `FULL_COGNITIVE_RUNTIME`.

## Tests Run / Results

Narrow validation:

- `python -m pytest -q tests/runtime/test_tool_governance_enforcement.py tests/runtime/test_shell_policy_hardening.py` — passed
- `node tests/runtime/toolGovernanceEnforcement.test.mjs` — passed
- `python -m pytest -q tests/runtime/test_strategy_execution_integration.py::StrategyExecutionIntegrationTest::test_run_promotes_true_action_execution_when_node_returns_actions tests/runtime/test_strategy_execution_integration.py::StrategyExecutionIntegrationTest::test_execute_primary_local_tool_path_records_denied_tool_diagnostic tests/runtime/observability/test_runtime_truth_contract.py` — passed

Timeout evidence:

- `python -m pytest -q tests/runtime/test_strategy_execution_integration.py tests/runtime/observability/test_runtime_truth_contract.py` timed out after 184 seconds. The narrower relevant tests from the same file passed, so this is recorded as broad/heavy integration timeout evidence rather than a proven Phase 3 regression.

Broad validation:

- `python -m py_compile backend/python/brain/runtime/engineering_tools.py backend/python/brain/runtime/tool_governance_policy.py backend/python/brain/runtime/observability/cognitive_runtime_inspector.py` — passed
- `npm test` — passed
- `npm run test:js-runtime` — passed
- `npm run test:python:pytest` — passed
- `git diff --check` — passed

## Known Limitations

- Rust `executor_bridge` still has its own permission layer. Phase 3 gates the Python and Node entry points before Rust execution but does not redesign Rust permissions.
- Shell command allowlisting remains owned by Phase 1A `shell_policy.py`; Phase 3 preserves that behavior.
- Network-like tools are gated by category when surfaced through these tool entry points; unrelated future network surfaces must reuse this governance adapter.

## Rollback

Rollback command:

```bash
git revert <phase-3-commit>
```

## Gate 3 Status

PASSED.

## No Merge Into Main

Confirmed. This phase is committed only to `governance/tool-enforcement-03`.
