"""Scoped CI patch proposal engine for governed sandbox CI repair.

Phase 34 converts clean Phase 33 gate eligibility and Phase 32 repair plan
metadata into bounded scoped CI patch proposal metadata. It does not apply
patches, write files, edit code, inspect source files, execute commands,
call providers/agents/MCP, download logs, retry workflows, mutate Git,
commit, push, update PRs, or merge.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Mapping

from .scoped_ci_patch_proposal_engine_truth import (
    SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVIDENCE_VERSION,
    build_scoped_ci_patch_proposal_engine_evidence,
)
from .scoped_ci_patch_proposal_engine_types import (
    ScopedCIPatchProposalEngineRequest,
    ScopedCIPatchProposalEngineResult,
)

SCOPED_CI_PATCH_PROPOSAL_ENGINE_MODES = frozenset(
    {"disabled", "dry_run", "propose_patch", "blocked"}
)
DEFAULT_PROPOSAL_MODE = "disabled"
MAIN_BRANCH = "main"
EXPECTED_REPOSITORY = "misaeldasilva123ms96-commits/Projeto-Omni"

_CREDENTIAL_PATTERNS = (
    re.compile(r"Authentication:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API_KEY", re.IGNORECASE),
    re.compile("SECRET", re.IGNORECASE),
    re.compile("TOKEN", re.IGNORECASE),
    re.compile("PASSWORD", re.IGNORECASE),
    re.compile("SUPABASE", re.IGNORECASE),
    re.compile("OPENAI", re.IGNORECASE),
    re.compile("JWT", re.IGNORECASE),
    re.compile("PRIVATE_KEY", re.IGNORECASE),
    re.compile("AUTHORIZATION", re.IGNORECASE),
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"token@", re.IGNORECASE),
    re.compile(r"oauth", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9_]+", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]+", re.IGNORECASE),
)
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_SHA_PATTERN = re.compile(r"^[A-Fa-f0-9]{7,64}$")
_SHELL_CHARS = re.compile(r"[;&|`$<>]")
_PROTECTED_PREFIXES = ("release/", "prod/", "production/", "protected/")

_ALLOWED_TARGET_AREAS = frozenset({
    "tests", "backend/python", "backend/rust", "frontend/src", "docs", "sandbox/local",
})
_ALLOWED_FILE_ROOTS = frozenset({
    "backend/python", "backend/rust/src", "frontend/src", "tests", "docs", "sandbox/local",
})
_BLOCKED_FILE_ROOTS = frozenset({
    ".git", ".github/workflows", ".circleci", "docs/security", "docs/governance",
    "vault/08_ADR", ".env", "secrets", "deploy", "deployment", "production", "prod",
    "billing", "credentials", "keys", "tokens", "auth secrets",
})
_ALLOWED_OPERATIONS = frozenset({
    "modify_existing", "add_test", "add_documentation",
})
_BLOCKED_OPERATIONS = frozenset({
    "delete_file", "rename_file", "move_file", "chmod_change",
    "dependency_upgrade", "ci_threshold_change", "security_policy_change",
    "governance_policy_change", "production_deploy_change",
    "billing_change", "secret_change",
})
_ALLOWED_VALIDATION_COMMANDS = (
    re.compile(r"^python\s+-m\s+pytest\b"),
    re.compile(r"^pytest\b"),
    re.compile(r"^npm\s+test\b"),
    re.compile(r"^npm\s+run\s+test\b"),
    re.compile(r"^npm\s+run\s+build\b"),
    re.compile(r"^npm\s+run\s+lint\b"),
    re.compile(r"^npm\s+run\s+typecheck\b"),
    re.compile(r"^cargo\s+test\b"),
    re.compile(r"^cargo\s+check\b"),
    re.compile(r"^cargo\s+clippy\b"),
    re.compile(r"^cargo\s+fmt\s+--check\b"),
    re.compile(r"^git\s+diff\s+--check\b"),
    re.compile(r"^python\s+-m\s+json\.tool\b"),
    re.compile(r"^python\s+-m\s+compileall\b"),
)
_BLOCKED_VALIDATION_PATTERNS = (
    re.compile(r"git\s+add\b"),
    re.compile(r"git\s+commit\b"),
    re.compile(r"git\s+push\b"),
    re.compile(r"git\s+merge\b"),
    re.compile(r"git\s+rebase\b"),
    re.compile(r"git\s+checkout\b"),
    re.compile(r"git\s+switch\b"),
    re.compile(r"\bgh\b"),
    re.compile(r"\bcurl\b"),
    re.compile(r"\bwget\b"),
    re.compile(r"\bdeploy\b"),
    re.compile(r"\brelease\b"),
    re.compile(r"\bsecret\b"),
    re.compile(r"\bchmod\b"),
    re.compile(r"\brm\b"),
)

_CATEGORY_OPERATION_MAP = {
    "test_failure": {"modify_existing", "add_test"},
    "typecheck_failure": {"modify_existing"},
    "lint_failure": {"modify_existing"},
    "format_failure": {"modify_existing"},
    "build_failure": {"modify_existing", "add_test"},
}
_CATEGORY_RISK_MAP = {
    "test_failure": "medium",
    "typecheck_failure": "medium",
    "lint_failure": "low",
    "format_failure": "low",
    "build_failure": "high",
}


def evaluate_scoped_ci_patch_proposal_engine(
    request_or_mapping: ScopedCIPatchProposalEngineRequest | Mapping[str, Any] | Any,
) -> ScopedCIPatchProposalEngineResult:
    request = _coerce_request(request_or_mapping)

    gate_result = _coerce_mapping(request.scoped_ci_patch_proposal_gate_result)
    repair_planner = _coerce_mapping(request.ci_repair_planner_result)
    repair_gate = _coerce_mapping(request.ci_repair_loop_gate_result)
    ci_monitor = _coerce_mapping(request.ci_monitor_result)
    ci_gate = _coerce_mapping(request.ci_monitor_gate_result)
    pr_creator = _coerce_mapping(request.pr_creator_result)

    gate_truth = _coerce_mapping(gate_result.get("runtime_truth"))
    planner_truth = _coerce_mapping(repair_planner.get("runtime_truth"))
    repair_gate_truth = _coerce_mapping(repair_gate.get("runtime_truth"))
    ci_monitor_truth = _coerce_mapping(ci_monitor.get("runtime_truth"))
    ci_gate_truth = _coerce_mapping(ci_gate.get("runtime_truth"))
    pr_creator_truth = _coerce_mapping(pr_creator.get("runtime_truth"))
    child_truths = [
        truth for truth in (
            gate_truth, planner_truth, repair_gate_truth,
            ci_monitor_truth, ci_gate_truth, pr_creator_truth,
        ) if truth
    ]

    mode = str(request.proposal_mode or DEFAULT_PROPOSAL_MODE).strip() or DEFAULT_PROPOSAL_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)

    repository, repository_redacted = _redact_optional(
        request.repository_full_name
        or gate_result.get("repository_full_name")
        or repair_planner.get("repository_full_name")
        or repair_gate.get("repository_full_name")
        or ci_monitor.get("repository_full_name")
    )
    pr_number = _optional_int(
        request.pr_number
        if request.pr_number is not None
        else gate_result.get("pr_number")
        or repair_planner.get("pr_number")
        or repair_gate.get("pr_number")
    )
    pr_url, pr_url_redacted = _redact_optional(
        request.pr_url
        or gate_result.get("pr_url")
        or repair_planner.get("pr_url")
        or repair_gate.get("pr_url")
    )
    pr_state, pr_state_redacted = _redact_optional(
        request.pr_state
        or gate_result.get("pr_state")
        or repair_planner.get("pr_state")
        or repair_gate.get("pr_state")
        or ci_monitor.get("pr_state")
        or "open"
    )
    source_branch, source_redacted = _redact_optional(
        request.source_branch
        or gate_result.get("source_branch")
        or repair_planner.get("source_branch")
        or repair_gate.get("source_branch")
    )
    head_branch, head_redacted = _redact_optional(
        request.head_branch
        or gate_result.get("head_branch")
        or repair_planner.get("head_branch")
        or repair_gate.get("head_branch")
        or source_branch
    )
    base_branch = str(
        request.base_branch
        or gate_result.get("base_branch")
        or repair_planner.get("base_branch")
        or repair_gate.get("base_branch")
        or MAIN_BRANCH
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha
        or gate_result.get("commit_sha")
        or repair_planner.get("commit_sha")
        or repair_gate.get("commit_sha")
    )
    head_sha, head_sha_redacted = _redact_optional(
        request.head_sha
        or gate_result.get("head_sha")
        or repair_planner.get("head_sha")
        or repair_gate.get("head_sha")
        or commit_sha
    )

    gate_eligible, gate_success_valid = _gate_evidence(gate_result, gate_truth, request)
    gate_blocked = gate_result.get("blocked") is True
    gate_human = gate_result.get("requires_human_intervention") is True
    gate_patch_proposal_eligible = gate_result.get("patch_proposal_eligible") is True
    gate_has_unsafe_steps = bool(
        gate_result.get("unsafe_repair_steps")
        and len(gate_result.get("unsafe_repair_steps", [])) > 0
    )

    planner_clean, repair_plan_ready = _planner_evidence(repair_planner, planner_truth, request)
    planner_blocked = repair_planner.get("blocked") is True
    planner_human = repair_planner.get("requires_human_intervention") is True
    planner_blocked_cats = list(repair_planner.get("blocked_failure_categories") or [])

    ci_failed = _ci_failed(ci_monitor)
    ci_passed = _ci_passed(ci_monitor)
    ci_pending = _ci_pending(ci_monitor)
    ci_inconclusive = _ci_inconclusive(ci_monitor, ci_failed, ci_passed, ci_pending)

    aggregate_status = str(
        request.aggregate_status
        or gate_result.get("aggregate_status")
        or repair_planner.get("aggregate_status")
        or "unknown"
    )
    aggregate_conclusion = str(
        request.aggregate_conclusion
        or gate_result.get("aggregate_conclusion")
        or repair_planner.get("aggregate_conclusion")
        or "inconclusive"
    )

    failure_categories = list(
        request.failure_categories
        or gate_result.get("failure_categories")
        or repair_planner.get("failure_categories")
        or []
    )
    blocked_failure_categories = list(
        request.blocked_failure_categories
        or gate_result.get("blocked_failure_categories")
        or repair_planner.get("blocked_failure_categories")
        or []
    )
    repair_plan = dict(repair_planner.get("repair_plan") or {})
    repair_plan_steps_raw = list(repair_planner.get("repair_plan_steps") or [])
    scoped_plan = dict(gate_result.get("scoped_patch_proposal_plan") or {})
    patch_proposal_scope = dict(gate_result.get("patch_proposal_scope") or {})
    gate_candidate_areas = list(gate_result.get("candidate_target_areas") or request.candidate_target_areas or [])
    gate_candidate_roots = list(gate_result.get("candidate_file_roots") or request.candidate_file_roots or [])
    gate_suggested_commands = list(
        gate_result.get("suggested_validation_commands")
        or request.suggested_validation_commands
        or []
    )
    gate_required_checks = list(
        gate_result.get("required_pre_patch_proposal_checks")
        or request.required_pre_patch_proposal_checks
        or _default_required_checks()
    )

    repository_safe, unsafe_repository_detected = _repository_safe(repository, request.metadata)
    pr_safe, merged_pr_detected, closed_pr_detected = _pr_state_safe(request, pr_state, request.metadata)
    branch_safe = _branch_safe(request, source_branch, head_branch, base_branch)
    base_safe = not request.require_base_main or base_branch.strip().lower() == MAIN_BRANCH
    head_sha_safe = _sha_safe(head_sha) if request.require_head_sha else True
    protected_branch_detected = any(_protected_branch(branch) for branch in (source_branch, head_branch))
    main_head_detected = any(
        str(branch or "").strip().lower() == MAIN_BRANCH for branch in (source_branch, head_branch)
    )

    attempt_budget_valid, attempt_budget_remaining = _check_attempt_budget(
        request.current_repair_attempt,
        request.max_repair_attempts,
    )

    secret_detected = any((
        requested_redacted, phase_redacted, related_pr_redacted, workspace_redacted,
        repository_redacted, pr_url_redacted, pr_state_redacted, source_redacted,
        head_redacted, commit_sha_redacted, head_sha_redacted,
        _contains_credential_like(_metadata_text(request.metadata)),
        _source_secret(child_truths),
        _planner_check_credential(gate_result),
        _planner_check_credential(repair_planner),
    ))

    validated_steps, safe_steps, unsafe_steps, skipped_steps = _validate_repair_steps(
        repair_plan_steps_raw, gate_result
    )
    candidate_target_areas, blocked_target_areas = _classify_target_areas(gate_candidate_areas)
    candidate_file_roots = _classify_file_roots(gate_candidate_roots)
    validated_commands, unsafe_commands = _validate_commands(gate_suggested_commands)

    scope_valid, scope_block_reason = _validate_scope_limits(
        request.max_patch_proposal_files,
        request.max_patch_proposal_hunks,
        request.max_hunks_per_file,
        request.max_files_to_change,
        request.max_hunks_total,
    )

    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        gate_result=gate_result,
        gate_truth=gate_truth,
        gate_eligible=gate_eligible,
        gate_success_valid=gate_success_valid,
        gate_blocked=gate_blocked,
        gate_human=gate_human,
        gate_patch_proposal_eligible=gate_patch_proposal_eligible,
        gate_has_unsafe_steps=gate_has_unsafe_steps,
        repair_planner=repair_planner,
        planner_truth=planner_truth,
        planner_clean=planner_clean,
        repair_plan_ready=repair_plan_ready,
        planner_blocked=planner_blocked,
        planner_human=planner_human,
        planner_blocked_cats=planner_blocked_cats,
        ci_monitor=ci_monitor,
        ci_failed=ci_failed,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        ci_monitor_truth=ci_monitor_truth,
        secret_detected=secret_detected,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        protected_branch_detected=protected_branch_detected,
        main_head_detected=main_head_detected,
        pr_number=pr_number,
        pr_url=pr_url,
        attempt_budget_valid=attempt_budget_valid,
        attempt_budget_remaining=attempt_budget_remaining,
        blocked_categories=blocked_failure_categories,
        validated_steps=validated_steps,
        candidate_target_areas=candidate_target_areas,
        blocked_target_areas=blocked_target_areas,
        scope_valid=scope_valid,
        scope_block_reason=scope_block_reason,
        unsafe_commands=unsafe_commands,
    )

    evaluated = mode in {"dry_run", "propose_patch"} and not blocked_reason
    dry_run = mode == "dry_run" and not blocked_reason
    blocked = bool(blocked_reason)

    has_safe_steps = bool(safe_steps)
    has_unsafe = bool(unsafe_steps or skipped_steps or blocked_target_areas or unsafe_commands)
    proposed_operations, blocked_operations_found = _classify_operations(failure_categories, candidate_target_areas)
    has_blocked_op = bool(blocked_operations_found)

    proposals, hunks, files_used, files_count, hunks_count = _generate_proposals(
        safe_steps=safe_steps,
        failure_categories=failure_categories,
        candidate_target_areas=candidate_target_areas,
        candidate_file_roots=candidate_file_roots,
        proposed_operations=proposed_operations,
        validated_commands=validated_commands,
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        gate_scoped_plan=scoped_plan,
    )

    proposal_created = bool(
        mode == "propose_patch"
        and evaluated
        and gate_eligible
        and gate_success_valid
        and gate_patch_proposal_eligible
        and not gate_blocked
        and not gate_human
        and planner_clean
        and repair_plan_ready
        and not planner_blocked
        and not planner_human
        and not planner_blocked_cats
        and ci_failed
        and not ci_passed
        and not ci_pending
        and repository_safe
        and pr_safe
        and branch_safe
        and base_safe
        and head_sha_safe
        and pr_number is not None
        and bool(pr_url)
        and not secret_detected
        and attempt_budget_valid
        and attempt_budget_remaining > 0
        and not blocked_failure_categories
        and not protected_branch_detected
        and not main_head_detected
        and not merged_pr_detected
        and not closed_pr_detected
        and has_safe_steps
        and not has_blocked_op
        and not blocked_target_areas
        and scope_valid
        and not unsafe_commands
        and request.allow_proposal_generation
        and proposals
    )

    partial = bool(
        mode == "propose_patch"
        and not blocked
        and not dry_run
        and evaluated
        and not proposal_created
        and has_safe_steps
        and has_unsafe
        and ci_failed
        and not blocked_failure_categories
    )

    summary = _patch_proposal_summary(
        proposal_created=proposal_created,
        partial=partial,
        files_proposed_count=files_count,
        hunks_proposed_count=hunks_count,
        operations=proposed_operations,
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        attempt_budget_remaining=attempt_budget_remaining,
    )

    required_followup_tests = _followup_tests(failure_categories, candidate_target_areas)

    requires_human = bool(
        blocked
        or secret_detected
        or protected_branch_detected
        or main_head_detected
        or merged_pr_detected
        or closed_pr_detected
        or unsafe_repository_detected
        or blocked_failure_categories
        or gate_human
        or gate_blocked
        or planner_human
        or planner_blocked
        or blocked_target_areas
        or (not attempt_budget_valid)
        or (not scope_valid)
        or unsafe_commands
        or has_blocked_op
    )

    runtime_truth = build_scoped_ci_patch_proposal_engine_evidence(
        proposal_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        proposal_created=proposal_created,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        gate_eligible=gate_eligible,
        repair_plan_ready=repair_plan_ready,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        safe_repair_steps_count=len(safe_steps),
        unsafe_repair_steps_count=len(unsafe_steps),
        skipped_repair_steps_count=len(skipped_steps),
        proposal_files_count=files_count,
        proposal_hunks_count=hunks_count,
        proposal_operations_count=len(proposed_operations),
        candidate_target_areas_count=len(candidate_target_areas),
        candidate_file_roots_count=len(candidate_file_roots),
        blocked_target_areas_count=len(blocked_target_areas),
        suggested_validation_commands_count=len(validated_commands),
        secrets_detected=secret_detected,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()

    return ScopedCIPatchProposalEngineResult(
        proposal_created=proposal_created,
        blocked=blocked,
        dry_run=dry_run,
        success=bool(evaluated and not blocked and not dry_run and (proposal_created or partial)),
        partial=partial,
        proposal_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        gate_eligible=gate_eligible,
        repair_plan_ready=repair_plan_ready,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        repair_plan=repair_plan,
        repair_plan_steps=validated_steps,
        scoped_ci_patch_proposals=proposals,
        patch_proposal_summary=summary,
        proposal_hunks=hunks,
        proposal_files=list(files_used),
        proposal_operations=list(proposed_operations),
        proposal_scope=candidate_target_areas,
        candidate_target_areas=candidate_target_areas,
        candidate_file_roots=candidate_file_roots,
        blocked_target_areas=blocked_target_areas,
        skipped_repair_steps=skipped_steps,
        unsafe_repair_steps=unsafe_steps,
        safe_repair_steps=safe_steps,
        suggested_validation_commands=validated_commands,
        required_pre_patch_application_checks=gate_required_checks,
        required_followup_tests=required_followup_tests,
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        files_proposed_count=files_count,
        hunks_proposed_count=hunks_count,
        can_apply_patch=False,
        can_write_files=False,
        can_inspect_source=False,
        can_download_logs=False,
        can_retry_workflows=False,
        can_trigger_workflows=False,
        can_call_provider=False,
        can_call_agent=False,
        can_commit=False,
        can_push=False,
        can_update_pr=False,
        can_merge=False,
        can_auto_merge=False,
        can_mutate_git=False,
        can_execute_commands=False,
        requires_patch_application_gate_phase=proposal_created,
        requires_human_intervention=requires_human,
        reason=_reason(
            proposal_created=proposal_created,
            dry_run=dry_run,
            blocked_reason=blocked_reason,
            partial=partial,
            ci_passed=ci_passed,
            ci_pending=ci_pending,
        ),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _gate_evidence(
    gate_result: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    request: ScopedCIPatchProposalEngineRequest,
) -> tuple[bool, bool]:
    if not gate_result:
        return False, False

    eligible = gate_result.get("patch_proposal_eligible") is True
    ready_meta = gate_result.get("patch_proposal_ready_metadata_only") is True
    success = gate_result.get("success") is True
    blocked = gate_result.get("blocked") is True
    human = gate_result.get("requires_human_intervention") is True

    truth_secrets = gate_truth.get("secrets_detected") is True
    truth_proposed = gate_truth.get("patch_proposal_created") is True
    truth_hunks = gate_truth.get("patch_hunks_generated") is True
    truth_applied = gate_truth.get("patch_applied") is True
    truth_files = gate_truth.get("files_written") is True
    truth_code = gate_truth.get("code_edited") is True
    truth_source = gate_truth.get("source_inspected") is True
    truth_logs = gate_truth.get("logs_downloaded") is True
    truth_retry = gate_truth.get("workflow_retried") is True
    truth_trigger = gate_truth.get("workflow_triggered") is True
    truth_loop = gate_truth.get("repair_loop_started") is True
    truth_provider = gate_truth.get("provider_called") is True
    truth_agent = gate_truth.get("agent_called") is True
    truth_mcp = gate_truth.get("mcp_used") is True
    truth_cmd = gate_truth.get("command_executed") is True
    truth_git = gate_truth.get("git_mutated") is True
    truth_commit = gate_truth.get("commit_executed") is True
    truth_push = gate_truth.get("push_executed") is True
    truth_pr_upd = gate_truth.get("pr_updated") is True
    truth_pr_mrg = gate_truth.get("pr_merged") is True
    truth_auto_mrg = gate_truth.get("auto_merge_enabled") is True
    truth_main = gate_truth.get("main_modified") is True
    truth_vault = gate_truth.get("vault_written") is True

    truth_unsafe = any((
        truth_secrets, truth_proposed, truth_hunks, truth_applied,
        truth_files, truth_code, truth_source,
        truth_logs, truth_retry, truth_trigger, truth_loop,
        truth_provider, truth_agent, truth_mcp,
        truth_cmd, truth_git, truth_commit, truth_push,
        truth_pr_upd, truth_pr_mrg, truth_auto_mrg, truth_main, truth_vault,
    ))

    if truth_secrets or truth_unsafe:
        return False, False
    if blocked or human or not success:
        return False, False
    return bool(eligible and ready_meta and not truth_unsafe), bool(
        eligible and ready_meta and not truth_unsafe
    )


def _planner_evidence(
    repair_planner: Mapping[str, Any],
    planner_truth: Mapping[str, Any],
    request: ScopedCIPatchProposalEngineRequest,
) -> tuple[bool, bool]:
    if not repair_planner:
        return True, True

    planned = repair_planner.get("planned") is True
    success = repair_planner.get("success") is True
    blocked = repair_planner.get("blocked") is True
    human = repair_planner.get("requires_human_intervention") is True
    ready = repair_planner.get("repair_plan_ready") is True
    blocked_cats = list(repair_planner.get("blocked_failure_categories") or [])

    truth_secrets = planner_truth.get("secrets_detected") is True
    truth_loop = planner_truth.get("repair_loop_started") is True
    truth_logs = planner_truth.get("logs_downloaded") is True
    truth_retry = planner_truth.get("workflow_retried") is True
    truth_trigger = planner_truth.get("workflow_triggered") is True
    truth_provider = planner_truth.get("provider_called") is True
    truth_agent = planner_truth.get("agent_called") is True
    truth_mcp = planner_truth.get("mcp_used") is True
    truth_proposed = planner_truth.get("patch_proposed") is True
    truth_applied = planner_truth.get("patch_applied") is True
    truth_files = planner_truth.get("files_written") is True
    truth_code = planner_truth.get("code_edited") is True
    truth_cmd = planner_truth.get("command_executed") is True
    truth_git = planner_truth.get("git_mutated") is True
    truth_commit = planner_truth.get("commit_executed") is True
    truth_push = planner_truth.get("push_executed") is True
    truth_pr_upd = planner_truth.get("pr_updated") is True
    truth_pr_mrg = planner_truth.get("pr_merged") is True
    truth_auto_mrg = planner_truth.get("auto_merge_enabled") is True
    truth_main = planner_truth.get("main_modified") is True
    truth_vault = planner_truth.get("vault_written") is True

    truth_unsafe = any((
        truth_secrets, truth_loop, truth_logs, truth_retry, truth_trigger,
        truth_provider, truth_agent, truth_mcp,
        truth_proposed, truth_applied, truth_files, truth_code,
        truth_cmd, truth_git, truth_commit, truth_push,
        truth_pr_upd, truth_pr_mrg, truth_auto_mrg, truth_main, truth_vault,
    ))

    if blocked or human or not success or truth_unsafe:
        return False, False
    if blocked_cats:
        return False, False
    return bool(planned and ready), bool(planned and ready)


def _blocked_reason(
    *,
    request: ScopedCIPatchProposalEngineRequest,
    mode: str,
    gate_result: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    gate_eligible: bool,
    gate_success_valid: bool,
    gate_blocked: bool,
    gate_human: bool,
    gate_patch_proposal_eligible: bool,
    gate_has_unsafe_steps: bool,
    repair_planner: Mapping[str, Any],
    planner_truth: Mapping[str, Any],
    planner_clean: bool,
    repair_plan_ready: bool,
    planner_blocked: bool,
    planner_human: bool,
    planner_blocked_cats: list[str],
    ci_monitor: Mapping[str, Any],
    ci_failed: bool,
    ci_passed: bool,
    ci_pending: bool,
    ci_monitor_truth: Mapping[str, Any],
    secret_detected: bool,
    repository_safe: bool,
    pr_safe: bool,
    branch_safe: bool,
    base_safe: bool,
    head_sha_safe: bool,
    protected_branch_detected: bool,
    main_head_detected: bool,
    pr_number: int | None,
    pr_url: str | None,
    attempt_budget_valid: bool,
    attempt_budget_remaining: int,
    blocked_categories: list[str],
    validated_steps: list[dict[str, object]],
    candidate_target_areas: list[str],
    blocked_target_areas: list[str],
    scope_valid: bool,
    scope_block_reason: str | None,
    unsafe_commands: list[str],
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in SCOPED_CI_PATCH_PROPOSAL_ENGINE_MODES:
        return "Scoped CI patch proposal engine mode is unknown."
    if mode == "disabled":
        return "Scoped CI patch proposal engine is disabled by default."
    if mode == "blocked":
        return "Scoped CI patch proposal engine mode blocks all proposal generation."
    if any((
        request.allow_patch_application,
        request.allow_file_write,
        request.allow_source_inspection,
        request.allow_log_download,
        request.allow_workflow_retry,
        request.allow_workflow_trigger,
        request.allow_provider_call,
        request.allow_agent_call,
        request.allow_commit,
        request.allow_push,
        request.allow_pr_update,
        request.allow_merge,
        request.allow_auto_merge,
        request.allow_git_mutation,
        request.allow_command_execution,
    )):
        return "Phase 34 cannot enable patch application, file writes, source inspection, logs, retries, triggers, providers, agents, commits, pushes, PR updates, merge, auto-merge, Git mutation, or command execution."
    if request.require_gate_eligible and not gate_result:
        return "Phase 33 scoped CI patch proposal gate result is required."
    if request.require_gate_eligible and not gate_eligible:
        return "Phase 33 scoped CI patch proposal gate is not eligible."
    if not gate_success_valid:
        return "Phase 33 scoped CI patch proposal gate evidence is invalid."
    if gate_blocked:
        return "Phase 33 scoped CI patch proposal gate is blocked."
    if gate_human:
        return "Phase 33 scoped CI patch proposal gate requires human intervention."
    if not gate_patch_proposal_eligible:
        return "Phase 33 did not mark patch proposal eligible."
    if gate_truth.get("secrets_detected") is True:
        return "Phase 33 Runtime Truth reports secrets detected."
    if gate_truth.get("patch_proposal_created") is True:
        return "Phase 33 Runtime Truth reports patch proposals already created (unsafe)."
    if gate_truth.get("patch_hunks_generated") is True:
        return "Phase 33 Runtime Truth reports patch hunks already generated (unsafe)."
    if gate_truth.get("patch_applied") is True:
        return "Phase 33 Runtime Truth reports patch already applied (unsafe)."
    if gate_truth.get("files_written") is True:
        return "Phase 33 Runtime Truth reports files already written (unsafe)."
    if gate_truth.get("code_edited") is True:
        return "Phase 33 Runtime Truth reports code already edited (unsafe)."
    if gate_truth.get("source_inspected") is True:
        return "Phase 33 Runtime Truth reports source already inspected (unsafe)."
    if gate_truth.get("logs_downloaded") is True:
        return "Phase 33 Runtime Truth reports logs already downloaded."
    if gate_truth.get("workflow_retried") is True:
        return "Phase 33 Runtime Truth reports workflows already retried."
    if gate_truth.get("workflow_triggered") is True:
        return "Phase 33 Runtime Truth reports workflows already triggered."
    if gate_truth.get("repair_loop_started") is True:
        return "Phase 33 Runtime Truth reports repair loop already started."
    if gate_truth.get("provider_called") is True:
        return "Phase 33 Runtime Truth reports provider already called."
    if gate_truth.get("agent_called") is True:
        return "Phase 33 Runtime Truth reports agent already called."
    if gate_truth.get("mcp_used") is True:
        return "Phase 33 Runtime Truth reports MCP already used."
    if gate_truth.get("command_executed") is True:
        return "Phase 33 Runtime Truth reports commands already executed."
    if gate_truth.get("git_mutated") is True:
        return "Phase 33 Runtime Truth reports Git already mutated."
    if gate_truth.get("commit_executed") is True:
        return "Phase 33 Runtime Truth reports commits already executed."
    if gate_truth.get("push_executed") is True:
        return "Phase 33 Runtime Truth reports pushes already executed."
    if gate_truth.get("pr_updated") is True:
        return "Phase 33 Runtime Truth reports PR already updated."
    if gate_truth.get("pr_merged") is True:
        return "Phase 33 Runtime Truth reports PR already merged."
    if gate_truth.get("auto_merge_enabled") is True:
        return "Phase 33 Runtime Truth reports auto-merge already enabled."
    if gate_truth.get("main_modified") is True:
        return "Phase 33 Runtime Truth reports main already modified."
    if gate_truth.get("vault_written") is True:
        return "Phase 33 Runtime Truth reports vault already written."

    if repair_planner:
        if not planner_clean:
            return "Phase 32 CI repair planner evidence is not clean."
        if not repair_plan_ready:
            return "Phase 32 repair plan is not ready."
        if planner_blocked:
            return "Phase 32 CI repair planner is blocked."
        if planner_human:
            return "Phase 32 CI repair planner requires human intervention."
        if planner_blocked_cats:
            return "Phase 32 CI repair planner has blocked failure categories."
        if planner_truth.get("secrets_detected") is True:
            return "Phase 32 Runtime Truth reports secrets detected."

    if ci_monitor and ci_monitor.get("monitored") is not True:
        return "Phase 30 CI monitor did not complete monitoring."

    if pr_number is None:
        return "pr_number is required."
    if not pr_url:
        return "pr_url is required."
    if not pr_safe:
        return "PR state metadata is unsafe for proposal generation."
    if not repository_safe:
        return "repository_full_name metadata is unsafe."
    if not branch_safe:
        return "source_branch or head_branch metadata is unsafe."
    if not base_safe:
        return "base_branch must be main."
    if not head_sha_safe:
        return "head_sha or commit_sha metadata is required and must be safe."
    if protected_branch_detected:
        return "Protected source or head branch requires human intervention."
    if main_head_detected:
        return "Main branch head is not allowed for proposal generation."
    if ci_passed:
        return "CI passed; proposal not needed."
    if ci_pending:
        return "CI is pending; proposal must wait for CI completion."
    if not ci_failed:
        return "CI has not failed; no proposal required."
    if blocked_categories:
        return "Blocked failure categories detected; human intervention required."
    if not attempt_budget_valid:
        return "Attempt budget configuration is invalid."
    if attempt_budget_remaining <= 0:
        return "Attempt budget exceeded."
    if blocked_target_areas:
        return f"Blocked target areas detected: {', '.join(sorted(blocked_target_areas))}."
    if not scope_valid:
        return scope_block_reason or "Patch proposal scope limits are invalid."
    if unsafe_commands:
        return f"Unsafe validation commands detected: {', '.join(unsafe_commands)}."
    return None


def _validate_repair_steps(
    steps: list[dict[str, object]],
    gate_result: Mapping[str, Any],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    validated: list[dict[str, object]] = []
    safe: list[dict[str, object]] = []
    unsafe: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    gate_unsafe_steps = list(gate_result.get("unsafe_repair_steps") or [])
    gate_unsafe_types = {
        str(s.get("step_type", "")) for s in gate_unsafe_steps
    }

    for step in steps:
        step_type = str(step.get("step_type", "")).strip()
        target_area = str(step.get("target_area", "")).strip()
        source_check = str(step.get("source_check_name", "")).strip()
        action_intent = str(step.get("action_intent", "")).strip()
        requires_human = step.get("requires_human") is True

        if _contains_credential_like(source_check) or _contains_credential_like(action_intent):
            unsafe.append(step)
            continue

        if step_type in gate_unsafe_types:
            skipped.append(step)
            continue

        if step_type in {"propose_scoped_test_fix", "propose_scoped_typecheck_fix",
                          "propose_scoped_lint_fix", "propose_scoped_format_fix",
                          "propose_scoped_build_fix"}:
            if target_area in _ALLOWED_TARGET_AREAS and not requires_human:
                validated.append(step)
                safe.append(step)
            else:
                skipped.append(step)
            continue

        if step_type.startswith("inspect_"):
            validated.append(step)
            safe.append(step)
            continue

        if step_type == "request_human_review" and requires_human:
            skipped.append(step)
            continue

        validated.append(step)
        safe.append(step)

    return validated, safe, unsafe, skipped


def _classify_operations(
    failure_categories: list[str],
    target_areas: list[str],
) -> tuple[set[str], set[str]]:
    allowed: set[str] = set()
    blocked: set[str] = set()
    for cat in failure_categories:
        ops = _CATEGORY_OPERATION_MAP.get(cat, set())
        for op in ops:
            if op in _ALLOWED_OPERATIONS:
                allowed.add(op)
            else:
                blocked.add(op)

    if "docs" in target_areas and "add_documentation" not in allowed:
        allowed.add("add_documentation")

    return allowed, blocked


def _generate_proposals(
    *,
    safe_steps: list[dict[str, object]],
    failure_categories: list[str],
    candidate_target_areas: list[str],
    candidate_file_roots: list[str],
    proposed_operations: set[str],
    validated_commands: list[str],
    max_patch_proposal_files: int,
    max_patch_proposal_hunks: int,
    max_hunks_per_file: int,
    gate_scoped_plan: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]], set[str], int, int]:
    proposals: list[dict[str, object]] = []
    all_hunks: list[dict[str, object]] = []
    files_used: set[str] = set()
    file_hunk_count: dict[str, int] = {}

    for step_idx, step in enumerate(safe_steps):
        if len(proposals) >= max_patch_proposal_files:
            break

        step_type = str(step.get("step_type", "")).strip()
        target_area = str(step.get("target_area", "")).strip()
        failure_category = str(step.get("failure_category", "")).strip()
        source_check = str(step.get("source_check_name", "")).strip()

        if target_area not in _ALLOWED_TARGET_AREAS:
            continue

        operation = _step_to_operation(step_type, target_area, failure_category)
        if operation not in _ALLOWED_OPERATIONS:
            continue

        file_root = _area_to_root(target_area)
        if not file_root or file_root not in _ALLOWED_FILE_ROOTS:
            continue

        current_file_hunks = file_hunk_count.get(file_root, 0)
        if current_file_hunks >= max_hunks_per_file:
            continue
        if len(all_hunks) >= max_patch_proposal_hunks:
            break

        hunk_type = _step_to_hunk_type(step_type)
        risk = _CATEGORY_RISK_MAP.get(failure_category, "medium")
        requires_human = risk in {"high", "critical"}

        hunk = {
            "hunk_id": f"phase34-hunk-{step_idx + 1}",
            "hunk_type": hunk_type,
            "source_repair_step_id": step.get("step_id"),
            "failure_category": failure_category,
            "target_area": target_area,
            "target_file_root": file_root,
            "operation": operation,
            "target_symbol": None,
            "before_context": None,
            "after_intent": step.get("action_intent"),
            "proposed_snippet": None,
            "confidence": "high" if not requires_human else "medium",
            "risk_level": risk,
            "requires_human": requires_human,
            "allowed_for_future_patch_application": not requires_human,
        }
        all_hunks.append(hunk)
        file_hunk_count[file_root] = current_file_hunks + 1
        files_used.add(file_root)

        if file_root not in [p.get("target_file_root") for p in proposals]:
            proposal = {
                "proposal_id": f"scoped-ci-patch-proposal-{step_idx + 1}",
                "proposal_kind": "scoped_ci_patch_proposal",
                "repository_full_name": gate_scoped_plan.get("repository_full_name"),
                "pr_number": gate_scoped_plan.get("pr_number"),
                "pr_url": gate_scoped_plan.get("pr_url"),
                "head_branch": gate_scoped_plan.get("head_branch"),
                "base_branch": gate_scoped_plan.get("base_branch"),
                "head_sha": gate_scoped_plan.get("head_sha"),
                "commit_sha": gate_scoped_plan.get("commit_sha"),
                "source_phase": "phase_34_scoped_ci_patch_proposal_engine",
                "source_repair_plan_id": gate_scoped_plan.get("repair_plan_id"),
                "failure_categories": failure_categories,
                "affected_areas": candidate_target_areas,
                "target_file_roots": candidate_file_roots,
                "operations": list(proposed_operations),
                "hunks": all_hunks,
                "suggested_validation_commands": validated_commands,
                "required_pre_patch_application_checks": gate_scoped_plan.get(
                    "required_pre_patch_proposal_checks", []
                ),
                "allowed_for_future_patch_application_gate": True,
                "requires_human": requires_human,
                "risk_level": risk,
                "reason": f"Scoped CI patch proposal for {failure_category} in {target_area}.",
            }
            proposals.append(proposal)

    return proposals, all_hunks, files_used, len(proposals), len(all_hunks)


def _step_to_operation(step_type: str, target_area: str, category: str) -> str:
    if "test" in step_type or "test" in category:
        return "modify_existing" if target_area != "docs" else "add_documentation"
    if "typecheck" in step_type or "typecheck" in category:
        return "modify_existing"
    if "lint" in step_type or "lint" in category:
        return "modify_existing"
    if "format" in step_type or "format" in category:
        return "modify_existing"
    if "build" in step_type or "build" in category:
        return "modify_existing"
    if target_area == "docs":
        return "add_documentation"
    return "modify_existing"


def _area_to_root(area: str) -> str | None:
    if area == "backend/rust":
        return "backend/rust/src"
    if area in _ALLOWED_FILE_ROOTS:
        return area
    return None


def _step_to_hunk_type(step_type: str) -> str:
    if "test" in step_type:
        return "test_fix"
    if "typecheck" in step_type:
        return "typecheck_fix"
    if "lint" in step_type:
        return "lint_fix"
    if "format" in step_type:
        return "format_fix"
    if "build" in step_type:
        return "build_fix"
    return "code_fix"


def _classify_target_areas(
    areas: list[str],
) -> tuple[list[str], list[str]]:
    candidate: list[str] = []
    blocked: list[str] = []
    for area in areas:
        area_stripped = area.strip()
        if area_stripped in _ALLOWED_TARGET_AREAS:
            if area_stripped not in candidate:
                candidate.append(area_stripped)
        elif area_stripped in _BLOCKED_FILE_ROOTS:
            if area_stripped not in blocked:
                blocked.append(area_stripped)
        else:
            if area_stripped not in blocked:
                blocked.append(area_stripped)
    return candidate, blocked


def _classify_file_roots(roots: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for root in roots:
        r = root.strip()
        if r in _ALLOWED_FILE_ROOTS and r not in seen:
            seen.add(r)
            result.append(r)
    return result


def _validate_commands(commands: list[str]) -> tuple[list[str], list[str]]:
    safe_cmds: list[str] = []
    unsafe_cmds: list[str] = []
    seen: set[str] = set()
    for cmd in commands:
        cmd_str = str(cmd).strip()
        if _contains_credential_like(cmd_str):
            unsafe_cmds.append(cmd_str)
            continue
        blocked = any(pat.search(cmd_str) for pat in _BLOCKED_VALIDATION_PATTERNS)
        if blocked:
            unsafe_cmds.append(cmd_str)
            continue
        allowed = any(pat.search(cmd_str) for pat in _ALLOWED_VALIDATION_COMMANDS)
        if allowed:
            if cmd_str not in seen:
                seen.add(cmd_str)
                safe_cmds.append(cmd_str)
        else:
            unsafe_cmds.append(cmd_str)
    return safe_cmds, unsafe_cmds


def _validate_scope_limits(
    max_files: int,
    max_hunks: int,
    max_per_file: int,
    planner_max_files: int,
    planner_max_hunks: int,
) -> tuple[bool, str | None]:
    if max_files < 1 or max_files > 10:
        return False, "max_patch_proposal_files must be between 1 and 10."
    if max_hunks < 1 or max_hunks > 50:
        return False, "max_patch_proposal_hunks must be between 1 and 50."
    if max_per_file < 1 or max_per_file > 20:
        return False, "max_hunks_per_file must be between 1 and 20."
    if planner_max_files > max_files:
        return False, "Phase 32 max_files_to_change exceeds max_patch_proposal_files."
    if planner_max_hunks > max_hunks:
        return False, "Phase 32 max_hunks_total exceeds max_patch_proposal_hunks."
    return True, None


def _check_attempt_budget(current: int, maximum: int) -> tuple[bool, int]:
    if current < 0:
        return False, 0
    if maximum < 1 or maximum > 10:
        return False, 0
    remaining = maximum - current
    if remaining < 0:
        remaining = 0
    return True, remaining


def _patch_proposal_summary(
    *,
    proposal_created: bool,
    partial: bool,
    files_proposed_count: int,
    hunks_proposed_count: int,
    operations: set[str],
    max_patch_proposal_files: int,
    max_patch_proposal_hunks: int,
    max_hunks_per_file: int,
    attempt_budget_remaining: int,
) -> dict[str, object]:
    return {
        "proposal_created": proposal_created,
        "partial": partial,
        "files_proposed_count": files_proposed_count,
        "hunks_proposed_count": hunks_proposed_count,
        "operations": list(operations),
        "scope_limits": {
            "max_patch_proposal_files": max_patch_proposal_files,
            "max_patch_proposal_hunks": max_patch_proposal_hunks,
            "max_hunks_per_file": max_hunks_per_file,
        },
        "attempt_budget_remaining": attempt_budget_remaining,
    }


def _default_required_checks() -> list[str]:
    return [
        "ci_monitor_succeeded",
        "ci_repair_loop_gate_eligible",
        "ci_repair_planner_success",
        "repair_plan_ready",
        "patch_proposal_gate_eligible",
        "proposal_metadata_created",
        "ci_failed",
        "pr_number_present",
        "pr_url_present",
        "pr_open_or_draft",
        "repository_safe",
        "base_branch_main",
        "head_branch_non_main",
        "head_sha_present",
        "secrets_absent",
        "runtime_truth_clean",
        "allowed_failure_categories_only",
        "attempt_budget_available",
        "repair_steps_validated",
        "target_areas_safe",
        "scope_limits_valid",
    ]


def _followup_tests(
    failure_categories: list[str],
    target_areas: list[str],
) -> list[str]:
    tests: list[str] = []
    seen: set[str] = set()
    for cat in failure_categories:
        if cat == "test_failure" and "python -m pytest tests" not in seen:
            tests.append("python -m pytest tests")
            seen.add("python -m pytest tests")
        if cat == "typecheck_failure":
            if "python -m pytest tests --typecheck" not in seen:
                tests.append("python -m pytest tests --typecheck")
                seen.add("python -m pytest tests --typecheck")
            if "npm run typecheck" not in seen:
                tests.append("npm run typecheck")
                seen.add("npm run typecheck")
        if cat in ("lint_failure", "format_failure"):
            if "npm run lint" not in seen:
                tests.append("npm run lint")
                seen.add("npm run lint")
        if cat == "build_failure":
            if "npm run build" not in seen:
                tests.append("npm run build")
                seen.add("npm run build")
    for area in target_areas:
        if area == "backend/rust":
            if "cargo test" not in seen:
                tests.append("cargo test")
                seen.add("cargo test")
            if "cargo check" not in seen:
                tests.append("cargo check")
                seen.add("cargo check")
        if area == "frontend/src":
            if "npm test" not in seen:
                tests.append("npm test")
                seen.add("npm test")
    if not tests:
        tests.append("git diff --check")
    return tests


def _reason(
    *,
    proposal_created: bool,
    dry_run: bool,
    blocked_reason: str | None,
    partial: bool,
    ci_passed: bool,
    ci_pending: bool,
) -> str:
    if blocked_reason:
        return "Scoped CI patch proposal engine blocked this request."
    if dry_run:
        return "Scoped CI patch proposal engine evaluated evidence in dry-run mode without creating proposals."
    if ci_passed:
        return "CI passed; proposal not needed."
    if ci_pending:
        return "CI is pending; proposal must wait for CI completion."
    if partial:
        return "Scoped CI patch proposal engine created partial patch proposal metadata (some steps skipped)."
    if proposal_created:
        return "Scoped CI patch proposal engine created scoped CI patch proposal metadata."
    return "Scoped CI patch proposal engine did not create proposal metadata."


def _ci_failed(ci_monitor: Mapping[str, Any]) -> bool:
    if not ci_monitor:
        return False
    return bool(ci_monitor.get("failed") is True)


def _ci_passed(ci_monitor: Mapping[str, Any]) -> bool:
    if not ci_monitor:
        return False
    return bool(ci_monitor.get("passed") is True)


def _ci_pending(ci_monitor: Mapping[str, Any]) -> bool:
    if not ci_monitor:
        return False
    return bool(ci_monitor.get("pending") is True)


def _ci_inconclusive(
    ci_monitor: Mapping[str, Any],
    ci_failed: bool,
    ci_passed: bool,
    ci_pending: bool,
) -> bool:
    if not ci_monitor:
        return True
    conclusion = str(ci_monitor.get("aggregate_conclusion") or "")
    if conclusion == "inconclusive" and not ci_failed and not ci_passed and not ci_pending:
        return True
    return False


def _pr_state_safe(
    request: ScopedCIPatchProposalEngineRequest,
    pr_state: str | None,
    metadata: Mapping[str, Any],
) -> tuple[bool, bool, bool]:
    state = str(pr_state or "").strip().lower()
    merged = state == "merged" or metadata.get("merged") is True
    closed = state == "closed" or metadata.get("closed") is True
    if merged or closed:
        return False, merged, closed
    if request.require_pr_open and state not in {"open"}:
        return False, merged, closed
    if metadata.get("locked") is True or metadata.get("repository_archived") is True:
        return False, merged, closed
    return True, merged, closed


def _branch_safe(
    request: ScopedCIPatchProposalEngineRequest,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
) -> bool:
    if not request.require_non_main_head:
        return True
    source = str(source_branch or "").strip()
    head = str(head_branch or "").strip()
    base = str(base_branch or "").strip().lower()
    if not source or not head:
        return False
    lowered = {source.lower(), head.lower()}
    if MAIN_BRANCH in lowered or base in lowered:
        return False
    return all(_branch_name_safe(branch) for branch in (source, head))


def _branch_name_safe(branch: object) -> bool:
    text = str(branch or "").strip()
    lowered = text.lower()
    if not text or text.startswith(("-", "+", "/", ".")) or text.endswith(("/", ".")):
        return False
    if lowered == MAIN_BRANCH or lowered.startswith(_PROTECTED_PREFIXES):
        return False
    if ".." in text.split("/") or "//" in text or ":" in text or "\\" in text:
        return False
    if any(char in text for char in (" ", "~", "^", "?", "*", "[", "]", "&", "|", ";", "`", "$", "<", ">")):
        return False
    return bool(_BRANCH_PATTERN.fullmatch(text))


def _protected_branch(branch: object) -> bool:
    lowered = str(branch or "").strip().lower()
    return lowered.startswith(_PROTECTED_PREFIXES)


def _repository_safe(repository: str | None, metadata: Mapping[str, Any]) -> tuple[bool, bool]:
    if not repository:
        return False, True
    if _contains_credential_like(repository) or _SHELL_CHARS.search(repository):
        return False, True
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        return False, True
    expected = str(metadata.get("expected_repository") or EXPECTED_REPOSITORY)
    if repository != expected and metadata.get("allow_unexpected_repository") is not True:
        return False, True
    return True, False


def _sha_safe(value: str | None) -> bool:
    if not value:
        return False
    if _contains_credential_like(value) or _SHELL_CHARS.search(value) or any(char.isspace() for char in value):
        return False
    return bool(_SHA_PATTERN.fullmatch(value))


def _source_secret(truths: list[Mapping[str, Any]]) -> bool:
    return any(truth.get("secrets_detected") is True for truth in truths)


def _coerce_request(
    value: ScopedCIPatchProposalEngineRequest | Mapping[str, Any] | Any,
) -> ScopedCIPatchProposalEngineRequest:
    if isinstance(value, ScopedCIPatchProposalEngineRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Scoped CI patch proposal engine input must be a request, mapping, or object.")
    return ScopedCIPatchProposalEngineRequest(
        scoped_ci_patch_proposal_gate_result=_coerce_mapping(
            payload.get("scoped_ci_patch_proposal_gate_result")
        ),
        ci_repair_planner_result=_coerce_mapping(payload.get("ci_repair_planner_result")),
        ci_repair_loop_gate_result=_coerce_mapping(payload.get("ci_repair_loop_gate_result")),
        ci_monitor_result=_coerce_mapping(payload.get("ci_monitor_result")),
        ci_monitor_gate_result=_coerce_mapping(payload.get("ci_monitor_gate_result")),
        pr_creator_result=_coerce_mapping(payload.get("pr_creator_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        proposal_mode=str(payload.get("proposal_mode") or DEFAULT_PROPOSAL_MODE),
        workspace_root=payload.get("workspace_root"),
        repository_full_name=payload.get("repository_full_name"),
        pr_number=payload.get("pr_number"),
        pr_url=payload.get("pr_url"),
        pr_state=payload.get("pr_state"),
        source_branch=payload.get("source_branch"),
        head_branch=payload.get("head_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        head_sha=payload.get("head_sha"),
        commit_sha=payload.get("commit_sha"),
        aggregate_status=payload.get("aggregate_status"),
        aggregate_conclusion=payload.get("aggregate_conclusion"),
        failure_categories=list(payload.get("failure_categories") or []),
        blocked_failure_categories=list(payload.get("blocked_failure_categories") or []),
        repair_plan=dict(payload.get("repair_plan") or {}),
        repair_plan_steps=list(payload.get("repair_plan_steps") or []),
        scoped_patch_proposal_plan=dict(payload.get("scoped_patch_proposal_plan") or {}),
        patch_proposal_scope=dict(payload.get("patch_proposal_scope") or {}),
        candidate_target_areas=list(payload.get("candidate_target_areas") or []),
        candidate_file_roots=list(payload.get("candidate_file_roots") or []),
        suggested_validation_commands=list(payload.get("suggested_validation_commands") or []),
        required_pre_patch_proposal_checks=list(payload.get("required_pre_patch_proposal_checks") or []),
        max_repair_attempts=int(payload.get("max_repair_attempts", 3)),
        current_repair_attempt=int(payload.get("current_repair_attempt", 0)),
        max_files_to_change=int(payload.get("max_files_to_change", 5)),
        max_hunks_total=int(payload.get("max_hunks_total", 20)),
        max_patch_proposal_files=int(payload.get("max_patch_proposal_files", 5)),
        max_patch_proposal_hunks=int(payload.get("max_patch_proposal_hunks", 20)),
        max_hunks_per_file=int(payload.get("max_hunks_per_file", 8)),
        allowed_operations=list(
            payload.get("allowed_operations") or ScopedCIPatchProposalEngineRequest().allowed_operations
        ),
        blocked_operations=list(
            payload.get("blocked_operations") or ScopedCIPatchProposalEngineRequest().blocked_operations
        ),
        allowed_repair_categories=list(
            payload.get("allowed_repair_categories")
            or ScopedCIPatchProposalEngineRequest().allowed_repair_categories
        ),
        blocked_repair_categories=list(
            payload.get("blocked_repair_categories")
            or ScopedCIPatchProposalEngineRequest().blocked_repair_categories
        ),
        allowed_file_roots=list(
            payload.get("allowed_file_roots") or ScopedCIPatchProposalEngineRequest().allowed_file_roots
        ),
        blocked_file_roots=list(
            payload.get("blocked_file_roots") or ScopedCIPatchProposalEngineRequest().blocked_file_roots
        ),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_gate_eligible=bool(payload.get("require_gate_eligible", True)),
        require_gate_success=bool(payload.get("require_gate_success", True)),
        require_repair_plan_ready=bool(payload.get("require_repair_plan_ready", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_gate_evidence=bool(payload.get("require_clean_gate_evidence", True)),
        require_pr_open=bool(payload.get("require_pr_open", True)),
        require_head_sha=bool(payload.get("require_head_sha", True)),
        allow_proposal_generation=bool(payload.get("allow_proposal_generation", True)),
        allow_patch_application=bool(payload.get("allow_patch_application", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
        allow_source_inspection=bool(payload.get("allow_source_inspection", False)),
        allow_log_download=bool(payload.get("allow_log_download", False)),
        allow_workflow_retry=bool(payload.get("allow_workflow_retry", False)),
        allow_workflow_trigger=bool(payload.get("allow_workflow_trigger", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
        allow_commit=bool(payload.get("allow_commit", False)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_pr_update=bool(payload.get("allow_pr_update", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_auto_merge=bool(payload.get("allow_auto_merge", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_command_execution=bool(payload.get("allow_command_execution", False)),
        metadata=dict(payload.get("metadata") or {}),
    )


def _coerce_mapping(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if hasattr(value, "__dataclass_fields__"):
        return dict(asdict(value))
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _redact_optional(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    return _redact_text(value)


def _redact_text(value: object) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    redacted = text
    for pattern in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, redacted != text


def _contains_credential_like(value: object) -> bool:
    text = "" if value is None else str(value)
    return any(pattern.search(text) for pattern in _CREDENTIAL_PATTERNS)


def _metadata_text(metadata: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, value in metadata.items():
        parts.append(str(key))
        if isinstance(value, Mapping):
            parts.append(_metadata_text(value))
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _planner_check_credential(source: Mapping[str, Any]) -> bool:
    checks = source.get("failing_checks") or source.get("repair_plan_steps")
    if not checks or not isinstance(checks, (list, tuple)):
        return False
    for check in checks:
        if isinstance(check, dict):
            name = str(check.get("name", ""))
            if _contains_credential_like(name):
                return True
            source_check = str(check.get("source_check_name", ""))
            if _contains_credential_like(source_check):
                return True
    return False
