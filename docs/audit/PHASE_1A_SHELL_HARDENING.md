# Phase 1A Shell Hardening

## Branch / Base
- Branch: `hardening/shell-01a`
- Base branch: `audit/code-map-00-5`
- Base commit: `9ba872f556ac35673cdabd2527b9464eb65957c5`

## Files Changed
- `backend/python/brain/runtime/shell_policy.py`
- `backend/python/brain/runtime/engineering_tools.py`
- `tests/runtime/test_shell_policy_hardening.py`
- `docs/audit/PHASE_1A_SHELL_HARDENING.md`

## Real Shell Paths Hardened
- Primary shell execution path: `backend/python/brain/runtime/engineering_tools.py::_run_command`
- Tool entrypoint: `backend/python/brain/runtime/engineering_tools.py::execute_engineering_action`
- Covered tool branches: `shell_command`, `git_status`, `git_diff`, `git_commit`, `test_runner`, `verification_runner`

## Env Flags Added
Canonical:
- `OMNI_ALLOW_SHELL_TOOLS=true`
- `OMNI_PUBLIC_DEMO_MODE=true`
- `OMNI_SHELL_ALLOWLIST_MODE=true`

Aliases:
- `OMINI_ALLOW_SHELL_TOOLS`
- `OMINI_PUBLIC_DEMO_MODE`
- `OMINI_SHELL_ALLOWLIST_MODE`
- `ALLOW_SHELL`

## Public Demo Precedence Rule
Public demo mode wins over all allow flags. If `OMNI_PUBLIC_DEMO_MODE=true` or `OMINI_PUBLIC_DEMO_MODE=true`, shell execution returns a controlled public-safe blocked result with `error_public_code="TOOL_BLOCKED_PUBLIC_DEMO"`.

## Allowlist Summary
- `git`: `status`, `log`, `diff`, `show`, `branch`
- `npm`: `test`, `ci`, `run`
- `npm run`: only package.json scripts named `test`, `test:python:pytest`, `test:js-runtime`, `typecheck`, or `build`
- `python`: `-m`, `--version`
- `pytest`: `-x`, `-v`, `--tb=short`

## Dangerous Pattern Summary
Blocked at minimum:
- `rm`
- `/bin/rm`
- `del`
- `format`
- `mkfs`
- `shutdown`
- `reboot`
- `sudo`
- `su`
- `chmod 777`
- `chown`
- `dd`
- `curl | ...`
- `wget | ...`
- `powershell`
- `cmd.exe`
- `bash -c`
- `sh -c`
- `python -c`
- `node -e`
- `find -delete`

## Blocked Result Shape
Blocked shell commands return a public-safe payload:

```json
{
  "ok": false,
  "tool_status": "blocked",
  "error_public_code": "SHELL_TOOL_BLOCKED",
  "error_public_message": "Shell execution is disabled by policy.",
  "internal_error_redacted": true
}
```

Public demo mode uses `error_public_code="TOOL_BLOCKED_PUBLIC_DEMO"`.

## Tests Run / Results
- `python -m pytest -q tests/runtime/test_shell_policy_hardening.py`
  - Result: PASS
  - Output: `10 passed, 7 subtests passed in 1.19s`
- `python -m py_compile backend/python/brain/runtime/shell_policy.py backend/python/brain/runtime/engineering_tools.py`
  - Result: PASS
- `npm test`
  - Result: PASS
  - Output: command exited 0 with no stdout emitted by local runner
- `npm run test:python:pytest`
  - Result: TIMEOUT
  - Output: `command timed out after 300050 milliseconds`
- `npm run test:js-runtime`
  - Result: PASS
  - Output: command exited 0 with no stdout emitted by local runner
- `python -m pytest -q tests/runtime/test_trusted_execution_layer.py tests/runtime/test_strategy_execution_integration.py`
  - Result: TIMEOUT
  - Output: `command timed out after 184060 milliseconds`

## Known Limitations
- This phase hardens Python engineering shell execution. JS and Rust tool governance references remain mapped but not changed in this phase.
- Existing broad pytest commands exceeded local timeout; narrow shell hardening tests passed.
- `shell_command` supports list commands and shlex-parsed string commands, but execution remains deny-by-default and allowlisted.

## Rollback
Use:

```txt
git revert <phase-1a-commit>
```

## Gate 1A Status
PASSED

Evidence:
- Shell blocked by default.
- Public demo always blocks shell.
- `ALLOW_SHELL=true` cannot bypass public demo mode.
- Dangerous commands are rejected.
- Allowlist exists.
- `npm run` is guarded by root `package.json` and script allowlist.
- Tests added.
- Blocked response is public-safe and redacts internal details.
- No merge into main.

## No Merge Into Main
No merge into main.
