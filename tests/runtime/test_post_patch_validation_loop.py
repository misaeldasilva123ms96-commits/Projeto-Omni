from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    PostPatchValidationRequest,
    validate_post_patch,
)
from brain.runtime.sandbox import post_patch_validator  # noqa: E402


def _patch_result(**overrides):
    payload = {
        "applied": True,
        "blocked": False,
        "success": True,
        "requires_followup_validation": True,
        "workspace_root": "C:/safe/workspace",
        "current_branch": "sandbox/post-patch-validation-loop",
        "target_branch": "sandbox/post-patch-validation-loop",
        "base_branch": "main",
        "files_applied": ["tests/example_test.py"],
        "hunks_applied": 1,
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "required_followup_tests": ["python -m pytest tests/example_test.py"],
        "runtime_truth": {
            "event_type": "sandbox.patch_applier.apply",
            "governance_decision": "patch_applied",
            "files_applied_count": 1,
            "hunks_applied_count": 1,
            "secrets_detected": False,
            "git_mutated": False,
            "main_modified": False,
            "command_executed": False,
        },
    }
    payload.update(overrides)
    return payload


def _loop_result(**overrides):
    payload = {
        "executed": True,
        "blocked": False,
        "dry_run": False,
        "success": True,
        "failed": False,
        "timed_out": False,
        "partial": False,
        "commands_executed": 1,
        "commands_blocked": 0,
        "failure_summary": None,
        "failure_classification": None,
        "runtime_truth": {
            "event_type": "sandbox.test_runner.loop",
            "governance_decision": "validation_passed",
            "secrets_detected": False,
            "command_executed": True,
        },
        "redacted": False,
    }
    payload.update(overrides)
    return payload


