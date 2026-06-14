"""Controlled branch patch application for governed sandbox proposals.

Phase 21 is denied by default and writes only safe scoped files when every
gate passes. It does not run commands, mutate Git, create pull requests, call
providers, call agents, use MCP, or write Vault notes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .patch_applier_truth import (
    PATCH_APPLIER_EVIDENCE_VERSION,
    build_patch_applier_evidence,
)
from .patch_applier_types import (
    ControlledPatchApplierRequest,
    ControlledPatchApplierResult,
)

APPLIER_MODES = frozenset({"disabled", "dry_run", "apply_to_branch", "blocked"})
DEFAULT_APPLIER_MODE = "disabled"
MAIN_BRANCH = "main"

_SUPPORTED_OPERATIONS = {"modify_existing", "add_test", "add_documentation"}
_UNSUPPORTED_OPERATIONS = {
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
}
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
_SAFE_COMMAND_PREFIXES = (
    "python -m pytest",
    "pytest",
    "npm test",
    "npm run test",
    "npm run build",
    "npm run lint",
    "npm run typecheck",
    "cargo test",
    "cargo check",
    "cargo clippy",
    "cargo fmt --check",
    "git diff --check",
    "python -m json.tool",
    "python -m compileall",
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


def apply_controlled_patch(
    request_or_mapping: ControlledPatchApplierRequest | Mapping[str, Any] | Any,
) -> ControlledPatchApplierResult:
    request = _coerce_request(request_or_mapping)
    proposal_source = _coerce_mapping(request.patch_proposal)
    proposals = _proposal_list(request, proposal_source)
    applier_mode = str(request.applier_mode or DEFAULT_APPLIER_MODE).strip() or DEFAULT_APPLIER_MODE
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(request.target_branch or proposal_source.get("target_branch"))
    files_requested = [_redact_text(item.get("file_path"))[0] for item in proposals if item.get("file_path")]
    validation_commands, commands_redacted = _redact_list(_safe_validation_commands(proposals, proposal_source))
    secret_detected = any(
        (
            requested_by_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            commands_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            _contains_credential_like(str(proposals)),
            _contains_credential_like(str(proposal_source)),
        )
    )
    workspace_path, workspace_issue = _workspace_path(request.workspace_root)
    global_block = _global_block_reason(
        request=request,
        applier_mode=applier_mode,
        workspace_issue=workspace_issue,
        secret_detected=secret_detected,
    )

    files_considered: list[str] = []
    files_applied: list[str] = []
    files_blocked: list[str] = []
    applied_changes: list[dict[str, object]] = []
    blocked_changes: list[dict[str, object]] = []
    pre_hashes: dict[str, str | None] = {}
    post_hashes: dict[str, str | None] = {}
    hunks_requested = 0
    hunks_applied = 0
    hunks_blocked = 0
    file_budget = max(1, int(request.max_files_to_apply or 5))
    total_hunk_budget = max(1, int(request.max_total_hunks or 20))
    if not global_block:
        for proposal in proposals:
            if len(files_considered) >= file_budget:
                files_blocked.append(_redact_text(proposal.get("file_path"))[0])
                blocked_changes.append(_blocked_change(proposal, None, "max_files_to_apply limit reached"))
                continue
            file_path = _redact_text(proposal.get("file_path"))[0]
            files_considered.append(file_path)
            target_path, path_issue = _target_path(workspace_path, proposal.get("file_path"))
            proposal_issue = _proposal_issue(request, proposal, file_path, path_issue)
            hunks = list(proposal.get("hunks") or [])[: max(1, int(request.max_hunks_per_file or 8))]
            hunks_requested += len(hunks)
            if proposal_issue:
                files_blocked.append(file_path)
                hunks_blocked += len(hunks)
                blocked_changes.append(_blocked_change(proposal, None, proposal_issue))
                continue
            original = _read_target_text(target_path)
            pre_hashes[file_path] = _sha256_text(original) if original is not None else None
            updated = original
            file_applied_hunks: list[str] = []
            for hunk in hunks:
                if hunks_applied + hunks_blocked >= total_hunk_budget:
                    hunks_blocked += 1
                    blocked_changes.append(_blocked_change(proposal, hunk, "max_total_hunks limit reached"))
                    continue
                hunk_issue = _hunk_issue(hunk)
                if hunk_issue:
                    hunks_blocked += 1
                    blocked_changes.append(_blocked_change(proposal, hunk, hunk_issue))
                    continue
                next_text, apply_issue = _apply_hunk(
                    operation=str(proposal.get("operation") or ""),
                    current_text=updated,
                    before_context=str(hunk.get("before_context") or ""),
                    proposed_snippet=str(hunk.get("proposed_snippet") or ""),
                    file_exists=target_path.exists(),
                    allow_file_create=request.allow_file_create,
                    max_file_bytes=request.max_file_bytes,
                )
                if apply_issue:
                    hunks_blocked += 1
                    blocked_changes.append(_blocked_change(proposal, hunk, apply_issue))
                    continue
                updated = next_text
                hunks_applied += 1
                file_applied_hunks.append(str(hunk.get("hunk_id") or "unknown-hunk"))
            if file_applied_hunks and updated is not None:
                if applier_mode == "apply_to_branch":
                    _write_target_text(target_path, updated)
                    post_hashes[file_path] = _sha256_text(_read_target_text(target_path) or "")
                else:
                    post_hashes[file_path] = _sha256_text(updated)
                files_applied.append(file_path)
                applied_changes.append(
                    {
                        "file_path": file_path,
                        "operation": proposal.get("operation"),
                        "hunk_ids": file_applied_hunks,
                        "dry_run": applier_mode == "dry_run",
                    }
                )
            elif file_path not in files_blocked:
                files_blocked.append(file_path)

    dry_run = applier_mode == "dry_run" and not global_block
    actual_write = applier_mode == "apply_to_branch" and bool(files_applied)
    applied = actual_write
    partial = bool(files_applied and blocked_changes)
    blocked = bool(global_block) or (not files_applied and bool(blocked_changes))
    success = bool((applied or dry_run) and not global_block)
    requires_human = bool(secret_detected or global_block or _human_required(request, proposals, files_blocked))
    runtime_truth = build_patch_applier_evidence(
        applier_mode=applier_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        applied=applied,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        files_requested_count=len(files_requested),
        files_considered_count=len(files_considered),
        files_applied_count=len(files_applied),
        files_blocked_count=len(set(files_blocked)),
        hunks_requested_count=hunks_requested,
        hunks_applied_count=hunks_applied if applied else 0,
        hunks_blocked_count=hunks_blocked,
        secrets_detected=secret_detected,
        human_intervention_required=requires_human,
        escalation_reason=global_block or _escalation_reason(requires_human, files_blocked),
    ).to_dict()
    return ControlledPatchApplierResult(
        applied=applied,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        partial=partial,
        applier_mode=applier_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        files_requested=files_requested,
        files_considered=files_considered,
        files_applied=files_applied,
        files_blocked=sorted(set(files_blocked)),
        hunks_requested=hunks_requested,
        hunks_applied=hunks_applied if applied else 0,
        hunks_blocked=hunks_blocked,
        applied_changes=applied_changes,
        blocked_changes=blocked_changes,
        validation_commands=validation_commands,
        required_followup_tests=list(validation_commands),
        pre_apply_hashes=pre_hashes,
        post_apply_hashes=post_hashes,
        can_commit=False,
        can_push=False,
        can_open_pr=False,
        can_merge=False,
        can_execute_tests=False,
        requires_followup_validation=applied,
        requires_human_intervention=requires_human,
        reason=_reason(applied=applied, dry_run=dry_run, blocked_reason=global_block),
        blocked_reason=global_block,
        escalation_reason=global_block or _escalation_reason(requires_human, files_blocked),
        runtime_truth=runtime_truth,
        evidence_version=PATCH_APPLIER_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _coerce_request(value: ControlledPatchApplierRequest | Mapping[str, Any] | Any) -> ControlledPatchApplierRequest:
    if isinstance(value, ControlledPatchApplierRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Patch applier input must be a request, mapping, or object.")
    return ControlledPatchApplierRequest(
        patch_proposal=_coerce_mapping(payload.get("patch_proposal")),
        patch_proposals=list(payload.get("patch_proposals") or []),
        requested_by=str(payload.get("requested_by") or "unknown"),
        applier_mode=str(payload.get("applier_mode") or DEFAULT_APPLIER_MODE),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        allowed_files=list(payload.get("allowed_files") or []),
        blocked_files=list(payload.get("blocked_files") or []),
        max_files_to_apply=int(payload.get("max_files_to_apply") or 5),
        max_hunks_per_file=int(payload.get("max_hunks_per_file") or 8),
        max_total_hunks=int(payload.get("max_total_hunks") or 20),
        max_file_bytes=int(payload.get("max_file_bytes") or 500000),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_validation_commands=bool(payload.get("require_validation_commands", True)),
        allow_file_create=bool(payload.get("allow_file_create", False)),
        allow_file_delete=bool(payload.get("allow_file_delete", False)),
        allow_file_rename=bool(payload.get("allow_file_rename", False)),
        allow_chmod=bool(payload.get("allow_chmod", False)),
        allow_dependency_change=bool(payload.get("allow_dependency_change", False)),
        allow_ci_change=bool(payload.get("allow_ci_change", False)),
        allow_governance_change=bool(payload.get("allow_governance_change", False)),
        allow_security_change=bool(payload.get("allow_security_change", False)),
        allow_vault_write=bool(payload.get("allow_vault_write", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
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


def _proposal_list(
    request: ControlledPatchApplierRequest,
    proposal_source: Mapping[str, Any],
) -> list[dict[str, Any]]:
    proposals = list(request.patch_proposals or proposal_source.get("patch_proposals") or [])
    return [_coerce_mapping(item) for item in proposals]


def _workspace_path(raw_workspace: str | None) -> tuple[Path | None, str | None]:
    if not raw_workspace:
        return None, "workspace_root is required for patch application."
    raw = str(raw_workspace).strip()
    if ".." in raw.replace("\\", "/").split("/"):
        return None, "workspace_root must not contain path traversal."
    path = Path(raw).expanduser().resolve()
    anchor = Path(path.anchor).resolve()
    if path == anchor:
        return None, "workspace_root must not be a filesystem root."
    return path, None


def _target_path(workspace_path: Path | None, raw_path: object) -> tuple[Path | None, str | None]:
    if workspace_path is None:
        return None, "workspace_root is invalid."
    normalized = _normalize_path(raw_path)
    if normalized is None:
        return None, "target path is outside the allowed relative path model."
    target = (workspace_path / normalized).resolve()
    if not _is_relative_to(target, workspace_path):
        return None, "target path escapes workspace_root."
    return target, None


def _normalize_path(path: object) -> str | None:
    text = str(path or "").replace("\\", "/").strip()
    if not text or ".." in text.split("/") or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    redacted, _ = _redact_text(text)
    return redacted


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _global_block_reason(
    *,
    request: ControlledPatchApplierRequest,
    applier_mode: str,
    workspace_issue: str | None,
    secret_detected: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if applier_mode not in APPLIER_MODES:
        return "Patch applier mode is unknown."
    if applier_mode == "disabled":
        return "Patch applier is disabled by default."
    if applier_mode == "blocked":
        return "Patch applier mode blocks all application."
    if applier_mode == "apply_to_branch" and workspace_issue:
        return workspace_issue
    if request.require_non_main_branch:
        current = str(request.current_branch or "").strip().lower()
        target = str(request.target_branch or "").strip().lower()
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
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if any(
        (
            request.allow_file_delete,
            request.allow_file_rename,
            request.allow_chmod,
            request.allow_dependency_change,
            request.allow_ci_change,
            request.allow_governance_change,
            request.allow_security_change,
            request.allow_vault_write,
            request.allow_git_mutation,
        )
    ):
        return "Phase 21 cannot enable delete, rename, chmod, dependency, CI, governance, security, Vault, or Git mutation capabilities."
    return None


def _proposal_issue(
    request: ControlledPatchApplierRequest,
    proposal: Mapping[str, Any],
    file_path: str,
    path_issue: str | None,
) -> str | None:
    if path_issue:
        return path_issue
    if _path_block_reason(file_path):
        return _path_block_reason(file_path)
    if file_path in request.blocked_files:
        return "target file is explicitly blocked."
    allowed = [_normalize_path(item) for item in request.allowed_files]
    if allowed and file_path not in allowed:
        return "target file is outside allowed_files."
    operation = str(proposal.get("operation") or "")
    if operation in _UNSUPPORTED_OPERATIONS:
        return "operation is unsupported by Phase 21."
    if operation not in _SUPPORTED_OPERATIONS:
        return "operation is unknown or unsupported."
    if proposal.get("requires_human") is True:
        return "proposal requires human intervention."
    if proposal.get("allowed_in_future_patch_apply") is False:
        return "proposal is not allowed for future patch application."
    if str(proposal.get("risk_level") or "").lower() in {"high", "critical"}:
        return "proposal risk is too high for controlled application."
    return None


def _path_block_reason(path: str) -> str | None:
    lowered = str(path or "").replace("\\", "/").lower()
    if _contains_credential_like(path):
        return "target path contains secret-like content."
    if lowered.startswith(".git/"):
        return "repository internals are blocked."
    if any(lowered.startswith(prefix.lower()) for prefix in _PROTECTED_PREFIXES):
        return "protected governance, security, ADR, or CI file is blocked."
    if any(marker in lowered for marker in ("production", "deploy", "billing", "secret", "credential", "private")):
        return "production, deploy, billing, or credential file scope is blocked."
    if lowered.endswith(("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock")):
        return "lockfile mutation is blocked in this phase."
    if not any(lowered.startswith(prefix.lower()) for prefix in _ALLOWED_PREFIXES):
        return "target path is outside allowed file scopes."
    return None


def _hunk_issue(hunk: Mapping[str, Any]) -> str | None:
    before_context = str(hunk.get("before_context") or "")
    proposed_snippet = str(hunk.get("proposed_snippet") or "")
    if not proposed_snippet:
        return "proposed_snippet is required."
    if _contains_credential_like(before_context) or _contains_credential_like(proposed_snippet):
        return "hunk contains secret-like content."
    if str(hunk.get("risk_level") or "").lower() in {"high", "critical"}:
        return "hunk risk is too high for controlled application."
    return None


def _apply_hunk(
    *,
    operation: str,
    current_text: str | None,
    before_context: str,
    proposed_snippet: str,
    file_exists: bool,
    allow_file_create: bool,
    max_file_bytes: int,
) -> tuple[str | None, str | None]:
    if operation == "modify_existing":
        if current_text is None:
            return None, "modify_existing requires an existing file."
        if not before_context:
            return None, "before_context is required for modify_existing."
        occurrences = current_text.count(before_context)
        if occurrences == 0:
            return None, "before_context was not found."
        if occurrences > 1:
            return None, "before_context is ambiguous."
        updated = current_text.replace(before_context, proposed_snippet, 1)
        return _bounded_text(updated, max_file_bytes)
    if operation in {"add_test", "add_documentation"}:
        if current_text is None:
            if not allow_file_create:
                return None, "file creation is not allowed."
            return _bounded_text(proposed_snippet, max_file_bytes)
        separator = "" if current_text.endswith("\n") else "\n"
        return _bounded_text(f"{current_text}{separator}{proposed_snippet}", max_file_bytes)
    return None, "operation is unsupported."


def _bounded_text(text: str, max_file_bytes: int) -> tuple[str | None, str | None]:
    if len(text.encode("utf-8")) > int(max_file_bytes or 500000):
        return None, "updated file would exceed max_file_bytes."
    return text, None


def _read_target_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _write_target_text(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_validation_commands(
    proposals: list[Mapping[str, Any]],
    proposal_source: Mapping[str, Any],
) -> list[str]:
    candidates: list[str] = []
    for proposal in proposals:
        candidates.extend(str(item).strip() for item in proposal.get("validation_commands") or [])
    candidates.extend(str(item).strip() for item in proposal_source.get("validation_commands") or [])
    safe = []
    for command in candidates:
        lowered = command.lower()
        blocked = ("git add", "git commit", "git push", "git merge", "git rebase", "gh ", "curl", "wget")
        if command and not any(item in lowered for item in blocked) and any(
            lowered.startswith(prefix) for prefix in _SAFE_COMMAND_PREFIXES
        ):
            safe.append(command)
    return safe


def _blocked_change(
    proposal: Mapping[str, Any],
    hunk: Mapping[str, Any] | None,
    reason: str,
) -> dict[str, object]:
    return {
        "file_path": _redact_text(proposal.get("file_path"))[0],
        "operation": proposal.get("operation"),
        "hunk_id": None if hunk is None else hunk.get("hunk_id"),
        "reason": reason,
    }


def _human_required(
    request: ControlledPatchApplierRequest,
    proposals: list[Mapping[str, Any]],
    files_blocked: list[str],
) -> bool:
    if files_blocked:
        return True
    if any(proposal.get("requires_human") is True for proposal in proposals):
        return True
    return any(
        (
            request.allow_file_delete,
            request.allow_file_rename,
            request.allow_chmod,
            request.allow_dependency_change,
            request.allow_ci_change,
            request.allow_governance_change,
            request.allow_security_change,
            request.allow_vault_write,
            request.allow_git_mutation,
        )
    )


def _escalation_reason(requires_human: bool, files_blocked: list[str]) -> str | None:
    if not requires_human:
        return None
    if files_blocked:
        return "One or more patch changes were blocked and require human review."
    return "Patch application requires human intervention."


def _reason(*, applied: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "Controlled patch applier blocked this request."
    if dry_run:
        return "Controlled patch applier validated changes in dry-run mode without writing files."
    if applied:
        return "Controlled patch applier wrote safe scoped files only."
    return "Controlled patch applier did not apply any changes."


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
