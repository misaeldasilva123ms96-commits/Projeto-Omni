from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT_ROOT / "scripts" / "run_python_tests.mjs"


def _node_eval(source: str) -> str:
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", source],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_canonical_suite_names_map_to_separate_pytest_trees() -> None:
    source = (
        f"import {{ selectedSuites }} from {json.dumps(RUNNER.as_uri())};"
        "console.log(JSON.stringify({"
        "backend:selectedSuites('backend'),"
        "runtime:selectedSuites('runtime'),"
        "all:selectedSuites('all'),"
        "coverage:selectedSuites('coverage')"
        "}));"
    )

    result = json.loads(_node_eval(source))

    assert result["backend"] == ["backend"]
    assert result["runtime"] == ["runtime"]
    assert result["all"] == ["backend", "runtime"]
    assert result["coverage"] == ["backend", "runtime"]


def test_aggregate_fails_when_backend_suite_fails() -> None:
    source = (
        f"import {{ aggregateExitCode }} from {json.dumps(RUNNER.as_uri())};"
        "console.log(aggregateExitCode([1, 0]));"
    )

    assert _node_eval(source) == "1"


def test_aggregate_fails_when_runtime_suite_fails() -> None:
    source = (
        f"import {{ aggregateExitCode }} from {json.dumps(RUNNER.as_uri())};"
        "console.log(aggregateExitCode([0, 1]));"
    )

    assert _node_eval(source) == "1"


def test_aggregate_passes_only_when_both_suites_pass() -> None:
    source = (
        f"import {{ aggregateExitCode }} from {json.dumps(RUNNER.as_uri())};"
        "console.log(aggregateExitCode([0, 0]));"
    )

    assert _node_eval(source) == "0"


def test_runner_environment_uses_an_allowlist_and_rehomes_host_state() -> None:
    source = (
        "import { mkdtempSync, rmSync } from 'node:fs';"
        "import { tmpdir } from 'node:os';"
        "import { join } from 'node:path';"
        f"import {{ isolatedEnvironment }} from {json.dumps(RUNNER.as_uri())};"
        "const root=mkdtempSync(join(tmpdir(),'omni-runner-env-'));"
        "process.env.DATABASE_URL='database-marker';"
        "process.env.SSH_AUTH_SOCK='agent-marker';"
        "process.env.XDG_CONFIG_HOME='host-config-marker';"
        "try { const env=isolatedEnvironment(root); console.log(JSON.stringify({"
        "database:Object.hasOwn(env,'DATABASE_URL'),"
        "ssh:Object.hasOwn(env,'SSH_AUTH_SOCK'),"
        "home:env.HOME.startsWith(root),"
        "xdg:env.XDG_CONFIG_HOME.startsWith(root),"
        "tmp:env.TMPDIR.startsWith(root)"
        "})); } finally { rmSync(root,{recursive:true,force:true}); }"
    )

    result = json.loads(_node_eval(source))

    assert result == {
        "database": False,
        "ssh": False,
        "home": True,
        "xdg": True,
        "tmp": True,
    }


def test_coverage_command_runs_both_suites_and_enforces_threshold() -> None:
    package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "post-merge.yml").read_text(
        encoding="utf-8"
    )

    assert package["scripts"]["test:python:coverage"].endswith(" coverage")
    assert "--fail-under=40" in runner
    assert "coverage.xml" in runner
    assert "npm run test:python:coverage" in workflow
    assert "actions/upload-artifact@v7" in workflow
