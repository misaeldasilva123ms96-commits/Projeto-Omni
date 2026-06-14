"""Controlled commit eligibility gate.

Phase 23 evaluates whether validated patch evidence is eligible for a future
commit phase. It never stages files, commits, pushes, mutates Git, executes
commands, edits files, applies patches, calls providers, uses MCP, calls
agents, or writes Vault notes.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .commit_gate_truth import (
    COMMIT_GATE_EVIDENCE_VERSION,
    build_commit_gate_evidence,
)
from .commit_gate_types import ControlledCommitGateRequest, ControlledCommitGateResult

COMMIT_GATE_MODES = frozenset({"disabled", "dry_run", "evaluate_commit", "blocked"})
DEFAULT_COMMIT_GATE_MODE = "disabled"
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
    ".circleci/",
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
)


def evaluate_commit_gate(
    request_or_mapping: ControlledCommitGateRequest | Mapping[str, Any] | Any,
) -> ControlledCommitGateResult:
    request = _coerce_request(request_or_mapping)
    validation = _coerce_mapping(request.post_patch_validation_result)
    patch_apply = _coerce_mapping(request.patch_apply_result)
    patch_proposal = _coerce_mapping(request.patch_proposal_result)
    repair_plan = _coerce_mapping(request.repair_plan)
    validation_truth = _coerce_mapping(validation.get("runtime_truth"))
    patch_truth = _coerce_mapping(patch_apply.get("runtime_truth"))
    mode = str(request.commit_gate_mode or DEFAULT_COMMIT_GATE_MODE).strip() or DEFAULT_COMMIT_GATE_MODE
    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root or validation.get("workspace_root") or patch_apply.get("workspace_root"))
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(request.target_branch)
    commit_hint, hint_redacted = _redact_optional(request.commit_message_hint)
    files_considered, files_redacted = _redact_list(_files_considered(request, validation, patch_apply))
    files_eligible, files_blocked = _classify_files(files_considered, request.allow_protected_files)
    protected_detected = bool(files_blocked)
    validation_summary, summary_redacted = _redact_optional(
        request.validation_summary or validation.get("validation_summary")
    )
    source_truths = [truth for truth in (validation_truth, patch_truth, _coerce_mapping(patch_proposal.get("runtime_truth")), _coerce_mapping(repair_plan.get("runtime_truth"))) if truth]
    source_flags = _source_flags(source_truths)
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            hint_redacted,
            files_redacted,
            summary_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            source_flags["secrets_detected"],
        )
    )
    patch_was_applied = bool(patch_apply.get("applied") is True or validation.get("patch_was_applied") is True)
    post_patch_validated = bool(validation.get("validated") is True)
    validation_passed = bool(validation.get("success") is True and validation.get("ready_for_commit") is True)
    validation_failed = bool(validation.get("failed") is True)
    validation_timed_out = bool(validation.get("timed_out") is True)
    git_mutation = bool(source_flags["git_mutated"])
    main_modified = bool(source_flags["main_modified"])
    disallowed_source_activity = any(
        source_flags[key]
        for key in (
            "pr_created",
            "pr_merged",
            "command_executed",
            "provider_called",
            "network_used",
            "mcp_used",
            "vault_written",
        )
    )
    blocked_reason = _blocked_reason(
        request=request,
        mode=mode,
        secret_detected=secret_detected,
        validation=validation,
        patch_apply=patch_apply,
        patch_truth=patch_truth,
        branch_block=_branch_block_reason(request, current_branch, target_branch),
        protected_detected=protected_detected,
        git_mutation=git_mutation,
        main_modified=main_modified,
        disallowed_source_activity=disallowed_source_activity,
        validation_passed=validation_passed,
        validation_failed=validation_failed,
        validation_timed_out=validation_timed_out,
        patch_was_applied=patch_was_applied,
    )
    dry_run = mode == "dry_run" and not blocked_reason
    evaluated = mode in {"dry_run", "evaluate_commit"} and not blocked_reason
    commit_eligible = bool(
        mode == "evaluate_commit"
        and evaluated
        and validation_passed
        and patch_was_applied
        and files_eligible
        and not files_blocked
        and not secret_detected
        and not git_mutation
        and not main_modified
    )
    commit_type = _commit_type(files_eligible)
    commit_scope = _commit_scope(files_eligible)
    proposed_message = _proposed_message(commit_type, commit_scope, commit_hint, files_eligible)
    if secret_detected:
        proposed_message = "[REDACTED]"
    required_checks = _required_checks()
    commit_plan = _commit_plan(
        commit_type=commit_type,
        commit_scope=commit_scope,
        files=files_eligible,
        validation_summary=validation_summary,
        risk_level="low" if commit_eligible else "high",
        proposed_commit_message=proposed_message,
        required_checks=required_checks,
        eligible=commit_eligible,
        requires_human=bool(
            blocked_reason
            or protected_detected
            or secret_detected
            or git_mutation
            or main_modified
            or disallowed_source_activity
        ),
    )
    blocked = bool(blocked_reason)
    success = bool(evaluated and not blocked)
    requires_human = bool(
        blocked
        or protected_detected
        or secret_detected
        or git_mutation
        or main_modified
        or disallowed_source_activity
    )
    child_events = [dict(truth) for truth in source_truths]
    runtime_truth = build_commit_gate_evidence(
        commit_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        commit_eligible=commit_eligible,
        commit_ready_metadata_only=commit_eligible,
        patch_was_applied=patch_was_applied,
        post_patch_validated=post_patch_validated,
        validation_passed=validation_passed,
        validation_failed=validation_failed,
        validation_timed_out=validation_timed_out,
        files_considered_count=len(files_considered),
        files_eligible_count=len(files_eligible),
        files_blocked_count=len(files_blocked),
        protected_files_detected=protected_detected,
        secrets_detected=secret_detected,
        git_mutation_detected=git_mutation,
        main_modification_detected=main_modified,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason or _escalation_reason(requires_human),
        child_runtime_truth_events=child_events,
    ).to_dict()
    return ControlledCommitGateResult(
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        commit_eligible=commit_eligible,
        commit_ready_metadata_only=commit_eligible,
        commit_gate_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        patch_was_applied=patch_was_applied,
        post_patch_validated=post_patch_validated,
        validation_passed=validation_passed,
        validation_failed=validation_failed,
        validation_timed_out=validation_timed_out,
        protected_files_detected=protected_detected,
        secrets_detected=secret_detected,
        git_mutation_detected=git_mutation,
        main_modification_detected=main_modified,
        files_considered=files_considered,
        files_eligible_for_commit=files_eligible,
        files_blocked_from_commit=files_blocked,
        commit_plan=commit_plan,
        proposed_commit_message=proposed_message,
        validation_summary=validation_summary,
        required_pre_commit_checks=required_checks,
        required_followup_tests=list(validation.get("required_followup_tests") or request.validation_commands),
        can_execute_commit=False,
        can_stage_files=False,
        can_push=False,
        can_open_pr=False,
        can_merge=False,
        can_edit_code=False,
        can_apply_patch=False,
        can_mutate_git=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        requires_human_intervention=requires_human,
        reason=_reason(commit_eligible=commit_eligible, dry_run=dry_run, blocked_reason=blocked_reason),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason or _escalation_reason(requires_human),
        runtime_truth=runtime_truth,
        evidence_version=COMMIT_GATE_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _coerce_request(value: ControlledCommitGateRequest | Mapping[str, Any] | Any) -> ControlledCommitGateRequest:
    if isinstance(value, ControlledCommitGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Commit gate input must be a request, mapping, or object.")
    return ControlledCommitGateRequest(
        post_patch_validation_result=_coerce_mapping(payload.get("post_patch_validation_result")),
        patch_apply_result=_coerce_mapping(payload.get("patch_apply_result")),
        patch_proposal_result=_coerce_mapping(payload.get("patch_proposal_result")),
        repair_plan=_coerce_mapping(payload.get("repair_plan")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        commit_gate_mode=str(payload.get("commit_gate_mode") or DEFAULT_COMMIT_GATE_MODE),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        changed_files=list(payload.get("changed_files") or []),
        files_applied=list(payload.get("files_applied") or []),
        files_blocked=list(payload.get("files_blocked") or []),
        validation_commands=list(payload.get("validation_commands") or []),
        validation_summary=payload.get("validation_summary"),
        commit_message_hint=payload.get("commit_message_hint"),
        require_post_patch_validation=bool(payload.get("require_post_patch_validation", True)),
        require_patch_applied=bool(payload.get("require_patch_applied", True)),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_validation=bool(payload.get("require_clean_validation", True)),
        allow_commit_execution=bool(payload.get("allow_commit_execution", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_protected_files=bool(payload.get("allow_protected_files", False)),
        allow_ci_change=bool(payload.get("allow_ci_change", False)),
        allow_governance_change=bool(payload.get("allow_governance_change", False)),
        allow_security_change=bool(payload.get("allow_security_change", False)),
        allow_vault_write=bool(payload.get("allow_vault_write", False)),
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


def _files_considered(
    request: ControlledCommitGateRequest,
    validation: Mapping[str, Any],
    patch_apply: Mapping[str, Any],
) -> list[str]:
    candidates = (
        request.changed_files
        or request.files_applied
        or patch_apply.get("files_applied")
        or validation.get("files_applied")
        or []
    )
    return list(candidates)


def _classify_files(files: list[str], allow_protected: bool) -> tuple[list[str], list[str]]:
    eligible: list[str] = []
    blocked: list[str] = []
    for raw in files:
        normalized = _normalize_path(raw)
        if normalized is None:
            safe, _ = _redact_text(raw)
            blocked.append(safe)
            continue
        issue = _path_issue(normalized)
        if issue and not allow_protected:
            blocked.append(normalized)
        elif normalized not in eligible:
            eligible.append(normalized)
    return eligible, blocked


def _normalize_path(path: object) -> str | None:
    text = str(path or "").replace("\\", "/").strip()
    if not text or ".." in text.split("/") or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
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
    return {
        "secrets_detected": any(truth.get("secrets_detected") is True for truth in truths),
        "git_mutated": any(truth.get("git_mutated") is True for truth in truths),
        "main_modified": any(truth.get("main_modified") is True for truth in truths),
        "pr_created": any(truth.get("pr_created") is True for truth in truths),
        "pr_merged": any(truth.get("pr_merged") is True for truth in truths),
        "command_executed": any(truth.get("command_executed") is True and truth.get("event_type") == "sandbox.patch_applier.apply" for truth in truths),
        "provider_called": any(truth.get("provider_called") is True for truth in truths),
        "network_used": any(truth.get("network_used") is True for truth in truths),
        "mcp_used": any(truth.get("mcp_used") is True for truth in truths),
        "vault_written": any(truth.get("vault_written") is True for truth in truths),
    }


def _blocked_reason(
    *,
    request: ControlledCommitGateRequest,
    mode: str,
    secret_detected: bool,
    validation: Mapping[str, Any],
    patch_apply: Mapping[str, Any],
    patch_truth: Mapping[str, Any],
    branch_block: str | None,
    protected_detected: bool,
    git_mutation: bool,
    main_modified: bool,
    disallowed_source_activity: bool,
    validation_passed: bool,
    validation_failed: bool,
    validation_timed_out: bool,
    patch_was_applied: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in COMMIT_GATE_MODES:
        return "Controlled commit gate mode is unknown."
    if mode == "disabled":
        return "Controlled commit gate is disabled by default."
    if mode == "blocked":
        return "Controlled commit gate mode blocks all eligibility."
    if any((request.allow_commit_execution, request.allow_git_mutation, request.allow_push, request.allow_pr_creation, request.allow_merge, request.allow_ci_change, request.allow_governance_change, request.allow_security_change, request.allow_vault_write, request.allow_network, request.allow_provider_call, request.allow_agent_call)):
        return "Phase 23 cannot enable commit, Git, push, PR, merge, CI, governance, security, Vault, network, provider, or agent capabilities."
    if branch_block:
        return branch_block
    if request.require_runtime_truth and (request.require_post_patch_validation and not _coerce_mapping(validation.get("runtime_truth"))):
        return "Post-patch validation Runtime Truth is required."
    if request.require_runtime_truth and request.require_patch_applied and not patch_truth:
        return "Patch application Runtime Truth is required."
    if request.require_patch_applied and not patch_was_applied:
        return "Patch application evidence does not show an applied patch."
    if patch_apply.get("success") is False:
        return "Patch application result is not successful."
    if patch_apply.get("files_blocked"):
        return "Patch application reported blocked files."
    if patch_apply.get("requires_followup_validation") is True and not validation:
        return "Post-patch validation is required before commit eligibility."
    if request.require_post_patch_validation and not validation:
        return "Post-patch validation evidence is required."
    if validation.get("blocked") is True:
        return "Post-patch validation is blocked."
    if validation.get("requires_human_intervention") is True:
        return "Post-patch validation requires human intervention."
    if request.require_clean_validation and validation_failed:
        return "Post-patch validation failed."
    if validation_timed_out:
        return "Post-patch validation timed out."
    if request.require_clean_validation and not validation_passed:
        return "Post-patch validation has not passed."
    if protected_detected:
        return "Protected or high-risk files require human intervention."
    if git_mutation:
        return "Source evidence reports Git mutation."
    if main_modified:
        return "Source evidence reports main modification."
    if disallowed_source_activity:
        return "Source evidence reports disallowed runtime activity."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    return None


def _branch_block_reason(
    request: ControlledCommitGateRequest,
    current_branch: str | None,
    target_branch: str | None,
) -> str | None:
    if not request.require_non_main_branch:
        return None
    current = str(current_branch or "").strip().lower()
    target = str(target_branch or "").strip().lower()
    base = str(request.base_branch or "").strip().lower()
    if not current:
        return "current_branch metadata is required."
    if current == MAIN_BRANCH:
        return "current_branch must not be main."
    if current == base:
        return "current_branch must not equal base_branch."
    if target == MAIN_BRANCH:
        return "target_branch must not be main."
    if base != MAIN_BRANCH:
        return "base_branch must be main."
    if current.startswith(("release/", "prod/", "production/")):
        return "protected release or production branch is blocked."
    return None


def _commit_type(files: list[str]) -> str:
    if not files:
        return "unknown"
    if all(path.startswith("tests/") for path in files):
        return "test"
    if all(path.startswith("docs/") or path.startswith("vault/templates/") for path in files):
        return "docs"
    if any(path.startswith(".github/") or path.startswith(".circleci/") for path in files):
        return "ci"
    if any(path.startswith("backend/") or path.startswith("frontend/") for path in files):
        return "fix"
    if any(path.startswith("sandbox/local/") for path in files):
        return "chore"
    return "chore"


def _commit_scope(files: list[str]) -> str:
    if not files:
        return "unknown"
    first = files[0]
    if first.startswith("backend/python/"):
        return "python"
    if first.startswith("backend/rust/"):
        return "rust"
    if first.startswith("frontend/"):
        return "frontend"
    if first.startswith("tests/"):
        return "runtime"
    if first.startswith("docs/"):
        return "docs"
    if first.startswith("sandbox/local/"):
        return "sandbox"
    if first.startswith("vault/templates/"):
        return "vault"
    return "omni"


def _proposed_message(commit_type: str, scope: str, hint: str | None, files: list[str]) -> str:
    if hint:
        safe_hint = " ".join(hint.split())
        return safe_hint[:120]
    summary = "update governed sandbox files"
    if commit_type == "test":
        summary = "add runtime validation coverage"
    elif commit_type == "docs":
        summary = "update governed sandbox documentation"
    elif commit_type == "fix":
        summary = "update governed sandbox runtime"
    elif files:
        summary = "update governed sandbox metadata"
    return f"{commit_type}({scope}): {summary}"[:120]


def _commit_plan(
    *,
    commit_type: str,
    commit_scope: str,
    files: list[str],
    validation_summary: str | None,
    risk_level: str,
    proposed_commit_message: str,
    required_checks: list[str],
    eligible: bool,
    requires_human: bool,
) -> dict[str, object]:
    return {
        "plan_id": "commit-plan-1",
        "commit_type": commit_type,
        "commit_scope": commit_scope,
        "summary": "Metadata-only future commit eligibility plan.",
        "files": files,
        "validation_evidence_summary": validation_summary,
        "risk_level": risk_level,
        "proposed_commit_message": proposed_commit_message,
        "required_checks_before_execution": required_checks,
        "allowed_in_future_commit_execution": eligible,
        "requires_human": requires_human,
    }


def _required_checks() -> list[str]:
    return [
        "post_patch_validation_passed",
        "runtime_truth_clean",
        "non_main_branch_confirmed",
        "protected_files_absent",
        "secrets_absent",
        "git_mutation_absent",
        "main_modification_absent",
        "validation_commands_recorded",
        "commit_message_safe",
    ]


def _reason(*, commit_eligible: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "Controlled commit gate blocked this eligibility request."
    if dry_run:
        return "Controlled commit gate evaluated evidence in dry-run mode without eligibility."
    if commit_eligible:
        return "Controlled commit gate marked this change eligible for a future commit phase."
    return "Controlled commit gate did not mark this change eligible."


def _escalation_reason(requires_human: bool) -> str | None:
    return "Controlled commit gate requires human intervention." if requires_human else None


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