def _request(**overrides) -> PostPatchValidationRequest:
    values = {
        "patch_apply_result": _patch_result(),
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "requested_by": "codex",
        "validator_mode": "validate_patch",
        "loop_mode": "sandbox_readonly",
        "runner_mode": "sandbox_readonly",
        "command_mode": "sandbox_allowed",
        "workspace_root": "C:/safe/workspace",
        "current_branch": "sandbox/post-patch-validation-loop",
        "target_branch": "sandbox/post-patch-validation-loop",
        "base_branch": "main",
        "related_phase": "phase-22",
        "related_pr": "future",
        "stop_on_first_failure": True,
        "max_commands": 10,
        "timeout_seconds_per_command": 60,
        "total_timeout_seconds": 600,
        "max_stdout_bytes_per_command": 20000,
        "max_stderr_bytes_per_command": 20000,
        "require_patch_applied": True,
        "require_non_main_branch": True,
        "require_runtime_truth": True,
        "allow_commit_recommendation": True,
        "allow_git_mutation": False,
        "allow_code_edit": False,
        "allow_patch_apply": False,
        "allow_network": False,
        "allow_provider_call": False,
        "allow_agent_call": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return PostPatchValidationRequest(**values)


def _run(**overrides):
    calls = []

    def fake_loop(request):
        calls.append(request)
        return _loop_result()

    result = validate_post_patch(_request(**overrides), loop_runner=fake_loop)
    return result, calls


def test_modes_block_dry_run_validate_and_unknown() -> None:
    disabled, disabled_calls = _run(validator_mode="disabled")
    blocked, blocked_calls = _run(validator_mode="blocked")
    dry_run, dry_calls = _run(validator_mode="dry_run")
    validated, validation_calls = _run(validator_mode="validate_patch")
    unknown, unknown_calls = _run(validator_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert dry_run.dry_run is True
    assert dry_calls == []
    assert validated.validated is True
    assert len(validation_calls) == 1
    assert disabled_calls == []
    assert blocked_calls == []
    assert unknown_calls == []


def test_patch_apply_integration_blocks_bad_evidence() -> None:
    assert _run(patch_apply_result=_patch_result(blocked=True))[0].blocked is True
    assert _run(patch_apply_result=_patch_result(applied=False))[0].validation_classification == "invalid_patch_apply_evidence"
    assert _run(patch_apply_result=_patch_result(runtime_truth={**_patch_result()["runtime_truth"], "secrets_detected": True}))[0].validation_classification == "secret_detected"
    assert _run(patch_apply_result=_patch_result(runtime_truth={**_patch_result()["runtime_truth"], "git_mutated": True}))[0].validation_classification == "git_mutation_detected"
    assert _run(patch_apply_result=_patch_result(runtime_truth={**_patch_result()["runtime_truth"], "main_modified": True}))[0].validation_classification == "main_modification_detected"
    protected = _run(patch_apply_result=_patch_result(files_applied=["docs/security/threat-model.md"]))[0]
    assert protected.validation_classification == "protected_file_modified"
    assert protected.requires_human_intervention is True


def test_phase_18_loop_integration_success_failure_timeout_blocked() -> None:
    calls = []

    def success_loop(request):
        calls.append(request)
        return _loop_result()

    success = validate_post_patch(_request(), loop_runner=success_loop)
    assert success.validated is True
    assert success.ready_for_commit is True
    assert success.recommended_next_action == "ready_for_commit_phase"
    assert calls[0].commands == ["python -m pytest tests/example_test.py"]

    def failed_loop(_request_obj):
        return _loop_result(success=False, failed=True, failure_summary="pytest failed", failure_classification="tests_failed")

    failed = validate_post_patch(_request(), loop_runner=failed_loop)
    assert failed.failed is True
    assert failed.validation_classification == "tests_failed"
    assert failed.requires_repair_cycle is True
    assert failed.recommended_next_action == "start_repair_cycle"

    def timeout_loop(_request_obj):
        return _loop_result(success=False, failed=True, timed_out=True, failure_classification="command_timed_out")

    timed_out = validate_post_patch(_request(), loop_runner=timeout_loop)
    assert timed_out.timed_out is True
    assert timed_out.validation_classification == "command_timed_out"

    def blocked_loop(_request_obj):
        return _loop_result(success=False, failed=True, blocked=True, commands_blocked=1, failure_classification="command_blocked")

    blocked = validate_post_patch(_request(), loop_runner=blocked_loop)
    assert blocked.validation_classification == "command_blocked"
    assert blocked.commands_blocked == 1


def test_allowed_validation_commands_are_accepted() -> None:
    commands = [
        "python --version",
        "python -m pytest tests/example_test.py",
        "pytest tests/example_test.py",
        "npm run build",
        "npm run lint",
        "npm run typecheck",
        "cargo test",
        "cargo fmt --check",
        "git diff --check",
        "python -m json.tool sandbox/local/allowlist.commands.json",
        "python -m compileall backend/python",
    ]

    for command in commands:
        result, calls = _run(validation_commands=[command])

        assert result.blocked is False
        assert calls[0].commands == [command]


def test_blocked_validation_commands_never_call_loop() -> None:
    commands = [
        "git add .",
        "git commit -m nope",
        "git push origin main",
        "git checkout -b feature/nope",
        "git merge main",
        "git rebase main",
        "gh pr merge 1",
        "curl https://example.invalid",
        "wget https://example.invalid",
        "ssh example.invalid",
        "rm -rf build",
        "cat .env",
        "printenv",
        "env",
    ]

    for command in commands:
        result, calls = _run(validation_commands=[command])

        assert result.blocked is True
        assert result.validation_classification in {"command_blocked", "secret_detected"}
        assert calls == []


def test_branch_and_workspace_safety() -> None:
    assert _run(current_branch="main")[0].blocked is True
    assert _run(current_branch=None)[0].blocked is True
    assert _run(current_branch="main", base_branch="main")[0].blocked is True
    assert _run(target_branch="main")[0].blocked is True
    assert _run(base_branch="develop")[0].blocked is True
    assert _run(workspace_root="../escape")[0].blocked is True
    assert _run(metadata={"direct_main_edit": True})[0].validation_classification == "main_modification_detected"
    assert _run(current_branch="feature/safe", target_branch="feature/safe")[0].validated is True


def test_validation_classifications_and_next_actions() -> None:
    cases = {
        "tests_failed": "start_repair_cycle",
        "build_failed": "start_repair_cycle",
        "lint_failed": "start_repair_cycle",
        "typecheck_failed": "start_repair_cycle",
        "format_failed": "start_repair_cycle",
    }

    for classification, action in cases.items():
        def loop(_request_obj, classification=classification):
            return _loop_result(success=False, failed=True, failure_classification=classification)

        result = validate_post_patch(_request(), loop_runner=loop)

        assert result.validation_classification == classification
        assert result.recommended_next_action == action


def test_commit_readiness_is_metadata_only() -> None:
    result, _calls = _run()

    assert result.ready_for_commit is True
    assert result.ready_for_pr is False
    assert result.can_commit is False
    assert result.can_push is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_mutate_git is False


def test_runtime_truth_links_patch_and_loop_evidence() -> None:
    result, _calls = _run()

    truth = result.runtime_truth
    assert truth["event_type"] == "sandbox.post_patch_validation.loop"
    assert truth["patch_apply_event_type"] == "sandbox.patch_applier.apply"
    assert truth["patch_apply_governance_decision"] == "patch_applied"
    assert len(truth["child_runtime_truth_events"]) == 2
    assert truth["code_edited"] is False
    assert truth["patch_applied"] is False
    assert truth["files_written"] is False
    assert truth["command_executed"] is True
    for key in (
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
        assert truth[key] is False


def test_redaction_blocks_secret_like_inputs_without_loop_call() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"

    command, command_calls = _run(validation_commands=[f"python -m pytest {marker}"])
    metadata, metadata_calls = _run(metadata={"header": f"{bearer} placeholder"})
    evidence, evidence_calls = _run(patch_apply_result=_patch_result(files_applied=[".env"]))
    loop_secret = validate_post_patch(
        _request(),
        loop_runner=lambda _request_obj: _loop_result(
            success=False,
            failed=True,
            redacted=True,
            failure_summary=f"{marker}=placeholder",
            failure_classification="secret_detected",
            runtime_truth={"event_type": "sandbox.test_runner.loop", "secrets_detected": True},
        ),
    )
    encoded = json.dumps(command.to_dict()) + json.dumps(metadata.to_dict()) + json.dumps(evidence.to_dict()) + json.dumps(loop_secret.to_dict())

    assert command.blocked is True
    assert metadata.blocked is True
    assert evidence.blocked is True
    assert loop_secret.validation_classification == "secret_detected"
    assert command_calls == []
    assert metadata_calls == []
    assert evidence_calls == []
    assert marker not in encoded
    assert bearer not in encoded


def test_capability_enablement_is_blocked() -> None:
    for flag in (
        "allow_git_mutation",
        "allow_code_edit",
        "allow_patch_apply",
        "allow_network",
        "allow_provider_call",
        "allow_agent_call",
    ):
        result, calls = _run(**{flag: True})

        assert result.blocked is True
        assert calls == []


def test_source_has_no_unsafe_implementation() -> None:
    source = inspect.getsource(post_patch_validator)
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
        "open" + "(",
        "write" + "(",
        "unlink" + "(",
        "rename" + "(",
        "remove" + "(",
        "rmtree" + "(",
        "shutil" + ".move",
    )

    for pattern in forbidden:
        assert pattern not in source
