# GitHub Pages Deploy

## Scope

The `Docs Deploy` workflow publishes the repository `docs/` directory to GitHub Pages through GitHub Actions. It does not build runtime, backend, frontend, or security artifacts.

## Required repository settings

- GitHub Pages source must be set to `GitHub Actions`.
- The `github-pages` environment must allow deployments from the workflow.
- The workflow token must keep `contents: read`, `pages: write`, and `id-token: write`.
- The `docs/` directory must exist and contain the documentation to publish.

## 2026-07-02 deploy failure

The failed `Docs Deploy` run on `main` after PR #510 uploaded the docs artifact successfully, but the `Deploy Pages` step failed before deployment. The deploy action reported that it found three artifacts named `github-pages` in the same workflow run and refused to choose one.

This was not caused by an empty `docs/` path, missing Pages permissions, or a missing artifact. The workflow now uses a run-specific Pages artifact name and serializes deploys per ref so repeated or overlapping attempts cannot leave duplicate default-named artifacts for `actions/deploy-pages`.

## Manual checks

If a future run fails before artifact lookup, verify the external repository configuration first:

1. Open repository Settings.
2. Open Pages.
3. Confirm Build and deployment Source is `GitHub Actions`.
4. Confirm the `github-pages` environment is not blocked by required reviewers or branch rules that exclude `main`.

Do not add secrets or provider credentials to this workflow. It should publish only the checked-in documentation tree.
