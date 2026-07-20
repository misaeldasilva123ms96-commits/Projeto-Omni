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
        "all:selectedSuites('all')"
        "}));"
    )

    result = json.loads(_node_eval(source))

    assert result["backend"] == ["backend"]
    assert result["runtime"] == ["runtime"]
    assert result["all"] == ["backend", "runtime"]


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
