"""CI repair loop eligibility gate.

Phase 31 decides whether a failed or inconclusive CI monitor result is eligible
for a future repair loop. It produces eligibility metadata, repair plan metadata,
and Runtime Truth only.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .ci_repair_loop_gate_truth import (
    CI_REPAIR_LOOP_GATE_EVIDENCE_VERSION,
    build_ci_repair_loop_gate_evidence,
)
from .ci_repair_loop_gate_types import (
    CIRepairLoopGateRequest,
    CIRepairLoopGateResult,
)

CI_REPAIR_LOOP_GATE_MODES = frozenset({"disabled", "dry_run", "evaluate_repair", "blocked"})
DEFAULT_REPAIR_GATE_MODE = "disabled"
MAIN_BRANCH = "main"
EXPECTED_REPOSITORY = "misaeldasilva123ms96-commits/Projeto-Omni"

_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
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


def evaluate_ci_repair_loop_gate(
    request_or_mapping: CIRepairLoopGateRequest | Mapping[str, Any] | Any,
) -> CIRepairLoopGateResult:
    request = _coerce_request(request_or_mapping)
    ci_monitor = _coerce_mapping(request.ci_monitor_result)
    ci_gate = _coerce_mapping(request.ci_monitor_gate_result)
    pr_creator = _coerce_mapping(request.pr_creator_result)
    pr_gate = _coerce_mapping(request.pr_creation_gate_result)
    ci_monitor_truth = _coerce_mapping(ci_monitor.get("runtime_truth"))
    ci_gate_truth = _coerce_mapping(ci_gate.get("runtime_truth"))
    pr_creator_truth = _coerce_mapping(pr_creator.get("runtime_truth"))
    pr_gate_truth = _coerce_mapping(pr_gate.get("runtime_truth"))
    mode = str(request.repair_gate_mode or DEFAULT_REPAIR_GATE_MODE).strip() or DEFAULT_REPAIR_GATE_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)
    repository, repository_redacted = _redact_optional(
        request.repository_full_name
        or ci_monitor.get("repository_full_name")
        or ci_gate.get("repository_full_name")
        or pr_creator.get("repository_full_name")
    )
    pr_number = _optional_int(
        request.pr_number
        if request.pr_number is not None
        else ci_monitor.get("pr_number")
        or ci_gate.get("pr_number")
        or pr_creator.get("pr_number")
    )
    pr_url, pr_url_redacted = _redact_optional(
        request.pr_url or ci_monitor.get("pr_url") or ci_gate.get("pr_url") or pr_creator.get("pr_url")
    )
    pr_state, pr_state_redacted = _redact_optional(
        request.pr_state or ci_monitor.get("pr_state") or ci_gate.get("pr_state") or pr_creator.get("pr_state") or "open"
    )
    source_branch, source_redacted = _redact_optional(
        request.source_branch
        or ci_monitor.get("source_branch")
        or ci_gate.get("source_branch")
        or pr_creator.get("source_branch")
    )
    head_branch, head_redacted = _redact_optional(
        request.head_branch
        or ci_monitor.get("head_branch")
        or ci_gate.get("head_branch")
        or pr_creator.get("head_branch")
        or source_branch
    )
    base_branch = str(
        request.base_branch
        or ci_monitor.get("base_branch")
        or ci_gate.get("base_branch")
        or pr_creator.get("base_branch")
        or MAIN_BRANCH
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha
        or ci_monitor.get("commit_sha")
        or ci_gate.get("commit_sha")
        or pr_creator.get("commit_sha")
    )
    head_sha, head_sha_redacted = _redact_optional(
        request.head_sha or ci_monitor.get("head_sha") or ci_gate.get("head_sha") or commit_sha
    )
    child_truths = [
        truth for truth in (ci_monitor_truth, ci_gate_truth, pr_creator_truth, pr_gate_truth) if truth
    ]

    ci_monitor_clean = _ci_monitor_clean(ci_monitor, ci_monitor_truth)
    ci_failed = _ci_failed(ci_monitor)
    ci_passed = _ci_passed(ci_monitor)
    ci_pending = _ci_pending(ci_monitor)
    ci_inconclusive = _ci_inconclusive(ci_monitor, ci_failed, ci_passed, ci_pending)

    failing_check_data = list(ci_monitor.get("failing_checks") or [])
    failing_check_redacted = any(
        _contains_credential_like(check.get("name", ""))
        for check in failing_check_data
    )
    pending_check_data = list(ci_monitor.get("pending_checks") or [])
    missing_checks = list(ci_monitor.get("missing_required_checks") or [])
    unknown_check_data = list(ci_monitor.get("unknown_checks") or [])
    success_check_data = list(ci_monitor.get("successful_checks") or [])
    skipped_check_data = list(ci_monitor.get("skipped_or_neutral_checks") or [])

    aggregate_status = str(request.aggregate_status or ci_monitor.get("aggregate_status") or "unknown")
    aggregate_conclusion = str(
        request.aggregate_conclusion or ci_monitor.get("aggregate_conclusion") or "inconclusive"
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

    failure_categories, blocked_categories = _classify_failures(
        failing_check_data,
        request.allowed_repair_categories,
        request.blocked_repair_categories,
    )

    attempt_budget_valid, attempt_budget_remaining = _check_attempt_budget(
        request.current_repair_attempt,
        request.max_repair_attempts,
    )

    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            related_pr_redacted,
            workspace_redacted,
            repository_redacted,
            pr_url_redacted,
            pr_state_redacted,
            source_redacted,
            head_redacted,
            commit_sha_redacted,
            head_sha_redacted,
            failing_check_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            _source_secret(child_truths),
        )
    )

    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        ci_monitor=ci_monitor,
        ci_gate=ci_gate,
        ci_monitor_truth=ci_monitor_truth,
        ci_gate_truth=ci_gate_truth,
        pr_creator=pr_creator,
        pr_gate=pr_gate,
        pr_creator_truth=pr_creator_truth,
        pr_gate_truth=pr_gate_truth,
        secret_detected=secret_detected,
        ci_monitor_clean=ci_monitor_clean,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        protected_branch_detected=protected_branch_detected,
        main_head_detected=main_head_detected,
        pr_number=pr_number,
        pr_url=pr_url,
    )

    evaluated = mode in {"dry_run", "evaluate_repair"} and not blocked_reason
    dry_run = mode == "dry_run" and not blocked_reason
    blocked = bool(blocked_reason)

    repair_loop_eligible = bool(
        mode == "evaluate_repair"
        and evaluated
        and ci_monitor_clean
        and ci_failed
        and not ci_passed
        and not ci_pending
        and branch_safe
        and base_safe
        and head_sha_safe
        and repository_safe
        and pr_safe
        and pr_number is not None
        and bool(pr_url)
        and not secret_detected
        and attempt_budget_valid
        and attempt_budget_remaining > 0
        and not blocked_categories
        and not protected_branch_detected
        and not main_head_detected
        and not merged_pr_detected
        and not closed_pr_detected
        and not missing_checks
    )

    repair_scope = _repair_scope(
        failing_checks=failing_check_data,
        failure_categories=failure_categories,
        blocked_categories=blocked_categories,
        repair_loop_eligible=repair_loop_eligible,
        attempt_budget_remaining=attempt_budget_remaining,
    )

    plan = _repair_plan(
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
        blocked_categories=blocked_categories,
        repair_scope=repair_scope,
        max_repair_attempts=request.max_repair_attempts,
        current_repair_attempt=request.current_repair_attempt,
        attempt_budget_remaining=attempt_budget_remaining,
        repair_loop_eligible=repair_loop_eligible,
        ci_failed=ci_failed,
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
        or blocked_categories
        or (not attempt_budget_valid)
        or missing_checks
        or (ci_inconclusive and not ci_failed)
    )

    required_checks = _required_checks()
    runtime_truth = build_ci_repair_loop_gate_evidence(
        repair_gate_mode=mode,
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
        repair_loop_eligible=repair_loop_eligible,
        repair_loop_ready_metadata_only=repair_loop_eligible,
        ci_monitor_clean=ci_monitor_clean,
        ci_failed=ci_failed,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        ci_inconclusive=ci_inconclusive,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failing_checks_count=len(failing_check_data),
        pending_checks_count=len(pending_check_data),
        missing_required_checks_count=len(missing_checks),
        unknown_checks_count=len(unknown_check_data),
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_categories,
        max_repair_attempts=request.max_repair_attempts,
        current_repair_attempt=request.current_repair_attempt,
        attempt_budget_remaining=attempt_budget_remaining,
        secrets_detected=secret_detected,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()

    return CIRepairLoopGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=bool(evaluated and not blocked),
        repair_loop_eligible=repair_loop_eligible,
        repair_loop_ready_metadata_only=repair_loop_eligible,
        repair_gate_mode=mode,
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
        ci_monitor_clean=ci_monitor_clean,
        ci_failed=ci_failed,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        ci_inconclusive=ci_inconclusive,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failing_checks=failing_check_data,
        pending_checks=pending_check_data,
        missing_required_checks=missing_checks,
        unknown_checks=unknown_check_data,
        successful_checks=success_check_data,
        skipped_or_neutral_checks=skipped_check_data,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_categories,
        repair_scope=repair_scope,
        repair_plan=plan,
        required_pre_repair_checks=required_checks,
        max_repair_attempts=request.max_repair_attempts,
        current_repair_attempt=request.current_repair_attempt,
        attempt_budget_remaining=attempt_budget_remaining,
        can_start_repair_loop=False,
        can_download_logs=False,
        can_retry_workflows=False,
        can_trigger_workflows=False,
        can_call_provider=False,
        can_call_agent=False,
        can_create_patch_proposal=False,
        can_apply_patch=False,
        can_write_files=False,
        can_commit=False,
        can_push=False,
        can_update_pr=False,
        can_merge=False,
        can_auto_merge=False,
        can_mutate_git=False,
        can_execute_commands=False,
        requires_repair_planner_phase=repair_loop_eligible,
        requires_patch_proposal_phase=False,
        requires_human_intervention=requires_human,
        reason=_reason(
            repair_loop_eligible=repair_loop_eligible,
            dry_run=dry_run,
            blocked_reason=blocked_reason,
            ci_passed=ci_passed,
            ci_pending=ci_pending,
        ),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=CI_REPAIR_LOOP_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _blocked_reason(
    *,
    request: CIRepairLoopGateRequest,
    mode: str,
    ci_monitor: Mapping[str, Any],
    ci_gate: Mapping[str, Any],
    ci_monitor_truth: Mapping[str, Any],
    ci_gate_truth: Mapping[str, Any],
    pr_creator: Mapping[str, Any],
    pr_gate: Mapping[str, Any],
    pr_creator_truth: Mapping[str, Any],
    pr_gate_truth: Mapping[str, Any],
    secret_detected: bool,
    ci_monitor_clean: bool,
    repository_safe: bool,
    pr_safe: bool,
    branch_safe: bool,
    base_safe: bool,
    head_sha_safe: bool,
    protected_branch_detected: bool,
    main_head_detected: bool,
    pr_number: int | None,
    pr_url: str | None,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in CI_REPAIR_LOOP_GATE_MODES:
        return "CI repair loop gate mode is unknown."
    if mode == "disabled":
        return "CI repair loop gate is disabled by default."
    if mode == "blocked":
        return "CI repair loop gate mode blocks all repair-loop eligibility."
    if any(
        (
            request.allow_repair_loop,
            request.allow_log_download,
            request.allow_workflow_retry,
            request.allow_workflow_trigger,
            request.allow_provider_call,
            request.allow_agent_call,
            request.allow_patch_proposal,
            request.allow_patch_apply,
            request.allow_file_write,
            request.allow_commit,
            request.allow_push,
            request.allow_pr_update,
            request.allow_merge,
            request.allow_auto_merge,
            request.allow_git_mutation,
            request.allow_command_execution,
        )
    ):
        return "Phase 31 cannot enable repair loop, logs, retries, triggers, providers, agents, patches, file writes, commits, pushes, PR updates, merge, auto-merge, Git mutation, or command execution."
    if not ci_monitor:
        return "Phase 30 CI monitor evidence is required."
    if ci_monitor.get("monitored") is not True:
        return "Phase 30 CI monitor did not complete monitoring."
    if ci_monitor.get("success") is not True:
        return "Phase 30 CI monitor was not successful."
    if ci_monitor.get("blocked") is True:
        return "Phase 30 CI monitor is blocked."
    if ci_monitor.get("requires_human_intervention") is True:
        return "Phase 30 CI monitor requires human intervention."
    if request.require_runtime_truth and not ci_monitor_truth:
        return "Phase 30 Runtime Truth is required."
    if request.require_clean_ci_evidence and _ci_monitor_truth_unsafe(ci_monitor_truth):
        return "Phase 30 Runtime Truth reports unsafe CI monitor evidence."
    if ci_gate:
        if ci_gate.get("blocked") is True:
            return "Phase 29 CI monitor gate is blocked."
        if ci_gate.get("requires_human_intervention") is True:
            return "Phase 29 CI monitor gate requires human intervention."
        if ci_gate.get("ci_monitor_eligible") is False:
            return "Phase 29 CI monitor gate did not mark monitoring eligible."
        if request.require_clean_ci_evidence and _ci_gate_truth_unsafe(ci_gate_truth):
            return "Phase 29 Runtime Truth reports unsafe CI gate evidence."
    if pr_creator:
        if pr_creator.get("blocked") is True:
            return "Phase 28 PR creator is blocked."
        if pr_creator.get("success") is not True:
            return "Phase 28 PR creator was not successful."
        if request.require_clean_ci_evidence and _pr_creator_truth_unsafe(pr_creator_truth):
            return "Phase 28 Runtime Truth reports unsafe PR creator evidence."
    if pr_gate:
        if pr_gate.get("blocked") is True:
            return "Phase 27 PR gate is blocked."
        if request.require_clean_ci_evidence and _pr_gate_truth_unsafe(pr_gate_truth):
            return "Phase 27 Runtime Truth reports unsafe PR gate evidence."
    if pr_number is None:
        return "pr_number is required."
    if not pr_url:
        return "pr_url is required."
    if not pr_safe:
        return "PR state metadata is unsafe for repair-loop eligibility."
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
        return "Main branch head is not allowed for repair-loop eligibility."
    if not ci_monitor_clean:
        return "CI monitor evidence is not clean."
    if request.metadata.get("locked") is True or request.metadata.get("repository_archived") is True:
        return "PR lock or archived repository metadata requires human intervention."
    return None


def _ci_monitor_clean(ci_monitor: Mapping[str, Any], ci_monitor_truth: Mapping[str, Any]) -> bool:
    if not ci_monitor:
        return False
    if ci_monitor.get("blocked") is True:
        return False
    if ci_monitor.get("requires_human_intervention") is True:
        return False
    if ci_monitor.get("success") is not True:
        return False
    if ci_monitor.get("monitored") is not True:
        return False
    return True


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


def _classify_failures(
    failing_checks: list[dict[str, object]],
    allowed_categories: list[str],
    blocked_categories: list[str],
) -> tuple[list[str], list[str]]:
    found_allowed: list[str] = []
    found_blocked: list[str] = []
    seen: set[str] = set()
    for check in failing_checks:
        name = str(check.get("name") or "")
        lower = name.lower()
        category = "unknown"
        for keyword, cat in _FAILURE_MAP:
            if keyword in lower:
                category = cat
                break
        if category in allowed_categories and category not in seen:
            found_allowed.append(category)
            seen.add(category)
        elif category in blocked_categories and category not in seen:
            found_blocked.append(category)
            seen.add(category)
        elif category not in seen:
            found_blocked.append("unknown_infrastructure_failure")
            seen.add("unknown_infrastructure_failure")
    return found_allowed, found_blocked


_FAILURE_MAP = (
    ("cargo test", "test_failure"),
    ("npm test", "test_failure"),
    ("cargo check", "build_failure"),
    ("vite build", "build_failure"),
    ("production", "deployment_failure"),
    ("permission", "permission_failure"),
    ("credential", "permission_failure"),
    ("codeql", "security_failure"),
    ("secret", "secret_failure"),
    ("trivy", "security_failure"),
    ("snyk", "security_failure"),
    ("audit", "security_failure"),
    ("security", "security_failure"),
    ("deploy", "deployment_failure"),
    ("release", "deployment_failure"),
    ("prod", "deployment_failure"),
    ("billing", "billing_failure"),
    ("payment", "billing_failure"),
    ("invoice", "billing_failure"),
    ("auth", "permission_failure"),
    ("token", "permission_failure"),
    ("typecheck", "typecheck_failure"),
    ("pyright", "typecheck_failure"),
    ("mypy", "typecheck_failure"),
    ("tsc", "typecheck_failure"),
    ("clippy", "lint_failure"),
    ("eslint", "lint_failure"),
    ("ruff", "lint_failure"),
    ("lint", "lint_failure"),
    ("prettier", "format_failure"),
    ("black", "format_failure"),
    ("fmt", "format_failure"),
    ("format", "format_failure"),
    ("build", "build_failure"),
    ("pytest", "test_failure"),
    ("test", "test_failure"),
)


def _check_attempt_budget(current: int, maximum: int) -> tuple[bool, int]:
    if current < 0:
        return False, 0
    if maximum < 1 or maximum > 10:
        return False, 0
    remaining = maximum - current
    if remaining < 0:
        remaining = 0
    return True, remaining


def _repair_scope(
    *,
    failing_checks: list[dict[str, object]],
    failure_categories: list[str],
    blocked_categories: list[str],
    repair_loop_eligible: bool,
    attempt_budget_remaining: int,
) -> list[dict[str, object]]:
    scope: list[dict[str, object]] = []
    for check in failing_checks:
        name = str(check.get("name") or "")
        lower = name.lower()
        category = "unknown"
        for keyword, cat in _FAILURE_MAP:
            if keyword in lower:
                category = cat
                break
        if category not in failure_categories and category not in blocked_categories:
            category = "unknown_infrastructure_failure"
        blocking = category in blocked_categories
        effective = failure_categories or blocked_categories
        scope.append(
            {
                "affected_provider": check.get("provider", "unknown"),
                "failing_check_name": _redact_text(name)[0],
                "failure_category": category,
                "blocking": blocking,
                "required": bool(check.get("required", False)),
                "suggested_next_phase": "ci_repair_planner" if repair_loop_eligible else "human_review",
                "safe_to_plan_repair": repair_loop_eligible and not blocking,
                "requires_human": blocking or not repair_loop_eligible,
            }
        )
    return scope


def _repair_plan(
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
    blocked_categories: list[str],
    repair_scope: list[dict[str, object]],
    max_repair_attempts: int,
    current_repair_attempt: int,
    attempt_budget_remaining: int,
    repair_loop_eligible: bool,
    ci_failed: bool,
    ci_passed: bool,
    ci_pending: bool,
    blocked_reason: str | None,
) -> dict[str, object]:
    allowed_in_future = bool(repair_loop_eligible and not blocked_categories and ci_failed)
    requires_human = bool(blocked_reason or blocked_categories or not ci_failed)
    next_allowed = "ci_repair_planner" if repair_loop_eligible else (
        "wait_for_ci" if ci_pending else (
            "merge_gate" if ci_passed else "human_review"
        )
    )
    return {
        "plan_id": "ci-repair-loop-plan-1",
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
        "blocked_failure_categories": blocked_categories,
        "repair_scope": repair_scope,
        "max_repair_attempts": max_repair_attempts,
        "current_repair_attempt": current_repair_attempt,
        "attempt_budget_remaining": attempt_budget_remaining,
        "allowed_in_future_repair_loop": allowed_in_future,
        "requires_human": requires_human,
        "required_checks_before_repair": _required_checks(),
        "next_allowed_phase": next_allowed,
    }


def _required_checks() -> list[str]:
    return [
        "ci_monitor_succeeded",
        "ci_monitor_evidence_clean",
        "ci_failed_or_inconclusive",
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
    ]


def _reason(
    *,
    repair_loop_eligible: bool,
    dry_run: bool,
    blocked_reason: str | None,
    ci_passed: bool,
    ci_pending: bool,
) -> str:
    if blocked_reason:
        return "CI repair loop gate blocked this eligibility request."
    if dry_run:
        return "CI repair loop gate evaluated evidence in dry-run mode without eligibility."
    if ci_passed:
        return "CI passed; repair loop not needed."
    if ci_pending:
        return "CI is pending; repair loop must wait for CI completion."
    if repair_loop_eligible:
        return "CI repair loop gate marked this CI result eligible for a future repair planner phase."
    return "CI repair loop gate did not mark this CI result eligible."


def _ci_monitor_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    keys = (
        "secrets_detected",
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
        "mcp_used",
        "agent_called",
        "vault_written",
        "main_modified",
    )
    return any(truth.get(key) is True for key in keys)


def _ci_gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    keys = (
        "secrets_detected",
        "ci_monitored",
        "logs_downloaded",
        "workflow_retried",
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
    )
    return any(truth.get(key) is True for key in keys)


def _pr_creator_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    keys = (
        "secrets_detected",
        "pr_merged",
        "auto_merge_enabled",
        "approval_submitted",
        "push_executed",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    )
    return any(truth.get(key) is True for key in keys)


def _pr_gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    keys = (
        "secrets_detected",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "main_modified",
        "provider_called",
        "mcp_used",
    )
    return any(truth.get(key) is True for key in keys)


def _pr_state_safe(
    request: CIRepairLoopGateRequest,
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
    request: CIRepairLoopGateRequest,
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


def _coerce_request(value: CIRepairLoopGateRequest | Mapping[str, Any] | Any) -> CIRepairLoopGateRequest:
    if isinstance(value, CIRepairLoopGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("CI repair loop gate input must be a request, mapping, or object.")
    return CIRepairLoopGateRequest(
        ci_monitor_result=_coerce_mapping(payload.get("ci_monitor_result")),
        ci_monitor_gate_result=_coerce_mapping(payload.get("ci_monitor_gate_result")),
        pr_creator_result=_coerce_mapping(payload.get("pr_creator_result")),
        pr_creation_gate_result=_coerce_mapping(payload.get("pr_creation_gate_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        repair_gate_mode=str(payload.get("repair_gate_mode") or DEFAULT_REPAIR_GATE_MODE),
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
        failing_checks=list(payload.get("failing_checks") or []),
        pending_checks=list(payload.get("pending_checks") or []),
        missing_required_checks=list(payload.get("missing_required_checks") or []),
        unknown_checks=list(payload.get("unknown_checks") or []),
        successful_checks=list(payload.get("successful_checks") or []),
        skipped_or_neutral_checks=list(payload.get("skipped_or_neutral_checks") or []),
        repair_scope=list(payload.get("repair_scope") or []),
        max_repair_attempts=int(payload.get("max_repair_attempts", 3)),
        current_repair_attempt=int(payload.get("current_repair_attempt", 0)),
        max_files_to_change=int(payload.get("max_files_to_change", 5)),
        max_hunks_total=int(payload.get("max_hunks_total", 20)),
        allowed_repair_categories=list(payload.get("allowed_repair_categories") or CIRepairLoopGateRequest().allowed_repair_categories),
        blocked_repair_categories=list(payload.get("blocked_repair_categories") or CIRepairLoopGateRequest().blocked_repair_categories),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_ci_monitor_failed=bool(payload.get("require_ci_monitor_failed", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_ci_evidence=bool(payload.get("require_clean_ci_evidence", True)),
        require_pr_open=bool(payload.get("require_pr_open", True)),
        require_head_sha=bool(payload.get("require_head_sha", True)),
        allow_repair_loop=bool(payload.get("allow_repair_loop", False)),
        allow_log_download=bool(payload.get("allow_log_download", False)),
        allow_workflow_retry=bool(payload.get("allow_workflow_retry", False)),
        allow_workflow_trigger=bool(payload.get("allow_workflow_trigger", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
        allow_patch_proposal=bool(payload.get("allow_patch_proposal", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
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
