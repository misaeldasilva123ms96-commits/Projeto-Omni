# Post-Merge Deploy Fix - Projeto Omni

Date: 2026-06-29
Branch: `fix/cloudflare-deploy-opt-in`
Source failure: GitHub Actions run `28370382299`, workflow `Deploy`, job `optional-wrangler-deploy`.

## Failure

After PR #455 was merged, the Deploy workflow failed in the Cloudflare Pages Wrangler step.

The token was present, but Cloudflare rejected the request from the GitHub-hosted runner location:

```text
Cannot use the access token from location: 172.182.211.26 [code: 9109]
```

This indicates the optional Cloudflare deploy was attempted from an unauthorized runner location. The GitHub Pages deploy completed successfully.

## Fix

The Cloudflare Pages deploy job is now explicitly opt-in:

```yaml
if: ${{ vars.CLOUDFLARE_PAGES_DEPLOY_ENABLED == 'true' }}
```

When the repository variable is not set to `true`, the optional Wrangler job is skipped. When it is set to `true`, the job still requires `CLOUDFLARE_API_TOKEN`; if the token exists and Wrangler fails, the step remains blocking.

## Governance

- No secret or token value was changed.
- No token value is printed.
- GitHub Pages deploy remains active.
- Cloudflare Pages deploy is not silently swallowed when explicitly enabled.
- No merge was performed by this branch.
