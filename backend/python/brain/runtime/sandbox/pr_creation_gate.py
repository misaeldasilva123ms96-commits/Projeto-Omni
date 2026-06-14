"""PR creation eligibility gate.

Phase 27 evaluates whether a pushed non-main branch is eligible for a future
PR creation phase. It produces metadata and Runtime Truth only.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .pr_creation_gate_truth import (
    PR_CREATION_GATE_EVIDENCE_VERSION,
    build_pr_creation_gate_evidence,
)
from .pr_creation_gate_types import PRCreationGateRequest, PRCreationGateResult

PR_GATE_MODES = frozenset({"disabled", "dry_run", "evaluate_pr", "blocked"})
DEFAULT_PR_GATE_MODE = "disabled"
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
_SIMPLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,63}$")
_SHELL_CHARS = re.compile(r"[;&|`$<>]")
_PROTECTED_PREFIXES = ("release/", "prod/", "production/", "protected/")


def evaluate_pr_creation_gate(
    request_or_mapping: PRCreationGateRequest | Mapping[str, Any] | Any,
) -> PRCreationGateResult:
    request = _coerce_request(request_or_mapping)
    push_executor = _coerce_mapping(request.push_executor_result)
    push_gate = _coerce_mapping(request.push_gate_result)
    commit_executor = _coerce_mapping(request.commit_executor_result)
    commit_gate = _coerce_mapping(request.commit_gate_result)
    push_executor_truth = _coerce_mapping(push_executor.get("runtime_truth"))
    push_gate_truth = _coerce_mapping(push_gate.get("runtime_truth"))
    commit_executor_truth = _coerce_mapping(commit_executor.get("runtime_truth"))
    commit_gate_truth = _coerce_mapping(commit_gate.get("runtime_truth"))
    mode = str(request.pr_gate_mode or DEFAULT_PR_GATE_MODE).strip() or DEFAULT_PR_GATE_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(
        request.workspace_root or push_executor.get("workspace_root")
    )
    repository_full_name, repository_redacted = _redact_optional(
        request.repository_full_name or request.metadata.get("repository_full_name")
    )
    source_branch, source_redacted = _redact_optional(request.source_branch)
    head_branch, head_redacted = _redact_optional(request.head_branch)
    current_branch, current_redacted = _redact_optional(
        request.current_branch or push_executor.get("current_branch")
    )
    remote_name, remote_redacted = _redact_text(request.remote_name or push_executor.get("pushed_remote") or "origin")
    remote_branch, remote_branch_redacted = _redact_optional(
        request.remote_branch or push_executor.get("remote_branch")
    )
    pushed_ref, pushed_ref_redacted = _redact_optional(
        request.pushed_ref or push_executor.get("pushed_ref")
    )
    pushed_remote, pushed_remote_redacted = _redact_optional(
        request.pushed_remote or push_executor.get("pushed_remote")
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha or push_executor.get("commit_sha")
    )
    title, title_redacted = _proposed_title(request, source_branch)
    body, body_redacted = _proposed_body(request, push_executor, push_gate)
    labels, labels_safe, labels_redacted = _sanitize_labels(request.labels)
    reviewers, reviewers_safe, reviewers_redacted = _sanitize_logins(request.reviewers)
    assignees, assignees_safe, assignees_redacted = _sanitize_logins(request.assignees)
    title_safe = not title_redacted and bool(title)
    body_safe = not body_redacted and bool(body)

    child_truths = [
        truth
        for truth in (
            push_executor_truth,
            push_gate_truth,
            commit_executor_truth,
            commit_gate_truth,
        )
        if truth
    ]
    protected_branch_detected = any(
        _protected_branch(branch)
        for branch in (source_branch, head_branch, current_branch, remote_branch)
    )
    main_source_branch_detected = any(
        str(branch or "").strip().lower() == MAIN_BRANCH
        for branch in (source_branch, head_branch, current_branch, remote_branch)
    )
    base_safe = _base_safe(request)
    branch_safe = not _branch_block_reason(
        request=request,
        source_branch=source_branch,
        head_branch=head_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
    )
    repository_safe, unsafe_repository_detected = _repository_safe(repository_full_name, request.metadata)
    duplicate_pr_risk = bool(request.metadata.get("duplicate_pr_risk") is True)
    push_was_executed = bool(push_executor.get("pushed") is True)
    push_evidence_clean = bool(
        push_was_executed
        and push_executor.get("success") is True
        and push_executor.get("blocked") is not True
        and not _push_executor_truth_unsafe(push_executor_truth)
    )
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            related_pr_redacted,
            workspace_redacted,
            repository_redacted,
            source_redacted,
            head_redacted,
            current_redacted,
            remote_redacted,
            remote_branch_redacted,
            pushed_ref_redacted,
            pushed_remote_redacted,
            commit_sha_redacted,
            title_redacted,
            body_redacted,
            labels_redacted,
            reviewers_redacted,
            assignees_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            _source_secret(child_truths),
        )
    )
    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        push_executor=push_executor,
        push_gate=push_gate,
        push_executor_truth=push_executor_truth,
        push_gate_truth=push_gate_truth,
        secret_detected=secret_detected,
        branch_safe=branch_safe,
        base_safe=base_safe,
        repository_safe=repository_safe,
        title_safe=title_safe,
        body_safe=body_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        duplicate_pr_risk=duplicate_pr_risk,
        push_was_executed=push_was_executed,
        push_evidence_clean=push_evidence_clean,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
    )
    dry_run = mode == "dry_run" and not blocked_reason
    evaluated = mode in {"dry_run", "evaluate_pr"} and not blocked_reason
    pr_eligible = bool(
        mode == "evaluate_pr"
        and evaluated
        and push_evidence_clean
        and branch_safe
        and base_safe
        and repository_safe
        and title_safe
        and body_safe
        and labels_safe
        and reviewers_safe
        and assignees_safe
        and not duplicate_pr_risk
        and not secret_detected
        and not protected_branch_detected
        and not main_source_branch_detected
    )
    checks = _required_checks()
    pr_plan = _pr_plan(
        repository_full_name=repository_full_name,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=request.base_branch,
        commit_sha=commit_sha,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        title=title,
        body=body,
        draft=True,
        labels=labels,
        reviewers=reviewers,
        assignees=assignees,
        risk_level=_risk_level(
            pr_eligible=pr_eligible,
            secret_detected=secret_detected,
            protected_branch_detected=protected_branch_detected,
            main_source_branch_detected=main_source_branch_detected,
            unsafe_repository_detected=unsafe_repository_detected,
            duplicate_pr_risk=duplicate_pr_risk,
        ),
        required_checks=checks,
        eligible=pr_eligible,
        requires_human=bool(blocked_reason or duplicate_pr_risk or protected_branch_detected),
    )
    blocked = bool(blocked_reason)
    success = bool(evaluated and not blocked)
    requires_human = bool(
        blocked
        or secret_detected
        or duplicate_pr_risk
        or protected_branch_detected
        or main_source_branch_detected
        or unsafe_repository_detected
    )
    runtime_truth = build_pr_creation_gate_evidence(
        pr_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository_full_name,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=request.base_branch,
        current_branch=current_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        pr_eligible=pr_eligible,
        pr_ready_metadata_only=pr_eligible,
        push_was_executed=push_was_executed,
        push_evidence_clean=push_evidence_clean,
        branch_safe=branch_safe,
        base_safe=base_safe,
        repository_safe=repository_safe,
        title_safe=title_safe,
        body_safe=body_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        secrets_detected=secret_detected,
        protected_branch_detected=protected_branch_detected,
        main_source_branch_detected=main_source_branch_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        duplicate_pr_risk=duplicate_pr_risk,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=[dict(truth) for truth in child_truths],
    ).to_dict()
    return PRCreationGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        pr_eligible=pr_eligible,
        pr_ready_metadata_only=pr_eligible,
        pr_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository_full_name,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=request.base_branch,
        current_branch=current_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        push_was_executed=push_was_executed,
        push_evidence_clean=push_evidence_clean,
        branch_safe=branch_safe,
        base_safe=base_safe,
        repository_safe=repository_safe,
        title_safe=title_safe,
        body_safe=body_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        secrets_detected=secret_detected,
        protected_branch_detected=protected_branch_detected,
        main_source_branch_detected=main_source_branch_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        duplicate_pr_risk=duplicate_pr_risk,
        pr_plan=pr_plan,
        proposed_pr_title=title,
        proposed_pr_body=body,
        proposed_pr_draft=True,
        proposed_labels=labels,
        proposed_reviewers=reviewers,
        proposed_assignees=assignees,
        required_pre_pr_checks=checks,
        can_create_pr=False,
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
        requires_pr_executor_phase=pr_eligible,
        requires_ci_monitor_phase=False,
        requires_human_intervention=requires_human,
        reason=_reason(pr_eligible=pr_eligible, dry_run=dry_run, blocked_reason=blocked_reason),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=PR_CREATION_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _blocked_reason(
    *,
    request: PRCreationGateRequest,
    mode: str,
    push_executor: Mapping[str, Any],
    push_gate: Mapping[str, Any],
    push_executor_truth: Mapping[str, Any],
    push_gate_truth: Mapping[str, Any],
    secret_detected: bool,
    branch_safe: bool,
    base_safe: bool,
    repository_safe: bool,
    title_safe: bool,
    body_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    duplicate_pr_risk: bool,
    push_was_executed: bool,
    push_evidence_clean: bool,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in PR_GATE_MODES:
        return "PR creation gate mode is unknown."
    if mode == "disabled":
        return "PR creation gate is disabled by default."
    if mode == "blocked":
        return "PR creation gate mode blocks all PR eligibility."
    if any(
        (
            request.allow_pr_creation,
            request.allow_auto_merge,
            request.allow_merge,
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
        return "Phase 27 cannot enable PR creation, merge, push, Git mutation, command, network, provider, or agent capabilities."
    if request.require_push_executed and not push_executor:
        return "Phase 26 push executor evidence is required."
    if push_executor.get("blocked") is True:
        return "Phase 26 push executor result is blocked."
    if push_executor.get("requires_human_intervention") is True:
        return "Phase 26 push executor requires human intervention."
    if request.require_push_executed and not push_was_executed:
        return "Phase 26 push executor did not push a branch."
    if push_executor.get("success") is False:
        return "Phase 26 push executor was not successful."
    if request.require_runtime_truth and not push_executor_truth:
        return "Phase 26 Runtime Truth is required."
    if request.require_clean_push_evidence and not push_evidence_clean:
        return "Phase 26 push evidence is not clean."
    if not pushed_ref:
        return "pushed_ref is required."
    if not pushed_remote:
        return "pushed_remote is required."
    if request.require_commit_sha and not commit_sha:
        return "commit_sha is required."
    if push_gate:
        if push_gate.get("push_eligible") is False:
            return "Phase 25 push gate did not mark the branch eligible."
        if push_gate.get("blocked") is True:
            return "Phase 25 push gate is blocked."
        if push_gate.get("requires_human_intervention") is True:
            return "Phase 25 push gate requires human intervention."
        if request.require_runtime_truth and not push_gate_truth:
            return "Phase 25 Runtime Truth is required when push gate evidence is provided."
        if _push_gate_truth_unsafe(push_gate_truth):
            return "Phase 25 Runtime Truth reports unsafe push eligibility evidence."
    if not branch_safe:
        return "Source, head, current, or remote branch metadata is unsafe."
    if not base_safe:
        return "base_branch must be main."
    if not repository_safe:
        return "repository_full_name metadata is unsafe."
    if not title_safe:
        return "PR title metadata is unsafe."
    if not body_safe:
        return "PR body metadata is unsafe."
    if not labels_safe:
        return "PR label metadata is unsafe."
    if not reviewers_safe:
        return "PR reviewer metadata is unsafe."
    if not assignees_safe:
        return "PR assignee metadata is unsafe."
    if duplicate_pr_risk:
        return "Duplicate PR risk requires human intervention."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if request.metadata.get("source_main") is True:
        return "source_main metadata is blocked."
    if request.metadata.get("base_not_main") is True:
        return "base_not_main metadata is blocked."
    return None


def _branch_block_reason(
    *,
    request: PRCreationGateRequest,
    source_branch: str | None,
    head_branch: str | None,
    current_branch: str | None,
    remote_branch: str | None,
) -> str | None:
    if not request.require_non_main_source_branch:
        return None
    source = str(source_branch or "").strip().lower()
    head = str(head_branch or "").strip().lower()
    current = str(current_branch or "").strip().lower()
    remote = str(remote_branch or "").strip().lower()
    base = str(request.base_branch or "").strip().lower()
    if not source:
        return "source_branch is required."
    if not head:
        return "head_branch is required."
    if any(branch == MAIN_BRANCH for branch in (source, head, current, remote)):
        return "PR source, head, current, and remote branches must not be main."
    if source == base or head == base:
        return "PR source and head branches must not equal base_branch."
    if any(_protected_branch(branch) for branch in (source, head, remote)):
        return "Protected source, head, or remote branch is blocked."
    if not all(_branch_name_safe(branch) for branch in (source, head)):
        return "PR source or head branch contains unsafe characters."
    return None


def _base_safe(request: PRCreationGateRequest) -> bool:
    if not request.require_base_main:
        return True
    return str(request.base_branch or "").strip().lower() == MAIN_BRANCH


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


def _proposed_title(request: PRCreationGateRequest, source_branch: str | None) -> tuple[str | None, bool]:
    candidate = request.pr_title_hint or _title_from_branch(source_branch)
    title, redacted = _redact_text(" ".join(str(candidate or "").split()))
    if not title:
        return None, False
    if len(title) > 120:
        title = title[:120].rstrip()
    return title, redacted


def _title_from_branch(source_branch: str | None) -> str:
    branch = str(source_branch or "sandbox/pr-creation-gate").split("/")[-1].replace("-", " ")
    return f"sandbox: add {branch}".strip()


def _proposed_body(
    request: PRCreationGateRequest,
    push_executor: Mapping[str, Any],
    push_gate: Mapping[str, Any],
) -> tuple[str | None, bool]:
    if request.pr_body_hint:
        return _redact_text(request.pr_body_hint)
    body = "\n".join(
        [
            "Summary:",
            "- Adds governed PR creation eligibility metadata.",
            "",
            "Evidence reviewed:",
            "- Phase 26 push executor evidence.",
            "- Phase 25 push gate evidence when provided.",
            "",
            "Safety confirmations:",
            "- No PR creation, merge, auto-merge, push, or command execution occurs in this phase.",
            f"- Commit SHA metadata: {push_executor.get('commit_sha') or push_gate.get('commit_sha') or 'not provided'}.",
            "",
            "Runtime Truth generated: yes.",
        ]
    )
    return _redact_text(body)


def _sanitize_labels(values: list[str]) -> tuple[list[str], bool, bool]:
    sanitized: list[str] = []
    redacted = False
    safe = True
    for value in values:
        text, item_redacted = _redact_text(value)
        redacted = redacted or item_redacted
        if item_redacted or not _LABEL_PATTERN.fullmatch(text) or _metadata_string_unsafe(text):
            safe = False
        sanitized.append(text)
    return sanitized, safe, redacted


def _sanitize_logins(values: list[str]) -> tuple[list[str], bool, bool]:
    sanitized: list[str] = []
    redacted = False
    safe = True
    for value in values:
        text, item_redacted = _redact_text(value)
        redacted = redacted or item_redacted
        if item_redacted or not _SIMPLE_NAME_PATTERN.fullmatch(text) or _metadata_string_unsafe(text):
            safe = False
        sanitized.append(text)
    return sanitized, safe, redacted


def _metadata_string_unsafe(value: str) -> bool:
    lowered = value.lower()
    return (
        bool(_SHELL_CHARS.search(value))
        or "@" in value
        or "://" in lowered
        or lowered in {"@everyone", "@all"}
        or "/" in value
    )


def _pr_plan(
    *,
    repository_full_name: str | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    commit_sha: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    title: str | None,
    body: str | None,
    draft: bool,
    labels: list[str],
    reviewers: list[str],
    assignees: list[str],
    risk_level: str,
    required_checks: list[str],
    eligible: bool,
    requires_human: bool,
) -> dict[str, object]:
    return {
        "plan_id": "pr-plan-1",
        "repository_full_name": repository_full_name,
        "source_branch": source_branch,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "commit_sha": commit_sha,
        "pushed_ref": pushed_ref,
        "pushed_remote": pushed_remote,
        "title": title,
        "body_summary": _body_summary(body),
        "draft": draft,
        "labels": labels,
        "reviewers": reviewers,
        "assignees": assignees,
        "risk_level": risk_level,
        "required_checks_before_execution": required_checks,
        "allowed_in_future_pr_creation": eligible,
        "requires_human": requires_human,
    }


def _body_summary(body: str | None) -> str | None:
    if not body:
        return None
    return " ".join(body.split())[:200]


def _required_checks() -> list[str]:
    return [
        "push_executor_succeeded",
        "pushed_ref_present",
        "pushed_remote_present",
        "commit_sha_present",
        "source_branch_non_main",
        "base_branch_main",
        "repository_safe",
        "title_safe",
        "body_safe",
        "secrets_absent",
        "runtime_truth_clean",
        "no_merge_or_auto_merge",
    ]


def _risk_level(
    *,
    pr_eligible: bool,
    secret_detected: bool,
    protected_branch_detected: bool,
    main_source_branch_detected: bool,
    unsafe_repository_detected: bool,
    duplicate_pr_risk: bool,
) -> str:
    if secret_detected or main_source_branch_detected:
        return "critical"
    if protected_branch_detected or unsafe_repository_detected or duplicate_pr_risk:
        return "high"
    return "low" if pr_eligible else "medium"


def _reason(*, pr_eligible: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "PR creation gate blocked this eligibility request."
    if dry_run:
        return "PR creation gate evaluated evidence in dry-run mode without eligibility."
    if pr_eligible:
        return "PR creation gate marked this branch eligible for a future PR creation phase."
    return "PR creation gate did not mark this branch eligible."


def _push_executor_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "force_push_executed",
        "main_pushed",
        "pr_created",
        "pr_merged",
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


def _push_gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "main_push_detected",
        "force_push_detected",
        "protected_branch_detected",
        "main_modified",
        "pr_created",
        "pr_merged",
        "network_used",
        "provider_called",
        "agent_called",
        "mcp_used",
        "vault_written",
    )
    return any(truth.get(key) is True for key in unsafe_keys)


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


def _coerce_request(value: PRCreationGateRequest | Mapping[str, Any] | Any) -> PRCreationGateRequest:
    if isinstance(value, PRCreationGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("PR creation gate input must be a request, mapping, or object.")
    return PRCreationGateRequest(
        push_executor_result=_coerce_mapping(payload.get("push_executor_result")),
        push_gate_result=_coerce_mapping(payload.get("push_gate_result")),
        commit_executor_result=_coerce_mapping(payload.get("commit_executor_result")),
        commit_gate_result=_coerce_mapping(payload.get("commit_gate_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        pr_gate_mode=str(payload.get("pr_gate_mode") or DEFAULT_PR_GATE_MODE),
        workspace_root=payload.get("workspace_root"),
        repository_full_name=payload.get("repository_full_name"),
        source_branch=payload.get("source_branch"),
        head_branch=payload.get("head_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        current_branch=payload.get("current_branch"),
        remote_name=str(payload.get("remote_name") or "origin"),
        remote_branch=payload.get("remote_branch"),
        pushed_ref=payload.get("pushed_ref"),
        pushed_remote=payload.get("pushed_remote"),
        commit_sha=payload.get("commit_sha"),
        pr_title_hint=payload.get("pr_title_hint"),
        pr_body_hint=payload.get("pr_body_hint"),
        labels=list(payload.get("labels") or []),
        reviewers=list(payload.get("reviewers") or []),
        assignees=list(payload.get("assignees") or []),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_push_executed=bool(payload.get("require_push_executed", True)),
        require_non_main_source_branch=bool(payload.get("require_non_main_source_branch", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_push_evidence=bool(payload.get("require_clean_push_evidence", True)),
        require_commit_sha=bool(payload.get("require_commit_sha", True)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", False)),
        allow_draft_pr=bool(payload.get("allow_draft_pr", True)),
        allow_ready_pr=bool(payload.get("allow_ready_pr", True)),
        allow_auto_merge=bool(payload.get("allow_auto_merge", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
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
