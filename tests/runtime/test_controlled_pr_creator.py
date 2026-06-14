"""Tests for the controlled PR creator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from brain.runtime.sandbox.pr_creator import create_controlled_pr


class FakeGitHubClient:
    def __init__(self, existing: Mapping[str, Any] | None = None, response: Mapping[str, Any] | None = None) -> None:
        self.existing = existing
        self.response = response or {
            "number": 357,
            "url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/357",
            "html_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/357",
            "node_id": "PR_kwDOExample",
            "state": "open",
        }
        self.find_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []
        self.merge_calls = 0
        self.auto_merge_calls = 0
        self.approve_calls = 0

    def find_open_pull_request(
        self,
        *,
        repository_full_name: str,
        head_branch: str,
        base_branch: str,
    ) -> Mapping[str, Any] | None:
        self.find_calls.append(
            {
                "repository_full_name": repository_full_name,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        )
        return self.existing

    def create_pull_request(
        self,
        *,
        repository_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool,
    ) -> Mapping[str, Any]:
        self.create_calls.append(
            {
                "repository_full_name": repository_full_name,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
                "draft": draft,
            }
        )
        return self.response


def _push_executor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pushed": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "current_branch": "feature/phase28",
        "remote_branch": "feature/phase28",
        "pushed_ref": "feature/phase28:refs/heads/feature/phase28",
        "pushed_remote": "origin",
        "commit_sha": "abc123def456",
        "runtime_truth": {
            "event_type": "sandbox.push_executor.push",
            "secrets_detected": False,
            "push_executed": True,
            "force_push_executed": False,
            "main_pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "merge_performed": False,
            "rebase_performed": False,
            "checkout_performed": False,
            "branch_created": False,
            "provider_called": False,
            "agent_called": False,
            "mcp_used": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pr_eligible": True,
        "pr_ready_metadata_only": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "source_branch": "feature/phase28",
        "head_branch": "feature/phase28",
        "base_branch": "main",
        "current_branch": "feature/phase28",
        "remote_branch": "feature/phase28",
        "pushed_ref": "feature/phase28:refs/heads/feature/phase28",
        "pushed_remote": "origin",
        "commit_sha": "abc123def456",
        "proposed_pr_title": "sandbox: add controlled PR creator",
        "proposed_pr_body": "Summary only. No merge or auto-merge.",
        "proposed_pr_draft": True,
        "proposed_labels": ["sandbox", "phase-28"],
        "proposed_reviewers": ["misael"],
        "proposed_assignees": ["misael"],
        "runtime_truth": {
            "event_type": "sandbox.pr_creation_gate.decision",
            "secrets_detected": False,
            "pr_created": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "push_executed": False,
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
        "pr_creation_gate_result": _gate(),
        "push_executor_result": _push_executor(),
        "creator_mode": "create_pr",
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "source_branch": "feature/phase28",
        "head_branch": "feature/phase28",
        "base_branch": "main",
        "current_branch": "feature/phase28",
        "remote_branch": "feature/phase28",
        "pushed_ref": "feature/phase28:refs/heads/feature/phase28",
        "pushed_remote": "origin",
        "commit_sha": "abc123def456",
        "labels": ["sandbox"],
        "reviewers": ["misael"],
        "assignees": ["misael"],
    }
    if "pr_creation_gate_result" not in overrides:
        gate = dict(payload["pr_creation_gate_result"])  # type: ignore[arg-type]
        for field in (
            "repository_full_name",
            "source_branch",
            "head_branch",
            "base_branch",
            "current_branch",
            "remote_branch",
            "pushed_ref",
            "pushed_remote",
            "commit_sha",
        ):
            if field in overrides:
                gate[field] = overrides[field]
        if "pr_title" in overrides:
            gate["proposed_pr_title"] = overrides["pr_title"]
        if "pr_body" in overrides:
            gate["proposed_pr_body"] = overrides["pr_body"]
        payload["pr_creation_gate_result"] = gate
    if "push_executor_result" not in overrides:
        push_executor = dict(payload["push_executor_result"])  # type: ignore[arg-type]
        for field in ("current_branch", "remote_branch", "pushed_ref", "pushed_remote", "commit_sha"):
            if field in overrides:
                push_executor[field] = overrides[field]
        payload["push_executor_result"] = push_executor
    payload.update(overrides)
    return payload


def test_modes_block_or_dry_run() -> None:
    fake = FakeGitHubClient()
    assert create_controlled_pr(_request(creator_mode="disabled"), fake).blocked is True
    assert create_controlled_pr(_request(creator_mode="blocked"), fake).blocked is True
    assert create_controlled_pr(_request(creator_mode="unknown"), fake).blocked is True

    dry_run = create_controlled_pr(_request(creator_mode="dry_run"), fake)
    assert dry_run.dry_run is True
    assert dry_run.pr_created is False
    assert fake.find_calls == []
    assert fake.create_calls == []


def test_create_pr_calls_fake_client_once() -> None:
    fake = FakeGitHubClient()
    result = create_controlled_pr(_request(), fake)
    assert result.success is True
    assert result.pr_created is True
    assert result.pr_number == 357
    assert result.pr_url == "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/357"
    assert result.pr_state == "open"
    assert result.final_draft is True
    assert len(fake.find_calls) == 1
    assert len(fake.create_calls) == 1
    assert fake.create_calls[0] == {
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "title": "sandbox: add controlled PR creator",
        "body": "Summary only. No merge or auto-merge.",
        "head_branch": "feature/phase28",
        "base_branch": "main",
        "draft": True,
    }
    assert fake.merge_calls == 0
    assert fake.auto_merge_calls == 0
    assert fake.approve_calls == 0
    assert result.runtime_truth["event_type"] == "sandbox.pr_creator.create"
    assert result.runtime_truth["pr_created"] is True
    assert result.runtime_truth["network_used"] is True


def test_phase27_integration_blocks_invalid_gate_evidence() -> None:
    fake = FakeGitHubClient()
    assert create_controlled_pr(_request(pr_creation_gate_result=None), fake).blocked is True
    assert create_controlled_pr(_request(pr_creation_gate_result=_gate(pr_eligible=False)), fake).blocked is True
    assert create_controlled_pr(_request(pr_creation_gate_result=_gate(pr_ready_metadata_only=False)), fake).blocked is True
    assert create_controlled_pr(_request(pr_creation_gate_result=_gate(blocked=True)), fake).blocked is True
    assert create_controlled_pr(_request(pr_creation_gate_result=_gate(requires_human_intervention=True)), fake).blocked is True

    for flag in (
        "secrets_detected",
        "pr_created",
        "pr_merged",
        "auto_merge_enabled",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    ):
        gate = _gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert create_controlled_pr(_request(pr_creation_gate_result=gate), fake).blocked is True
    assert fake.create_calls == []


def test_phase26_integration_blocks_invalid_push_evidence() -> None:
    fake = FakeGitHubClient()
    assert create_controlled_pr(_request(push_executor_result=None), fake).blocked is True
    assert create_controlled_pr(_request(push_executor_result=_push_executor(pushed=False)), fake).blocked is True
    assert create_controlled_pr(_request(push_executor_result=_push_executor(success=False)), fake).blocked is True
    assert create_controlled_pr(_request(push_executor_result=_push_executor(pushed_ref=None), pushed_ref=None), fake).blocked is True
    assert create_controlled_pr(_request(push_executor_result=_push_executor(pushed_remote=None), pushed_remote=None), fake).blocked is True
    assert create_controlled_pr(_request(push_executor_result=_push_executor(commit_sha=None), commit_sha=None), fake).blocked is True

    for flag in (
        "force_push_executed",
        "main_pushed",
        "pr_created",
        "pr_merged",
        "auto_merge_enabled",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    ):
        executor = _push_executor()
        truth = dict(executor["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        executor["runtime_truth"] = truth
        assert create_controlled_pr(_request(push_executor_result=executor), fake).blocked is True


def test_branch_and_repository_safety() -> None:
    fake = FakeGitHubClient()
    cases = [
        {"head_branch": "main"},
        {"source_branch": "main"},
        {"current_branch": "main"},
        {"remote_branch": "main"},
        {"source_branch": None},
        {"base_branch": "develop"},
        {"head_branch": "main", "base_branch": "main"},
        {"source_branch": "main", "base_branch": "main"},
        {"head_branch": "release/1.0", "source_branch": "release/1.0", "remote_branch": "release/1.0"},
        {"head_branch": "prod/x", "source_branch": "prod/x", "remote_branch": "prod/x"},
        {"metadata": {"direct_main_edit": True}},
        {"metadata": {"source_main": True}},
        {"repository_full_name": None},
        {"repository_full_name": "owner/repo;bad"},
        {"repository_full_name": "owner/ghp_placeholder"},
        {"repository_full_name": "owner/github_pat_placeholder"},
        {"repository_full_name": "https://token@example.invalid/repo"},
        {"repository_full_name": "missing-owner"},
        {"repository_full_name": "other/fork"},
    ]
    for override in cases:
        result = create_controlled_pr(_request(**override), fake)
        assert result.blocked is True
    assert fake.create_calls == []


def test_duplicate_pr_detected_prevents_second_creation() -> None:
    fake = FakeGitHubClient(existing={"number": 12, "url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/12", "state": "open"})
    result = create_controlled_pr(_request(), fake)
    assert result.success is True
    assert result.pr_created is False
    assert result.duplicate_pr_detected is True
    assert result.existing_pr_url == "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/12"
    assert len(fake.find_calls) == 1
    assert fake.create_calls == []
    assert result.runtime_truth["governance_decision"] == "existing_pr_detected"


def test_title_body_and_metadata_safety() -> None:
    fake = FakeGitHubClient()
    long_title = create_controlled_pr(_request(pr_title="x" * 150), fake)
    assert long_title.blocked is False
    assert len(long_title.final_pr_title or "") <= 120

    blocked_cases = [
        {"pr_title": "OPENAI_API_KEY placeholder"},
        {"pr_title": "touch .env"},
        {"pr_body": "Authorization: Bearer placeholder"},
        {"labels": ["sandbox;bad"]},
        {"reviewers": ["person@example.invalid"]},
        {"assignees": ["https://example.invalid/user"]},
        {"labels": ["ghp_placeholder"]},
        {"reviewers": ["TOKEN_placeholder"]},
        {"assignees": ["SECRET_placeholder"]},
    ]
    for override in blocked_cases:
        result = create_controlled_pr(_request(**override), fake)
        assert result.blocked is True
        assert result.pr_created is False
        assert "Authorization: Bearer" not in json.dumps(result.to_dict())
        assert "OPENAI_API_KEY" not in json.dumps(result.to_dict())
        assert ".env" not in json.dumps(result.to_dict())
        assert "ghp_" not in json.dumps(result.to_dict())


def test_generated_body_and_safe_flags() -> None:
    fake = FakeGitHubClient()
    gate = _gate(proposed_pr_body=None)
    result = create_controlled_pr(_request(pr_creation_gate_result=gate, pr_body=None), fake)
    assert result.pr_created is True
    assert result.final_pr_body is not None
    assert "Safety confirmations" in result.final_pr_body
    assert "Next expected phase: CI Monitor" in result.final_pr_body
    assert result.can_merge is False
    assert result.can_auto_merge is False
    assert result.can_push is False
    assert result.can_force_push is False
    assert result.can_push_main is False
    assert result.can_rebase is False
    assert result.can_create_branch is False
    assert result.can_checkout is False
    assert result.can_edit_code is False
    assert result.can_apply_patch is False
    assert result.requires_ci_monitor_phase is True
    assert result.requires_merge_gate_phase is False


def test_runtime_truth_locks_unsafe_actions_false() -> None:
    result = create_controlled_pr(_request(), FakeGitHubClient())
    for flag in (
        "pr_merged",
        "auto_merge_enabled",
        "approval_submitted",
        "push_executed",
        "force_push_executed",
        "main_pushed",
        "command_executed",
        "git_mutated",
        "commit_executed",
        "files_staged",
        "code_edited",
        "patch_applied",
        "files_written",
        "branch_created",
        "checkout_performed",
        "rebase_performed",
        "merge_performed",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
        "main_modified",
    ):
        assert result.runtime_truth[flag] is False


def test_redaction_blocks_secret_like_metadata_and_response() -> None:
    fake = FakeGitHubClient(response={"number": 5, "url": "https://example.invalid/ghp_placeholder", "state": "open"})
    result = create_controlled_pr(_request(metadata={"header": "Authorization: Bearer placeholder"}), fake)
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    branch = create_controlled_pr(_request(head_branch="feature/SECRET-placeholder"), fake)
    assert branch.blocked is True
    assert "SECRET" not in json.dumps(branch.to_dict())

    repo = create_controlled_pr(_request(repository_full_name="owner/ghp_placeholder"), fake)
    assert repo.blocked is True
    assert "ghp_" not in json.dumps(repo.to_dict())

    clean = create_controlled_pr(_request(), fake)
    assert clean.redacted is True
    assert "ghp_" not in json.dumps(clean.to_dict())


def test_source_has_no_unsafe_implementation() -> None:
    source = Path("backend/python/brain/runtime/sandbox/pr_creator.py").read_text(encoding="utf-8")
    forbidden = [
        "subprocess",
        "shell=True",
        "os.system",
        "eval(",
        "exec(",
        " gh ",
        "git push",
        "git add",
        "git commit",
        "git merge",
        "git rebase",
        "git checkout",
        "git switch",
        "git branch",
        "auto_merge(",
        "approve(",
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
