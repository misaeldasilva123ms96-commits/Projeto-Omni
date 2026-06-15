"""Scoped CI patch proposal gate for governed sandbox CI repair.

Phase 33 decides whether a safe Phase 32 CI repair plan is eligible for a
future scoped CI patch proposal phase. It does not create patch proposals,
generate patch hunks, apply patches, edit files, write source files, inspect
source files to infer edits, execute repair, download logs, retry workflows,
trigger workflows, call providers, call agents, call MCP, execute commands,
mutate Git, commit, push, update PRs, merge, or enable auto-merge.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Mapping

from .scoped_ci_patch_proposal_gate_truth import (
    SCOPED_CI_PATCH_PROPOSAL_GATE_EVIDENCE_VERSION,
    build_scoped_ci_patch_proposal_gate_evidence,
)
from .scoped_ci_patch_proposal_gate_types import (
    ScopedCIPatchProposalGateRequest,
    ScopedCIPatchProposalGateResult,
)

SCOPED_CI_PATCH_PROPOSAL_GATE_MODES = frozenset(
    {"disabled", "dry_run", "evaluate_patch_proposal", "blocked"}
)
DEFAULT_GATE_MODE = "disabled"
MAIN_BRANCH = "main"
EXPECTED_REPOSITORY = "misaeldasilva123ms96-commits/Projeto-Omni"

_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile("TO" + r"KEN", re.IGNORECASE),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile("AUTH" + r"ORIZATION", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
    re.compile(r"token@", re.IGNORECASE),
    re.compile(r"oauth", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9_]+", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]+", re.IGNORECASE),
)
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_SHA_PATTERN = re.compile(r"^[A-Fa-f0-9]{7,64}$")
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./:(),\\-]{0,159}$")
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
_ALLOWED_STEP_TYPES = frozenset({
    "inspect_test_failure_metadata", "inspect_typecheck_failure_metadata",
    "inspect_lint_failure_metadata", "inspect_format_failure_metadata",
    "inspect_build_failure_metadata", "propose_scoped_test_fix",
    "propose_scoped_typecheck_fix", "propose_scoped_lint_fix",
    "propose_scoped_format_fix", "propose_scoped_build_fix",
    "request_human_review",
})
_PROPOSE_STEP_TYPES = frozenset({
    "propose_scoped_test_fix", "propose_scoped_typecheck_fix",
    "propose_scoped_lint_fix", "propose_scoped_format_fix",
    "propose_scoped_build_fix",
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
    re.compile(r"\bdel\b"),
    re.compile(r"\bremove-item\b"),
)


def evaluate_scoped_ci_patch_proposal_gate(
    request_or_mapping: ScopedCIPatchProposalGateRequest | Mapping[str, Any] | Any,
) -> ScopedCIPatchProposalGateResult:
    request = _coerce_request(request_or_mapping)

    repair_planner = _coerce_mapping(request.ci_repair_planner_result)
    repair_gate = _coerce_mapping(request.ci_repair_loop_gate_result)
    ci_monitor = _coerce_mapping(request.ci_monitor_result)
    ci_gate = _coerce_mapping(request.ci_monitor_gate_result)
    pr_creator = _coerce_mapping(request.pr_creator_result)

    repair_planner_truth = _coerce_mapping(repair_planner.get("runtime_truth"))
    repair_gate_truth = _coerce_mapping(repair_gate.get("runtime_truth"))
    ci_monitor_truth = _coerce_mapping(ci_monitor.get("runtime_truth"))
    ci_gate_truth = _coerce_mapping(ci_gate.get("runtime_truth"))
    pr_creator_truth = _coerce_mapping(pr_creator.get("runtime_truth"))
    child_truths = [
        truth
        for truth in (repair_planner_truth, repair_gate_truth, ci_monitor_truth, ci_gate_truth, pr_creator_truth)
        if truth
    ]

    mode = str(request.patch_proposal_gate_mode or DEFAULT_GATE_MODE).strip() or DEFAULT_GATE_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)
    repository, repository_redacted = _redact_optional(
        request.repository_full_name
        or repair_planner.get("repository_full_name")
        or repair_gate.get("repository_full_name")
        or ci_monitor.get("repository_full_name")
    )
    pr_number = _optional_int(
        request.pr_number
        if request.pr_number is not None
        else repair_planner.get("pr_number")
        or repair_gate.get("pr_number")
        or ci_monitor.get("pr_number")
    )
    pr_url, pr_url_redacted = _redact_optional(
        request.pr_url
        or repair_planner.get("pr_url")
        or repair_gate.get("pr_url")
        or ci_monitor.get("pr_url")
    )
    pr_state, pr_state_redacted = _redact_optional(
        request.pr_state
        or repair_planner.get("pr_state")
        or repair_gate.get("pr_state")
        or ci_monitor.get("pr_state")
        or ci_gate.get("pr_state")
        or pr_creator.get("pr_state")
        or "open"
    )
    source_branch, source_redacted = _redact_optional(
        request.source_branch
        or repair_planner.get("source_branch")
        or repair_gate.get("source_branch")
        or ci_monitor.get("source_branch")
    )
    head_branch, head_redacted = _redact_optional(
        request.head_branch
        or repair_planner.get("head_branch")
        or repair_gate.get("head_branch")
        or ci_monitor.get("head_branch")
        or source_branch
    )
    base_branch = str(
        request.base_branch
        or repair_planner.get("base_branch")
        or repair_gate.get("base_branch")
        or ci_monitor.get("base_branch")
        or MAIN_BRANCH
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha
        or repair_planner.get("commit_sha")
        or repair_gate.get("commit_sha")
        or ci_monitor.get("commit_sha")
    )
    head_sha, head_sha_redacted = _redact_optional(
        request.head_sha
        or repair_planner.get("head_sha")
        or repair_gate.get("head_sha")
        or ci_monitor.get("head_sha")
        or commit_sha
    )

    repair_planner_clean, repair_plan_ready = _repair_planner_evidence(
        repair_planner, repair_planner_truth, request
    )
    repair_planner_blocked = repair_planner.get("blocked") is True
    repair_planner_human = repair_planner.get("requires_human_intervention") is True
    planner_fail_cats = list(repair_planner.get("failure_categories") or [])
    planner_blocked_cats = list(repair_planner.get("blocked_failure_categories") or [])
    planner_attempt_budget = _optional_int(repair_planner.get("attempt_budget_remaining"))
    planner_planned = repair_planner.get("planned") is True
    planner_success = repair_planner.get("success") is True

    repair_gate_valid, repair_gate_blocked_cats, repair_gate_eligible = _repair_gate_evidence(
        repair_gate, repair_gate_truth, request
    )
    repair_gate_blocked = repair_gate.get("blocked") is True
    repair_gate_human = repair_gate.get("requires_human_intervention") is True

    ci_failed = _ci_failed(ci_monitor)
    ci_passed = _ci_passed(ci_monitor)
    ci_pending = _ci_pending(ci_monitor)
    ci_inconclusive = _ci_inconclusive(ci_monitor, ci_failed, ci_passed, ci_pending)

    aggregate_status = str(
        request.aggregate_status
        or repair_planner.get("aggregate_status")
        or repair_gate.get("aggregate_status")
        or ci_monitor.get("aggregate_status")
        or "unknown"
    )
    aggregate_conclusion = str(
        request.aggregate_conclusion
        or repair_planner.get("aggregate_conclusion")
        or repair_gate.get("aggregate_conclusion")
        or ci_monitor.get("aggregate_conclusion")
        or "inconclusive"
    )

    failure_categories = list(
        request.failure_categories
        or repair_planner.get("failure_categories")
        or repair_gate.get("failure_categories")
        or ci_monitor.get("failure_categories")
        or []
    )
    blocked_failure_categories = list(
        request.blocked_failure_categories
        or repair_planner.get("blocked_failure_categories")
        or repair_gate.get("blocked_failure_categories")
        or []
    )
    repair_plan = dict(repair_planner.get("repair_plan") or {})
    repair_plan_steps_raw = list(repair_planner.get("repair_plan_steps") or [])
    affected_areas_raw = list(repair_planner.get("affected_areas") or [])
    suggested_commands_raw = list(repair_planner.get("suggested_validation_commands") or [])
    required_checks_raw = list(
        request.required_pre_patch_proposal_checks
        or repair_planner.get("required_pre_patch_proposal_checks")
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
        _planner_check_credential(repair_planner),
        _planner_check_credential(repair_gate),
    ))

    validated_steps, safe_steps, unsafe_steps = _validate_repair_steps(repair_plan_steps_raw)
    candidate_target_areas, blocked_target_areas = _classify_target_areas(affected_areas_raw)
    candidate_file_roots = _classify_file_roots(candidate_target_areas)
    validated_commands, unsafe_commands = _validate_commands(suggested_commands_raw)

    scope_valid, scope_block_reason = _validate_scope_limits(
        request.max_patch_proposal_files,
        request.max_patch_proposal_hunks,
        request.max_hunks_per_file,
        request.max_files_to_change,
        request.max_hunks_total,
    )

    has_propose_steps = any(
        str(step.get("step_type", "")).strip() in _PROPOSE_STEP_TYPES
        for step in validated_steps
    )
    has_human_step = any(
        str(step.get("step_type", "")).strip() == "request_human_review"
        and step.get("requires_human") is True
        for step in validated_steps
    )
    has_unsafe_step_type = any(
        str(step.get("step_type", "")).strip() not in _ALLOWED_STEP_TYPES
        for step in validated_steps
    )
    has_high_risk_step = any(
        str(step.get("risk_level", "")).strip() == "high"
        and step.get("requires_human") is True
        for step in validated_steps
    )
    has_sensitive_area_step = any(
        str(step.get("target_area", "")).strip() in _BLOCKED_FILE_ROOTS
        or str(step.get("target_area", "")).strip() == ".env"
        for step in validated_steps
    )

    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        repair_planner=repair_planner,
        repair_planner_truth=repair_planner_truth,
        repair_planner_clean=repair_planner_clean,
        repair_plan_ready=repair_plan_ready,
        repair_planner_blocked=repair_planner_blocked,
        repair_planner_human=repair_planner_human,
        planner_blocked_cats=planner_blocked_cats,
        planner_attempt_budget=planner_attempt_budget,
        planner_planned=planner_planned,
        planner_success=planner_success,
        repair_gate=repair_gate,
        repair_gate_truth=repair_gate_truth,
        repair_gate_valid=repair_gate_valid,
        repair_gate_eligible=repair_gate_eligible,
        repair_gate_blocked=repair_gate_blocked,
        repair_gate_human=repair_gate_human,
        repair_gate_blocked_cats=repair_gate_blocked_cats,
        ci_monitor=ci_monitor,
        ci_failed=ci_failed,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        ci_monitor_truth=ci_monitor_truth,
        ci_gate=ci_gate,
        ci_gate_truth=ci_gate_truth,
        pr_creator=pr_creator,
        pr_creator_truth=pr_creator_truth,
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
        has_propose_steps=has_propose_steps,
        has_human_step=has_human_step,
        has_unsafe_step_type=has_unsafe_step_type,
        has_high_risk_step=has_high_risk_step,
        has_sensitive_area_step=has_sensitive_area_step,
        candidate_target_areas=candidate_target_areas,
        blocked_target_areas=blocked_target_areas,
        scope_valid=scope_valid,
        scope_block_reason=scope_block_reason,
        unsafe_commands=unsafe_commands,
    )

    evaluated = mode in {"dry_run", "evaluate_patch_proposal"} and not blocked_reason
    dry_run = mode == "dry_run" and not blocked_reason
    blocked = bool(blocked_reason)

    patch_proposal_eligible = bool(
        mode == "evaluate_patch_proposal"
        and evaluated
        and repair_planner_clean
        and repair_plan_ready
        and planner_planned
        and planner_success
        and not repair_planner_blocked
        and not repair_planner_human
        and not planner_blocked_cats
        and (planner_attempt_budget is None or planner_attempt_budget > 0)
        and repair_gate_eligible
        and not repair_gate_blocked
        and not repair_gate_human
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
        and has_propose_steps
        and not has_human_step
        and not has_unsafe_step_type
        and not has_high_risk_step
        and not has_sensitive_area_step
        and not blocked_target_areas
        and scope_valid
        and not unsafe_commands
        and request.allow_patch_proposal_eligibility
    )

    patch_proposal_ready_metadata_only = bool(
        patch_proposal_eligible
        and not blocked
        and not dry_run
        and not secret_detected
    )

    scope_plan = _scoped_patch_proposal_plan(
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        repair_plan=repair_plan,
        validated_steps=validated_steps,
        candidate_target_areas=candidate_target_areas,
        candidate_file_roots=candidate_file_roots,
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        attempt_budget_remaining=attempt_budget_remaining,
        suggested_validation_commands=validated_commands,
        required_checks=required_checks_raw,
        patch_proposal_eligible=patch_proposal_eligible,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        blocked_reason=blocked_reason,
    )

    requires_human = bool(
        blocked
        or secret_detected
        or protected_branch_detected
        or main_head_detected
        or merged_pr_detected
        or closed_pr_detected
        or unsafe_repository_detected
        or blocked_failure_categories
        or has_unsafe_step_type
        or has_high_risk_step
        or has_sensitive_area_step
        or (not attempt_budget_valid)
        or repair_planner_human
        or repair_planner_blocked
        or repair_gate_human
        or repair_gate_blocked
        or blocked_target_areas
        or (not scope_valid)
        or unsafe_commands
    )

    runtime_truth = build_scoped_ci_patch_proposal_gate_evidence(
        patch_proposal_gate_mode=mode,
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
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        patch_proposal_eligible=patch_proposal_eligible,
        patch_proposal_ready_metadata_only=patch_proposal_ready_metadata_only,
        repair_planner_clean=repair_planner_clean,
        repair_plan_ready=repair_plan_ready,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        repair_plan_steps_count=len(validated_steps),
        safe_repair_steps_count=len(safe_steps),
        unsafe_repair_steps_count=len(unsafe_steps),
        affected_areas_count=len(candidate_target_areas),
        candidate_target_areas_count=len(candidate_target_areas),
        candidate_file_roots_count=len(candidate_file_roots),
        blocked_target_areas_count=len(blocked_target_areas),
        suggested_validation_commands_count=len(validated_commands),
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        secrets_detected=secret_detected,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()

    return ScopedCIPatchProposalGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=bool(evaluated and not blocked and not dry_run),
        patch_proposal_eligible=patch_proposal_eligible,
        patch_proposal_ready_metadata_only=patch_proposal_ready_metadata_only,
        patch_proposal_gate_mode=mode,
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
        repair_planner_clean=repair_planner_clean,
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
        affected_areas=candidate_target_areas,
        suggested_validation_commands=validated_commands,
        required_pre_patch_proposal_checks=required_checks_raw,
        scoped_patch_proposal_plan=scope_plan,
        patch_proposal_scope=candidate_target_areas,
        candidate_target_areas=candidate_target_areas,
        candidate_file_roots=candidate_file_roots,
        blocked_target_areas=blocked_target_areas,
        unsafe_repair_steps=unsafe_steps,
        safe_repair_steps=safe_steps,
        attempt_budget_remaining=attempt_budget_remaining,
        max_patch_proposal_files=request.max_patch_proposal_files,
        max_patch_proposal_hunks=request.max_patch_proposal_hunks,
        max_hunks_per_file=request.max_hunks_per_file,
        can_create_patch_proposal=False,
        can_generate_patch_hunks=False,
        can_apply_patch=False,
        can_write_files=False,
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
        requires_scoped_patch_proposal_phase=patch_proposal_eligible,
        requires_patch_application_gate_phase=False,
        requires_human_intervention=requires_human,
        reason=_reason(
            patch_proposal_eligible=patch_proposal_eligible,
            dry_run=dry_run,
            blocked_reason=blocked_reason,
            ci_passed=ci_passed,
            ci_pending=ci_pending,
        ),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=SCOPED_CI_PATCH_PROPOSAL_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _repair_planner_evidence(
    repair_planner: Mapping[str, Any],
    repair_planner_truth: Mapping[str, Any],
    request: ScopedCIPatchProposalGateRequest,
) -> tuple[bool, bool]:
    if not repair_planner:
        return False, False

    planner_planned = repair_planner.get("planned") is True
    planner_success = repair_planner.get("success") is True
    planner_blocked = repair_planner.get("blocked") is True
    planner_human = repair_planner.get("requires_human_intervention") is True
    planner_ready = repair_planner.get("repair_plan_ready") is True
    planner_blocked_cats = list(repair_planner.get("blocked_failure_categories") or [])
    planner_remaining = int(repair_planner.get("attempt_budget_remaining", 0))

    truth_secrets = repair_planner_truth.get("secrets_detected") is True
    truth_proposed = repair_planner_truth.get("patch_proposed") is True
    truth_applied = repair_planner_truth.get("patch_applied") is True
    truth_files = repair_planner_truth.get("files_written") is True
    truth_code = repair_planner_truth.get("code_edited") is True
    truth_loop = repair_planner_truth.get("repair_loop_started") is True
    truth_logs = repair_planner_truth.get("logs_downloaded") is True
    truth_retry = repair_planner_truth.get("workflow_retried") is True
    truth_trigger = repair_planner_truth.get("workflow_triggered") is True
    truth_provider = repair_planner_truth.get("provider_called") is True
    truth_agent = repair_planner_truth.get("agent_called") is True
    truth_mcp = repair_planner_truth.get("mcp_used") is True
    truth_cmd = repair_planner_truth.get("command_executed") is True
    truth_git = repair_planner_truth.get("git_mutated") is True
    truth_commit = repair_planner_truth.get("commit_executed") is True
    truth_push = repair_planner_truth.get("push_executed") is True
    truth_pr_upd = repair_planner_truth.get("pr_updated") is True
    truth_pr_mrg = repair_planner_truth.get("pr_merged") is True
    truth_auto_mrg = repair_planner_truth.get("auto_merge_enabled") is True
    truth_main = repair_planner_truth.get("main_modified") is True
    truth_vault = repair_planner_truth.get("vault_written") is True

    truth_unsafe = any((
        truth_secrets, truth_proposed, truth_applied, truth_files, truth_code,
        truth_loop, truth_logs, truth_retry, truth_trigger,
        truth_provider, truth_agent, truth_mcp,
        truth_cmd, truth_git, truth_commit, truth_push,
        truth_pr_upd, truth_pr_mrg, truth_auto_mrg, truth_main, truth_vault,
    ))

    if truth_unsafe or truth_secrets:
        return False, False
    if planner_blocked or planner_human or not planner_success:
        return False, False
    if planner_blocked_cats:
        return False, False
    if planner_remaining <= 0:
        return False, False

    return bool(planner_planned and planner_ready and not truth_unsafe), bool(
        planner_planned and planner_ready and not truth_unsafe
    )


def _repair_gate_evidence(
    repair_gate: Mapping[str, Any],
    repair_gate_truth: Mapping[str, Any],
    request: ScopedCIPatchProposalGateRequest,
) -> tuple[bool, list[str], bool]:
    if not repair_gate:
        return True, [], True

    eligible = repair_gate.get("repair_loop_eligible") is True
    success = repair_gate.get("success") is True
    blocked = repair_gate.get("blocked") is True
    human = repair_gate.get("requires_human_intervention") is True
    blocked_cats = list(repair_gate.get("blocked_failure_categories") or [])
    remaining = int(repair_gate.get("attempt_budget_remaining", 0))

    truth_secrets = repair_gate_truth.get("secrets_detected") is True
    truth_loop = repair_gate_truth.get("repair_loop_started") is True
    truth_logs = repair_gate_truth.get("logs_downloaded") is True
    truth_retry = repair_gate_truth.get("workflow_retried") is True
    truth_trigger = repair_gate_truth.get("workflow_triggered") is True
    truth_provider = repair_gate_truth.get("provider_called") is True
    truth_agent = repair_gate_truth.get("agent_called") is True
    truth_mcp = repair_gate_truth.get("mcp_used") is True
    truth_proposed = repair_gate_truth.get("patch_proposed") is True
    truth_applied = repair_gate_truth.get("patch_applied") is True
    truth_files = repair_gate_truth.get("files_written") is True
    truth_code = repair_gate_truth.get("code_edited") is True
    truth_cmd = repair_gate_truth.get("command_executed") is True
    truth_git = repair_gate_truth.get("git_mutated") is True
    truth_commit = repair_gate_truth.get("commit_executed") is True
    truth_push = repair_gate_truth.get("push_executed") is True
    truth_pr_upd = repair_gate_truth.get("pr_updated") is True
    truth_pr_mrg = repair_gate_truth.get("pr_merged") is True
    truth_auto_mrg = repair_gate_truth.get("auto_merge_enabled") is True
    truth_main = repair_gate_truth.get("main_modified") is True
    truth_vault = repair_gate_truth.get("vault_written") is True

    truth_unsafe = any((
        truth_secrets, truth_loop, truth_logs, truth_retry, truth_trigger,
        truth_provider, truth_agent, truth_mcp,
        truth_proposed, truth_applied, truth_files, truth_code,
        truth_cmd, truth_git, truth_commit, truth_push,
        truth_pr_upd, truth_pr_mrg, truth_auto_mrg, truth_main, truth_vault,
    ))

    if blocked or human or not success or truth_unsafe:
        return False, blocked_cats, False
    if remaining <= 0:
        return False, blocked_cats, False
    if blocked_cats:
        return False, blocked_cats, False
    if not eligible:
        return False, blocked_cats, False

    return True, blocked_cats, True


def _blocked_reason(
    *,
    request: ScopedCIPatchProposalGateRequest,
    mode: str,
    repair_planner: Mapping[str, Any],
    repair_planner_truth: Mapping[str, Any],
    repair_planner_clean: bool,
    repair_plan_ready: bool,
    repair_planner_blocked: bool,
    repair_planner_human: bool,
    planner_blocked_cats: list[str],
    planner_attempt_budget: int | None,
    planner_planned: bool,
    planner_success: bool,
    repair_gate: Mapping[str, Any],
    repair_gate_truth: Mapping[str, Any],
    repair_gate_valid: bool,
    repair_gate_eligible: bool,
    repair_gate_blocked: bool,
    repair_gate_human: bool,
    repair_gate_blocked_cats: list[str],
    ci_monitor: Mapping[str, Any],
    ci_failed: bool,
    ci_passed: bool,
    ci_pending: bool,
    ci_monitor_truth: Mapping[str, Any],
    ci_gate: Mapping[str, Any],
    ci_gate_truth: Mapping[str, Any],
    pr_creator: Mapping[str, Any],
    pr_creator_truth: Mapping[str, Any],
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
    has_propose_steps: bool,
    has_human_step: bool,
    has_unsafe_step_type: bool,
    has_high_risk_step: bool,
    has_sensitive_area_step: bool,
    candidate_target_areas: list[str],
    blocked_target_areas: list[str],
    scope_valid: bool,
    scope_block_reason: str | None,
    unsafe_commands: list[str],
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in SCOPED_CI_PATCH_PROPOSAL_GATE_MODES:
        return "Scoped CI patch proposal gate mode is unknown."
    if mode == "disabled":
        return "Scoped CI patch proposal gate is disabled by default."
    if mode == "blocked":
        return "Scoped CI patch proposal gate mode blocks all eligibility."
    if any((
        request.allow_patch_proposal_creation,
        request.allow_patch_hunk_generation,
        request.allow_patch_apply,
        request.allow_file_write,
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
        return "Phase 33 cannot enable patch creation, patch hunks, patch apply, file writes, logs, retries, triggers, providers, agents, commits, pushes, PR updates, merge, auto-merge, Git mutation, or command execution."
    if request.require_repair_planner_success and not repair_planner:
        return "Phase 32 CI repair planner result is required."
    if request.require_repair_planner_success and not repair_planner_clean:
        return "Phase 32 CI repair planner evidence is not clean."
    if request.require_repair_plan_ready and not repair_plan_ready:
        return "Phase 32 repair plan is not ready."
    if not planner_planned:
        return "Phase 32 did not mark planned."
    if not planner_success:
        return "Phase 32 did not mark success."
    if repair_planner_blocked:
        return "Phase 32 CI repair planner is blocked."
    if repair_planner_human:
        return "Phase 32 CI repair planner requires human intervention."
    if planner_blocked_cats:
        return "Phase 32 CI repair planner has blocked failure categories."
    if repair_planner_truth.get("secrets_detected") is True:
        return "Phase 32 Runtime Truth reports secrets detected."
    if repair_planner_truth.get("patch_proposed") is True:
        return "Phase 32 Runtime Truth reports patch already proposed (unsafe)."
    if repair_planner_truth.get("patch_applied") is True:
        return "Phase 32 Runtime Truth reports patch already applied (unsafe)."
    if repair_planner_truth.get("files_written") is True:
        return "Phase 32 Runtime Truth reports files already written (unsafe)."
    if repair_planner_truth.get("code_edited") is True:
        return "Phase 32 Runtime Truth reports code already edited (unsafe)."
    if repair_planner_truth.get("repair_loop_started") is True:
        return "Phase 32 Runtime Truth reports repair loop already started."
    if repair_planner_truth.get("logs_downloaded") is True:
        return "Phase 32 Runtime Truth reports logs already downloaded."
    if repair_planner_truth.get("workflow_retried") is True:
        return "Phase 32 Runtime Truth reports workflows already retried."
    if repair_planner_truth.get("workflow_triggered") is True:
        return "Phase 32 Runtime Truth reports workflows already triggered."
    if repair_planner_truth.get("provider_called") is True:
        return "Phase 32 Runtime Truth reports provider already called."
    if repair_planner_truth.get("agent_called") is True:
        return "Phase 32 Runtime Truth reports agent already called."
    if repair_planner_truth.get("mcp_used") is True:
        return "Phase 32 Runtime Truth reports MCP already used."
    if repair_planner_truth.get("command_executed") is True:
        return "Phase 32 Runtime Truth reports commands already executed."
    if repair_planner_truth.get("git_mutated") is True:
        return "Phase 32 Runtime Truth reports Git already mutated."
    if repair_planner_truth.get("commit_executed") is True:
        return "Phase 32 Runtime Truth reports commits already executed."
    if repair_planner_truth.get("push_executed") is True:
        return "Phase 32 Runtime Truth reports pushes already executed."
    if repair_planner_truth.get("pr_updated") is True:
        return "Phase 32 Runtime Truth reports PR already updated."
    if repair_planner_truth.get("pr_merged") is True:
        return "Phase 32 Runtime Truth reports PR already merged."
    if repair_planner_truth.get("auto_merge_enabled") is True:
        return "Phase 32 Runtime Truth reports auto-merge already enabled."
    if repair_planner_truth.get("main_modified") is True:
        return "Phase 32 Runtime Truth reports main already modified."
    if repair_planner_truth.get("vault_written") is True:
        return "Phase 32 Runtime Truth reports vault already written."
    if planner_attempt_budget is not None and planner_attempt_budget <= 0:
        return "Phase 32 has no attempt budget remaining."

    if repair_gate:
        if not repair_gate_valid:
            return "Phase 31 CI repair loop gate evidence is invalid."
        if repair_gate_blocked:
            return "Phase 31 CI repair loop gate is blocked."
        if repair_gate_human:
            return "Phase 31 CI repair loop gate requires human intervention."
        if repair_gate_blocked_cats:
            return "Phase 31 CI repair loop gate has blocked failure categories."
        if repair_gate_truth.get("secrets_detected") is True:
            return "Phase 31 Runtime Truth reports secrets detected."
        if repair_gate_truth.get("repair_loop_started") is True:
            return "Phase 31 Runtime Truth reports repair loop already started."

    if ci_monitor:
        if ci_monitor.get("monitored") is not True:
            return "Phase 30 CI monitor did not complete monitoring."
        if ci_monitor.get("success") is not True:
            return "Phase 30 CI monitor was not successful."
        if ci_monitor.get("blocked") is True:
            return "Phase 30 CI monitor is blocked."
        if ci_monitor.get("requires_human_intervention") is True:
            return "Phase 30 CI monitor requires human intervention."

    if pr_number is None:
        return "pr_number is required."
    if not pr_url:
        return "pr_url is required."
    if not pr_safe:
        return "PR state metadata is unsafe for patch proposal eligibility."
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
        return "Main branch head is not allowed for patch proposal eligibility."
    if ci_passed:
        return "CI passed; patch proposal not needed."
    if ci_pending:
        return "CI is pending; patch proposal must wait for CI completion."
    if not ci_failed:
        return "CI has not failed; no patch proposal required."
    if blocked_categories:
        return "Blocked failure categories detected; human intervention required."
    if not attempt_budget_valid:
        return "Attempt budget configuration is invalid."
    if attempt_budget_remaining <= 0:
        return "Attempt budget exceeded."
    if not has_propose_steps:
        return "No propose-scoped-* repair steps found; cannot determine eligibility."
    if has_human_step:
        return "Repair plan has request_human_review steps; human intervention required."
    if has_unsafe_step_type:
        return "Repair plan has unknown step types; human intervention required."
    if has_high_risk_step:
        return "Repair plan has high-risk steps; human intervention required."
    if has_sensitive_area_step:
        return "Repair plan has steps targeting sensitive areas; human intervention required."
    if blocked_target_areas:
        return f"Blocked target areas detected: {', '.join(sorted(blocked_target_areas))}."
    if not scope_valid:
        return scope_block_reason or "Patch proposal scope limits are invalid."
    if unsafe_commands:
        return f"Unsafe validation commands detected: {', '.join(unsafe_commands)}."
    return None


def _validate_repair_steps(
    steps: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    validated: list[dict[str, object]] = []
    safe: list[dict[str, object]] = []
    unsafe: list[dict[str, object]] = []
    for step in steps:
        step_type = str(step.get("step_type", "")).strip()
        target_area = str(step.get("target_area", "")).strip()
        risk_level = str(step.get("risk_level", "")).strip()
        source_check = str(step.get("source_check_name", "")).strip()
        action_intent = str(step.get("action_intent", "")).strip()
        requires_human = step.get("requires_human") is True

        if _contains_credential_like(source_check) or _contains_credential_like(action_intent):
            unsafe.append(step)
            continue

        if step_type not in _ALLOWED_STEP_TYPES:
            validated.append(step)
            unsafe.append(step)
            continue

        if step_type in _PROPOSE_STEP_TYPES and target_area in _ALLOWED_TARGET_AREAS:
            validated.append(step)
            safe.append(step)
        elif step_type == "request_human_review":
            validated.append(step)
            if requires_human:
                unsafe.append(step)
            else:
                safe.append(step)
        elif step_type.startswith("inspect_"):
            validated.append(step)
            safe.append(step)
        else:
            validated.append(step)
            unsafe.append(step)

    return validated, safe, unsafe


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
        elif area_stripped == "unknown":
            if area_stripped not in candidate:
                candidate.append(area_stripped)
        else:
            if area_stripped not in blocked:
                blocked.append(area_stripped)
    return candidate, blocked


def _classify_file_roots(areas: list[str]) -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()
    for area in areas:
        root = area
        if root == "backend/rust":
            root = "backend/rust/src"
        if root in _ALLOWED_FILE_ROOTS and root not in seen:
            seen.add(root)
            roots.append(root)
    return roots


def _validate_commands(
    commands: list[str],
) -> tuple[list[str], list[str]]:
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
        allowed = any(pat.fullmatch(cmd_str) if hasattr(pat, 'fullmatch') else pat.search(cmd_str) for pat in _ALLOWED_VALIDATION_COMMANDS)
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


def _scoped_patch_proposal_plan(
    *,
    repository_full_name: str | None,
    pr_number: int | None,
    pr_url: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    commit_sha: str | None,
    aggregate_status: str,
    aggregate_conclusion: str,
    failure_categories: list[str],
    blocked_failure_categories: list[str],
    repair_plan: dict[str, object],
    validated_steps: list[dict[str, object]],
    candidate_target_areas: list[str],
    candidate_file_roots: list[str],
    max_patch_proposal_files: int,
    max_patch_proposal_hunks: int,
    max_hunks_per_file: int,
    attempt_budget_remaining: int,
    suggested_validation_commands: list[str],
    required_checks: list[str],
    patch_proposal_eligible: bool,
    ci_passed: bool,
    ci_pending: bool,
    blocked_reason: str | None,
) -> dict[str, object]:
    plan_id = f"scoped-ci-patch-proposal-plan-pr-{pr_number}-1" if pr_number else "scoped-ci-patch-proposal-plan-1"

    next_allowed = (
        "scoped_ci_patch_proposal" if patch_proposal_eligible else
        "wait_for_ci" if ci_pending else
        "merge_gate" if ci_passed else
        "human_review"
    )

    return {
        "plan_id": plan_id,
        "repository_full_name": repository_full_name,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "head_sha": head_sha,
        "commit_sha": commit_sha,
        "aggregate_status": aggregate_status,
        "aggregate_conclusion": aggregate_conclusion,
        "failure_categories": failure_categories,
        "blocked_failure_categories": blocked_failure_categories,
        "repair_plan_id": repair_plan.get("plan_id"),
        "repair_plan_steps": validated_steps,
        "affected_areas": candidate_target_areas,
        "candidate_target_areas": candidate_target_areas,
        "candidate_file_roots": candidate_file_roots,
        "patch_scope_limits": {
            "max_patch_proposal_files": max_patch_proposal_files,
            "max_patch_proposal_hunks": max_patch_proposal_hunks,
            "max_hunks_per_file": max_hunks_per_file,
            "attempt_budget_remaining": attempt_budget_remaining,
        },
        "suggested_validation_commands": suggested_validation_commands,
        "required_pre_patch_proposal_checks": required_checks,
        "allowed_in_future_scoped_patch_proposal": patch_proposal_eligible,
        "requires_human": bool(blocked_reason),
        "next_allowed_phase": next_allowed,
    }


def _default_required_checks() -> list[str]:
    return [
        "ci_monitor_succeeded",
        "ci_repair_loop_gate_eligible",
        "ci_repair_planner_success",
        "repair_plan_ready",
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


def _reason(
    *,
    patch_proposal_eligible: bool,
    dry_run: bool,
    blocked_reason: str | None,
    ci_passed: bool,
    ci_pending: bool,
) -> str:
    if blocked_reason:
        return "Scoped CI patch proposal gate blocked this request."
    if dry_run:
        return "Scoped CI patch proposal gate evaluated evidence in dry-run mode without marking eligibility."
    if ci_passed:
        return "CI passed; patch proposal not needed."
    if ci_pending:
        return "CI is pending; patch proposal must wait for CI completion."
    if patch_proposal_eligible:
        return "Scoped CI patch proposal gate marked patch proposal eligible."
    return "Scoped CI patch proposal gate did not mark patch proposal eligible."


def _pr_state_safe(
    request: ScopedCIPatchProposalGateRequest,
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
    request: ScopedCIPatchProposalGateRequest,
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
    value: ScopedCIPatchProposalGateRequest | Mapping[str, Any] | Any,
) -> ScopedCIPatchProposalGateRequest:
    if isinstance(value, ScopedCIPatchProposalGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Scoped CI patch proposal gate input must be a request, mapping, or object.")
    return ScopedCIPatchProposalGateRequest(
        ci_repair_planner_result=_coerce_mapping(payload.get("ci_repair_planner_result")),
        ci_repair_loop_gate_result=_coerce_mapping(payload.get("ci_repair_loop_gate_result")),
        ci_monitor_result=_coerce_mapping(payload.get("ci_monitor_result")),
        ci_monitor_gate_result=_coerce_mapping(payload.get("ci_monitor_gate_result")),
        pr_creator_result=_coerce_mapping(payload.get("pr_creator_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        patch_proposal_gate_mode=str(payload.get("patch_proposal_gate_mode") or DEFAULT_GATE_MODE),
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
        affected_areas=list(payload.get("affected_areas") or []),
        suggested_validation_commands=list(payload.get("suggested_validation_commands") or []),
        required_pre_patch_proposal_checks=list(payload.get("required_pre_patch_proposal_checks") or []),
        max_repair_attempts=int(payload.get("max_repair_attempts", 3)),
        current_repair_attempt=int(payload.get("current_repair_attempt", 0)),
        max_files_to_change=int(payload.get("max_files_to_change", 5)),
        max_hunks_total=int(payload.get("max_hunks_total", 20)),
        max_patch_proposal_files=int(payload.get("max_patch_proposal_files", 5)),
        max_patch_proposal_hunks=int(payload.get("max_patch_proposal_hunks", 20)),
        max_hunks_per_file=int(payload.get("max_hunks_per_file", 8)),
        allowed_repair_categories=list(
            payload.get("allowed_repair_categories") or ScopedCIPatchProposalGateRequest().allowed_repair_categories
        ),
        blocked_repair_categories=list(
            payload.get("blocked_repair_categories") or ScopedCIPatchProposalGateRequest().blocked_repair_categories
        ),
        allowed_file_roots=list(
            payload.get("allowed_file_roots") or ScopedCIPatchProposalGateRequest().allowed_file_roots
        ),
        blocked_file_roots=list(
            payload.get("blocked_file_roots") or ScopedCIPatchProposalGateRequest().blocked_file_roots
        ),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_repair_plan_ready=bool(payload.get("require_repair_plan_ready", True)),
        require_repair_planner_success=bool(payload.get("require_repair_planner_success", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_repair_plan_evidence=bool(payload.get("require_clean_repair_plan_evidence", True)),
        require_pr_open=bool(payload.get("require_pr_open", True)),
        require_head_sha=bool(payload.get("require_head_sha", True)),
        allow_patch_proposal_eligibility=bool(payload.get("allow_patch_proposal_eligibility", True)),
        allow_patch_proposal_creation=bool(payload.get("allow_patch_proposal_creation", False)),
        allow_patch_hunk_generation=bool(payload.get("allow_patch_hunk_generation", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
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
