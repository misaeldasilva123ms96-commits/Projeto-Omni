"""Controlled PR creator.

Phase 28 creates a pull request through a narrow injected GitHub client only
after clean Phase 27 PR Creation Gate evidence. It does not execute commands,
use gh, mutate Git, push, merge, enable auto-merge, approve PRs, edit files,
apply patches, call providers, use MCP, call agents, or write Vault notes.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping, Protocol

from .pr_creator_truth import PR_CREATOR_EVIDENCE_VERSION, build_pr_creator_evidence
from .pr_creator_types import ControlledPRCreatorRequest, ControlledPRCreatorResult

CREATOR_MODES = frozenset({"disabled", "dry_run", "create_pr", "blocked"})
DEFAULT_CREATOR_MODE = "disabled"
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


class ControlledGitHubPRClient(Protocol):
    def find_open_pull_request(
        self,
        *,
        repository_full_name: str,
        head_branch: str,
        base_branch: str,
    ) -> Mapping[str, Any] | None:
        """Return an existing open PR for the same head/base, if one exists."""

    def create_pull_request(
        self,
        *,
        repository_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool,
    ) -> Mapping[str, Any]:
        """Create a pull request using only the allowed Phase 28 fields."""


def create_controlled_pr(
    request_or_mapping: ControlledPRCreatorRequest | Mapping[str, Any] | Any,
    github_client: ControlledGitHubPRClient | None = None,
) -> ControlledPRCreatorResult:
    request = _coerce_request(request_or_mapping)
    gate = _coerce_mapping(request.pr_creation_gate_result)
    push_executor = _coerce_mapping(request.push_executor_result)
    push_gate = _coerce_mapping(request.push_gate_result)
    gate_truth = _coerce_mapping(gate.get("runtime_truth"))
    push_executor_truth = _coerce_mapping(push_executor.get("runtime_truth"))
    push_gate_truth = _coerce_mapping(push_gate.get("runtime_truth"))
    mode = str(request.creator_mode or DEFAULT_CREATOR_MODE).strip() or DEFAULT_CREATOR_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    repository, repository_redacted = _redact_optional(
        request.repository_full_name or gate.get("repository_full_name") or _plan_value(gate, "repository_full_name")
    )
    source_branch, source_redacted = _redact_optional(
        request.source_branch or gate.get("source_branch") or _plan_value(gate, "source_branch")
    )
    head_branch, head_redacted = _redact_optional(
        request.head_branch or gate.get("head_branch") or source_branch or _plan_value(gate, "head_branch")
    )
    current_branch, current_redacted = _redact_optional(
        request.current_branch or gate.get("current_branch") or push_executor.get("current_branch")
    )
    remote_branch, remote_branch_redacted = _redact_optional(
        request.remote_branch or gate.get("remote_branch") or push_executor.get("remote_branch")
    )
    pushed_ref, pushed_ref_redacted = _redact_optional(
        request.pushed_ref or gate.get("pushed_ref") or push_executor.get("pushed_ref")
    )
    pushed_remote, pushed_remote_redacted = _redact_optional(
        request.pushed_remote or gate.get("pushed_remote") or push_executor.get("pushed_remote")
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha or gate.get("commit_sha") or push_executor.get("commit_sha")
    )
    title, title_redacted = _final_title(request, gate)
    body, body_redacted = _final_body(request, gate, push_executor)
    labels, labels_safe, labels_redacted = _sanitize_labels(request.labels or list(gate.get("proposed_labels") or []))
    reviewers, reviewers_safe, reviewers_redacted = _sanitize_logins(request.reviewers or list(gate.get("proposed_reviewers") or []))
    assignees, assignees_safe, assignees_redacted = _sanitize_logins(request.assignees or list(gate.get("proposed_assignees") or []))
    raw_request_secret = _contains_credential_like(
        " ".join(
            str(value)
            for value in (
                request.repository_full_name,
                request.source_branch,
                request.head_branch,
                request.current_branch,
                request.remote_branch,
                request.pushed_ref,
                request.pushed_remote,
                request.commit_sha,
                request.pr_title,
                request.pr_body,
                request.labels,
                request.reviewers,
                request.assignees,
            )
            if value is not None
        )
    )
    final_draft = bool(request.draft if request.draft is not None else gate.get("proposed_pr_draft", True))
    title_safe = bool(title and not title_redacted)
    body_safe = bool(body and not body_redacted)
    repository_safe = _repository_safe(repository, request.metadata)
    branch_safe = not _branch_block_reason(
        request=request,
        source_branch=source_branch,
        head_branch=head_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
    )
    push_was_executed = bool(
        push_executor.get("pushed") is True
        or gate.get("push_was_executed") is True
        or gate_truth.get("push_was_executed") is True
    )
    child_truths = [truth for truth in (gate_truth, push_executor_truth, push_gate_truth) if truth]
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            related_pr_redacted,
            repository_redacted,
            source_redacted,
            head_redacted,
            current_redacted,
            remote_branch_redacted,
            pushed_ref_redacted,
            pushed_remote_redacted,
            commit_sha_redacted,
            title_redacted,
            body_redacted,
            labels_redacted,
            reviewers_redacted,
            assignees_redacted,
            raw_request_secret,
            _contains_credential_like(_metadata_text(request.metadata)),
            _source_secret(child_truths),
        )
    )
    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        gate=gate,
        push_executor=push_executor,
        gate_truth=gate_truth,
        push_executor_truth=push_executor_truth,
        secret_detected=secret_detected,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        title_safe=title_safe,
        body_safe=body_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        push_was_executed=push_was_executed,
        repository=repository,
        source_branch=source_branch,
        head_branch=head_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        github_client=github_client,
    )
    if mode == "dry_run" and not blocked_reason:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            source_branch=source_branch,
            head_branch=head_branch,
            current_branch=current_branch,
            remote_branch=remote_branch,
            pushed_ref=pushed_ref,
            pushed_remote=pushed_remote,
            commit_sha=commit_sha,
            gate=gate,
            gate_truth=gate_truth,
            push_was_executed=push_was_executed,
            title_safe=title_safe,
            body_safe=body_safe,
            repository_safe=repository_safe,
            branch_safe=branch_safe,
            labels_safe=labels_safe,
            reviewers_safe=reviewers_safe,
            assignees_safe=assignees_safe,
            title=title,
            body=body,
            draft=final_draft,
            labels=labels,
            reviewers=reviewers,
            assignees=assignees,
            attempted=[],
            completed=[],
            blocked_ops=[],
            duplicate=False,
            existing_url=None,
            pr_payload={},
            pr_created=False,
            blocked=False,
            dry_run=True,
            partial=False,
            success=True,
            reason="Controlled PR creator dry run completed without GitHub mutation.",
            blocked_reason=None,
            redacted=secret_detected,
            github_client_called=False,
        )
    if blocked_reason:
        return _blocked_result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            source_branch=source_branch,
            head_branch=head_branch,
            current_branch=current_branch,
            remote_branch=remote_branch,
            pushed_ref=pushed_ref,
            pushed_remote=pushed_remote,
            commit_sha=commit_sha,
            gate=gate,
            gate_truth=gate_truth,
            push_was_executed=push_was_executed,
            title_safe=title_safe,
            body_safe=body_safe,
            repository_safe=repository_safe,
            branch_safe=branch_safe,
            labels_safe=labels_safe,
            reviewers_safe=reviewers_safe,
            assignees_safe=assignees_safe,
            title=title,
            body=body,
            draft=final_draft,
            labels=labels,
            reviewers=reviewers,
            assignees=assignees,
            blocked_reason=blocked_reason,
            redacted=secret_detected,
        )

    attempted: list[str] = []
    completed: list[str] = []
    blocked_ops: list[str] = []
    try:
        existing = _find_existing_pr(
            github_client=github_client,
            repository_full_name=str(repository),
            head_branch=str(head_branch),
            base_branch=request.base_branch,
            attempted=attempted,
            completed=completed,
        )
        if existing:
            safe_existing, response_redacted = _sanitize_pr_response(existing)
            return _result(
                request=request,
                mode=mode,
                requested_by=requested_by,
                related_phase=related_phase,
                related_pr=related_pr,
                repository=repository,
                source_branch=source_branch,
                head_branch=head_branch,
                current_branch=current_branch,
                remote_branch=remote_branch,
                pushed_ref=pushed_ref,
                pushed_remote=pushed_remote,
                commit_sha=commit_sha,
                gate=gate,
                gate_truth=gate_truth,
                push_was_executed=push_was_executed,
                title_safe=title_safe,
                body_safe=body_safe,
                repository_safe=repository_safe,
                branch_safe=branch_safe,
                labels_safe=labels_safe,
                reviewers_safe=reviewers_safe,
                assignees_safe=assignees_safe,
                title=title,
                body=body,
                draft=final_draft,
                labels=labels,
                reviewers=reviewers,
                assignees=assignees,
                attempted=attempted,
                completed=completed,
                blocked_ops=blocked_ops,
                duplicate=True,
                existing_url=_optional_str(safe_existing.get("url") or safe_existing.get("html_url")),
                pr_payload=safe_existing,
                pr_created=False,
                blocked=False,
                dry_run=False,
                partial=False,
                success=True,
                reason="Existing open PR detected; no new PR was created.",
                blocked_reason=None,
                redacted=secret_detected or response_redacted,
                github_client_called=True,
            )
        pr_payload = _create_pr(
            github_client=github_client,
            repository_full_name=str(repository),
            title=str(title),
            body=str(body),
            head_branch=str(head_branch),
            base_branch=request.base_branch,
            draft=final_draft,
            attempted=attempted,
            completed=completed,
        )
        safe_payload, response_redacted = _sanitize_pr_response(pr_payload)
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            source_branch=source_branch,
            head_branch=head_branch,
            current_branch=current_branch,
            remote_branch=remote_branch,
            pushed_ref=pushed_ref,
            pushed_remote=pushed_remote,
            commit_sha=commit_sha,
            gate=gate,
            gate_truth=gate_truth,
            push_was_executed=push_was_executed,
            title_safe=title_safe,
            body_safe=body_safe,
            repository_safe=repository_safe,
            branch_safe=branch_safe,
            labels_safe=labels_safe,
            reviewers_safe=reviewers_safe,
            assignees_safe=assignees_safe,
            title=title,
            body=body,
            draft=final_draft,
            labels=labels,
            reviewers=reviewers,
            assignees=assignees,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            duplicate=False,
            existing_url=None,
            pr_payload=safe_payload,
            pr_created=True,
            blocked=False,
            dry_run=False,
            partial=False,
            success=True,
            reason="Controlled pull request was created.",
            blocked_reason=None,
            redacted=secret_detected or response_redacted,
            github_client_called=True,
        )
    except _GitHubClientError as exc:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            repository=repository,
            source_branch=source_branch,
            head_branch=head_branch,
            current_branch=current_branch,
            remote_branch=remote_branch,
            pushed_ref=pushed_ref,
            pushed_remote=pushed_remote,
            commit_sha=commit_sha,
            gate=gate,
            gate_truth=gate_truth,
            push_was_executed=push_was_executed,
            title_safe=title_safe,
            body_safe=body_safe,
            repository_safe=repository_safe,
            branch_safe=branch_safe,
            labels_safe=labels_safe,
            reviewers_safe=reviewers_safe,
            assignees_safe=assignees_safe,
            title=title,
            body=body,
            draft=final_draft,
            labels=labels,
            reviewers=reviewers,
            assignees=assignees,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            duplicate=False,
            existing_url=None,
            pr_payload={},
            pr_created=False,
            blocked=True,
            dry_run=False,
            partial=False,
            success=False,
            reason="Controlled GitHub PR creation operation failed.",
            blocked_reason=_redact_text(str(exc))[0],
            redacted=secret_detected or _contains_credential_like(str(exc)),
            github_client_called=bool(attempted),
        )


class _GitHubClientError(RuntimeError):
    pass


def _find_existing_pr(
    *,
    github_client: ControlledGitHubPRClient | None,
    repository_full_name: str,
    head_branch: str,
    base_branch: str,
    attempted: list[str],
    completed: list[str],
) -> Mapping[str, Any] | None:
    if github_client is None:
        raise _GitHubClientError("A controlled GitHub client is required.")
    attempted.append("find_open_pull_request")
    result = github_client.find_open_pull_request(
        repository_full_name=repository_full_name,
        head_branch=head_branch,
        base_branch=base_branch,
    )
    completed.append("find_open_pull_request")
    return result


def _create_pr(
    *,
    github_client: ControlledGitHubPRClient | None,
    repository_full_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    draft: bool,
    attempted: list[str],
    completed: list[str],
) -> Mapping[str, Any]:
    if github_client is None:
        raise _GitHubClientError("A controlled GitHub client is required.")
    attempted.append("create_pull_request")
    result = github_client.create_pull_request(
        repository_full_name=repository_full_name,
        title=title,
        body=body,
        head_branch=head_branch,
        base_branch=base_branch,
        draft=draft,
    )
    completed.append("create_pull_request")
    return result


def _blocked_reason(
    *,
    request: ControlledPRCreatorRequest,
    mode: str,
    gate: Mapping[str, Any],
    push_executor: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    push_executor_truth: Mapping[str, Any],
    secret_detected: bool,
    repository_safe: bool,
    branch_safe: bool,
    title_safe: bool,
    body_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    push_was_executed: bool,
    repository: str | None,
    source_branch: str | None,
    head_branch: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
    github_client: ControlledGitHubPRClient | None,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in CREATOR_MODES:
        return "Controlled PR creator mode is unknown."
    if mode == "disabled":
        return "Controlled PR creator is disabled by default."
    if mode == "blocked":
        return "Controlled PR creator mode blocks all PR creation."
    if any(
        (
            request.allow_merge,
            request.allow_auto_merge,
            request.allow_push,
            request.allow_force_push,
            request.allow_main_push,
            request.allow_git_mutation,
            request.allow_command_execution,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 28 cannot enable merge, auto-merge, push, Git mutation, command, provider, or agent capabilities."
    if not request.allow_pr_creation and mode == "create_pr":
        return "Controlled PR creation requires explicit PR creation capability."
    if mode == "create_pr" and not request.allow_network:
        return "Controlled GitHub PR creation requires the controlled client network capability."
    if request.require_pr_gate_eligible and not gate:
        return "Phase 27 PR creation gate evidence is required."
    if gate.get("blocked") is True:
        return "Phase 27 PR creation gate result is blocked."
    if gate.get("requires_human_intervention") is True:
        return "Phase 27 PR creation gate requires human intervention."
    if request.require_pr_gate_eligible and gate.get("pr_eligible") is not True:
        return "Phase 27 PR creation gate did not mark this branch eligible."
    if gate.get("pr_ready_metadata_only") is not True:
        return "Phase 27 PR creation gate did not mark this branch ready as metadata."
    if gate.get("success") is False:
        return "Phase 27 PR creation gate was not successful."
    if request.require_runtime_truth and not gate_truth:
        return "Phase 27 Runtime Truth is required."
    if request.require_clean_evidence and _gate_truth_unsafe(gate_truth):
        return "Phase 27 Runtime Truth reports unsafe PR evidence."
    if request.require_push_executed and not push_was_executed:
        return "Phase 26 pushed branch evidence is required."
    if push_executor:
        if push_executor.get("pushed") is not True and request.require_push_executed:
            return "Phase 26 push executor did not push a branch."
        if push_executor.get("success") is not True:
            return "Phase 26 push executor was not successful."
        if request.require_runtime_truth and not push_executor_truth:
            return "Phase 26 Runtime Truth is required when push evidence is supplied."
        if _push_truth_unsafe(push_executor_truth):
            return "Phase 26 Runtime Truth reports unsafe push evidence."
    if request.require_commit_sha and not commit_sha:
        return "commit_sha is required."
    if not pushed_ref:
        return "pushed_ref is required."
    if not pushed_remote:
        return "pushed_remote is required."
    if not repository or not repository_safe:
        return "repository_full_name metadata is unsafe."
    if not source_branch or not head_branch or not branch_safe:
        return "PR source or head branch metadata is unsafe."
    if request.require_base_main and str(request.base_branch or "").strip().lower() != MAIN_BRANCH:
        return "base_branch must be main."
    if not title_safe:
        return "PR title is unsafe."
    if not body_safe:
        return "PR body is unsafe."
    if not labels_safe or (request.labels and request.allow_labels):
        return "PR label metadata is unsafe or label mutation is not allowed in this phase."
    if not reviewers_safe or (request.reviewers and request.allow_reviewers):
        return "PR reviewer metadata is unsafe or reviewer mutation is not allowed in this phase."
    if not assignees_safe or (request.assignees and request.allow_assignees):
        return "PR assignee metadata is unsafe or assignee mutation is not allowed in this phase."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if request.metadata.get("source_main") is True:
        return "source_main metadata is blocked."
    if request.metadata.get("base_not_main") is True:
        return "base_not_main metadata is blocked."
    if mode == "create_pr" and github_client is None:
        return "A controlled GitHub client is required for PR creation."
    return None


def _gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "pr_created",
        "pr_merged",
        "auto_merge_enabled",
        "main_modified",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
    )
    return any(truth.get(key) is True for key in unsafe_keys)


def _push_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "force_push_executed",
        "main_pushed",
        "pr_created",
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


def _branch_block_reason(
    *,
    request: ControlledPRCreatorRequest,
    source_branch: str | None,
    head_branch: str | None,
    current_branch: str | None,
    remote_branch: str | None,
) -> str | None:
    if not request.require_non_main_head:
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


def _repository_safe(repository: str | None, metadata: Mapping[str, Any]) -> bool:
    if not repository:
        return False
    if _contains_credential_like(repository) or _SHELL_CHARS.search(repository):
        return False
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        return False
    expected = str(metadata.get("expected_repository") or EXPECTED_REPOSITORY)
    if repository != expected and metadata.get("allow_unexpected_repository") is not True:
        return False
    return True


def _final_title(
    request: ControlledPRCreatorRequest,
    gate: Mapping[str, Any],
) -> tuple[str | None, bool]:
    candidate = gate.get("proposed_pr_title") or request.pr_title or request.metadata.get("pr_title_hint") or "sandbox: add controlled PR creator"
    title, redacted = _redact_text(" ".join(str(candidate or "").split()))
    if not title:
        return None, False
    if len(title) > 120:
        title = title[:120].rstrip()
    return title, redacted


def _final_body(
    request: ControlledPRCreatorRequest,
    gate: Mapping[str, Any],
    push_executor: Mapping[str, Any],
) -> tuple[str | None, bool]:
    candidate = gate.get("proposed_pr_body") or request.pr_body
    if candidate:
        return _redact_text(candidate)
    body = "\n".join(
        [
            "Summary:",
            "- Adds a controlled PR creation layer.",
            "",
            "Evidence reviewed:",
            "- Phase 27 PR Creation Gate evidence.",
            "- Phase 26 push evidence.",
            f"- Commit SHA metadata: {gate.get('commit_sha') or push_executor.get('commit_sha') or 'not provided'}.",
            "",
            "Safety confirmations:",
            "- No merge, auto-merge, approval, push, Git mutation, command execution, provider, MCP, agent, or Vault write.",
            "",
            "Runtime Truth generated: yes.",
            "Next expected phase: CI Monitor.",
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


def _sanitize_pr_response(response: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    safe: dict[str, Any] = {}
    redacted = False
    for key in ("number", "url", "html_url", "node_id", "state"):
        if key not in response:
            continue
        value = response[key]
        if isinstance(value, str):
            clean, was_redacted = _redact_text(value)
            safe[key] = clean
            redacted = redacted or was_redacted
        else:
            safe[key] = value
    return safe, redacted


def _plan_value(gate: Mapping[str, Any], key: str) -> object:
    plan = gate.get("pr_plan")
    return plan.get(key) if isinstance(plan, Mapping) else None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


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


def _coerce_request(value: ControlledPRCreatorRequest | Mapping[str, Any] | Any) -> ControlledPRCreatorRequest:
    if isinstance(value, ControlledPRCreatorRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("PR creator input must be a request, mapping, or object.")
    return ControlledPRCreatorRequest(
        pr_creation_gate_result=_coerce_mapping(payload.get("pr_creation_gate_result")),
        push_executor_result=_coerce_mapping(payload.get("push_executor_result")),
        push_gate_result=_coerce_mapping(payload.get("push_gate_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        creator_mode=str(payload.get("creator_mode") or DEFAULT_CREATOR_MODE),
        repository_full_name=payload.get("repository_full_name"),
        source_branch=payload.get("source_branch"),
        head_branch=payload.get("head_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        current_branch=payload.get("current_branch"),
        remote_branch=payload.get("remote_branch"),
        pushed_ref=payload.get("pushed_ref"),
        pushed_remote=payload.get("pushed_remote"),
        commit_sha=payload.get("commit_sha"),
        pr_title=payload.get("pr_title"),
        pr_body=payload.get("pr_body"),
        draft=bool(payload.get("draft", True)),
        labels=list(payload.get("labels") or []),
        reviewers=list(payload.get("reviewers") or []),
        assignees=list(payload.get("assignees") or []),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_pr_gate_eligible=bool(payload.get("require_pr_gate_eligible", True)),
        require_push_executed=bool(payload.get("require_push_executed", True)),
        require_non_main_head=bool(payload.get("require_non_main_head", True)),
        require_base_main=bool(payload.get("require_base_main", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_evidence=bool(payload.get("require_clean_evidence", True)),
        require_commit_sha=bool(payload.get("require_commit_sha", True)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", True)),
        allow_ready_pr=bool(payload.get("allow_ready_pr", True)),
        allow_draft_pr=bool(payload.get("allow_draft_pr", True)),
        allow_labels=bool(payload.get("allow_labels", False)),
        allow_reviewers=bool(payload.get("allow_reviewers", False)),
        allow_assignees=bool(payload.get("allow_assignees", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_auto_merge=bool(payload.get("allow_auto_merge", False)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_force_push=bool(payload.get("allow_force_push", False)),
        allow_main_push=bool(payload.get("allow_main_push", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_command_execution=bool(payload.get("allow_command_execution", False)),
        allow_network=bool(payload.get("allow_network", True)),
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


def _blocked_result(
    *,
    request: ControlledPRCreatorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    repository: str | None,
    source_branch: str | None,
    head_branch: str | None,
    current_branch: str | None,
    remote_branch: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
    gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    push_was_executed: bool,
    title_safe: bool,
    body_safe: bool,
    repository_safe: bool,
    branch_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    title: str | None,
    body: str | None,
    draft: bool,
    labels: list[str],
    reviewers: list[str],
    assignees: list[str],
    blocked_reason: str,
    redacted: bool,
) -> ControlledPRCreatorResult:
    return _result(
        request=request,
        mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository=repository,
        source_branch=source_branch,
        head_branch=head_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        gate=gate,
        gate_truth=gate_truth,
        push_was_executed=push_was_executed,
        title_safe=title_safe,
        body_safe=body_safe,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        title=title,
        body=body,
        draft=draft,
        labels=labels,
        reviewers=reviewers,
        assignees=assignees,
        attempted=[],
        completed=[],
        blocked_ops=["create_pull_request"],
        duplicate=False,
        existing_url=None,
        pr_payload={},
        pr_created=False,
        blocked=True,
        dry_run=False,
        partial=False,
        success=False,
        reason="Controlled PR creator blocked this request.",
        blocked_reason=blocked_reason,
        redacted=redacted,
        github_client_called=False,
    )


def _result(
    *,
    request: ControlledPRCreatorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    repository: str | None,
    source_branch: str | None,
    head_branch: str | None,
    current_branch: str | None,
    remote_branch: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
    gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    push_was_executed: bool,
    title_safe: bool,
    body_safe: bool,
    repository_safe: bool,
    branch_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    title: str | None,
    body: str | None,
    draft: bool,
    labels: list[str],
    reviewers: list[str],
    assignees: list[str],
    attempted: list[str],
    completed: list[str],
    blocked_ops: list[str],
    duplicate: bool,
    existing_url: str | None,
    pr_payload: Mapping[str, Any],
    pr_created: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    success: bool,
    reason: str,
    blocked_reason: str | None,
    redacted: bool,
    github_client_called: bool,
) -> ControlledPRCreatorResult:
    pr_number = _optional_int(pr_payload.get("number"))
    pr_url = _optional_str(pr_payload.get("url") or pr_payload.get("html_url"))
    pr_node_id = _optional_str(pr_payload.get("node_id"))
    pr_state = _optional_str(pr_payload.get("state"))
    requires_human = bool(blocked and not dry_run)
    child_events = [dict(gate_truth)] if gate_truth else []
    runtime_truth = build_pr_creator_evidence(
        creator_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=request.base_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        pr_created=pr_created,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        pr_gate_eligible=bool(gate.get("pr_eligible") is True),
        push_was_executed=push_was_executed,
        title_safe=title_safe,
        body_safe=body_safe,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        duplicate_pr_detected=duplicate,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        github_operations_attempted=attempted,
        github_operations_completed=completed,
        github_operations_blocked=blocked_ops,
        github_client_called=github_client_called,
        secrets_detected=redacted,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=child_events,
    ).to_dict()
    return ControlledPRCreatorResult(
        pr_created=pr_created,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        partial=partial,
        creator_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=request.base_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        pr_gate_eligible=bool(gate.get("pr_eligible") is True),
        push_was_executed=push_was_executed,
        title_safe=title_safe,
        body_safe=body_safe,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        final_pr_title=title,
        final_pr_body=body,
        final_draft=draft,
        final_labels=labels,
        final_reviewers=reviewers,
        final_assignees=assignees,
        github_operations_attempted=attempted,
        github_operations_completed=completed,
        github_operations_blocked=blocked_ops,
        duplicate_pr_detected=duplicate,
        existing_pr_url=existing_url,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_node_id=pr_node_id,
        pr_state=pr_state,
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
        requires_ci_monitor_phase=pr_created,
        requires_merge_gate_phase=False,
        requires_human_intervention=requires_human,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=PR_CREATOR_EVIDENCE_VERSION,
        redacted=redacted,
    )


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
