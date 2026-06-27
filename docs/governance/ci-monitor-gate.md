# CI Monitor Gate

Phase 29 adds the CI Monitor Gate for the Omni Governed Knowledge Sandbox.

The gate decides whether a PR created by Phase 28 is eligible for a future CI/check monitoring phase. It is metadata-only: it does not monitor CI, call GitHub APIs, execute `gh`, download logs, retry workflows, trigger workflows, start repair loops, mutate Git, push, merge, rebase, update PRs, or approve PRs.

Phase 30 consumes this gate evidence in the Controlled CI Monitor. That monitor may read bounded status snapshots through narrow injected clients, but it still cannot download logs, retry workflows, update PRs, merge, push, or start repair loops.

## Inputs

The gate consumes provided evidence only:

- Phase 28 Controlled PR Creator result.
- Phase 27 PR Creation Gate result when provided.
- Phase 26 Controlled Push Executor result when provided.
- PR metadata such as repository, PR number, PR URL, PR state, branch names, and head SHA.
- Expected CI provider/workflow/check metadata.

No branch, PR, check, workflow, or repository state is discovered by this phase.

## Governance

The gate may produce `ci_monitor_eligible=true` only in `evaluate_ci_monitor` mode when:

- Phase 28 evidence shows a PR was created successfully.
- Runtime Truth is present and clean.
- PR number and PR URL are present.
- PR state is open, including draft open PRs.
- Repository metadata is the expected repository or an explicitly approved safe repository.
- Source and head branches are non-main and not protected release/production branches.
- Base branch is `main`.
- Head SHA or commit SHA is safe and present.
- CI provider, workflow, and required-check metadata is safe.
- No secret-like content is detected.

`ci_monitor_eligible` and `ci_monitor_plan` are metadata only. `can_monitor_ci`, `can_call_github_api`, `can_download_logs`, `can_retry_workflows`, `can_start_repair_loop`, `can_merge`, and `can_auto_merge` remain false.

## Escalation

Human intervention is required for secret-like content, closed or merged PRs, locked PRs, archived repositories, protected branches, main head/source branches, unsafe repositories, missing head SHA, unsafe CI provider/workflow/check metadata, unsafe upstream Runtime Truth, or any metadata indicating direct main edits.

Public demos must not enable unrestricted CI monitoring automation.
