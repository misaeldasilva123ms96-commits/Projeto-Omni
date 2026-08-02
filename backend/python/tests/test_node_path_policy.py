from __future__ import annotations

import sys
import os
import shutil
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.node_path_policy import (  # noqa: E402
    NodePathPolicy,
    NodePathPolicyError,
    ValidatedNodeExecutionPlan,
    validate_runtime_executable,
)


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    for relative in ("backend/python/brain/runtime", "backend/rust", "js-runner", "contract", "src", "core/brain"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        "package.json",
        "backend/python/brain/runtime/entrypoint.py",
        "js-runner/queryEngineRunner.js",
        "js-runner/runtimeHealthcheck.js",
        "contract/runner-schema.v1.json",
        "src/queryEngineRunnerAdapter.js",
        "core/brain/fusionBrain.js",
    ):
        (root / relative).write_text("{}", encoding="utf-8")
    return root, root / "backend/python/brain/runtime/entrypoint.py"


def _fixture_policy(tmp_path: Path) -> NodePathPolicy:
    root, active = _fixture_repo(tmp_path)
    return NodePathPolicy.from_runtime(
        project_root=root,
        python_root=root / "backend/python",
        runner_path=root / "js-runner/queryEngineRunner.js",
        active_python_entrypoint=active,
    )


def test_real_repository_root_and_required_artifacts_are_accepted() -> None:
    policy = NodePathPolicy.from_runtime(
        project_root=PROJECT_ROOT,
        python_root=PROJECT_ROOT / "backend" / "python",
        runner_path=PROJECT_ROOT / "js-runner" / "queryEngineRunner.js",
    )

    assert policy.project_root == PROJECT_ROOT.resolve()
    assert policy.runner_path.name == "queryEngineRunner.js"


def test_imitation_root_is_rejected_when_active_python_code_is_external(tmp_path: Path) -> None:
    imitation = tmp_path / "imitation"
    for relative in ("backend/python", "backend/rust", "js-runner", "contract"):
        (imitation / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        "package.json",
        "js-runner/queryEngineRunner.js",
        "contract/runner-schema.v1.json",
    ):
        (imitation / relative).write_text("{}", encoding="utf-8")

    with pytest.raises(NodePathPolicyError, match="node_project_root_invalid"):
        NodePathPolicy.from_runtime(
            project_root=imitation,
            python_root=imitation / "backend" / "python",
            runner_path=imitation / "js-runner" / "queryEngineRunner.js",
        )


def test_sibling_prefix_is_not_contained() -> None:
    policy = NodePathPolicy.from_runtime(
        project_root=PROJECT_ROOT,
        python_root=PROJECT_ROOT / "backend" / "python",
        runner_path=PROJECT_ROOT / "js-runner" / "queryEngineRunner.js",
    )

    with pytest.raises(NodePathPolicyError):
        policy.validate_file(PROJECT_ROOT.parent / f"{PROJECT_ROOT.name}-evil" / "runner.js", "runner")


def test_dotdot_root_normalizes_only_to_the_bound_repository(tmp_path: Path) -> None:
    root, active = _fixture_repo(tmp_path)
    policy = NodePathPolicy.from_runtime(
        project_root=root / "backend" / "..",
        python_root=root / "backend/python",
        runner_path=root / "js-runner/queryEngineRunner.js",
        active_python_entrypoint=active,
    )
    assert policy.project_root == root.resolve()
    assert policy.python_root == (root / "backend/python").resolve()


def test_missing_marker_and_missing_required_runner_fail_closed(tmp_path: Path) -> None:
    root, active = _fixture_repo(tmp_path)
    (root / "package.json").unlink()
    with pytest.raises(NodePathPolicyError, match="node_project_root_invalid"):
        NodePathPolicy.from_runtime(project_root=root, python_root=root / "backend/python", runner_path=root / "js-runner/queryEngineRunner.js", active_python_entrypoint=active)

    root, active = _fixture_repo(tmp_path / "second")
    (root / "js-runner/queryEngineRunner.js").unlink()
    with pytest.raises(NodePathPolicyError):
        NodePathPolicy.from_runtime(project_root=root, python_root=root / "backend/python", runner_path=root / "js-runner/queryEngineRunner.js", active_python_entrypoint=active)


def test_runner_adapter_and_schema_outside_root_are_rejected(tmp_path: Path) -> None:
    policy = _fixture_policy(tmp_path)
    outside = tmp_path / "outside.js"
    outside.write_text("{}", encoding="utf-8")
    for label in ("runner", "adapter", "schema"):
        with pytest.raises(NodePathPolicyError, match=f"node_{label}_outside_root"):
            policy.validate_file(outside, label)


