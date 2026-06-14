"""Tests for the controlled push executor."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from brain.runtime.sandbox.push_executor import execute_controlled_push


def _commit_executor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "committed": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "commit_sha": "abc123def456",
        "current_branch": "feature/phase26",
        "target_branch": "feature/phase26",
        "workspace_root": "repo",
        "requires_push_phase": True,
        "can_push": False,
        "runtime_truth": {
            "event_type": "sandbox.commit_executor.commit",
            "secrets_detected": False,
            "pushed": False,
            "push_executed": False,
            "force_push_executed": False,
            "main_pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
            "main_modified": False,
            "provider_called": False,
            "mcp_used": False,
            "agent_called": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _push_gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "push_eligible": True,
        "push_ready_metadata_only": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "current_branch": "feature/phase26",
        "target_branch": "feature/phase26",
        "remote_name": "origin",
        "remote_branch": "feature/phase26",
        "proposed_push_ref": "feature/phase26",
        "commit_sha": "abc123def456",
        "runtime_truth": {
            "event_type": "sandbox.push_gate.decision",
            "secrets_detected": False,
            "force_push_detected": False,
            "main_push_detected": False,
            "protected_branch_detected": False,
            "push_executed": False,
            "main_pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
            "main_modified": False,
            "provider_called": False,
            "mcp_used": False,
            "agent_called": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "push_gate_result": _push_gate(),
        "commit_executor_result": _commit_executor(),
        "executor_mode": "dry_run",
        "current_branch": "feature/phase26",
        "verified_current_branch": "feature/phase26",
        "target_branch": "feature/phase26",
        "remote_name": "origin",
        "remote_branch": "feature/phase26",
        "proposed_push_ref": "feature/phase26",
        "commit_sha": "abc123def456",
    }
    payload.update(overrides)
    return payload


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return (completed.stdout or "").strip()


def _make_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, shell=False, capture_output=True)
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "omni@example.invalid")
    _git(repo, "config", "user.name", "Omni Test")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "example_test.py").write_text("def test_example():\n    assert True\n", encoding="utf-8")
    _git(repo, "add", "--", "tests/example_test.py")
    _git(repo, "commit", "-m", "test: seed repo")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "checkout", "-b", "feature/phase26")
    (tests_dir / "example_test.py").write_text("def test_example():\n    assert 1 == 1\n", encoding="utf-8")
    _git(repo, "add", "--", "tests/example_test.py")
    _git(repo, "commit", "-m", "test: update example")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, remote, head


def test_modes_block_or_dry_run() -> None:
    assert execute_controlled_push(_request(executor_mode="disabled")).blocked is True
    assert execute_controlled_push(_request(executor_mode="blocked")).blocked is True
    assert execute_controlled_push(_request(executor_mode="unknown")).blocked is True

    result = execute_controlled_push(_request(executor_mode="dry_run"))
    assert result.dry_run is True
    assert result.success is True
    assert result.pushed is False
    assert result.git_operations_attempted == []
    assert result.runtime_truth["push_executed"] is False


def test_phase25_push_gate_integration_blocks_invalid_evidence() -> None:
    assert execute_controlled_push(_request(push_gate_result=None)).blocked is True
    assert execute_controlled_push(_request(push_gate_result=_push_gate(push_eligible=False))).blocked is True
    assert execute_controlled_push(_request(push_gate_result=_push_gate(blocked=True))).blocked is True
    assert execute_controlled_push(_request(push_gate_result=_push_gate(requires_human_intervention=True))).blocked is True
    assert execute_controlled_push(_request(push_gate_result=_push_gate(success=False))).blocked is True
    for flag in (
        "secrets_detected",
        "force_push_detected",
        "main_push_detected",
        "protected_branch_detected",
        "push_executed",
        "main_pushed",
        "pr_created",
        "pr_merged",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    ):
        gate = _push_gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert execute_controlled_push(_request(push_gate_result=gate)).blocked is True


def test_phase24_commit_executor_integration_blocks_invalid_evidence() -> None:
    assert execute_controlled_push(_request(commit_executor_result=None)).blocked is True
    assert execute_controlled_push(_request(commit_executor_result=_commit_executor(committed=False))).blocked is True
    assert execute_controlled_push(_request(commit_executor_result=_commit_executor(success=False))).blocked is True
    assert execute_controlled_push(_request(commit_executor_result=_commit_executor(blocked=True))).blocked is True
    assert execute_controlled_push(_request(commit_executor_result=_commit_executor(requires_human_intervention=True))).blocked is True
    assert execute_controlled_push(_request(commit_executor_result=_commit_executor(commit_sha=None), commit_sha=None)).blocked is True
    for flag in (
        "secrets_detected",
        "pushed",
        "push_executed",
        "force_push_executed",
        "main_pushed",
        "pr_created",
        "pr_merged",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    ):
        executor = _commit_executor()
        truth = dict(executor["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        executor["runtime_truth"] = truth
        assert execute_controlled_push(_request(commit_executor_result=executor)).blocked is True


def test_branch_and_remote_safety() -> None:
    cases = [
        {"current_branch": "main"},
        {"current_branch": None},
        {"verified_current_branch": "main"},
        {"verified_current_branch": None},
        {"verified_current_branch": "feature/other"},
        {"current_branch": "feature/phase26", "base_branch": "feature/phase26"},
        {"target_branch": "main"},
        {"remote_branch": "main"},
        {"base_branch": "develop"},
        {"current_branch": "release/1.0", "verified_current_branch": "release/1.0", "remote_branch": "release/1.0"},
        {"remote_name": "upstream"},
        {"remote_name": "origin;bad"},
        {"remote_branch": "feature/other"},
        {"proposed_push_ref": "+feature/phase26"},
        {"proposed_push_ref": "feature/phase26:refs/heads/main"},
        {"metadata": {"direct_main_edit": True}},
        {"metadata": {"push_main": True}},
        {"metadata": {"force_push": True}},
    ]
    for override in cases:
        result = execute_controlled_push(_request(**override))
        assert result.blocked is True


def test_redaction_blocks_secret_like_content() -> None:
    result = execute_controlled_push(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    branch = execute_controlled_push(_request(current_branch="feature/SECRET-placeholder"))
    assert branch.blocked is True
    assert branch.redacted is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    ref = execute_controlled_push(_request(proposed_push_ref="feature/ghp_placeholder"))
    assert ref.blocked is True
    assert ref.redacted is True
    assert "ghp_" not in json.dumps(ref.to_dict())


def test_push_branch_performs_controlled_push(tmp_path: Path) -> None:
    repo, remote, head = _make_repo(tmp_path)
    result = execute_controlled_push(
        _request(
            executor_mode="push_branch",
            workspace_root=str(repo),
            commit_sha=head,
            push_gate_result=_push_gate(commit_sha=head),
            commit_executor_result=_commit_executor(commit_sha=head, workspace_root=str(repo)),
        )
    )
    assert result.success is True
    assert result.pushed is True
    assert result.pushed_remote == "origin"
    assert result.pushed_ref == "feature/phase26:refs/heads/feature/phase26"
    assert result.pre_push_head == head
    assert result.post_push_head == head
    assert "git push origin <safe_branch>:refs/heads/<safe_remote_branch>" in result.git_operations_attempted
    assert result.runtime_truth["event_type"] == "sandbox.push_executor.push"
    assert result.runtime_truth["push_executed"] is True
    assert result.runtime_truth["git_mutated"] is True
    assert result.runtime_truth["network_used"] is True
    assert result.runtime_truth["pr_created"] is False
    assert result.runtime_truth["pr_merged"] is False
    assert result.runtime_truth["main_modified"] is False
    pushed_head = subprocess.run(
        ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/feature/phase26"],
        check=True,
        shell=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert pushed_head == head


def test_push_branch_blocks_status_with_secret_like_file(tmp_path: Path) -> None:
    repo, _, head = _make_repo(tmp_path)
    (repo / ".env").write_text("placeholder only\n", encoding="utf-8")
    result = execute_controlled_push(
        _request(
            executor_mode="push_branch",
            workspace_root=str(repo),
            commit_sha=head,
            push_gate_result=_push_gate(commit_sha=head),
            commit_executor_result=_commit_executor(commit_sha=head, workspace_root=str(repo)),
        )
    )
    assert result.blocked is True
    assert result.redacted is True
    assert result.pushed is False
    assert "git push origin <safe_branch>:refs/heads/<safe_remote_branch>" in result.git_operations_blocked
    assert ".env" not in json.dumps(result.to_dict())


def test_push_failure_is_reported_without_bypassing_policy(tmp_path: Path) -> None:
    repo, _, head = _make_repo(tmp_path)
    _git(repo, "remote", "remove", "origin")
    result = execute_controlled_push(
        _request(
            executor_mode="push_branch",
            workspace_root=str(repo),
            commit_sha=head,
            push_gate_result=_push_gate(commit_sha=head),
            commit_executor_result=_commit_executor(commit_sha=head, workspace_root=str(repo)),
        )
    )
    assert result.success is False
    assert result.blocked is True
    assert result.pushed is False
    assert result.runtime_truth["push_executed"] is False
    assert "git push origin <safe_branch>:refs/heads/<safe_remote_branch>" in result.git_operations_attempted


def test_output_shape_and_flags_are_safe() -> None:
    result = execute_controlled_push(_request(executor_mode="dry_run"))
    json.dumps(result.to_dict())
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_rebase is False
    assert result.can_force_push is False
    assert result.can_push_main is False
    assert result.can_create_branch is False
    assert result.can_checkout is False
    assert result.can_edit_code is False
    assert result.can_apply_patch is False
    assert result.runtime_truth["force_push_executed"] is False
    assert result.runtime_truth["main_pushed"] is False
    assert len(result.runtime_truth["child_runtime_truth_events"]) == 2


def test_source_restricts_subprocess_to_fixed_git_allowlist() -> None:
    source = Path("backend/python/brain/runtime/sandbox/push_executor.py").read_text(encoding="utf-8")
    assert "subprocess.run" in source
    assert "shell=False" in source
    forbidden = [
        "shell=True",
        "os.system",
        "eval(",
        "exec(",
        "requests.",
        "urllib",
        "socket",
        "websocket",
        "http.client",
        "pexpect",
        "git add",
        "git commit",
        "git merge",
        "git rebase",
        "git checkout",
        "git switch",
        "git branch",
        " gh ",
        "open(",
        "write(",
        "unlink(",
        "rename(",
        "remove(",
        "rmtree(",
        "shutil.move",
    ]
    for pattern in forbidden:
        assert pattern not in source
