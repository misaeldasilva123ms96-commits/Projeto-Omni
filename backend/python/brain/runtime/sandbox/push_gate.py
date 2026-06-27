"""Controlled push eligibility gate.

Phase 25 evaluates whether a committed non-main branch is eligible for a
future push phase. It never executes commands, mutates Git, contacts remotes,
pushes, force pushes, creates PRs, merges, rebases, stages files, commits,
edits files, applies patches, calls providers, uses MCP, calls agents, or
writes Vault notes.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .push_gate_truth import PUSH_GATE_EVIDENCE_VERSION, build_push_gate_evidence
from .push_gate_types import ControlledPushGateRequest, ControlledPushGateResult

PUSH_GATE_MODES = frozenset({"disabled", "dry_run", "evaluate_push", "blocked"})
DEFAULT_PUSH_GATE_MODE = "disabled"
MAIN_BRANCH = "main"

_ALLOWED_PREFIXES = (
    "backend/python/",
    "backend/rust/",
    "frontend/",
    "tests/",
    "docs/",
    "sandbox/local/",
    "vault/templates/",
)
_PROTECTED_PREFIXES = (
    "vault/08_ADR/",
    "docs/governance/",
    "docs/security/",
    ".github/workflows/",
)
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
_REMOTE_SHELL_CHARS = re.compile(r"[;&|`$<>\s]")


def evaluate_push_gate(
    request_or_mapping: ControlledPushGateRequest | Mapping[str, Any] | Any,
) -> ControlledPushGateResult:
    request = _coerce_request(request_or_mapping)
    executor = _coerce_mapping(request.commit_executor_result)
    commit_gate = _coerce_mapping(request.commit_gate_result)
    validation = _coerce_mapping(request.post_patch_validation_result)
    executor_truth = _coerce_mapping(executor.get("runtime_truth"))
    commit_gate_truth = _coerce_mapping(commit_gate.get("runtime_truth"))
    validation_truth = _coerce_mapping(validation.get("runtime_truth"))
    mode = str(request.push_gate_mode or DEFAULT_PUSH_GATE_MODE).strip() or DEFAULT_PUSH_GATE_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(
        request.workspace_root or executor.get("workspace_root")
    )
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(request.target_branch)
    remote_name, remote_name_redacted = _redact_text(request.remote_name)
    remote_branch, remote_branch_redacted = _redact_optional(
        request.remote_branch or current_branch
    )
    proposed_push_ref, push_ref_redacted = _redact_optional(
        request.proposed_push_ref or remote_branch
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha or executor.get("commit_sha")
    )
    pre_commit_head, pre_head_redacted = _redact_optional(
        request.pre_commit_head or executor.get("pre_commit_head")
    )
    post_commit_head, post_head_redacted = _redact_optional(
        request.post_commit_head or executor.get("post_commit_head")
    )
    files_considered, files_redacted = _redact_list(
        request.files_committed
        or list(executor.get("files_staged") or [])
        or list(executor.get("files_considered") or [])
    )
    files_blocked = _blocked_files(files_considered)
    source_truths = [
        truth for truth in (executor_truth, commit_gate_truth, validation_truth) if truth
    ]
    source_flags = _source_flags(source_truths)
    protected_branch_detected = _protected_branch(current_branch) or _protected_branch(remote_branch)
    force_push_detected = _force_push_detected(proposed_push_ref, request.metadata)
    main_push_detected = _main_push_detected(
        current_branch=current_branch,
        target_branch=target_branch,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        metadata=request.metadata,
    )
    branch_safe = not (
        protected_branch_detected
        or main_push_detected
        or _branch_block_reason(request, current_branch, target_branch, remote_branch)
    )
    remote_safe = not _remote_block_reason(
        request=request,
        remote_name=remote_name,
        current_branch=current_branch,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
    )
    commit_was_executed = bool(executor.get("committed") is True)
    commit_evidence_clean = bool(
        commit_was_executed
        and executor.get("success") is True
        and commit_sha
        and not source_flags["unsafe"]
        and not source_flags["secrets_detected"]
    )
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            remote_name_redacted,
            remote_branch_redacted,
            push_ref_redacted,
            commit_sha_redacted,
            pre_head_redacted,
            post_head_redacted,
            files_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            source_flags["secrets_detected"],
        )
    )
    git_mutation_issue = bool(source_flags["unsafe"])
    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        executor=executor,
        commit_gate=commit_gate,
        executor_truth=executor_truth,
        commit_gate_truth=commit_gate_truth,
        secret_detected=secret_detected,
        branch_block=_branch_block_reason(request, current_branch, target_branch, remote_branch),
        remote_block=_remote_block_reason(
            request=request,
            remote_name=remote_name,
            current_branch=current_branch,
            remote_branch=remote_branch,
            proposed_push_ref=proposed_push_ref,
        ),
        files_blocked=files_blocked,
        protected_branch_detected=protected_branch_detected,
        force_push_detected=force_push_detected,
        main_push_detected=main_push_detected,
        commit_was_executed=commit_was_executed,
        commit_sha=commit_sha,
        commit_evidence_clean=commit_evidence_clean,
        git_mutation_issue=git_mutation_issue,
    )
    dry_run = mode == "dry_run" and not blocked_reason
    evaluated = mode in {"dry_run", "evaluate_push"} and not blocked_reason
    push_eligible = bool(
        mode == "evaluate_push"
        and evaluated
        and commit_evidence_clean
        and branch_safe
        and remote_safe
        and not files_blocked
        and not protected_branch_detected
        and not force_push_detected
        and not main_push_detected
        and not secret_detected
        and not git_mutation_issue
    )
    required_checks = _required_checks()
    push_plan = _push_plan(
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        source_branch=current_branch,
        commit_sha=commit_sha,
        risk_level=_risk_level(
            push_eligible=push_eligible,
            protected_branch_detected=protected_branch_detected,
            force_push_detected=force_push_detected,
            main_push_detected=main_push_detected,
            secret_detected=secret_detected,
            files_blocked=files_blocked,
        ),
        required_checks=required_checks,
        eligible=push_eligible,
        requires_human=bool(blocked_reason or protected_branch_detected or files_blocked),
    )
    blocked = bool(blocked_reason)
    success = bool(evaluated and not blocked)
    requires_human = bool(
        blocked
        or protected_branch_detected
        or files_blocked
        or force_push_detected
        or main_push_detected
        or secret_detected
        or git_mutation_issue
    )
    runtime_truth = build_push_gate_evidence(
        push_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        push_eligible=push_eligible,
        push_ready_metadata_only=push_eligible,
        commit_was_executed=commit_was_executed,
        commit_sha=commit_sha,
        pre_commit_head=pre_commit_head,
        post_commit_head=post_commit_head,
        commit_evidence_clean=commit_evidence_clean,
        branch_safe=branch_safe,
        remote_safe=remote_safe,
        protected_branch_detected=protected_branch_detected,
        force_push_detected=force_push_detected,
        main_push_detected=main_push_detected,
        secrets_detected=secret_detected,
        git_mutation_issue_detected=git_mutation_issue,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason or _escalation_reason(requires_human),
        child_runtime_truth_events=[dict(truth) for truth in source_truths],
    ).to_dict()
    return ControlledPushGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        push_eligible=push_eligible,
        push_ready_metadata_only=push_eligible,
        push_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        commit_was_executed=commit_was_executed,
        commit_sha=commit_sha,
        pre_commit_head=pre_commit_head,
        post_commit_head=post_commit_head,
        commit_evidence_clean=commit_evidence_clean,
        branch_safe=branch_safe,
        remote_safe=remote_safe,
        protected_branch_detected=protected_branch_detected,
        force_push_detected=force_push_detected,
        main_push_detected=main_push_detected,
        secrets_detected=secret_detected,
        git_mutation_issue_detected=git_mutation_issue,
        files_considered=files_considered,
        files_blocked=files_blocked,
        push_plan=push_plan,
        required_pre_push_checks=required_checks,
        can_execute_push=False,
        can_force_push=False,
        can_push_main=False,
        can_open_pr=False,
        can_merge=False,
        can_rebase=False,
        can_create_branch=False,
        can_checkout=False,
        can_edit_code=False,
        can_apply_patch=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        requires_human_intervention=requires_human,
        reason=_reason(push_eligible=push_eligible, dry_run=dry_run, blocked_reason=blocked_reason),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason or _escalation_reason(requires_human),
        runtime_truth=runtime_truth,
        evidence_version=PUSH_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _blocked_reason(
    *,
    request: ControlledPushGateRequest,
    mode: str,
    executor: Mapping[str, Any],
    commit_gate: Mapping[str, Any],
    executor_truth: Mapping[str, Any],
    commit_gate_truth: Mapping[str, Any],
    secret_detected: bool,
    branch_block: str | None,
    remote_block: str | None,
    files_blocked: list[str],
    protected_branch_detected: bool,
    force_push_detected: bool,
    main_push_detected: bool,
    commit_was_executed: bool,
    commit_sha: str | None,
    commit_evidence_clean: bool,
    git_mutation_issue: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in PUSH_GATE_MODES:
        return "Controlled push gate mode is unknown."
    if mode == "disabled":
        return "Controlled push gate is disabled by default."
    if mode == "blocked":
        return "Controlled push gate mode blocks all push eligibility."
    if any(
        (
            request.allow_push_execution,
            request.allow_force_push,
            request.allow_main_push,
            request.allow_protected_branch_push,
            request.allow_git_mutation,
            request.allow_pr_creation,
            request.allow_merge,
            request.allow_rebase,
            request.allow_branch_create,
            request.allow_checkout,
            request.allow_network,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 25 cannot enable push, force push, main push, Git mutation, PR, merge, rebase, branch, checkout, network, provider, or agent capabilities."
    if request.require_commit_executed and not executor:
        return "Phase 24 commit executor evidence is required."
    if executor.get("blocked") is True:
        return "Phase 24 commit executor result is blocked."
    if executor.get("requires_human_intervention") is True:
        return "Phase 24 commit executor requires human intervention."
    if request.require_commit_executed and not commit_was_executed:
        return "Phase 24 commit executor did not create a commit."
    if executor.get("success") is False:
        return "Phase 24 commit executor was not successful."
    if request.require_commit_executed and not commit_sha:
        return "Commit SHA is required for push eligibility."
    if request.require_runtime_truth and not executor_truth:
        return "Phase 24 Runtime Truth is required."
    if request.require_clean_commit_evidence and not commit_evidence_clean:
        return "Phase 24 commit evidence is not clean."
    if commit_gate:
        if commit_gate.get("commit_eligible") is False:
            return "Phase 23 commit gate did not mark this change eligible."
        if commit_gate.get("blocked") is True:
            return "Phase 23 commit gate is blocked."
        if commit_gate.get("requires_human_intervention") is True:
            return "Phase 23 commit gate requires human intervention."
    if request.require_runtime_truth and commit_gate and not commit_gate_truth:
        return "Phase 23 Runtime Truth is required when commit gate evidence is provided."
    if branch_block:
        return branch_block
    if remote_block:
        return remote_block
    if files_blocked:
        return "Protected or ineligible committed files require human intervention."
    if protected_branch_detected:
        return "Protected branch push target requires human intervention."
    if force_push_detected:
        return "Force push metadata is blocked."
    if main_push_detected:
        return "Main push metadata is blocked."
    if git_mutation_issue:
        return "Source evidence reports disallowed push, PR, merge, branch, network, provider, MCP, agent, Vault, or main activity."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if request.metadata.get("push_main") is True:
        return "push_main metadata is blocked."
    if request.metadata.get("force_push") is True:
        return "force_push metadata is blocked."
    return None


def _branch_block_reason(
    request: ControlledPushGateRequest,
    current_branch: str | None,
    target_branch: str | None,
    remote_branch: str | None,
) -> str | None:
    if not request.require_non_main_branch:
        return None
    current = str(current_branch or "").strip().lower()
    target = str(target_branch or "").strip().lower()
    remote = str(remote_branch or "").strip().lower()
    base = str(request.base_branch or "").strip().lower()
    if not current:
        return "current_branch metadata is required."
    if current == MAIN_BRANCH:
        return "current_branch must not be main."
    if current == base:
        return "current_branch must not equal base_branch."
    if target == MAIN_BRANCH:
        return "target_branch must not be main."
    if remote == MAIN_BRANCH:
        return "remote_branch must not be main."
    if base != MAIN_BRANCH:
        return "base_branch must be main."
    if _protected_branch(current):
        return "protected current branch is blocked."
    if _protected_branch(remote):
        return "protected remote branch is blocked."
    return None


def _remote_block_reason(
    *,
    request: ControlledPushGateRequest,
    remote_name: str,
    current_branch: str | None,
    remote_branch: str | None,
    proposed_push_ref: str | None,
) -> str | None:
    if not remote_name:
        return "remote_name is required."
    if _REMOTE_SHELL_CHARS.search(remote_name):
        return "remote_name contains unsafe characters."
    if remote_name != "origin" and request.metadata.get("allow_named_remote") is not True:
        return "Only origin is allowed as remote metadata in this phase."
    if _contains_credential_like(remote_name) or _contains_credential_like(remote_branch) or _contains_credential_like(proposed_push_ref):
        return "Remote metadata contains secret-like content."
    remote = str(remote_branch or "").strip()
    current = str(current_branch or "").strip()
    push_ref = str(proposed_push_ref or "").strip()
    if remote and current and remote != current:
        return "remote_branch must match current_branch."
    if _protected_branch(remote):
        return "protected remote branch is blocked."
    if _ref_is_force_or_mutating(push_ref):
        return "proposed_push_ref contains force or refspec mutation."
    if _ref_targets_main(push_ref):
        return "proposed_push_ref must not target main."
    if push_ref and current and push_ref not in {current, f"refs/heads/{current}"}:
        return "proposed_push_ref must match the current branch."
    return None


def _protected_branch(branch: object) -> bool:
    lowered = str(branch or "").strip().lower()
    return lowered.startswith(("release/", "prod/", "production/", "protected/"))


def _force_push_detected(ref: object, metadata: Mapping[str, Any]) -> bool:
    text = str(ref or "").lower()
    return bool(metadata.get("force_push") is True or "+" in text or "--force" in text or " -f" in text or text == "-f")


def _main_push_detected(
    *,
    current_branch: str | None,
    target_branch: str | None,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    metadata: Mapping[str, Any],
) -> bool:
    if metadata.get("push_main") is True:
        return True
    values = [current_branch, target_branch, remote_branch]
    if any(str(value or "").strip().lower() == MAIN_BRANCH for value in values):
        return True
    return _ref_targets_main(proposed_push_ref)


def _ref_targets_main(ref: object) -> bool:
    text = str(ref or "").strip().lower()
    return text in {"main", "refs/heads/main", "head:main"} or text.endswith(":main") or "/main" in text


def _ref_is_force_or_mutating(ref: object) -> bool:
    text = str(ref or "").strip().lower()
    return "+" in text or ":" in text or "--force" in text or text == "-f" or " -f" in text


def _blocked_files(files: list[str]) -> list[str]:
    blocked: list[str] = []
    for raw in files:
        normalized = _normalize_path(raw)
        if normalized is None:
            safe, _ = _redact_text(raw)
            blocked.append(safe)
            continue
        issue = _path_issue(normalized)
        if issue:
            blocked.append(normalized)
    return blocked


def _normalize_path(path: object) -> str | None:
    text = str(path or "").replace("\\", "/").strip()
    if not text or text.startswith("-") or ".." in text.split("/") or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    safe, _ = _redact_text(text)
    return safe


def _path_issue(path: str) -> str | None:
    lowered = path.lower()
    if _contains_credential_like(path) or lowered.startswith(".git/"):
        return "secret_or_repo_internal"
    if any(lowered.startswith(prefix.lower()) for prefix in _PROTECTED_PREFIXES):
        return "protected_file"
    if any(marker in lowered for marker in ("production", "deploy", "billing", "secret", "credential", "private")):
        return "protected_file"
    if lowered.endswith(("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock")):
        return "lockfile"
    if not any(lowered.startswith(prefix.lower()) for prefix in _ALLOWED_PREFIXES):
        return "outside_scope"
    return None


def _source_flags(truths: list[Mapping[str, Any]]) -> dict[str, bool]:
    unsafe_keys = (
        "pushed",
        "push_executed",
        "pr_created",
        "pr_merged",
        "merge_performed",
        "rebase_performed",
        "checkout_performed",
        "branch_created",
        "main_modified",
        "network_used",
        "provider_called",
        "mcp_used",
        "agent_called",
        "vault_written",
        "git_mutated",
    )
    return {
        "secrets_detected": any(truth.get("secrets_detected") is True for truth in truths),
        "unsafe": any(truth.get(key) is True for truth in truths for key in unsafe_keys),
    }


def _push_plan(
    *,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    source_branch: str | None,
    commit_sha: str | None,
    risk_level: str,
    required_checks: list[str],
    eligible: bool,
    requires_human: bool,
) -> dict[str, object]:
    return {
        "plan_id": "push-plan-1",
        "remote_name": remote_name,
        "remote_branch": remote_branch,
        "proposed_push_ref": proposed_push_ref,
        "source_branch": source_branch,
        "commit_sha": commit_sha,
        "risk_level": risk_level,
        "summary": "Metadata-only future push eligibility plan.",
        "required_checks_before_execution": required_checks,
        "allowed_in_future_push_execution": eligible,
        "requires_human": requires_human,
    }


def _required_checks() -> list[str]:
    return [
        "commit_executor_succeeded",
        "commit_sha_present",
        "non_main_branch_confirmed",
        "remote_branch_safe",
        "force_push_absent",
        "main_push_absent",
        "protected_branch_absent",
        "secrets_absent",
        "runtime_truth_clean",
        "commit_evidence_clean",
    ]


def _risk_level(
    *,
    push_eligible: bool,
    protected_branch_detected: bool,
    force_push_detected: bool,
    main_push_detected: bool,
    secret_detected: bool,
    files_blocked: list[str],
) -> str:
    if secret_detected or force_push_detected or main_push_detected:
        return "critical"
    if protected_branch_detected or files_blocked:
        return "high"
    return "low" if push_eligible else "medium"


def _reason(*, push_eligible: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "Controlled push gate blocked this eligibility request."
    if dry_run:
        return "Controlled push gate evaluated evidence in dry-run mode without eligibility."
    if push_eligible:
        return "Controlled push gate marked this branch eligible for a future push phase."
    return "Controlled push gate did not mark this branch eligible."


def _escalation_reason(requires_human: bool) -> str | None:
    return "Controlled push gate requires human intervention." if requires_human else None


def _coerce_request(value: ControlledPushGateRequest | Mapping[str, Any] | Any) -> ControlledPushGateRequest:
    if isinstance(value, ControlledPushGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Push gate input must be a request, mapping, or object.")
    return ControlledPushGateRequest(
        commit_executor_result=_coerce_mapping(payload.get("commit_executor_result")),
        commit_gate_result=_coerce_mapping(payload.get("commit_gate_result")),
        post_patch_validation_result=_coerce_mapping(payload.get("post_patch_validation_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        push_gate_mode=str(payload.get("push_gate_mode") or DEFAULT_PUSH_GATE_MODE),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        remote_name=str(payload["remote_name"]) if "remote_name" in payload else "origin",
        remote_branch=payload.get("remote_branch"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        commit_sha=payload.get("commit_sha"),
        pre_commit_head=payload.get("pre_commit_head"),
        post_commit_head=payload.get("post_commit_head"),
        files_committed=list(payload.get("files_committed") or []),
        proposed_push_ref=payload.get("proposed_push_ref"),
        require_commit_executed=bool(payload.get("require_commit_executed", True)),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_commit_evidence=bool(payload.get("require_clean_commit_evidence", True)),
        require_no_uncommitted_changes=bool(payload.get("require_no_uncommitted_changes", False)),
        allow_push_execution=bool(payload.get("allow_push_execution", False)),
        allow_force_push=bool(payload.get("allow_force_push", False)),
        allow_main_push=bool(payload.get("allow_main_push", False)),
        allow_protected_branch_push=bool(payload.get("allow_protected_branch_push", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_rebase=bool(payload.get("allow_rebase", False)),
        allow_branch_create=bool(payload.get("allow_branch_create", False)),
        allow_checkout=bool(payload.get("allow_checkout", False)),
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


def _redact_list(values: list[object]) -> tuple[list[str], bool]:
    redacted_values = []
    redacted = False
    for value in values:
        text, was_redacted = _redact_text(value)
        redacted_values.append(text)
        redacted = redacted or was_redacted
    return redacted_values, redacted


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
