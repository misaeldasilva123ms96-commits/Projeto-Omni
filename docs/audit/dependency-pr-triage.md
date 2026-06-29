# Dependency PR Triage - Projeto Omni

Date: 2026-06-29
Branch: hardening/medium-audit-alerts-remediation
Source: `gh pr list --state open --limit 100 --json number,title,author,headRefName,baseRefName,labels,isDraft,updatedAt,url`

## Open Dependency PRs

No open dependency PRs were returned by GitHub at the time of this triage.

## Risk Classification

| PR | Dependency area | Risk | Manual review | Dedicated test |
| --- | --- | --- | --- | --- |
| None open | Not applicable | Not applicable | Not applicable | Not applicable |

## Recommended Manual Merge Order

When Dependabot PRs are opened, review and merge manually in this order:

1. Low risk: simple development dependencies with no runtime effect.
2. Medium risk: UI runtime dependencies, after frontend tests, typecheck, and build.
3. Medium to high risk: build, deploy, or CI tooling, after workflow-specific validation.
4. High risk: Rust or security-sensitive dependencies, after Rust formatting, clippy, tests, and security regression checks.
5. Needs manual review and dedicated tests: any dependency with a breaking change, major version bump, lockfile churn across runtimes, or public payload/security boundary impact.

## Governance Notes

- Do not merge Dependabot PRs automatically.
- Do not enable auto-merge for dependency PRs.
- Do not approve dependency PRs automatically.
- Keep dependency updates separate from CI hardening unless a dependency change is strictly required to restore the hardened CI path.
