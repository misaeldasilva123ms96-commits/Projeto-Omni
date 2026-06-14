from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    ScopedPatchProposalRequest,
    propose_scoped_patch,
)
from brain.runtime.sandbox import patch_proposal  # noqa: E402


def _repair_plan(**overrides):
    payload = {
        "planned": True,
        "blocked": False,
        "repair_requires_human": False,
        "repair_category": "test_repair",
        "normalized_failure_classification": "tests_failed",
        "target_branch": "sandbox/scoped-patch-proposal-engine",
        "allowed_files": ["tests/runtime/test_example.py"],
        "suspected_files": ["tests/runtime/test_example.py"],
        "proposed_steps": [{"step_id": "repair-step-1", "title": "Add focused test"}],
        "validation_commands": ["python -m pytest tests/runtime/test_example.py"],
        "runtime_truth": {"event_type": "sandbox.repair_planner.plan"},
    }
    payload.update(overrides)
    return payload


def _request(**overrides) -> ScopedPatchProposalRequest:
    values = {
        "repair_plan": _repair_plan(),
        "requested_by": "codex",
        "proposal_mode": "proposal_only",
        "related_phase": "phase-20",
        "related_pr": "future",
        "target_branch": "sandbox/scoped-patch-proposal-engine",
        "base_branch": "main",
        "allowed_files": ["tests/runtime/test_example.py"],
        "blocked_files": [],
        "suspected_files": ["tests/runtime/test_example.py"],
        "proposed_steps": [{"step_id": "repair-step-1", "title": "Add focused test"}],
        "validation_commands": ["python -m pytest tests/runtime/test_example.py"],
        "file_contexts": {},
        "max_files_to_patch": 5,
        "max_patch_hunks_per_file": 8,
        "max_total_patch_hunks": 20,
        "allow_code_edit": False,
        "allow_patch_apply": False,
        "allow_file_write": False,
        "allow_git_mutation": False,
        "allow_command_execution": False,
        "allow_provider_call": False,
        "allow_agent_call": False,
        "allow_network": False,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return ScopedPatchProposalRequest(**values)


def _proposal(**overrides):
    return propose_scoped_patch(_request(**overrides))


def test_modes_block_dry_run_and_proposal_only() -> None:
    disabled = _proposal(proposal_mode="disabled")
    blocked = _proposal(proposal_mode="blocked")
    dry_run = _proposal(proposal_mode="dry_run")
    proposal_only = _proposal(proposal_mode="proposal_only")
    unknown = _proposal(proposal_mode="unknown")

    assert disabled.blocked is True
    assert blocked.blocked is True
    assert unknown.blocked is True
    assert dry_run.dry_run is True
    assert dry_run.can_apply_patch is False
    assert proposal_only.proposed is True
    assert proposal_only.patch_proposals


def test_repair_plan_integration_for_common_categories() -> None:
    cases = {
        "test_repair": "medium",
        "build_repair": "high",
        "lint_repair": "medium",
        "type_repair": "medium",
        "formatting_repair": "low",
    }

    for category, complexity in cases.items():
        result = _proposal(
            repair_plan=_repair_plan(repair_category=category),
            repair_category=category,
        )

        assert result.proposed is True
        assert result.repair_category == category
        assert result.patch_complexity == complexity
        assert result.patch_proposals
        assert json.dumps(result.to_dict())


def test_no_repair_needed_and_blocked_repair_plan() -> None:
    no_repair = _proposal(
        repair_plan=_repair_plan(
            repair_category="no_repair_needed",
            reason="Validation passed; no repair plan is needed.",
        ),
        repair_category=None,
    )
    blocked = _proposal(repair_plan=_repair_plan(blocked=True))
    human = _proposal(repair_plan=_repair_plan(repair_requires_human=True))

    assert no_repair.success is True
    assert no_repair.proposed is False
    assert no_repair.patch_proposals[0]["operation"] == "no_change_needed"
    assert blocked.blocked is True
    assert human.patch_requires_human is True


def test_patch_proposal_structure_and_limits() -> None:
    files = [
        "tests/a_test.py",
        "backend/python/module.py",
        "frontend/src/App.tsx",
    ]
    result = _proposal(
        allowed_files=files,
        suspected_files=files,
        repair_plan=_repair_plan(allowed_files=files, suspected_files=files),
        max_files_to_patch=2,
        max_patch_hunks_per_file=1,
        max_total_patch_hunks=2,
    )

    assert len(result.files_considered) == 2
    assert len(result.patch_proposals) == 2
    assert sum(len(item["hunks"]) for item in result.patch_proposals) == 2
    for item in result.patch_proposals:
        assert {"proposal_id", "file_path", "operation", "summary", "rationale", "hunks"} <= item.keys()
        assert item["hunks"]
        assert item["operation"] in {"modify_existing", "add_test", "add_documentation"}


def test_file_contexts_create_bounded_snippet_metadata_only() -> None:
    result = _proposal(
        file_contexts={"tests/runtime/test_example.py": "def test_example():\n    assert False\n"},
    )

    hunk = result.patch_proposals[0]["hunks"][0]
    assert hunk["hunk_type"] == "bounded_snippet_metadata"
    assert "proposed_snippet" in hunk
    assert result.can_apply_patch is False


def test_file_scope_allowed_high_risk_and_blocked_paths() -> None:
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
        result = _proposal(
            allowed_files=[path],
            suspected_files=[path],
            repair_plan=_repair_plan(allowed_files=[path], suspected_files=[path]),
        )

        assert result.files_proposed == [path]
        assert result.blocked is False

    risky_paths = [
        "vault/08_ADR/example.md",
        "docs/governance/policy.md",
        "docs/security/threat-model.md",
        ".github/workflows/ci.yml",
        ".circleci/config.yml",
    ]
    for path in risky_paths:
        result = _proposal(
            allowed_files=[path],
            suspected_files=[path],
            repair_plan=_repair_plan(allowed_files=[path], suspected_files=[path]),
        )

        assert result.patch_requires_human is True
        assert path in result.files_blocked

    blocked_paths = [".env", "../escape.py", "/tmp/outside.py", ".git/config"]
    for path in blocked_paths:
        result = _proposal(
            allowed_files=[path],
            suspected_files=[path],
            repair_plan=_repair_plan(allowed_files=[path], suspected_files=[path]),
        )

        assert result.blocked or result.patch_requires_human
        assert result.files_blocked


def test_operations_that_require_human_or_blocking() -> None:
    blocked_operations = [
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
    ]

    for operation in blocked_operations:
        result = _proposal(
            proposed_steps=[{"operation": operation}],
            repair_plan=_repair_plan(proposed_steps=[{"operation": operation}]),
        )

        assert result.patch_requires_human is True


def test_validation_commands_are_safe_metadata_only() -> None:
    result = _proposal(
        validation_commands=[
            "python -m pytest tests/runtime/test_example.py",
            "git add .",
            "git commit -m nope",
            "git push origin main",
            "git merge main",
            "git rebase main",
            "gh pr merge 1",
            "curl https://example.invalid",
        ]
    )
    joined = " ".join(result.validation_commands)

    assert result.validation_commands == ["python -m pytest tests/runtime/test_example.py"]
    assert "git add" not in joined
    assert "git commit" not in joined
    assert "git push" not in joined
    assert "git merge" not in joined
    assert "git rebase" not in joined
    assert "gh " not in joined
    assert "curl" not in joined


def test_flags_and_runtime_truth_are_locked_down() -> None:
    result = _proposal()

    assert result.can_apply_patch is False
    assert result.patch_requires_new_phase is True
    assert result.can_edit_code is False
    assert result.can_write_files is False
    assert result.can_mutate_git is False
    assert result.can_execute_commands is False
    assert result.can_call_provider is False
    assert result.can_call_agent is False
    assert result.can_use_network is False
    assert result.can_open_pr is False
    assert result.can_merge is False
    assert result.runtime_truth["event_type"] == "sandbox.patch_proposal.plan"
    for key in (
        "code_edited",
        "patch_applied",
        "files_written",
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


def test_capability_enablement_is_blocked() -> None:
    for flag in (
        "allow_code_edit",
        "allow_patch_apply",
        "allow_file_write",
        "allow_git_mutation",
        "allow_command_execution",
        "allow_provider_call",
        "allow_agent_call",
        "allow_network",
    ):
        result = _proposal(**{flag: True})

        assert result.blocked is True
        assert result.proposed is False


def test_redaction_blocks_secret_like_inputs() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    bearer = "Authorization: " + "Bearer"
    context = _proposal(file_contexts={"backend/python/module.py": f"{marker}=placeholder"})
    metadata = _proposal(metadata={"header": f"{bearer} placeholder"})
    suspected = _proposal(
        allowed_files=[".env"],
        suspected_files=[".env"],
        repair_plan=_repair_plan(allowed_files=[".env"], suspected_files=[".env"]),
    )
    encoded = json.dumps(context.to_dict()) + json.dumps(metadata.to_dict()) + json.dumps(suspected.to_dict())

    assert context.blocked is True
    assert metadata.blocked is True
    assert suspected.blocked is True
    assert marker not in encoded
    assert bearer not in encoded


def test_source_has_no_unsafe_implementation() -> None:
    source = inspect.getsource(patch_proposal)
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
