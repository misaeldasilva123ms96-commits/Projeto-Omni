from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    ControlledPatchApplierRequest,
    apply_controlled_patch,
)
from brain.runtime.sandbox import patch_applier  # noqa: E402


def _proposal(path: str = "tests/example_test.py", **overrides):
    payload = {
        "proposal_id": "patch-proposal-1",
        "file_path": path,
        "operation": "modify_existing",
        "risk_level": "low",
        "requires_human": False,
        "allowed_in_future_patch_apply": True,
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "hunks": [
            {
                "hunk_id": "hunk-1",
                "hunk_type": "bounded_snippet_metadata",
                "before_context": "assert False",
                "proposed_snippet": "assert True",
                "after_intent": "fix assertion",
                "confidence": "medium",
                "risk_level": "low",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _request(tmp_path: Path, **overrides) -> ControlledPatchApplierRequest:
    values = {
        "patch_proposal": {
            "patch_proposals": [_proposal()],
            "validation_commands": ["python -m pytest tests/example_test.py"],
        },
        "requested_by": "codex",
        "applier_mode": "apply_to_branch",
        "workspace_root": str(tmp_path),
        "current_branch": "sandbox/controlled-branch-patch-applier",
        "target_branch": "sandbox/controlled-branch-patch-applier",
        "base_branch": "main",
        "related_phase": "phase-21",
        "related_pr": "future",
        "allowed_files": ["tests/example_test.py"],
        "blocked_files": [],
        "max_files_to_apply": 5,
        "max_hunks_per_file": 8,
        "max_total_hunks": 20,
        "max_file_bytes": 500000,
        "require_non_main_branch": True,
        "require_runtime_truth": True,
        "require_validation_commands": True,
        "allow_file_create": False,
        "allow_file_delete": False,
        "allow_file_rename": False,
        "allow_chmod": False,
        "allow_dependency_change": False,
        "allow_ci_change": False,
        "allow_governance_change": False,
        "allow_security_change": False,
        "allow_vault_write": False,
        "allow_git_mutation": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return ControlledPatchApplierRequest(**values)


def _write_target(tmp_path: Path, path: str, content: str = "def test_example():\n    assert False\n") -> Path:
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _apply(tmp_path: Path, **overrides):
    return apply_controlled_patch(_request(tmp_path, **overrides))


def test_modes_disabled_blocked_dry_run_apply_and_unknown(tmp_path: Path) -> None:
    target = _write_target(tmp_path, "tests/example_test.py")

    disabled = _apply(tmp_path, applier_mode="disabled")
    blocked = _apply(tmp_path, applier_mode="blocked")
    dry_run = _apply(tmp_path, applier_mode="dry_run")
    unknown = _apply(tmp_path, applier_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert dry_run.dry_run is True
    assert "assert False" in target.read_text(encoding="utf-8")
    applied = _apply(tmp_path, applier_mode="apply_to_branch")
    assert applied.applied is True
    assert "assert True" in target.read_text(encoding="utf-8")


def test_branch_safety_blocks_main_missing_base_and_target(tmp_path: Path) -> None:
    _write_target(tmp_path, "tests/example_test.py")

    assert _apply(tmp_path, current_branch="main").blocked is True
    assert _apply(tmp_path, current_branch=None).blocked is True
    assert _apply(tmp_path, current_branch="main", base_branch="main").blocked is True
    assert _apply(tmp_path, target_branch="main").blocked is True
    assert _apply(tmp_path, base_branch="develop").blocked is True
    assert _apply(tmp_path, current_branch="release/1.0").blocked is True
    assert _apply(tmp_path).applied is True


def test_modify_existing_exact_unique_missing_and_ambiguous_context(tmp_path: Path) -> None:
    target = _write_target(tmp_path, "tests/example_test.py")
    success = _apply(tmp_path)
    assert success.applied is True
    assert "assert True" in target.read_text(encoding="utf-8")

    _write_target(tmp_path, "tests/example_test.py", "assert False\nassert False\n")
    ambiguous = _apply(tmp_path)
    assert ambiguous.applied is False
    assert ambiguous.hunks_blocked == 1

    _write_target(tmp_path, "tests/example_test.py", "assert 1\n")
    missing = _apply(tmp_path)
    assert missing.applied is False
    assert missing.hunks_blocked == 1

    no_snippet = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [_proposal(hunks=[{"hunk_id": "h1", "before_context": "assert 1"}])]},
    )
    assert no_snippet.applied is False
    assert no_snippet.hunks_blocked == 1


def test_limits_and_max_file_bytes(tmp_path: Path) -> None:
    files = ["tests/a_test.py", "tests/b_test.py", "tests/c_test.py"]
    for path in files:
        _write_target(tmp_path, path)
    proposals = [_proposal(path) for path in files]
    limited = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": proposals},
        allowed_files=files,
        max_files_to_apply=2,
    )
    assert len(limited.files_considered) == 2
    assert len(limited.files_applied) == 2

    hunk_limited = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [_proposal(hunks=[_proposal()["hunks"][0], _proposal()["hunks"][0]])]},
        max_hunks_per_file=1,
        max_total_hunks=1,
    )
    assert hunk_limited.hunks_requested == 1

    _write_target(tmp_path, "tests/example_test.py")
    too_large = _apply(tmp_path, max_file_bytes=5)
    assert too_large.applied is False
    assert too_large.hunks_blocked == 1


