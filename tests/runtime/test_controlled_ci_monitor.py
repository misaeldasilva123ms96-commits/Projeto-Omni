"""Tests for the controlled CI monitor."""

from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.sandbox.ci_monitor import monitor_ci_status

SAFE_SHA = "abc123def4567890abc123def4567890abc123de"


class FakeGitHubActionsClient:
    def __init__(self, checks: list[dict[str, object]] | None = None, fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self.checks = checks or [{"name": "build-and-test-js-python", "status": "success", "required": True}]
        self.fail = fail
        self.logs_called = False
        self.retry_called = False
        self.trigger_called = False

    def get_actions_status_snapshot(self, *, repository_full_name: str, pr_number: int, head_sha: str) -> dict[str, object]:
        self.calls.append({"repository_full_name": repository_full_name, "pr_number": pr_number, "head_sha": head_sha})
        if self.fail:
            raise RuntimeError("temporary read failure")
        return {"checks": self.checks, "workflows": [{"name": "CI", "status": "success"}]}



def _gate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ci_monitor_eligible": True,
        "ci_monitor_ready_metadata_only": True,
        "success": True,
        "blocked": False,
        "requires_human_intervention": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 359,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/359",
        "pr_state": "open",
        "pr_draft": True,
        "source_branch": "sandbox/controlled-ci-monitor",
        "head_branch": "sandbox/controlled-ci-monitor",
        "base_branch": "main",
        "head_sha": SAFE_SHA,
        "commit_sha": SAFE_SHA,
        "runtime_truth": {
            "event_type": "sandbox.ci_monitor_gate.decision",
            "secrets_detected": False,
            "ci_monitored": False,
            "ci_status_fetched": False,
            "workflow_runs_fetched": False,
            "check_runs_fetched": False,
            "logs_downloaded": False,
            "workflow_retried": False,
            "repair_loop_started": False,
            "pr_updated": False,
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


def _creator(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pr_created": True,
        "success": True,
        "blocked": False,
        "repository_full_name": "misaeldasilva123ms96-commits/Projeto-Omni",
        "pr_number": 359,
        "pr_url": "https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/359",
        "pr_state": "open",
        "source_branch": "sandbox/controlled-ci-monitor",
        "head_branch": "sandbox/controlled-ci-monitor",
        "base_branch": "main",
        "commit_sha": SAFE_SHA,
        "runtime_truth": {
            "event_type": "sandbox.pr_creator.create",
            "secrets_detected": False,
            "pr_merged": False,
            "auto_merge_enabled": False,
            "approval_submitted": False,
            "push_executed": False,
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


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ci_monitor_gate_result": _gate(),
        "pr_creator_result": _creator(),
        "monitor_mode": "monitor_ci",
        "expected_required_checks": ["build-and-test-js-python"],
    }
    payload.update(overrides)
    return payload


def _monitor(request: dict[str, object] | None = None, github: FakeGitHubActionsClient | None = None):
    return monitor_ci_status(
        request or _request(),
        github_actions_client=github or FakeGitHubActionsClient(),
    )


def test_modes_block_or_dry_run_without_client_calls() -> None:
    github = FakeGitHubActionsClient()
    assert _monitor(_request(monitor_mode="disabled"), github).blocked is True
    assert _monitor(_request(monitor_mode="blocked"), github).blocked is True
    assert _monitor(_request(monitor_mode="unknown"), github).blocked is True
    dry = _monitor(_request(monitor_mode="dry_run"), github)
    assert dry.dry_run is True
    assert dry.monitored is False
    assert github.calls == []


def test_monitor_ci_reads_fake_clients_and_marks_passed() -> None:
    result = _monitor()
    assert result.monitored is True
    assert result.success is True
    assert result.passed is True
    assert result.failed is False
    assert result.pending is False
    assert result.aggregate_status == "success"
    assert result.aggregate_conclusion == "passed"
    assert result.requires_merge_gate_phase is True
    assert result.requires_repair_loop_gate_phase is False
    assert result.runtime_truth["event_type"] == "sandbox.ci_monitor.monitor"
    assert result.runtime_truth["network_used"] is True
    assert result.runtime_truth["ci_status_fetched"] is True
    assert result.runtime_truth["workflow_runs_fetched"] is True
    assert result.runtime_truth["check_runs_fetched"] is True
    assert result.runtime_truth["github_actions_read"] is True


def test_phase29_and_phase28_evidence_blocks_unsafe_inputs() -> None:
    assert _monitor(_request(ci_monitor_gate_result=None)).blocked is True
    assert _monitor(_request(ci_monitor_gate_result=_gate(ci_monitor_eligible=False))).blocked is True
    assert _monitor(_request(ci_monitor_gate_result=_gate(blocked=True))).blocked is True
    assert _monitor(_request(ci_monitor_gate_result=_gate(requires_human_intervention=True))).blocked is True
    assert _monitor(_request(pr_creator_result=_creator(pr_created=False))).blocked is True
    assert _monitor(_request(pr_creator_result=_creator(success=False))).blocked is True

    for flag in ("secrets_detected", "ci_monitored", "ci_status_fetched", "logs_downloaded", "workflow_retried", "repair_loop_started", "pr_updated", "pr_merged", "auto_merge_enabled", "push_executed", "main_modified"):
        gate = _gate()
        truth = dict(gate["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        gate["runtime_truth"] = truth
        assert _monitor(_request(ci_monitor_gate_result=gate)).blocked is True

    for flag in ("secrets_detected", "pr_merged", "auto_merge_enabled", "approval_submitted", "push_executed", "merge_performed", "rebase_performed", "checkout_performed", "branch_created"):
        creator = _creator()
        truth = dict(creator["runtime_truth"])  # type: ignore[index]
        truth[flag] = True
        creator["runtime_truth"] = truth
        assert _monitor(_request(pr_creator_result=creator)).blocked is True


def test_pr_repository_branch_and_sha_safety() -> None:
    assert _monitor(_request(pr_state="open")).blocked is False
    assert _monitor(_request(pr_draft=True)).blocked is False
    assert _monitor(_request(pr_state="unknown")).blocked is True
    assert _monitor(_request(pr_state="closed")).blocked is True
    assert _monitor(_request(pr_state="merged")).blocked is True
    assert _monitor(_request(head_branch="main")).blocked is True
    assert _monitor(_request(source_branch="main")).blocked is True
    assert _monitor(_request(base_branch="develop")).blocked is True
    assert _monitor(_request(head_branch="release/1.0", source_branch="release/1.0")).blocked is True
    assert _monitor(_request(repository_full_name="misaeldasilva123ms96-commits/Projeto-Omni")).blocked is False
    assert _monitor(_request(repository_full_name="owner/repo;bad")).blocked is True
    assert _monitor(_request(repository_full_name="owner/ghp_placeholder")).redacted is True
    assert _monitor(_request(head_sha="abc123d")).blocked is False
    assert _monitor(_request(head_sha=None, commit_sha=SAFE_SHA, ci_monitor_gate_result=_gate(head_sha=None))).blocked is False
    assert _monitor(
        _request(
            head_sha=None,
            commit_sha=None,
            ci_monitor_gate_result=_gate(head_sha=None, commit_sha=None),
            pr_creator_result=_creator(commit_sha=None),
        )
    ).blocked is True
    assert _monitor(_request(head_sha="OPENAI_API_KEY")).redacted is True


def test_ci_client_errors_are_partial_and_do_not_download_or_retry() -> None:
    github = FakeGitHubActionsClient(fail=True)
    result = _monitor(github=github)
    assert result.partial is True
    assert result.success is False
    assert result.monitored is False
    assert github.logs_called is False
    assert github.retry_called is False
    assert github.trigger_called is False


def test_status_normalization_for_failed_pending_and_neutral() -> None:
    failed = _monitor(github=FakeGitHubActionsClient([{"name": "build-and-test-js-python", "status": "failure", "required": True}]))
    assert failed.failed is True
    assert failed.requires_repair_loop_gate_phase is True
    assert failed.aggregate_conclusion == "failed"

    pending = _monitor(github=FakeGitHubActionsClient([{"name": "build-and-test-js-python", "status": "in_progress", "required": True}]))
    assert pending.pending is True
    assert pending.terminal is False

    neutral = _monitor(
        github=FakeGitHubActionsClient([
            {"name": "build-and-test-js-python", "status": "success", "required": True},
            {"name": "CodeQL", "status": "neutral", "required": False},
        ]),
    )
    assert neutral.passed is True
    assert neutral.failed is False
    assert neutral.skipped_or_neutral_checks

    missing = _monitor(_request(expected_required_checks=["missing-required-check"]))
    assert missing.failed is True
    assert missing.missing_required_checks == ["missing-required-check"]


def test_redaction_blocks_secret_like_content_without_exposing_markers() -> None:
    result = _monitor(_request(metadata={"header": "Authorization: Bearer placeholder"}))
    assert result.blocked is True
    assert result.redacted is True
    assert "Authorization: Bearer" not in json.dumps(result.to_dict())

    check = _monitor(github=FakeGitHubActionsClient([{"name": "SECRET placeholder", "status": "success", "required": True}]))
    assert check.blocked is True
    assert "SECRET" not in json.dumps(check.to_dict())

    url = _monitor(github=FakeGitHubActionsClient([{"name": "build-and-test-js-python", "status": "success", "url": "https://example.invalid/ghp_placeholder"}]))
    assert url.blocked is True
    assert "ghp_" not in json.dumps(url.to_dict())


def test_flags_remain_false_and_result_is_serializable() -> None:
    result = _monitor()
    json.dumps(result.to_dict())
    for flag in (
        "logs_downloaded",
        "workflow_retried",
        "repair_loop_started",
        "can_download_logs",
        "can_retry_workflows",
        "can_start_repair_loop",
        "can_update_pr",
        "can_merge",
        "can_auto_merge",
        "can_push",
        "can_edit_code",
        "can_apply_patch",
    ):
        assert getattr(result, flag) is False
    for flag in (
        "logs_downloaded",
        "workflow_retried",
        "workflow_triggered",
        "repair_loop_started",
        "pr_updated",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "command_executed",
        "git_mutated",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
        "main_modified",
    ):
        assert result.runtime_truth[flag] is False


def test_source_has_no_unsafe_implementation() -> None:
    source = Path("backend/python/brain/runtime/sandbox/ci_monitor.py").read_text(encoding="utf-8")
    forbidden = [
        "subprocess",
        "shell=True",
        "os.system",
        "eval(",
        "exec(",
        " gh ",
        "requests.",
        "urllib",
        "socket",
        "http.client",
        "download_logs(",
        "retry_workflow(",
        "trigger_workflow(",
        "repair_loop(",
        "create_pull_request",
        "update_pull_request",
        "merge_pull_request",
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