def test_directory_is_rejected_and_missing_optional_candidate_is_skipped(tmp_path: Path) -> None:
    policy = _fixture_policy(tmp_path)
    candidate = policy.project_root / "dist/QueryEngine.js"
    candidate.mkdir(parents=True)
    with pytest.raises(NodePathPolicyError, match="node_engine_candidate_unsafe"):
        policy.validate_file(candidate, "engine_candidate", required=False)
    candidate.rmdir()
    assert policy.validate_file(candidate, "engine_candidate", required=False) is None


def test_security_symlink_and_symlinked_parent_are_rejected(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink unavailable")
    policy = _fixture_policy(tmp_path)
    target = policy.project_root / "src/QueryEngine.js"
    target.write_text("module.exports = {}", encoding="utf-8")
    link = policy.project_root / "dist/QueryEngine.js"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlink unavailable: {error}")
    with pytest.raises(NodePathPolicyError, match="node_engine_candidate_unsafe"):
        policy.validate_file(link, "engine_candidate", required=False)

    link.unlink()
    real_parent = policy.project_root / "outside-parent"
    real_parent.mkdir()
    parent_link = policy.project_root / "dist"
    parent_link.rmdir()
    parent_link.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(NodePathPolicyError, match="node_engine_candidate_unsafe"):
        policy.validate_file(parent_link / "QueryEngine.js", "engine_candidate", required=False)


@pytest.mark.parametrize("target_location", ["inside", "outside"])
def test_runner_symlink_is_rejected_for_inside_and_outside_targets(tmp_path: Path, target_location: str) -> None:
    root, active = _fixture_repo(tmp_path)
    runner = root / "js-runner/queryEngineRunner.js"
    target = (root / "js-runner/realRunner.js") if target_location == "inside" else (tmp_path / "externalRunner.js")
    target.write_text("module.exports = {}", encoding="utf-8")
    runner.unlink()
    try:
        runner.symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlink unavailable: {error}")
    with pytest.raises(NodePathPolicyError, match="node_project_root_invalid|node_runner_symlink_rejected"):
        NodePathPolicy.from_runtime(
            project_root=root,
            python_root=root / "backend/python",
            runner_path=runner,
            active_python_entrypoint=active,
        )


@pytest.mark.skipif(os.name == "nt" or not hasattr(os, "mkfifo"), reason="FIFO fixture is POSIX-only")
def test_fifo_is_rejected_where_supported(tmp_path: Path) -> None:
    policy = _fixture_policy(tmp_path)
    candidate = policy.project_root / "dist/QueryEngine.js"
    candidate.parent.mkdir(parents=True)
    os.mkfifo(candidate)
    with pytest.raises(NodePathPolicyError, match="node_engine_candidate_unsafe"):
        policy.validate_file(candidate, "engine_candidate", required=False)


def test_runtime_executable_policy_accepts_bare_and_absolute_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(shutil.which("node") or "").resolve(strict=True)
    name = "node.exe" if os.name == "nt" else "node"
    controlled = tmp_path / name
    shutil.copy2(source, controlled)
    if os.name != "nt":
        controlled.chmod(0o755)
    resolved, runtime = validate_runtime_executable(name, controlled_path=str(tmp_path))
    absolute, absolute_runtime = validate_runtime_executable(str(controlled))
    assert resolved == controlled.resolve()
    assert absolute == controlled.resolve()
    assert runtime == absolute_runtime == "node"


def test_runtime_executable_symlink_policy_accepts_valid_target(tmp_path: Path) -> None:
    source = Path(shutil.which("node") or "").resolve(strict=True)
    link = tmp_path / ("node.exe" if os.name == "nt" else "node")
    try:
        link.symlink_to(source)
    except OSError as error:
        pytest.skip(f"executable symlink unavailable: {error}")
    resolved, runtime = validate_runtime_executable(str(link))
    assert resolved == source
    assert runtime == "node"


@pytest.mark.parametrize("candidate", ["./node", "bin/node", r"bin\node", "node --inspect", "missing-runtime", "python"])
def test_invalid_runtime_forms_are_rejected(candidate: str) -> None:
    with pytest.raises(NodePathPolicyError, match="node_runtime_invalid"):
        validate_runtime_executable(candidate, controlled_path="")


def test_directory_is_not_an_executable(tmp_path: Path) -> None:
    directory = tmp_path / "node"
    directory.mkdir()
    with pytest.raises(NodePathPolicyError, match="node_runtime_invalid"):
        validate_runtime_executable(str(directory))
