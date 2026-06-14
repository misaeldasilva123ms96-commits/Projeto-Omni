from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    ControlledCommitGateRequest,
    evaluate_commit_gate,
)
from brain.runtime.sandbox import commit_gate  # noqa: E402


def _patch_apply(**overrides):
    payload = {
        "applied": True,
        "blocked": False,
        "success": True,
        "requires_followup_validation": True,
        "files_applied": ["tests/example_test.py"],
        "files_blocked": [],
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "runtime_truth": {
            "event_type": "sandbox.patch_applier.apply",
            "governance_decision": "patch_applied",
            "secrets_detected": False,
            "git_mutated": False,
            "main_modified": False,
            "command_executed": False,
            "pr_created": False,
            "pr_merged": False,
            "provider_called": False,
            "network_used": False,
            "mcp_used": False,
            "vault_written": False,
        },
    }
    payload.update(overrides)
    return payload


def _validation(**overrides):
    payload = {
        "validated": True,
        "blocked": False,
        "success": True,
        "failed": False,
        "timed_out": False,
        "ready_for_commit": True,
        "requires_human_intervention": False,
        "validation_summary": "Post-patch validation passed.",
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "required_followup_tests": ["python -m pytest tests/example_test.py"],
        "runtime_truth": {
            "event_type": "sandbox.post_patch_validation.loop",
            "governance_decision": "post_patch_validation_passed",
            "secrets_detected": False,
            "git_mutated": False,
            "main_modified": False,
            "pr_created": False,
            "pr_merged": False,
        },
    }
    payload.update(overrides)
    return payload