def test_file_scope_allowed_and_protected_paths(tmp_path: Path) -> None:
    allowed_paths = [
        "tests/example_test.py",
        "backend/python/module.py",
        "backend/rust/src/lib.rs",
        "frontend/src/App.tsx",
        "docs/example.md",
        "sandbox/local/runbook.md",
        "vault/templates/example.md",
    ]
    for path in allowed_paths:
        _write_target(tmp_path, path)
        result = _apply(
            tmp_path,
            patch_proposal={"patch_proposals": [_proposal(path)]},
            allowed_files=[path],
        )
        assert result.applied is True

    blocked_paths = [
        ".env",
        "vault/08_ADR/example.md",
        "docs/governance/policy.md",
        "docs/security/threat-model.md",
        ".github/workflows/ci.yml",
        "../escape.py",
        str(tmp_path.parent / "outside.py"),
        ".git/config",
    ]
    for path in blocked_paths:
        result = _apply(
            tmp_path,
            patch_proposal={"patch_proposals": [_proposal(path)]},
            allowed_files=[path],
        )
        assert result.applied is False
        assert result.blocked or result.requires_human_intervention


def test_operations_create_append_and_blocked_operations(tmp_path: Path) -> None:
    new_test = _proposal(
        "tests/new_test.py",
        operation="add_test",
        hunks=[{"hunk_id": "h1", "proposed_snippet": "def test_new():\n    assert True\n", "risk_level": "low"}],
    )
    create_blocked = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [new_test]},
        allowed_files=["tests/new_test.py"],
    )
    create_allowed = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [new_test]},
        allowed_files=["tests/new_test.py"],
        allow_file_create=True,
    )
    assert create_blocked.applied is False
    assert create_allowed.applied is True
    assert (tmp_path / "tests/new_test.py").exists()

    docs = _proposal(
        "docs/example.md",
        operation="add_documentation",
        hunks=[{"hunk_id": "h1", "proposed_snippet": "# Example\n", "risk_level": "low"}],
    )
    doc_result = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [docs]},
        allowed_files=["docs/example.md"],
        allow_file_create=True,
    )
    assert doc_result.applied is True

    for operation in (
        "delete_file",
        "rename_file",
        "move_file",
        "chmod_change",
        "dependency_upgrade",
        "ci_threshold_change",
        "security_policy_change",
        "governance_policy_change",
        "production_deploy_change",
        "billing_change",
        "secret_change",
    ):
        _write_target(tmp_path, "tests/example_test.py")
        result = _apply(tmp_path, patch_proposal={"patch_proposals": [_proposal(operation=operation)]})
        assert result.applied is False
        assert result.requires_human_intervention is True


