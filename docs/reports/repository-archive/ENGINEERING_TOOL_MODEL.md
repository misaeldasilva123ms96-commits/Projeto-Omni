# Engineering Tool Model

## Tool families

Phase 9 adds engineering-oriented tools under the existing governance model:

- `filesystem_read`
- `filesystem_write`
- `directory_tree`
- `git_status`
- `git_diff`
- `git_commit`
- `test_runner`
- `package_manager`
- `dependency_inspection`
- `code_search`
- `autonomous_debug_loop`

## Governance

These tools remain under:
- tool taxonomy in `runtime/tooling/toolGovernance.js`
- policy decisions attached to actions
- supervision limits in the Python runtime

## Auditability

Every engineering action still returns a normalized result payload or error payload. Mutating flows such as `filesystem_write` and `git_commit` remain explicit and reviewable.

## Boundaries

- `git_commit` still requires explicit approval.
- package mutation commands are not auto-executed in this phase.
- engineering tools are implemented as bounded runtime adapters, not unconstrained shell access.
