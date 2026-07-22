from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_root_lock_excludes_unpatched_cloudflare_dependency_chain() -> None:
    package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((PROJECT_ROOT / "package-lock.json").read_text(encoding="utf-8"))

    assert "wrangler" not in package.get("devDependencies", {})
    assert "deploy" not in package.get("scripts", {})
    assert "preview" not in package.get("scripts", {})

    locked_packages = lock.get("packages", {})
    for dependency in ("wrangler", "miniflare", "sharp"):
        assert f"node_modules/{dependency}" not in locked_packages

    fast_uri = locked_packages.get("node_modules/fast-uri", {})
    version = tuple(int(part) for part in str(fast_uri.get("version", "0.0.0")).split("."))
    assert version >= (3, 1, 4)


def test_security_workflow_uses_node_24_and_keeps_cloudflare_suspended() -> None:
    security_workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    deploy_workflow = (PROJECT_ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )

    setup_node = security_workflow.index("uses: actions/setup-node@v7")
    node_audit = security_workflow.index("name: Node audit (blocking high/critical)")
    assert setup_node < node_audit
    assert 'node-version: "24"' in security_workflow[setup_node:node_audit]

    assert "optional-wrangler-deploy" not in deploy_workflow
    assert "npx wrangler" not in deploy_workflow
    assert "uses: actions/deploy-pages@v5" in deploy_workflow