def test_hashes_audit_runtime_truth_and_followup_validation(tmp_path: Path) -> None:
    _write_target(tmp_path, "tests/example_test.py")
    result = _apply(tmp_path)

    assert result.pre_apply_hashes["tests/example_test.py"]
    assert result.post_apply_hashes["tests/example_test.py"]
    assert result.pre_apply_hashes["tests/example_test.py"] != result.post_apply_hashes["tests/example_test.py"]
    assert result.applied_changes[0]["file_path"] == "tests/example_test.py"
    assert result.runtime_truth["event_type"] == "sandbox.patch_applier.apply"
    assert result.runtime_truth["files_written"] is True
    assert result.runtime_truth["code_edited"] is True
    assert result.runtime_truth["patch_applied"] is True
    assert result.requires_followup_validation is True
    for key in (
        "command_executed",
        "git_mutated",
        "pr_created",
        "pr_merged",
        "network_used",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
        "main_modified",
    ):
        assert result.runtime_truth[key] is False


def test_validation_commands_are_metadata_only_and_safe(tmp_path: Path) -> None:
    _write_target(tmp_path, "tests/example_test.py")
    proposal = _proposal(
        validation_commands=[
            "python -m pytest tests/example_test.py",
            "git add .",
            "git commit -m nope",
            "git push origin main",
            "git merge main",
            "git rebase main",
            "gh pr merge 1",
            "curl https://example.invalid",
        ]
    )
    result = _apply(tmp_path, patch_proposal={"patch_proposals": [proposal]})
    joined = " ".join(result.validation_commands)

    assert result.validation_commands == ["python -m pytest tests/example_test.py"]
    assert "git add" not in joined
    assert "git commit" not in joined
    assert "git push" not in joined
    assert "git merge" not in joined
    assert "git rebase" not in joined
    assert "gh " not in joined
    assert "curl" not in joined
    assert result.can_execute_tests is False


def test_flags_are_locked_down(tmp_path: Path) -> None:
    _write_target(tmp_path, "tests/example_test.py")
    result = _apply(tmp_path)

    assert result.can_commit is False
    assert result.can_push is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_execute_tests is False

    for flag in (
        "allow_file_delete",
        "allow_file_rename",
        "allow_chmod",
        "allow_dependency_change",
        "allow_ci_change",
        "allow_governance_change",
        "allow_security_change",
        "allow_vault_write",
        "allow_git_mutation",
    ):
        blocked = _apply(tmp_path, **{flag: True})
        assert blocked.blocked is True


def test_redaction_blocks_secret_like_inputs_without_writing(tmp_path: Path) -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"
    target = _write_target(tmp_path, "tests/example_test.py")
    before_secret = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [_proposal(hunks=[{"hunk_id": "h1", "before_context": f"{marker}=x", "proposed_snippet": "safe", "risk_level": "low"}])]},
    )
    snippet_secret = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [_proposal(hunks=[{"hunk_id": "h1", "before_context": "assert False", "proposed_snippet": f"{bearer} placeholder", "risk_level": "low"}])]},
    )
    path_secret = _apply(
        tmp_path,
        patch_proposal={"patch_proposals": [_proposal(".env")]},
        allowed_files=[".env"],
    )
    encoded = json.dumps(before_secret.to_dict()) + json.dumps(snippet_secret.to_dict()) + json.dumps(path_secret.to_dict())

    assert before_secret.blocked is True
    assert snippet_secret.blocked is True
    assert path_secret.blocked is True
    assert "assert False" in target.read_text(encoding="utf-8")
    assert marker not in encoded
    assert bearer not in encoded


def test_source_has_no_unsafe_implementation() -> None:
    source = inspect.getsource(patch_applier)
    forbidden = (
        "sub" + "process",
        "shell=True",
        "os.system",
        "eval" + "(",
        "exec" + "(",
        "requests" + ".",
        "urllib",
        "socket",
        "websocket",
        "http.client",
        "pexpect",
        "MCP SDK",
        "provider call implementation",
        "real GitHub PR creation",
        "real PR merge implementation",
        "auto_merge",
        "unlink" + "(",
        "remove" + "(",
        "rmtree" + "(",
        "rename" + "(",
        "chmod" + "(",
        "chown" + "(",
    )

    for pattern in forbidden:
        assert pattern not in source
