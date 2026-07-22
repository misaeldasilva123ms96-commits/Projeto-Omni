from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _workflow_job_block(workflow: str, job_name: str) -> str:
    lines = workflow.splitlines()
    start = lines.index(f"  {job_name}:")
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("  ")
            and not lines[index].startswith("    ")
            and lines[index].strip().endswith(":")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_root_lock_excludes_unpatched_cloudflare_dependency_chain() -> None:
    package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((PROJECT_ROOT / "package-lock.json").read_text(encoding="utf-8"))

    assert "wrangler" not in package.get("devDependencies", {})
    assert "deploy" not in package.get("scripts", {})
    assert "preview" not in package.get("scripts", {})

    locked_packages = lock.get("packages", {})
    fast_uri_versions: list[tuple[int, ...]] = []
    for package_path, metadata in locked_packages.items():
        if "node_modules/" not in package_path:
            continue
        dependency = package_path.rsplit("node_modules/", maxsplit=1)[-1]
        assert dependency not in {"wrangler", "miniflare", "sharp"}, package_path
        if dependency == "fast-uri":
            version = str(metadata.get("version", "0.0.0"))
            fast_uri_versions.append(tuple(int(part) for part in version.split(".")))

    assert fast_uri_versions
    assert all(version >= (3, 1, 4) for version in fast_uri_versions)


def test_security_workflow_uses_node_24_and_keeps_cloudflare_suspended() -> None:
    security_workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    deploy_workflow = (PROJECT_ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )

    dependency_audit_job = _workflow_job_block(security_workflow, "dependency-and-audit")
    setup_node = dependency_audit_job.index("uses: actions/setup-node@v7")
    node_audit = dependency_audit_job.index("name: Node audit (blocking high/critical)")
    assert setup_node < node_audit
    assert 'node-version: "24"' in dependency_audit_job[setup_node:node_audit]

    assert "optional-wrangler-deploy" not in deploy_workflow
    assert "npx wrangler" not in deploy_workflow
    assert "uses: actions/deploy-pages@v5" in deploy_workflow
