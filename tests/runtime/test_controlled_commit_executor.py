"""Tests for the controlled commit executor."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from brain.runtime.sandbox.commit_executor import execute_controlled_commit


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        check=True,
        shell=False,
    )
    return completed.stdout.decode("utf-8", errors="replace").strip()


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "omni@example.invalid")
    _git(repo, "config", "user.name", "Omni Test")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "example_test.py").write_text("def test_one():\n    assert True\n", encoding="utf-8")
    _git(repo, "add", "--", "tests/example_test.py")
    _git(repo, "commit", "-m", "test: seed repo")
    _git(repo, "checkout", "-b", "feature/phase24")
    (tests_dir / "example_test.py").write_text("def test_one():\n    assert 1 == 1\n", encoding="utf-8")
    return repo


def _gate(files: list[str] | None = None, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "success": True,
        "blocked": False,
        "commit_eligible": True,
        "commit_ready_metadata_only": True,
        "requires_human_intervention": False,
        "validation_passed": True,
        "patch_was_applied": True,
        "files_eligible_for_commit": files or ["tests/example_test.py"],
        "proposed_commit_message": "test(runtime): update governed sandbox coverage",
        "runtime_truth": {
            "event_type": "sandbox.commit_gate.decision",
            "secrets_detected": False,
            "main_modification_detected": False,
            "main_modified": False,
            "git_mutation_detected": False,
            "pr_created": False,
            "pr_merged": False,
            "validation_passed": True,
        },
    }
    payload.update(overrides)
    return payload


def _request(repo: Path | None = None, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "commit_gate_result": _gate(),
        "executor_mode": "commit_to_branch",
        "workspace_root": str(repo) if repo else None,
        "current_branch": "feature/phase24",
        "target_branch": "feature/phase24",
        "files_to_commit": ["tests/example_test.py"],
    }
    payload.update(overrides)
    return payload


def test_modes_block_or_dry_run_without_commit(git_repo: Path) -> None:
    disabled = execute_controlled_commit(_request(git_repo, executor_mode="disabled"))
    assert disabled.blocked is True
    blocked = execute_controlled_commit(_request(git_repo, executor_mode="blocked"))
    assert blocked.blocked is True
    unknown = execute_controlled_commit(_request(git_repo, executor_mode="unknown"))
    assert unknown.blocked is True

    head_before = _git(git_repo, "rev-parse", "HEAD")
    dry_run = execute_controlled_commit(_request(git_repo, executor_mode="dry_run"))
    assert dry_run.dry_run is True
    assert dry_run.committed is False
    assert dry_run.git_operations_attempted == []
    assert _git(git_repo, "rev-parse", "HEAD") == head_before


def test_commit_to_branch_creates_controlled_commit(git_repo: Path) -> None:
    head_before = _git(git_repo, "rev-parse", "HEAD")
    result = execute_controlled_commit(_request(git_repo))

    assert result.committed is True
    assert result.success is True
    assert result.commit_sha
    assert result.pre_commit_head == head_before
    assert result.post_commit_head == result.commit_sha
    assert result.post_commit_head != result.pre_commit_head
    assert result.files_staged == ["tests/example_test.py"]
    assert "git add -- <safe files>" in result.git_operations_attempted
    assert "git commit -m <safe message>" in result.git_operations_attempted
    assert result.can_push is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.requires_push_phase is True
    assert result.runtime_truth["event_type"] == "sandbox.commit_executor.commit"
    assert result.runtime_truth["commit_executed"] is True
    assert result.runtime_truth["files_staged"] is True
    assert result.runtime_truth["git_mutated"] is True
    assert result.runtime_truth["pushed"] is False
    assert result.runtime_truth["pr_created"] is False
    assert result.runtime_truth["main_modified"] is False


@pytest.mark.parametrize(
    ("gate_override", "expected"),
    [
        (None, "Phase 23 commit gate evidence is required."),
        ({"commit_eligible": False}, "Phase 23 commit gate did not mark this change eligible."),
        ({"blocked": True}, "Phase 23 commit gate blocked commit eligibility."),
        ({"requires_human_intervention": True}, "Phase 23 commit gate requires human intervention."),
        ({"validation_passed": False}, "Phase 23 validation evidence did not pass."),
    ],
)
def test_phase23_gate_blocks_invalid_evidence(
    git_repo: Path,
    gate_override: dict[str, object] | None,
    expected: str,
) -> None:
    gate = None if gate_override is None else _gate(**gate_override)
    result = execute_controlled_commit(_request(git_repo, commit_gate_result=gate))
    assert result.blocked is True
    assert result.committed is False
    assert result.blocked_reason == expected


@pytest.mark.parametrize(
    "truth_flag",
    ["secrets_detected", "main_modified", "main_modification_detected", "git_mutation_detected", "pr_created", "pr_merged"],
)
def test_gate_runtime_truth_unsafe_flags_block(git_repo: Path, truth_flag: str) -> None:
    gate = _gate()
    truth = dict(gate["runtime_truth"])  # type: ignore[index]
    truth[truth_flag] = True
    gate["runtime_truth"] = truth
    result = execute_controlled_commit(_request(git_repo, commit_gate_result=gate))
    assert result.blocked is True
    assert result.requires_human_intervention is True


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"current_branch": "main"}, "current_branch must not be main."),
        ({"current_branch": None}, "current_branch metadata is required."),
        ({"current_branch": "main"}, "current_branch must not be main."),
        ({"current_branch": "feature/other"}, "current_branch metadata does not match verified branch."),
        ({"current_branch": "main", "base_branch": "main"}, "current_branch must not be main."),
        ({"target_branch": "main"}, "target_branch must not be main."),
        ({"base_branch": "develop"}, "base_branch must be main."),
        ({"current_branch": "release/1.0"}, "protected release or production branch is blocked."),
    ],
)
def test_branch_safety_blocks(git_repo: Path, override: dict[str, object], reason: str) -> None:
    result = execute_controlled_commit(_request(git_repo, **override))
    assert result.blocked is True
    assert result.blocked_reason == reason


@pytest.mark.parametrize(
    "path",
    [
        "tests/example_test.py",
        "backend/python/module.py",
        "backend/rust/src/lib.rs",
        "frontend/src/App.tsx",
        "docs/example.md",
        "sandbox/local/runbook.md",
        "vault/templates/example.md",
    ],
)
def test_allowed_file_metadata_can_dry_run(path: str, git_repo: Path) -> None:
    result = execute_controlled_commit(
        _request(
            git_repo,
            executor_mode="dry_run",
            commit_gate_result=_gate([path]),
            files_to_commit=[path],
        )
    )
    assert result.blocked is False
    assert result.files_considered == [path]


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "vault/08_ADR/example.md",
        "docs/governance/policy.md",
        "docs/security/threat-model.md",
        ".github/workflows/ci.yml",
        ".circleci/config.yml",
        "../escape.py",
        "C:/outside/repo.py",
        ".git/config",
        "tests/not-eligible.py",
    ],
)
def test_file_safety_blocks(path: str, git_repo: Path) -> None:
    result = execute_controlled_commit(
        _request(git_repo, executor_mode="dry_run", commit_gate_result=_gate(), files_to_commit=[path])
    )
    assert result.blocked is True or result.redacted is True


def test_missing_workspace_and_no_eligible_changes_block(git_repo: Path) -> None:
    missing_workspace = execute_controlled_commit(_request(None))
    assert missing_workspace.blocked is True
    assert missing_workspace.blocked_reason == "workspace_root is required for commit execution."

    clean = execute_controlled_commit(_request(git_repo))
    assert clean.committed is True
    second = execute_controlled_commit(_request(git_repo))
    assert second.blocked is True
    assert second.blocked_reason == "No eligible changed files were available to stage."


def test_commit_message_safety_and_serialization(git_repo: Path) -> None:
    unsafe = execute_controlled_commit(
        _request(git_repo, proposed_commit_message="fix: OPENAI_API_KEY placeholder")
    )
    assert unsafe.blocked is True
    assert unsafe.redacted is True
    assert "OPENAI_API_KEY" not in json.dumps(unsafe.to_dict())

    long_message = "test(runtime): " + ("x" * 300)
    result = execute_controlled_commit(
        _request(git_repo, executor_mode="dry_run", commit_gate_result=_gate(proposed_commit_message=long_message))
    )
    assert result.final_commit_message is not None
    assert len(result.final_commit_message) <= 120
    json.dumps(result.to_dict())


def test_git_hook_failure_reported_without_bypass(git_repo: Path) -> None:
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    result = execute_controlled_commit(_request(git_repo))
    assert result.success is False
    assert result.blocked is True
    assert result.partial is True
    assert "--no-verify" not in " ".join(result.git_operations_attempted)


def test_source_has_only_controlled_subprocess_usage() -> None:
    source = Path("backend/python/brain/runtime/sandbox/commit_executor.py").read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "os.system" not in source
    assert "eval(" not in source
    assert "exec(" not in source
    assert "requests." not in source
    assert "urllib" not in source
    assert "socket" not in source
    assert "websocket" not in source
    assert "http.client" not in source
    assert "pexpect" not in source
    assert "subprocess.run(" in source
    assert "shell=False" in source
