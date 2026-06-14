"""CI monitor eligibility gate.

Phase 29 evaluates whether a created PR is eligible for a future CI/checks
monitoring phase. It produces metadata and Runtime Truth only.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .ci_monitor_gate_truth import (
    CI_MONITOR_GATE_EVIDENCE_VERSION,
    build_ci_monitor_gate_evidence,
)
from .ci_monitor_gate_types import CIMonitorGateRequest, CIMonitorGateResult

CI_MONITOR_GATE_MODES = frozenset({"disabled", "dry_run", "evaluate_ci_monitor", "blocked"})
DEFAULT_CI_MONITOR_GATE_MODE = "disabled"
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
_CI_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./:(),\\-]{0,119}$")
_SHELL_CHARS = re.compile(r"[;&|`$<>]")
_PROTECTED_PREFIXES = ("release/", "prod/", "production/", "protected/")
_ALLOWED_PROVIDERS = {"github_actions", "circleci"}
_DESTRUCTIVE_CI_WORDS = ("deploy", "release production", "production deploy", "billing", "destroy")


def evaluate_ci_monitor_gate(
    request_or_mapping: CIMonitorGateRequest | Mapping[str, Any] | Any,
) -> CIMonitorGateResult:
    request = _coerce_request(request_or_mapping)
    pr_creator = _coerce_mapping(request.pr_creator_result)
    pr_gate = _coerce_mapping(request.pr_creation_gate_result)
    push_executor = _coerce_mapping(request.push_executor_result)
    pr_creator_truth = _coerce_mapping(pr_creator.get("runtime_truth"))
    pr_gate_truth = _coerce_mapping(pr_gate.get("runtime_truth"))
    push_executor_truth = _coerce_mapping(push_executor.get("runtime_truth"))
    mode = str(request.ci_monitor_gate_mode or DEFAULT_CI_MONITOR_GATE_MODE).strip() or DEFAULT_CI_MONITOR_GATE_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)
    repository, repository_redacted = _redact_optional(
        request.repository_full_name or pr_creator.get("repository_full_name") or pr_gate.get("repository_full_name")
    )
    pr_number = _optional_int(request.pr_number if request.pr_number is not None else pr_creator.get("pr_number"))
    pr_url, pr_url_redacted = _redact_optional(request.pr_url or pr_creator.get("pr_url") or pr_creator.get("existing_pr_url"))
    pr_state, pr_state_redacted = _redact_optional(request.pr_state or pr_creator.get("pr_state") or "open")
    pr_draft = request.pr_draft if request.pr_draft is not None else pr_creator.get("final_draft")
    source_branch, source_redacted = _redact_optional(
        request.source_branch or pr_creator.get("source_branch") or pr_gate.get("source_branch")
    )
    head_branch, head_redacted = _redact_optional(
        request.head_branch or pr_creator.get("head_branch") or pr_gate.get("head_branch")
    )
    base_branch = str(request.base_branch or pr_creator.get("base_branch") or pr_gate.get("base_branch") or MAIN_BRANCH)
    base_sha, base_sha_redacted = _redact_optional(request.base_sha)
    merge_commit_sha, merge_sha_redacted = _redact_optional(request.merge_commit_sha)
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha or pr_creator.get("commit_sha") or pr_gate.get("commit_sha") or push_executor.get("commit_sha")
    )
    head_sha, head_sha_redacted = _redact_optional(request.head_sha or commit_sha)
    providers, providers_safe, providers_redacted = _sanitize_ci_names(
        request.expected_ci_providers,
        allowed_providers=True,
    )
    workflows, workflows_safe, workflows_redacted = _sanitize_ci_names(request.expected_workflows)
    checks, checks_safe, checks_redacted = _sanitize_ci_names(request.expected_required_checks)
    child_truths = [truth for truth in (pr_creator_truth, pr_gate_truth, push_executor_truth) if truth]

    repository_safe, unsafe_repository_detected = _repository_safe(repository, request.metadata)
    branch_reason = _branch_block_reason(request, source_branch, head_branch)
    branch_safe = branch_reason is None
    base_safe = not request.require_base_main or base_branch.strip().lower() == MAIN_BRANCH
    protected_branch_detected = any(_protected_branch(branch) for branch in (source_branch, head_branch))
    main_head_detected = any(str(branch or "").strip().lower() == MAIN_BRANCH for branch in (source_branch, head_branch))
    pr_safe, merged_pr_detected, closed_pr_detected = _pr_state_safe(request, pr_state, request.metadata)
    head_sha_safe = _sha_safe(head_sha) if request.require_head_sha else True
    pr_was_created = bool(pr_creator.get("pr_created") is True)
    pr_evidence_clean = bool(
        pr_was_created
        and pr_creator.get("success") is not False
        and pr_creator.get("blocked") is not True
        and not _pr_creator_truth_unsafe(pr_creator_truth)
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
            base_sha_redacted,
            merge_sha_redacted,
            commit_sha_redacted,
            head_sha_redacted,
            providers_redacted,
            workflows_redacted,
            checks_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            _source_secret(child_truths),
        )
    )
    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        pr_creator=pr_creator,
        pr_gate=pr_gate,
        push_executor=push_executor,
        pr_creator_truth=pr_creator_truth,
        pr_gate_truth=pr_gate_truth,
        push_executor_truth=push_executor_truth,
        secret_detected=secret_detected,
        pr_was_created=pr_was_created,
        pr_evidence_clean=pr_evidence_clean,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_safe=pr_safe,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        providers_safe=providers_safe,
        workflows_safe=workflows_safe,
        checks_safe=checks_safe,
    )
    dry_run = mode == "dry_run" and not blocked_reason
    evaluated = mode in {"dry_run", "evaluate_ci_monitor"} and not blocked_reason
    eligible = bool(
        mode == "evaluate_ci_monitor"
        and evaluated
        and pr_was_created
        and pr_evidence_clean
        and pr_number is not None
        and bool(pr_url)
        and pr_safe
        and repository_safe
        and branch_safe
        and base_safe
        and head_sha_safe
        and providers_safe
        and workflows_safe
        and checks_safe
        and not secret_detected
    )
    required_checks = _required_checks()
    plan = _ci_monitor_plan(
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        expected_ci_providers=providers,
        expected_workflows=workflows,
        expected_required_checks=checks,
        eligible=eligible,
        requires_human=bool(blocked_reason or merged_pr_detected or closed_pr_detected or protected_branch_detected),
        risk_level=_risk_level(
            eligible=eligible,
            secret_detected=secret_detected,
            protected_branch_detected=protected_branch_detected,
            main_head_detected=main_head_detected,
            unsafe_repository_detected=unsafe_repository_detected,
            pr_safe=pr_safe,
        ),
        required_checks=required_checks,
    )
    blocked = bool(blocked_reason)
    success = bool(evaluated and not blocked)
    requires_human = bool(
        blocked
        or secret_detected
        or protected_branch_detected
        or main_head_detected
        or unsafe_repository_detected
        or merged_pr_detected
        or closed_pr_detected
    )
    runtime_truth = build_ci_monitor_gate_evidence(
        ci_monitor_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=bool(pr_draft) if pr_draft is not None else None,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        base_sha=base_sha,
        merge_commit_sha=merge_commit_sha,
        commit_sha=commit_sha,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        ci_monitor_eligible=eligible,
        ci_monitor_ready_metadata_only=eligible,
        pr_was_created=pr_was_created,
        pr_evidence_clean=pr_evidence_clean,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        expected_ci_providers_safe=providers_safe,
        expected_workflows_safe=workflows_safe,
        expected_required_checks_safe=checks_safe,
        secrets_detected=secret_detected,
        protected_branch_detected=protected_branch_detected,
        main_head_detected=main_head_detected,
        merged_pr_detected=merged_pr_detected,
        closed_pr_detected=closed_pr_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()
    return CIMonitorGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        ci_monitor_eligible=eligible,
        ci_monitor_ready_metadata_only=eligible,
        ci_monitor_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=bool(pr_draft) if pr_draft is not None else None,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        base_sha=base_sha,
        merge_commit_sha=merge_commit_sha,
        commit_sha=commit_sha,
        pr_was_created=pr_was_created,
        pr_evidence_clean=pr_evidence_clean,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        expected_ci_providers_safe=providers_safe,
        expected_workflows_safe=workflows_safe,
        expected_required_checks_safe=checks_safe,
        secrets_detected=secret_detected,
        protected_branch_detected=protected_branch_detected,
        main_head_detected=main_head_detected,
        merged_pr_detected=merged_pr_detected,
        closed_pr_detected=closed_pr_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        ci_monitor_plan=plan,
        required_pre_ci_monitor_checks=required_checks,
        can_monitor_ci=False,
        can_call_github_api=False,
        can_call_circleci_api=False,
        can_download_logs=False,
        can_retry_workflows=False,
        can_start_repair_loop=False,
        can_update_pr=False,
        can_merge=False,
        can_auto_merge=False,
        can_push=False,
        can_force_push=False,
        can_push_main=False,
        can_rebase=False,
        can_create_branch=False,
        can_checkout=False,
        can_edit_code=False,
        can_apply_patch=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        requires_ci_monitor_executor_phase=eligible,
        requires_repair_loop_gate_phase=False,
        requires_merge_gate_phase=False,
        requires_human_intervention=requires_human,
        reason=_reason(eligible=eligible, dry_run=dry_run, blocked_reason=blocked_reason),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=CI_MONITOR_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _blocked_reason(
    *,
    request: CIMonitorGateRequest,
    mode: str,
    pr_creator: Mapping[str, Any],
    pr_gate: Mapping[str, Any],
    push_executor: Mapping[str, Any],
    pr_creator_truth: Mapping[str, Any],
    pr_gate_truth: Mapping[str, Any],
    push_executor_truth: Mapping[str, Any],
    secret_detected: bool,
    pr_was_created: bool,
    pr_evidence_clean: bool,
    pr_number: int | None,
    pr_url: str | None,
    pr_safe: bool,
    repository_safe: bool,
    branch_safe: bool,
    base_safe: bool,
    head_sha_safe: bool,
    providers_safe: bool,
    workflows_safe: bool,
    checks_safe: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in CI_MONITOR_GATE_MODES:
        return "CI monitor gate mode is unknown."
    if mode == "disabled":
        return "CI monitor gate is disabled by default."
    if mode == "blocked":
        return "CI monitor gate mode blocks all CI monitor eligibility."
    if any(
        (
            request.allow_ci_monitoring,
            request.allow_github_api,
            request.allow_circleci_api,
            request.allow_log_download,
            request.allow_workflow_retry,
            request.allow_repair_loop,
            request.allow_merge,
            request.allow_auto_merge,
            request.allow_pr_update,
            request.allow_push,
            request.allow_force_push,
            request.allow_main_push,
            request.allow_git_mutation,
            request.allow_command_execution,
            request.allow_network,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 29 cannot enable CI APIs, monitoring, repair, merge, push, Git mutation, command, network, provider, or agent capabilities."
    if request.require_pr_created and not pr_creator:
        return "Phase 28 PR creator evidence is required."
    if pr_creator.get("blocked") is True:
        return "Phase 28 PR creator result is blocked."
    if pr_creator.get("requires_human_intervention") is True:
        return "Phase 28 PR creator requires human intervention."
    if pr_creator.get("success") is False:
        return "Phase 28 PR creator was not successful."
    if request.require_runtime_truth and pr_creator and not pr_creator_truth:
        return "Phase 28 Runtime Truth is required."
    if request.require_clean_pr_evidence and _pr_creator_truth_unsafe(pr_creator_truth):
        return "Phase 28 Runtime Truth reports unsafe PR evidence."
    if request.require_pr_created and not pr_was_created:
        return "Phase 28 PR creator did not create a PR."
    if request.require_clean_pr_evidence and not pr_evidence_clean:
        return "Phase 28 PR evidence is not clean."
    if request.require_pr_created and pr_number is None:
        return "pr_number is required."
    if request.require_pr_created and not pr_url:
        return "pr_url is required."
    if not pr_safe:
        return "PR state metadata is unsafe for CI monitoring."
    if request.require_repository_safe and not repository_safe:
        return "repository_full_name metadata is unsafe."
    if not branch_safe:
        return "source_branch or head_branch metadata is unsafe."
    if not base_safe:
        return "base_branch must be main."
    if request.require_head_sha and not head_sha_safe:
        return "head_sha or commit_sha metadata is required and must be safe."
    if not providers_safe:
        return "CI provider metadata is unsafe."
    if not workflows_safe:
        return "CI workflow metadata is unsafe."
    if not checks_safe:
        return "Required check metadata is unsafe."
    if pr_gate:
        if pr_gate.get("pr_eligible") is False:
            return "Phase 27 PR creation gate did not mark this branch eligible."
        if pr_gate.get("blocked") is True:
            return "Phase 27 PR creation gate is blocked."
        if pr_gate.get("requires_human_intervention") is True:
            return "Phase 27 PR creation gate requires human intervention."
        if request.require_runtime_truth and not pr_gate_truth:
            return "Phase 27 Runtime Truth is required when PR gate evidence is provided."
        if _pr_gate_truth_unsafe(pr_gate_truth):
            return "Phase 27 Runtime Truth reports unsafe PR gate evidence."
    if push_executor:
        if request.require_clean_pr_evidence and push_executor.get("pushed") is not True:
            return "Phase 26 push executor did not push a branch."
        if push_executor.get("success") is not True:
            return "Phase 26 push executor was not successful."
        if _push_executor_truth_unsafe(push_executor_truth):
            return "Phase 26 Runtime Truth reports unsafe push evidence."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if request.metadata.get("source_main") is True:
        return "source_main metadata is blocked."
    if request.metadata.get("base_not_main") is True:
        return "base_not_main metadata is blocked."
    if request.metadata.get("locked") is True:
        return "locked PR metadata requires human intervention."
    if request.metadata.get("repository_archived") is True:
        return "archived repository metadata requires human intervention."
    return None


def _pr_creator_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "pr_merged",
        "auto_merge_enabled",
        "approval_submitted",
        "push_executed",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    )
    return any(truth.get(key) is True for key in unsafe_keys)


def _pr_gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "pr_created",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "main_modified",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    )
    return any(truth.get(key) is True for key in unsafe_keys)


def _push_executor_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "force_push_executed",
        "main_pushed",
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
    )
    return any(truth.get(key) is True for key in unsafe_keys)


def _pr_state_safe(
    request: CIMonitorGateRequest,
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


def _branch_block_reason(
    request: CIMonitorGateRequest,
    source_branch: str | None,
    head_branch: str | None,
) -> str | None:
    if not request.require_non_main_head:
        return None
    source = str(source_branch or "").strip().lower()
    head = str(head_branch or "").strip().lower()
    base = str(request.base_branch or "").strip().lower()
    if not source:
        return "source_branch is required."
    if not head:
        return "head_branch is required."
    if source == MAIN_BRANCH or head == MAIN_BRANCH:
        return "source_branch and head_branch must not be main."
    if source == base or head == base:
        return "source_branch and head_branch must not equal base_branch."
    if _protected_branch(source) or _protected_branch(head):
        return "Protected source or head branch is blocked."
    if not _branch_name_safe(source) or not _branch_name_safe(head):
        return "source_branch or head_branch contains unsafe characters."
    return None


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


def _sanitize_ci_names(values: list[str], *, allowed_providers: bool = False) -> tuple[list[str], bool, bool]:
    sanitized: list[str] = []
    safe = True
    redacted = False
    for value in values:
        text, item_redacted = _redact_text(value)
        lowered = text.lower()
        redacted = redacted or item_redacted
        if item_redacted or not _CI_NAME_PATTERN.fullmatch(text) or _SHELL_CHARS.search(text):
            safe = False
        if "://" in lowered or any(word in lowered for word in _DESTRUCTIVE_CI_WORDS):
            safe = False
        if allowed_providers and lowered not in _ALLOWED_PROVIDERS:
            safe = False
        sanitized.append(text)
    return sanitized, safe, redacted


def _ci_monitor_plan(
    *,
    repository_full_name: str | None,
    pr_number: int | None,
    pr_url: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    commit_sha: str | None,
    expected_ci_providers: list[str],
    expected_workflows: list[str],
    expected_required_checks: list[str],
    eligible: bool,
    requires_human: bool,
    risk_level: str,
    required_checks: list[str],
) -> dict[str, object]:
    return {
        "plan_id": "ci-monitor-plan-1",
        "repository_full_name": repository_full_name,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "head_sha": head_sha,
        "commit_sha": commit_sha,
        "expected_ci_providers": expected_ci_providers,
        "expected_workflows": expected_workflows,
        "expected_required_checks": expected_required_checks,
        "polling_strategy": "bounded_polling",
        "max_poll_attempts": 20,
        "poll_interval_seconds": 30,
        "terminal_success_states": ["success"],
        "terminal_failure_states": ["failure", "cancelled", "timed_out", "action_required"],
        "non_blocking_states": ["skipped", "neutral"],
        "risk_level": risk_level,
        "required_checks_before_execution": required_checks,
        "allowed_in_future_ci_monitoring": eligible,
        "requires_human": requires_human,
    }


def _required_checks() -> list[str]:
    return [
        "pr_creator_succeeded",
        "pr_number_present",
        "pr_url_present",
        "pr_open_or_draft",
        "repository_safe",
        "base_branch_main",
        "head_branch_non_main",
        "head_sha_present",
        "secrets_absent",
        "runtime_truth_clean",
        "no_merge_or_auto_merge",
        "no_repair_loop_started",
    ]


def _risk_level(
    *,
    eligible: bool,
    secret_detected: bool,
    protected_branch_detected: bool,
    main_head_detected: bool,
    unsafe_repository_detected: bool,
    pr_safe: bool,
) -> str:
    if secret_detected or main_head_detected:
        return "critical"
    if protected_branch_detected or unsafe_repository_detected or not pr_safe:
        return "high"
    return "low" if eligible else "medium"


def _reason(*, eligible: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "CI monitor gate blocked this eligibility request."
    if dry_run:
        return "CI monitor gate evaluated evidence in dry-run mode without eligibility."
    if eligible:
        return "CI monitor gate marked this PR eligible for a future CI monitor executor phase."
    return "CI monitor gate did not mark this PR eligible."


def _protected_branch(branch: object) -> bool:
    lowered = str(branch or "").strip().lower()
    return lowered.startswith(_PROTECTED_PREFIXES)


def _branch_name_safe(branch: object) -> bool:
    text = str(branch or "").strip()
    lowered = text.lower()
    if not text or text.startswith(("-", "+", "/", ".")) or text.endswith(("/", ".")):
        return False
    if lowered == MAIN_BRANCH or _protected_branch(lowered):
        return False
    if ".." in text.split("/") or "//" in text or ":" in text or "\\" in text:
        return False
    if any(char in text for char in (" ", "~", "^", "?", "*", "[", "]", "&", "|", ";", "`", "$", "<", ">")):
        return False
    return bool(_BRANCH_PATTERN.fullmatch(text))


def _source_secret(truths: list[Mapping[str, Any]]) -> bool:
    return any(truth.get("secrets_detected") is True for truth in truths)


def _coerce_request(value: CIMonitorGateRequest | Mapping[str, Any] | Any) -> CIMonitorGateRequest:
    if isinstance(value, CIMonitorGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("CI monitor gate input must be a request, mapping, or object.")
    return CIMonitorGateRequest(
        pr_creator_result=_coerce_mapping(payload.get("pr_creator_result")),
        pr_creation_gate_result=_coerce_mapping(payload.get("pr_creation_gate_result")),
        push_executor_result=_coerce_mapping(payload.get("push_executor_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        ci_monitor_gate_mode=str(payload.get("ci_monitor_gate_mode") or DEFAULT_CI_MONITOR_GATE_MODE),
        workspace_root=payload.get("workspace_root"),
        repository_full_name=payload.get("repository_full_name"),
        pr_number=payload.get("pr_number"),
        pr_url=payload.get("pr_url"),
        pr_state=payload.get("pr_state"),
        pr_draft=payload.get("pr_draft"),
        source_branch=payload.get("source_branch"),
        head_branch=payload.get("head_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        head_sha=payload.get("head_sha"),
        base_sha=payload.get("base_sha"),
        merge_commit_sha=payload.get("merge_commit_sha"),
        commit_sha=payload.get("commit_sha"),
        expected_ci_providers=list(payload.get("expected_ci_providers") or ["github_actions", "circleci"]),
        expected_workflows=list(payload.get("expected_workflows") or []),
        expected_required_checks=list(payload.get("expected_required_checks") or []),
        allowed_statuses=list(payload.get("allowed_statuses") or CIMonitorGateRequest().allowed_statuses),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_pr_created=bool(payload.get("require_pr_created", True)),
        require_pr_open=bool(payload.get("require_pr_open", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_pr_evidence=bool(payload.get("require_clean_pr_evidence", True)),
        require_head_sha=bool(payload.get("require_head_sha", True)),
        require_repository_safe=bool(payload.get("require_repository_safe", True)),
        allow_ci_monitoring=bool(payload.get("allow_ci_monitoring", False)),
        allow_github_api=bool(payload.get("allow_github_api", False)),
        allow_circleci_api=bool(payload.get("allow_circleci_api", False)),
        allow_log_download=bool(payload.get("allow_log_download", False)),
        allow_workflow_retry=bool(payload.get("allow_workflow_retry", False)),
        allow_repair_loop=bool(payload.get("allow_repair_loop", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_auto_merge=bool(payload.get("allow_auto_merge", False)),
        allow_pr_update=bool(payload.get("allow_pr_update", False)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_force_push=bool(payload.get("allow_force_push", False)),
        allow_main_push=bool(payload.get("allow_main_push", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_command_execution=bool(payload.get("allow_command_execution", False)),
        allow_network=bool(payload.get("allow_network", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
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
