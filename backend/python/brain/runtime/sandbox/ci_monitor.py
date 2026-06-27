"""Controlled CI monitor.

Phase 30 reads CI/check status through narrow injected clients only after clean
Phase 29 CI Monitor Gate evidence. It does not mutate repository state.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping, Protocol

from .ci_monitor_truth import CI_MONITOR_EVIDENCE_VERSION, build_ci_monitor_evidence
from .ci_monitor_types import ControlledCIMonitorRequest, ControlledCIMonitorResult

CI_MONITOR_MODES = frozenset({"disabled", "dry_run", "monitor_ci", "blocked"})
DEFAULT_CI_MONITOR_MODE = "disabled"
MAIN_BRANCH = "main"
EXPECTED_REPOSITORY = "misaeldasilva123ms96-commits/Projeto-Omni"
TERMINAL_STATUSES = {"success", "failure", "cancelled", "skipped", "neutral", "timed_out", "action_required"}
FAIL_STATUSES = {"failure", "cancelled", "timed_out", "action_required"}
PENDING_STATUSES = {"queued", "in_progress", "pending"}
KNOWN_STATUSES = TERMINAL_STATUSES | PENDING_STATUSES | {"unknown"}

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
_ALLOWED_PROVIDERS = {"github_actions"}


class ControlledGitHubActionsClient(Protocol):
    def get_actions_status_snapshot(
        self,
        *,
        repository_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> Mapping[str, Any]:
        """Return a read-only GitHub Actions/checks snapshot."""


def monitor_ci_status(
    request_or_mapping: ControlledCIMonitorRequest | Mapping[str, Any] | Any,
    *,
    github_actions_client: ControlledGitHubActionsClient | None = None,
) -> ControlledCIMonitorResult:
    request = _coerce_request(request_or_mapping)
    gate = _coerce_mapping(request.ci_monitor_gate_result)
    pr_creator = _coerce_mapping(request.pr_creator_result)
    pr_gate = _coerce_mapping(request.pr_creation_gate_result)
    gate_truth = _coerce_mapping(gate.get("runtime_truth"))
    pr_creator_truth = _coerce_mapping(pr_creator.get("runtime_truth"))
    pr_gate_truth = _coerce_mapping(pr_gate.get("runtime_truth"))
    mode = str(request.monitor_mode or DEFAULT_CI_MONITOR_MODE).strip() or DEFAULT_CI_MONITOR_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    plan = _coerce_mapping(gate.get("ci_monitor_plan"))
    repository, repository_redacted = _redact_optional(
        request.repository_full_name
        or gate.get("repository_full_name")
        or pr_creator.get("repository_full_name")
        or plan.get("repository_full_name")
    )
    pr_number = _optional_int(request.pr_number if request.pr_number is not None else gate.get("pr_number") or pr_creator.get("pr_number"))
    pr_url, pr_url_redacted = _redact_optional(request.pr_url or gate.get("pr_url") or pr_creator.get("pr_url"))
    pr_state, pr_state_redacted = _redact_optional(request.pr_state or gate.get("pr_state") or pr_creator.get("pr_state") or "open")
    pr_draft = request.pr_draft if request.pr_draft is not None else gate.get("pr_draft") if gate else pr_creator.get("final_draft")
    source_branch, source_redacted = _redact_optional(request.source_branch or gate.get("source_branch") or pr_creator.get("source_branch"))
    head_branch, head_redacted = _redact_optional(request.head_branch or gate.get("head_branch") or pr_creator.get("head_branch") or source_branch)
    base_branch = str(request.base_branch or gate.get("base_branch") or pr_creator.get("base_branch") or MAIN_BRANCH)
    commit_sha, commit_sha_redacted = _redact_optional(request.commit_sha or gate.get("commit_sha") or pr_creator.get("commit_sha"))
    head_sha, head_sha_redacted = _redact_optional(request.head_sha or gate.get("head_sha") or commit_sha)
    providers, providers_safe, providers_redacted = _sanitize_names(request.expected_ci_providers, providers=True)
    workflows, workflows_safe, workflows_redacted = _sanitize_names(request.expected_workflows)
    required_checks, checks_safe, checks_redacted = _sanitize_names(request.expected_required_checks)
    child_truths = [truth for truth in (gate_truth, pr_creator_truth, pr_gate_truth) if truth]

    repository_safe = _repository_safe(repository, request.metadata)
    pr_safe = _pr_state_safe(request, pr_state)
    branch_safe = _branch_safe(request, source_branch, head_branch, base_branch)
    base_safe = not request.require_base_main or base_branch.strip().lower() == MAIN_BRANCH
    head_sha_safe = _sha_safe(head_sha) if request.require_head_sha else True
    ci_monitor_gate_eligible = bool(gate.get("ci_monitor_eligible") is True)
    pr_was_created = bool(pr_creator.get("pr_created") is True or gate.get("pr_was_created") is True)
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            related_pr_redacted,
            repository_redacted,
            pr_url_redacted,
            pr_state_redacted,
            source_redacted,
            head_redacted,
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
        gate=gate,
        pr_creator=pr_creator,
        pr_gate=pr_gate,
        gate_truth=gate_truth,
        pr_creator_truth=pr_creator_truth,
        pr_gate_truth=pr_gate_truth,
        secret_detected=secret_detected,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        providers_safe=providers_safe,
        workflows_safe=workflows_safe,
        checks_safe=checks_safe,
        ci_monitor_gate_eligible=ci_monitor_gate_eligible,
        pr_was_created=pr_was_created,
        pr_number=pr_number,
        pr_url=pr_url,
        github_actions_client=github_actions_client,
        providers=providers,
    )
    if mode == "dry_run" and not blocked_reason:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_state=pr_state,
            pr_draft=bool(pr_draft) if pr_draft is not None else None,
            source_branch=source_branch,
            head_branch=head_branch,
            base_branch=base_branch,
            head_sha=head_sha,
            commit_sha=commit_sha,
            gate=gate,
            pr_was_created=pr_was_created,
            attempted=[],
            completed=[],
            blocked_ops=[],
            checks=[],
            workflows=[],
            required_checks=required_checks,
            github_status={},
            blocked=False,
            dry_run=True,
            partial=False,
            success=True,
            reason="Controlled CI monitor dry run completed without client calls.",
            blocked_reason=None,
            redacted=secret_detected,
            child_truths=child_truths,
        )
    if blocked_reason:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_state=pr_state,
            pr_draft=bool(pr_draft) if pr_draft is not None else None,
            source_branch=source_branch,
            head_branch=head_branch,
            base_branch=base_branch,
            head_sha=head_sha,
            commit_sha=commit_sha,
            gate=gate,
            pr_was_created=pr_was_created,
            attempted=[],
            completed=[],
            blocked_ops=["ci_status_snapshot"],
            checks=[],
            workflows=[],
            required_checks=required_checks,
            github_status={},
            blocked=True,
            dry_run=False,
            partial=False,
            success=False,
            reason="Controlled CI monitor blocked this request.",
            blocked_reason=blocked_reason,
            redacted=secret_detected,
            child_truths=child_truths,
        )

    attempted: list[str] = []
    completed: list[str] = []
    checks: list[dict[str, object]] = []
    workflows_seen: list[dict[str, object]] = []
    github_status: dict[str, object] = {}
    errors: list[str] = []

    if "github_actions" in providers:
        attempted.append("github_actions_status_snapshot")
        try:
            github_status, github_redacted = _sanitize_snapshot(
                github_actions_client.get_actions_status_snapshot(  # type: ignore[union-attr]
                    repository_full_name=str(repository),
                    pr_number=int(pr_number),
                    head_sha=str(head_sha),
                )
            )
            completed.append("github_actions_status_snapshot")
            checks.extend(_normalize_checks(github_status, "github_actions", required_checks))
            workflows_seen.extend(_normalize_workflows(github_status, "github_actions"))
            secret_detected = secret_detected or github_redacted
        except Exception as exc:  # noqa: BLE001 - injected read client failure becomes partial evidence.
            errors.append(_redact_text(str(exc))[0])
    if secret_detected:
        checks = []
        workflows_seen = []
        completed = []
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_state=pr_state,
            pr_draft=bool(pr_draft) if pr_draft is not None else None,
            source_branch=source_branch,
            head_branch=head_branch,
            base_branch=base_branch,
            head_sha=head_sha,
            commit_sha=commit_sha,
            gate=gate,
            pr_was_created=pr_was_created,
            attempted=attempted,
            completed=completed,
            blocked_ops=["ci_status_snapshot"],
            checks=[],
            workflows=[],
            required_checks=required_checks,
            github_status={},
            blocked=True,
            dry_run=False,
            partial=False,
            success=False,
            reason="Controlled CI monitor blocked this request.",
            blocked_reason="Secret-like content was detected and redacted.",
            redacted=True,
            child_truths=child_truths,
        )

    partial = bool(errors or (attempted and len(completed) < len(attempted)))
    return _result(
        request=request,
        mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=bool(pr_draft) if pr_draft is not None else None,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        gate=gate,
        pr_was_created=pr_was_created,
        attempted=attempted,
        completed=completed,
        blocked_ops=[],
        checks=checks,
        workflows=workflows_seen,
        required_checks=required_checks,
        github_status=github_status,
        blocked=False,
        dry_run=False,
        partial=partial,
        success=bool(completed),
        reason="Controlled CI monitor captured a read-only status snapshot.",
        blocked_reason="; ".join(errors) if errors and not completed else None,
        redacted=secret_detected,
        child_truths=child_truths,
    )


def _blocked_reason(
    *,
    request: ControlledCIMonitorRequest,
    mode: str,
    gate: Mapping[str, Any],
    pr_creator: Mapping[str, Any],
    pr_gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    pr_creator_truth: Mapping[str, Any],
    pr_gate_truth: Mapping[str, Any],
    secret_detected: bool,
    repository_safe: bool,
    pr_safe: bool,
    branch_safe: bool,
    base_safe: bool,
    head_sha_safe: bool,
    providers_safe: bool,
    workflows_safe: bool,
    checks_safe: bool,
    ci_monitor_gate_eligible: bool,
    pr_was_created: bool,
    pr_number: int | None,
    pr_url: str | None,
    github_actions_client: ControlledGitHubActionsClient | None,
    providers: list[str],
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in CI_MONITOR_MODES:
        return "CI monitor mode is unknown."
    if mode == "disabled":
        return "CI monitor is disabled by default."
    if mode == "blocked":
        return "CI monitor mode blocks all monitoring."
    if any(
        (
            request.allow_log_download,
            request.allow_workflow_retry,
            request.allow_workflow_trigger,
            request.allow_repair_loop,
            request.allow_pr_update,
            request.allow_merge,
            request.allow_auto_merge,
            request.allow_push,
            request.allow_git_mutation,
            request.allow_command_execution,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 30 cannot enable logs, retries, triggers, repair, PR updates, merge, push, Git mutation, commands, providers, or agents."
    if not request.allow_ci_monitoring:
        return "CI monitoring is not allowed by request policy."
    if request.require_ci_monitor_gate_eligible and not gate:
        return "Phase 29 CI Monitor Gate evidence is required."
    if gate.get("blocked") is True:
        return "Phase 29 CI Monitor Gate is blocked."
    if gate.get("requires_human_intervention") is True:
        return "Phase 29 CI Monitor Gate requires human intervention."
    if request.require_ci_monitor_gate_eligible and not ci_monitor_gate_eligible:
        return "Phase 29 CI Monitor Gate did not mark monitoring eligible."
    if request.require_clean_evidence and _gate_truth_unsafe(gate_truth):
        return "Phase 29 Runtime Truth reports unsafe monitor evidence."
    if request.require_pr_created:
        if pr_creator and pr_creator.get("success") is not True:
            return "Phase 28 PR creator was not successful."
        if pr_creator and pr_creator.get("pr_created") is not True:
            return "Phase 28 PR creator did not create a PR."
        if not pr_was_created:
            return "Created PR evidence is required."
    if request.require_runtime_truth and pr_creator and not pr_creator_truth:
        return "Phase 28 Runtime Truth is required when PR creator evidence is provided."
    if request.require_clean_evidence and _pr_creator_truth_unsafe(pr_creator_truth):
        return "Phase 28 Runtime Truth reports unsafe PR creator evidence."
    if pr_gate:
        if pr_gate.get("blocked") is True:
            return "Phase 27 PR gate is blocked."
        if request.require_clean_evidence and _pr_gate_truth_unsafe(pr_gate_truth):
            return "Phase 27 Runtime Truth reports unsafe PR gate evidence."
    if pr_number is None:
        return "pr_number is required."
    if not pr_url:
        return "pr_url is required."
    if not pr_safe:
        return "PR state metadata is unsafe for monitoring."
    if not repository_safe:
        return "repository_full_name metadata is unsafe."
    if not branch_safe:
        return "source_branch or head_branch metadata is unsafe."
    if not base_safe:
        return "base_branch must be main."
    if not head_sha_safe:
        return "head_sha or commit_sha metadata is required and must be safe."
    if not providers_safe or not workflows_safe or not checks_safe:
        return "CI provider, workflow, or required check metadata is unsafe."
    if request.metadata.get("locked") is True or request.metadata.get("repository_archived") is True:
        return "PR lock or archived repository metadata requires human intervention."
    if "github_actions" in providers and request.allow_github_actions_read and github_actions_client is None and mode == "monitor_ci":
        return "A GitHub Actions read client is required."
    return None


def _result(
    *,
    request: ControlledCIMonitorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    repository: str | None,
    pr_number: int | None,
    pr_url: str | None,
    pr_state: str | None,
    pr_draft: bool | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    commit_sha: str | None,
    gate: Mapping[str, Any],
    pr_was_created: bool,
    attempted: list[str],
    completed: list[str],
    blocked_ops: list[str],
    checks: list[dict[str, object]],
    workflows: list[dict[str, object]],
    required_checks: list[str],
    github_status: dict[str, object],
    blocked: bool,
    dry_run: bool,
    partial: bool,
    success: bool,
    reason: str,
    blocked_reason: str | None,
    redacted: bool,
    child_truths: list[Mapping[str, Any]],
) -> ControlledCIMonitorResult:
    summary = _summarize_checks(checks, required_checks, blocked)
    monitored = bool(completed and not blocked)
    requires_human = bool(blocked or redacted or pr_state in {"closed", "merged"})
    runtime_truth = build_ci_monitor_evidence(
        monitor_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=pr_draft,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        monitored=monitored,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        ci_monitor_gate_eligible=bool(gate.get("ci_monitor_eligible") is True),
        pr_was_created=pr_was_created,
        aggregate_status=str(summary["aggregate_status"]),
        aggregate_conclusion=str(summary["aggregate_conclusion"]),
        terminal=bool(summary["terminal"]),
        passed=bool(summary["passed"]),
        failed=bool(summary["failed"]),
        pending=bool(summary["pending"]),
        cancelled=bool(summary["cancelled"]),
        timed_out=bool(summary["timed_out"]),
        action_required=bool(summary["action_required"]),
        checks_observed_count=len(checks),
        workflows_observed_count=len(workflows),
        missing_required_checks_count=len(summary["missing_required_checks"]),
        failing_checks_count=len(summary["failing_checks"]),
        pending_checks_count=len(summary["pending_checks"]),
        successful_checks_count=len(summary["successful_checks"]),
        unknown_checks_count=len(summary["unknown_checks"]),
        ci_status_fetched=monitored,
        workflow_runs_fetched=bool(monitored and workflows),
        check_runs_fetched=bool(monitored and checks),
        github_actions_read="github_actions_status_snapshot" in completed,
        secrets_detected=redacted,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()
    return ControlledCIMonitorResult(
        monitored=monitored,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        partial=partial,
        monitor_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=pr_draft,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        ci_monitor_gate_eligible=bool(gate.get("ci_monitor_eligible") is True),
        pr_was_created=pr_was_created,
        ci_status_summary=summary,
        aggregate_status=str(summary["aggregate_status"]),
        aggregate_conclusion=str(summary["aggregate_conclusion"]),
        github_actions_status=github_status,
        checks_observed=checks,
        workflows_observed=workflows,
        required_checks_observed=list(summary["required_checks_observed"]),
        missing_required_checks=list(summary["missing_required_checks"]),
        failing_checks=list(summary["failing_checks"]),
        pending_checks=list(summary["pending_checks"]),
        skipped_or_neutral_checks=list(summary["skipped_or_neutral_checks"]),
        successful_checks=list(summary["successful_checks"]),
        unknown_checks=list(summary["unknown_checks"]),
        terminal=bool(summary["terminal"]),
        passed=bool(summary["passed"]),
        failed=bool(summary["failed"]),
        pending=bool(summary["pending"]),
        cancelled=bool(summary["cancelled"]),
        timed_out=bool(summary["timed_out"]),
        action_required=bool(summary["action_required"]),
        logs_downloaded=False,
        workflow_retried=False,
        repair_loop_started=False,
        ci_operations_attempted=attempted,
        ci_operations_completed=completed,
        ci_operations_blocked=blocked_ops,
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
        requires_repair_loop_gate_phase=bool(summary["failed"]),
        requires_merge_gate_phase=bool(summary["passed"]),
        requires_human_intervention=requires_human,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=CI_MONITOR_EVIDENCE_VERSION,
        redacted=redacted,
    )


def _summarize_checks(checks: list[dict[str, object]], required_checks: list[str], blocked: bool) -> dict[str, object]:
    required_names = set(required_checks)
    observed_names = {str(check["name"]) for check in checks}
    required_observed = [check for check in checks if check["required"] or str(check["name"]) in required_names]
    missing = sorted(required_names - observed_names)
    failing = [check for check in required_observed if check["status"] in FAIL_STATUSES]
    pending = [check for check in required_observed if check["status"] in PENDING_STATUSES]
    successful = [check for check in required_observed if check["status"] == "success"]
    skipped_or_neutral = [check for check in checks if check["status"] in {"skipped", "neutral"}]
    unknown = [check for check in required_observed if check["status"] == "unknown"]
    cancelled = any(check["status"] == "cancelled" for check in required_observed)
    timed_out = any(check["status"] == "timed_out" for check in required_observed)
    action_required = any(check["status"] == "action_required" for check in required_observed)
    failed = bool(failing or missing or (unknown and not pending))
    is_pending = bool(pending) and not failed
    passed = bool(required_observed or required_names) and not failed and not is_pending and not unknown and not missing
    if blocked:
        aggregate_status = "unknown"
        conclusion = "blocked"
    elif failed:
        aggregate_status = "failure"
        conclusion = "failed"
    elif is_pending:
        aggregate_status = "pending"
        conclusion = "pending"
    elif passed:
        aggregate_status = "success"
        conclusion = "passed"
    elif checks:
        aggregate_status = "partial"
        conclusion = "inconclusive"
    else:
        aggregate_status = "unknown"
        conclusion = "inconclusive"
    terminal = bool(checks) and not is_pending and not unknown and not blocked
    return {
        "aggregate_status": aggregate_status,
        "aggregate_conclusion": conclusion,
        "required_checks_observed": required_observed,
        "missing_required_checks": missing,
        "failing_checks": failing,
        "pending_checks": pending,
        "successful_checks": successful,
        "skipped_or_neutral_checks": skipped_or_neutral,
        "unknown_checks": unknown,
        "terminal": terminal,
        "passed": passed,
        "failed": failed,
        "pending": is_pending,
        "cancelled": cancelled,
        "timed_out": timed_out,
        "action_required": action_required,
    }


def _normalize_checks(snapshot: Mapping[str, Any], provider: str, required_checks: list[str]) -> list[dict[str, object]]:
    raw_checks = list(snapshot.get("checks") or snapshot.get("check_runs") or snapshot.get("statuses") or [])
    normalized: list[dict[str, object]] = []
    for item in raw_checks:
        if not isinstance(item, Mapping):
            continue
        name, redacted = _redact_text(item.get("name") or item.get("workflow") or item.get("context") or "unknown")
        status = _normalize_status(item.get("status") or item.get("conclusion") or item.get("state"))
        required = bool(item.get("required") or name in required_checks)
        blocking = bool(required and status not in {"success", "skipped", "neutral"})
        url, _ = _redact_optional(item.get("url") or item.get("html_url") or item.get("details_url"))
        normalized.append(
            {
                "name": name,
                "provider": provider,
                "status": status,
                "conclusion": _status_conclusion(status, required),
                "required": required,
                "blocking": blocking,
                "url": url,
                "started_at": item.get("started_at"),
                "completed_at": item.get("completed_at"),
                "redacted": redacted,
            }
        )
    return normalized


def _normalize_workflows(snapshot: Mapping[str, Any], provider: str) -> list[dict[str, object]]:
    raw_workflows = list(snapshot.get("workflows") or snapshot.get("workflow_runs") or [])
    workflows: list[dict[str, object]] = []
    for item in raw_workflows:
        if not isinstance(item, Mapping):
            continue
        name, redacted = _redact_text(item.get("name") or item.get("workflow") or "unknown")
        workflows.append(
            {
                "name": name,
                "provider": provider,
                "status": _normalize_status(item.get("status") or item.get("conclusion")),
                "url": _redact_optional(item.get("url") or item.get("html_url"))[0],
                "redacted": redacted,
            }
        )
    return workflows


def _normalize_status(value: object) -> str:
    status = str(value or "unknown").strip().lower().replace("-", "_")
    aliases = {"completed": "success", "passed": "success", "errored": "failure", "running": "in_progress"}
    status = aliases.get(status, status)
    return status if status in KNOWN_STATUSES else "unknown"


def _status_conclusion(status: str, required: bool) -> str:
    if status == "success":
        return "passed"
    if status in FAIL_STATUSES and required:
        return "failed"
    if status in PENDING_STATUSES:
        return "pending"
    if status in {"skipped", "neutral"}:
        return "inconclusive"
    return "inconclusive"


def _sanitize_snapshot(snapshot: Mapping[str, Any]) -> tuple[dict[str, object], bool]:
    safe: dict[str, object] = {}
    redacted = False
    for key in ("checks", "check_runs", "statuses", "workflows", "workflow_runs"):
        values = snapshot.get(key)
        if not isinstance(values, list):
            continue
        safe_values: list[object] = []
        for item in values[:50]:
            if isinstance(item, Mapping):
                safe_item: dict[str, object] = {}
                for item_key in ("name", "workflow", "context", "status", "conclusion", "state", "required", "url", "html_url", "details_url", "started_at", "completed_at"):
                    if item_key not in item:
                        continue
                    value = item[item_key]
                    if isinstance(value, str):
                        clean, item_redacted = _redact_text(value[:500])
                        safe_item[item_key] = clean
                        redacted = redacted or item_redacted
                    else:
                        safe_item[item_key] = value
                safe_values.append(safe_item)
        safe[key] = safe_values
    return safe, redacted


def _gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    keys = (
        "secrets_detected",
        "ci_monitored",
        "ci_status_fetched",
        "workflow_runs_fetched",
        "check_runs_fetched",
        "logs_downloaded",
        "workflow_retried",
        "repair_loop_started",
        "pr_updated",
        "pr_merged",
        "auto_merge_enabled",
        "push_executed",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
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
    keys = ("secrets_detected", "pr_merged", "auto_merge_enabled", "push_executed", "main_modified", "provider_called", "mcp_used")
    return any(truth.get(key) is True for key in keys)


def _pr_state_safe(request: ControlledCIMonitorRequest, pr_state: str | None) -> bool:
    state = str(pr_state or "").strip().lower()
    if state in {"closed", "merged"}:
        return False
    if request.require_pr_open and state != "open":
        return False
    return True


def _branch_safe(request: ControlledCIMonitorRequest, source_branch: str | None, head_branch: str | None, base_branch: str) -> bool:
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


def _repository_safe(repository: str | None, metadata: Mapping[str, Any]) -> bool:
    if not repository or _contains_credential_like(repository) or _SHELL_CHARS.search(repository):
        return False
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        return False
    expected = str(metadata.get("expected_repository") or EXPECTED_REPOSITORY)
    if repository != expected and metadata.get("allow_unexpected_repository") is not True:
        return False
    return True


def _sha_safe(value: str | None) -> bool:
    return bool(value and _SHA_PATTERN.fullmatch(value) and not _contains_credential_like(value) and not _SHELL_CHARS.search(value))


def _sanitize_names(values: list[str], *, providers: bool = False) -> tuple[list[str], bool, bool]:
    sanitized: list[str] = []
    safe = True
    redacted = False
    for value in values:
        text, item_redacted = _redact_text(value)
        lowered = text.lower()
        redacted = redacted or item_redacted
        if item_redacted or not _NAME_PATTERN.fullmatch(text) or _SHELL_CHARS.search(text) or "://" in lowered:
            safe = False
        if providers and lowered not in _ALLOWED_PROVIDERS:
            safe = False
        sanitized.append(text)
    return sanitized, safe, redacted


def _source_secret(truths: list[Mapping[str, Any]]) -> bool:
    return any(truth.get("secrets_detected") is True for truth in truths)


def _coerce_request(value: ControlledCIMonitorRequest | Mapping[str, Any] | Any) -> ControlledCIMonitorRequest:
    if isinstance(value, ControlledCIMonitorRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("CI monitor input must be a request, mapping, or object.")
    return ControlledCIMonitorRequest(
        ci_monitor_gate_result=_coerce_mapping(payload.get("ci_monitor_gate_result")),
        pr_creator_result=_coerce_mapping(payload.get("pr_creator_result")),
        pr_creation_gate_result=_coerce_mapping(payload.get("pr_creation_gate_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        monitor_mode=str(payload.get("monitor_mode") or DEFAULT_CI_MONITOR_MODE),
        repository_full_name=payload.get("repository_full_name"),
        pr_number=payload.get("pr_number"),
        pr_url=payload.get("pr_url"),
        pr_state=payload.get("pr_state"),
        pr_draft=payload.get("pr_draft"),
        source_branch=payload.get("source_branch"),
        head_branch=payload.get("head_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        head_sha=payload.get("head_sha"),
        commit_sha=payload.get("commit_sha"),
        expected_ci_providers=list(payload.get("expected_ci_providers") or ["github_actions"]),
        expected_workflows=list(payload.get("expected_workflows") or []),
        expected_required_checks=list(payload.get("expected_required_checks") or []),
        polling_strategy=str(payload.get("polling_strategy") or "single_snapshot"),
        max_poll_attempts=int(payload.get("max_poll_attempts", 1)),
        poll_interval_seconds=int(payload.get("poll_interval_seconds", 0)),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_ci_monitor_gate_eligible=bool(payload.get("require_ci_monitor_gate_eligible", True)),
        require_pr_created=bool(payload.get("require_pr_created", True)),
        require_pr_open=bool(payload.get("require_pr_open", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_evidence=bool(payload.get("require_clean_evidence", True)),
        require_head_sha=bool(payload.get("require_head_sha", True)),
        allow_ci_monitoring=bool(payload.get("allow_ci_monitoring", True)),
        allow_github_actions_read=bool(payload.get("allow_github_actions_read", True)),
        allow_log_download=bool(payload.get("allow_log_download", False)),
        allow_workflow_retry=bool(payload.get("allow_workflow_retry", False)),
        allow_workflow_trigger=bool(payload.get("allow_workflow_trigger", False)),
        allow_repair_loop=bool(payload.get("allow_repair_loop", False)),
        allow_pr_update=bool(payload.get("allow_pr_update", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_auto_merge=bool(payload.get("allow_auto_merge", False)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_command_execution=bool(payload.get("allow_command_execution", False)),
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