def _request(**overrides) -> ControlledCommitGateRequest:
    values = {
        "post_patch_validation_result": _validation(),
        "patch_apply_result": _patch_apply(),
        "patch_proposal_result": {"runtime_truth": {"event_type": "sandbox.patch_proposal.plan"}},
        "repair_plan": {"runtime_truth": {"event_type": "sandbox.repair_planner.plan"}},
        "requested_by": "codex",
        "commit_gate_mode": "evaluate_commit",
        "workspace_root": "C:/safe/workspace",
        "current_branch": "sandbox/controlled-commit-gate",
        "target_branch": "sandbox/controlled-commit-gate",
        "base_branch": "main",
        "related_phase": "phase-23",
        "related_pr": "future",
        "changed_files": [],
        "files_applied": [],
        "files_blocked": [],
        "validation_commands": ["python -m pytest tests/example_test.py"],
        "validation_summary": None,
        "commit_message_hint": None,
        "require_post_patch_validation": True,
        "require_patch_applied": True,
        "require_non_main_branch": True,
        "require_runtime_truth": True,
        "require_clean_validation": True,
        "allow_commit_execution": False,
        "allow_git_mutation": False,
        "allow_push": False,
        "allow_pr_creation": False,
        "allow_merge": False,
        "allow_protected_files": False,
        "allow_ci_change": False,
        "allow_governance_change": False,
        "allow_security_change": False,
        "allow_vault_write": False,
        "allow_network": False,
        "allow_provider_call": False,
        "allow_agent_call": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return ControlledCommitGateRequest(**values)


def _gate(**overrides):
    return evaluate_commit_gate(_request(**overrides))


def test_modes_block_dry_run_evaluate_and_unknown() -> None:
    disabled = _gate(commit_gate_mode="disabled")
    blocked = _gate(commit_gate_mode="blocked")
    dry_run = _gate(commit_gate_mode="dry_run")
    evaluated = _gate(commit_gate_mode="evaluate_commit")
    unknown = _gate(commit_gate_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert dry_run.dry_run is True
    assert dry_run.commit_eligible is False
    assert evaluated.commit_eligible is True
    assert evaluated.commit_ready_metadata_only is True


def test_phase_22_validation_integration() -> None:
    assert _gate().commit_eligible is True
    assert _gate(post_patch_validation_result=_validation(ready_for_commit=True)).commit_eligible is True
    assert _gate(post_patch_validation_result=_validation(success=False, failed=True)).commit_eligible is False
    assert _gate(post_patch_validation_result=_validation(timed_out=True, success=False)).commit_eligible is False
    assert _gate(post_patch_validation_result=_validation(blocked=True)).blocked is True
    assert _gate(post_patch_validation_result=_validation(requires_human_intervention=True)).requires_human_intervention is True
    assert _gate(post_patch_validation_result=_validation(runtime_truth={**_validation()["runtime_truth"], "secrets_detected": True})).secrets_detected is True
    assert _gate(post_patch_validation_result=_validation(runtime_truth={**_validation()["runtime_truth"], "git_mutated": True})).git_mutation_detected is True
    assert _gate(post_patch_validation_result=_validation(runtime_truth={**_validation()["runtime_truth"], "main_modified": True})).main_modification_detected is True
    assert _gate(post_patch_validation_result=_validation(runtime_truth={**_validation()["runtime_truth"], "pr_created": True})).blocked is True
    assert _gate().runtime_truth["child_runtime_truth_events"]


def test_phase_21_patch_apply_integration() -> None:
    assert _gate().commit_eligible is True
    assert _gate(patch_apply_result={}).blocked is True
    assert _gate(patch_apply_result=_patch_apply(applied=False)).blocked is True
    assert _gate(patch_apply_result=_patch_apply(success=False)).blocked is True
    assert _gate(patch_apply_result=_patch_apply(files_blocked=["tests/blocked.py"])).blocked is True
    assert _gate(patch_apply_result=_patch_apply(requires_followup_validation=True), post_patch_validation_result={}).blocked is True
    for flag in ("secrets_detected", "git_mutated", "main_modified", "command_executed", "provider_called", "network_used", "mcp_used", "vault_written"):
        result = _gate(patch_apply_result=_patch_apply(runtime_truth={**_patch_apply()["runtime_truth"], flag: True}))

        assert result.blocked is True or result.requires_human_intervention is True


def test_branch_safety() -> None:
    assert _gate(current_branch="main").blocked is True
    assert _gate(current_branch=None).blocked is True
    assert _gate(current_branch="main", base_branch="main").blocked is True
    assert _gate(target_branch="main").blocked is True
    assert _gate(base_branch="develop").blocked is True
    assert _gate(current_branch="release/1.0").blocked is True
    assert _gate(current_branch="feature/safe", target_branch="feature/safe").commit_eligible is True


def test_file_safety_allowed_and_blocked() -> None:
    allowed = [
        "tests/example_test.py",
        "backend/python/module.py",
        "backend/rust/src/lib.rs",
        "frontend/src/App.tsx",
        "docs/example.md",
        "sandbox/local/runbook.md",
        "vault/templates/example.md",
    ]
    for path in allowed:
        result = _gate(patch_apply_result=_patch_apply(files_applied=[path]))

        assert result.files_eligible_for_commit == [path]
        assert result.blocked is False

    blocked = [
        ".env",
        "vault/08_ADR/example.md",
        "docs/governance/policy.md",
        "docs/security/threat-model.md",
        ".github/workflows/ci.yml",
        ".circleci/config.yml",
        "../escape.py",
        "C:/outside.py",
        ".git/config",
    ]
    for path in blocked:
        result = _gate(patch_apply_result=_patch_apply(files_applied=[path]))

        assert result.commit_eligible is False
        assert result.files_blocked_from_commit
        assert result.requires_human_intervention is True


def test_commit_plan_and_message_metadata() -> None:
    result = _gate()

    assert json.dumps(result.commit_plan)
    assert result.proposed_commit_message.startswith("test(runtime):")
    assert len(result.proposed_commit_message) <= 120
    assert result.commit_plan["allowed_in_future_commit_execution"] is True
    assert result.required_pre_commit_checks

    docs = _gate(patch_apply_result=_patch_apply(files_applied=["docs/example.md"]))
    backend = _gate(patch_apply_result=_patch_apply(files_applied=["backend/python/module.py"]))

    assert docs.commit_plan["commit_type"] == "docs"
    assert backend.commit_plan["commit_type"] == "fix"


def test_flags_are_locked_down() -> None:
    result = _gate()

    assert result.can_execute_commit is False
    assert result.can_stage_files is False
    assert result.can_push is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.can_mutate_git is False
    assert result.can_edit_code is False
    assert result.can_apply_patch is False
    truth = result.runtime_truth
    for key in (
        "commit_executed",
        "files_staged",
        "command_executed",
        "code_edited",
        "patch_applied",
        "files_written",
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

    for flag in (
        "allow_commit_execution",
        "allow_git_mutation",
        "allow_push",
        "allow_pr_creation",
        "allow_merge",
        "allow_ci_change",
        "allow_governance_change",
        "allow_security_change",
        "allow_vault_write",
        "allow_network",
        "allow_provider_call",
        "allow_agent_call",
    ):
        assert _gate(**{flag: True}).blocked is True


def test_redaction_blocks_secret_like_inputs() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"

    metadata = _gate(metadata={"value": f"{marker}=placeholder"})
    hint = _gate(commit_message_hint=f"{bearer} placeholder")
    file_path = _gate(patch_apply_result=_patch_apply(files_applied=[".env"]))
    branch = _gate(current_branch="feature/SECRET-placeholder")
    encoded = json.dumps(metadata.to_dict()) + json.dumps(hint.to_dict()) + json.dumps(file_path.to_dict()) + json.dumps(branch.to_dict())

    assert metadata.blocked is True
    assert hint.blocked is True
    assert file_path.blocked is True
    assert branch.blocked is True
    assert marker not in encoded
    assert bearer not in encoded


def test_runtime_truth_governance_decisions() -> None:
    eligible = _gate()
    failed = _gate(post_patch_validation_result=_validation(success=False, failed=True))
    missing = _gate(post_patch_validation_result={})

    assert eligible.runtime_truth["event_type"] == "sandbox.commit_gate.decision"
    assert eligible.runtime_truth["governance_decision"] == "commit_eligible"
    assert failed.runtime_truth["governance_decision"] in {"blocked", "commit_not_eligible_validation_failed"}
    assert missing.runtime_truth["governance_decision"] == "blocked"


def test_source_has_no_unsafe_implementation() -> None:
    source = inspect.getsource(commit_gate)
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
