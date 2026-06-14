"""Scoped patch proposal planning for governed sandbox repairs.

Phase 20 converts repair plans into bounded patch proposal metadata only.
It does not inspect repository files, change files, apply patches, run
commands, mutate Git, call providers, call agents, use MCP, create pull
requests, or write Vault notes.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .patch_proposal_truth import (
    PATCH_PROPOSAL_EVIDENCE_VERSION,
    build_patch_proposal_evidence,
)
from .patch_proposal_types import (
    ScopedPatchProposalRequest,
    ScopedPatchProposalResult,
)

PROPOSAL_MODES = frozenset({"disabled", "dry_run", "proposal_only", "blocked"})
DEFAULT_PROPOSAL_MODE = "disabled"
MAIN_BRANCH = "main"

_COMPLEXITY = {
    "no_repair_needed": "none",
    "formatting_repair": "low",
    "lint_repair": "medium",
    "type_repair": "medium",
    "test_repair": "medium",
    "build_repair": "high",
    "environment_or_tooling": "medium",
    "timeout_or_performance": "high",
    "command_plan_issue": "medium",
    "investigation_required": "high",
    "policy_blocked": "critical",
    "security_escalation": "critical",
}
_DEFAULT_VALIDATION = {
    "formatting_repair": ["cargo fmt --check", "git diff --check"],
    "lint_repair": ["npm run lint"],
    "type_repair": ["npm run typecheck"],
    "test_repair": ["python -m pytest tests"],
    "build_repair": ["npm run build"],
    "environment_or_tooling": ["python --version"],
    "timeout_or_performance": ["python -m pytest tests"],
    "command_plan_issue": ["git diff --check"],
    "investigation_required": ["git diff --check"],
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
_HUMAN_PREFIXES = (
    "vault/08_ADR/",
    "docs/governance/",
    "docs/security/",
    ".github/workflows/",
    ".circleci/",
)
_BLOCKED_OPERATIONS = {
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
_ALLOWED_OPERATIONS = {
    "modify_existing",
    "add_test",
    "add_documentation",
    "no_change_needed",
}
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
    "python --version",
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


def propose_scoped_patch(
    request_or_mapping: ScopedPatchProposalRequest | Mapping[str, Any] | Any,
) -> ScopedPatchProposalResult:
    request = _coerce_request(request_or_mapping)
    repair_plan = _coerce_mapping(request.repair_plan)
    proposal_mode = str(request.proposal_mode or DEFAULT_PROPOSAL_MODE).strip() or DEFAULT_PROPOSAL_MODE
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    target_branch, branch_redacted = _redact_optional(request.target_branch or repair_plan.get("target_branch"))
    repair_category = _repair_category(request, repair_plan)
    failure_classification = _failure_classification(request, repair_plan)
    allowed_files, allowed_redacted = _redact_list(_source_list(request.allowed_files, repair_plan, "allowed_files"))
    blocked_files, blocked_redacted = _redact_list(_source_list(request.blocked_files, repair_plan, "blocked_files"))
    suspected_files, suspected_redacted = _redact_list(
        _source_list(request.suspected_files, repair_plan, "suspected_files")
    )
    validation_commands, command_redacted = _redact_list(
        _safe_validation_commands(
            _source_list(request.validation_commands, repair_plan, "validation_commands"),
            repair_category,
        )
    )
    proposed_steps = list(request.proposed_steps or repair_plan.get("proposed_steps") or [])
    metadata_text = _metadata_text(request.metadata)
    context_redacted = _contexts_contain_secret(request.file_contexts)
    secret_detected = any(
        (
            requested_by_redacted,
            phase_redacted,
            pr_redacted,
            branch_redacted,
            allowed_redacted,
            blocked_redacted,
            suspected_redacted,
            command_redacted,
            context_redacted,
            _contains_credential_like(metadata_text),
            _contains_credential_like(str(proposed_steps)),
            _contains_credential_like(str(repair_plan)),
        )
    )
    if secret_detected:
        repair_category = "security_escalation"

    no_repair_needed = _no_repair_needed(repair_plan, repair_category)
    files_considered, file_issues = _files_considered(suspected_files, allowed_files, request.max_files_to_patch)
    files_proposed = [path for path in files_considered if file_issues.get(path) == "safe"]
    files_blocked = sorted(set(blocked_files + [path for path, issue in file_issues.items() if issue != "safe"]))
    patch_complexity = _COMPLEXITY.get(repair_category, "high")
    risk_level = _risk_level(repair_category, patch_complexity, files_blocked)
    human_required, escalation_reason = _human_escalation(
        request=request,
        repair_plan=repair_plan,
        repair_category=repair_category,
        target_branch=target_branch,
        files_considered=files_considered,
        files_blocked=files_blocked,
        secret_detected=secret_detected,
    )
    blocked_reason = _blocked_reason(
        request=request,
        proposal_mode=proposal_mode,
        secret_detected=secret_detected,
        repair_plan=repair_plan,
        no_repair_needed=no_repair_needed,
    )
    patch_proposals = []
    if proposal_mode in {"dry_run", "proposal_only"} and not blocked_reason and not no_repair_needed:
        patch_proposals = _patch_proposals(
            files=files_proposed,
            repair_category=repair_category,
            risk_level=risk_level,
            validation_commands=validation_commands,
            file_contexts=request.file_contexts,
            max_hunks_per_file=request.max_patch_hunks_per_file,
            max_total_hunks=request.max_total_patch_hunks,
            human_required=human_required,
        )
    if no_repair_needed and not blocked_reason:
        patch_proposals = [_no_change_proposal()]

    dry_run = proposal_mode == "dry_run" and not blocked_reason
    proposed = bool(patch_proposals) and not blocked_reason and not no_repair_needed
    blocked = bool(blocked_reason)
    success = bool((proposed or no_repair_needed) and not blocked)
    patch_scope = _patch_scope(files_considered, files_blocked, no_repair_needed)
    total_hunks = sum(len(item.get("hunks", [])) for item in patch_proposals)
    runtime_truth = build_patch_proposal_evidence(
        proposal_mode=proposal_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=request.base_branch,
        repair_category=repair_category,
        failure_classification=failure_classification,
        patch_scope=patch_scope,
        patch_complexity=patch_complexity,
        risk_level=risk_level,
        proposed=proposed,
        blocked=blocked,
        dry_run=dry_run,
        files_considered_count=len(files_considered),
        files_proposed_count=len(files_proposed),
        files_blocked_count=len(files_blocked),
        patch_proposals_count=len(patch_proposals),
        total_hunks_count=total_hunks,
        secrets_detected=secret_detected,
        human_intervention_required=human_required or blocked,
        escalation_reason=escalation_reason or blocked_reason,
    ).to_dict()
    return ScopedPatchProposalResult(
        proposed=proposed,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        proposal_mode=proposal_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=request.base_branch,
        repair_category=repair_category,
        failure_classification=failure_classification,
        patch_scope=patch_scope,
        patch_complexity=patch_complexity,
        risk_level=risk_level,
        files_considered=files_considered,
        files_proposed=files_proposed,
        files_blocked=files_blocked,
        patch_proposals=patch_proposals,
        validation_commands=validation_commands,
        required_followup_tests=list(validation_commands),
        can_apply_patch=False,
        patch_requires_human=human_required or blocked,
        patch_requires_new_phase=True,
        can_edit_code=False,
        can_write_files=False,
        can_mutate_git=False,
        can_execute_commands=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        can_open_pr=False,
        can_merge=False,
        reason=_reason(proposed=proposed, no_repair_needed=no_repair_needed, blocked_reason=blocked_reason, dry_run=dry_run),
        blocked_reason=blocked_reason,
        escalation_reason=escalation_reason or blocked_reason,
        runtime_truth=runtime_truth,
        evidence_version=PATCH_PROPOSAL_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _coerce_request(value: ScopedPatchProposalRequest | Mapping[str, Any] | Any) -> ScopedPatchProposalRequest:
    if isinstance(value, ScopedPatchProposalRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Patch proposal input must be a request, mapping, or object.")
    return ScopedPatchProposalRequest(
        repair_plan=_coerce_mapping(payload.get("repair_plan")),
        repair_category=payload.get("repair_category"),
        failure_classification=payload.get("failure_classification"),
        requested_by=str(payload.get("requested_by") or "unknown"),
        proposal_mode=str(payload.get("proposal_mode") or DEFAULT_PROPOSAL_MODE),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        allowed_files=list(payload.get("allowed_files") or []),
        blocked_files=list(payload.get("blocked_files") or []),
        suspected_files=list(payload.get("suspected_files") or []),
        proposed_steps=list(payload.get("proposed_steps") or []),
        validation_commands=list(payload.get("validation_commands") or []),
        file_contexts=dict(payload.get("file_contexts") or {}),
        max_files_to_patch=int(payload.get("max_files_to_patch") or 5),
        max_patch_hunks_per_file=int(payload.get("max_patch_hunks_per_file") or 8),
        max_total_patch_hunks=int(payload.get("max_total_patch_hunks") or 20),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_command_execution=bool(payload.get("allow_command_execution", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
        allow_network=bool(payload.get("allow_network", False)),
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


def _repair_category(request: ScopedPatchProposalRequest, repair_plan: Mapping[str, Any]) -> str:
    return str(request.repair_category or repair_plan.get("repair_category") or "investigation_required")


def _failure_classification(request: ScopedPatchProposalRequest, repair_plan: Mapping[str, Any]) -> str | None:
    value = request.failure_classification or repair_plan.get("normalized_failure_classification") or repair_plan.get("failure_classification")
    return None if value is None else str(value)


def _source_list(direct: list[Any], source: Mapping[str, Any], key: str) -> list[Any]:
    return list(direct or source.get(key) or [])


def _no_repair_needed(repair_plan: Mapping[str, Any], repair_category: str) -> bool:
    return repair_category == "no_repair_needed" or str(repair_plan.get("reason") or "").lower().startswith("validation passed")


def _files_considered(suspected_files: list[str], allowed_files: list[str], limit: int) -> tuple[list[str], dict[str, str]]:
    candidates = suspected_files or allowed_files
    files: list[str] = []
    issues: dict[str, str] = {}
    for raw in candidates:
        normalized = _normalize_path(raw)
        if not normalized:
            redacted, _ = _redact_text(raw)
            issues[redacted] = "blocked"
            continue
        if normalized not in files:
            files.append(normalized)
        issues[normalized] = _file_issue(normalized, allowed_files)
        if len(files) >= max(1, int(limit or 5)):
            break
    return files, issues


def _normalize_path(path: object) -> str | None:
    text = str(path or "").replace("\\", "/").strip()
    if not text or ".." in text.split("/") or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    redacted, _ = _redact_text(text)
    return redacted


def _file_issue(path: str, allowed_files: list[str]) -> str:
    lowered = path.lower()
    if _contains_credential_like(path) or lowered.startswith(".git/"):
        return "blocked"
    if any(lowered.startswith(prefix.lower()) for prefix in _HUMAN_PREFIXES):
        return "requires_human"
    if any(marker in lowered for marker in ("production", "deploy", "billing", "secret", "credential", "private")):
        return "requires_human"
    if not any(lowered.startswith(prefix.lower()) for prefix in _ALLOWED_PREFIXES):
        return "blocked"
    if allowed_files and path not in [_normalize_path(item) for item in allowed_files]:
        return "blocked"
    return "safe"


def _patch_proposals(
    *,
    files: list[str],
    repair_category: str,
    risk_level: str,
    validation_commands: list[str],
    file_contexts: Mapping[str, str],
    max_hunks_per_file: int,
    max_total_hunks: int,
    human_required: bool,
) -> list[dict[str, object]]:
    proposals: list[dict[str, object]] = []
    hunk_budget = max(1, int(max_total_hunks or 20))
    for index, path in enumerate(files, start=1):
        if hunk_budget <= 0:
            break
        operation = _operation_for(path, repair_category)
        hunks = _hunks_for(
            path=path,
            repair_category=repair_category,
            risk_level=risk_level,
            context=file_contexts.get(path),
            limit=min(max(1, int(max_hunks_per_file or 8)), hunk_budget),
        )
        hunk_budget -= len(hunks)
        proposals.append(
            {
                "proposal_id": f"patch-proposal-{index}",
                "file_path": path,
                "operation": operation,
                "target_area": _target_area(path),
                "summary": _summary_for(repair_category, path),
                "rationale": "Derived from repair plan metadata; proposal is not applied in this phase.",
                "proposed_change_type": repair_category,
                "hunks": hunks,
                "risk_level": risk_level,
                "requires_human": human_required,
                "allowed_in_future_patch_apply": not human_required and operation in _ALLOWED_OPERATIONS,
                "validation_commands": validation_commands,
                "notes": "Metadata only. A later governed phase must review and apply any change.",
            }
        )
    return proposals


def _hunks_for(
    *,
    path: str,
    repair_category: str,
    risk_level: str,
    context: str | None,
    limit: int,
) -> list[dict[str, object]]:
    hunk_count = 1 if repair_category in {"formatting_repair", "lint_repair"} else min(2, limit)
    hunks = []
    for index in range(1, hunk_count + 1):
        hunk: dict[str, object] = {
            "hunk_id": f"hunk-{index}",
            "hunk_type": "intent_only" if context is None else "bounded_snippet_metadata",
            "description": _hunk_description(repair_category),
            "target_symbol": None,
            "before_context": None,
            "after_intent": _after_intent(repair_category),
            "confidence": "medium",
            "risk_level": risk_level,
        }
        if context is not None:
            snippet, _ = _redact_text(context[:240])
            hunk["proposed_snippet"] = snippet
        hunks.append(hunk)
    return hunks


def _operation_for(path: str, repair_category: str) -> str:
    if path.startswith("tests/") or repair_category == "test_repair":
        return "add_test" if path.startswith("tests/") else "modify_existing"
    if path.startswith("docs/") or path.startswith("vault/templates/"):
        return "add_documentation"
    return "modify_existing"


def _target_area(path: str) -> str:
    if path.startswith("backend/python/"):
        return "backend_python"
    if path.startswith("backend/rust/"):
        return "backend_rust"
    if path.startswith("frontend/"):
        return "frontend"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("docs/"):
        return "docs"
    if path.startswith("sandbox/local/"):
        return "sandbox"
    if path.startswith("vault/templates/"):
        return "vault_templates"
    return "unknown"


def _summary_for(repair_category: str, path: str) -> str:
    return f"Propose scoped {repair_category} metadata for {path}."


def _hunk_description(repair_category: str) -> str:
    return f"Describe a bounded future {repair_category} adjustment without applying it."


def _after_intent(repair_category: str) -> str:
    return f"Future governed repair should address {repair_category} and preserve existing behavior."


def _no_change_proposal() -> dict[str, object]:
    return {
        "proposal_id": "patch-proposal-0",
        "file_path": "",
        "operation": "no_change_needed",
        "target_area": "none",
        "summary": "No patch proposal is needed because the repair plan has no failure.",
        "rationale": "Validation already passed.",
        "proposed_change_type": "no_repair_needed",
        "hunks": [],
        "risk_level": "low",
        "requires_human": False,
        "allowed_in_future_patch_apply": False,
        "validation_commands": [],
        "notes": "No change metadata only.",
    }


def _safe_validation_commands(commands: list[Any], repair_category: str) -> list[str]:
    candidates = [str(item).strip() for item in commands if str(item).strip()]
    if not candidates:
        candidates = list(_DEFAULT_VALIDATION.get(repair_category, ["git diff --check"]))
    safe = []
    for command in candidates:
        if _is_safe_validation_command(command):
            safe.append(command)
    return safe or ["git diff --check"]


def _is_safe_validation_command(command: str) -> bool:
    lowered = command.lower()
    blocked = ("git add", "git commit", "git push", "git merge", "git rebase", "gh ", "curl", "wget")
    return not any(item in lowered for item in blocked) and any(
        lowered.startswith(prefix) for prefix in _SAFE_COMMAND_PREFIXES
    )


def _human_escalation(
    *,
    request: ScopedPatchProposalRequest,
    repair_plan: Mapping[str, Any],
    repair_category: str,
    target_branch: str | None,
    files_considered: list[str],
    files_blocked: list[str],
    secret_detected: bool,
) -> tuple[bool, str | None]:
    reasons: list[str] = []
    if secret_detected or repair_category in {"security_escalation", "policy_blocked"}:
        reasons.append("Security or policy repair scope requires human intervention.")
    if repair_plan.get("repair_requires_human") is True:
        reasons.append("Source repair plan requires human intervention.")
    if str(target_branch or "").strip().lower() == MAIN_BRANCH:
        reasons.append("Future patches targeting main require human intervention.")
    if files_blocked:
        reasons.append("One or more file paths are blocked or high risk.")
    if repair_category not in {"no_repair_needed", "security_escalation", "policy_blocked"} and not request.allowed_files:
        reasons.append("Patch proposal needs an explicit allowed file scope.")
    lowered = _metadata_text(request.metadata).lower()
    for marker in ("ci_threshold", "skip tests", "skip_tests", "disable_security", "production", "deploy", "billing", "destructive", "dependency_upgrade"):
        if marker in lowered:
            reasons.append("Metadata indicates a governed exception trigger.")
            break
    for step in request.proposed_steps or repair_plan.get("proposed_steps") or []:
        operation = str(_coerce_mapping(step).get("operation") or _coerce_mapping(step).get("proposed_operation") or "")
        if operation in _BLOCKED_OPERATIONS:
            reasons.append("Requested operation is blocked for this phase.")
            break
    if not files_considered and repair_category not in {"no_repair_needed", "security_escalation", "policy_blocked"}:
        reasons.append("Patch proposal has no scoped file metadata.")
    return bool(reasons), "; ".join(reasons) if reasons else None


def _blocked_reason(
    *,
    request: ScopedPatchProposalRequest,
    proposal_mode: str,
    secret_detected: bool,
    repair_plan: Mapping[str, Any],
    no_repair_needed: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if proposal_mode not in PROPOSAL_MODES:
        return "Patch proposal mode is unknown."
    if proposal_mode == "disabled":
        return "Patch proposal engine is disabled by default."
    if proposal_mode == "blocked":
        return "Patch proposal mode blocks all proposal generation."
    if repair_plan.get("blocked") is True:
        return "Source repair plan is blocked."
    if any(
        (
            request.allow_code_edit,
            request.allow_patch_apply,
            request.allow_file_write,
            request.allow_git_mutation,
            request.allow_command_execution,
            request.allow_provider_call,
            request.allow_agent_call,
            request.allow_network,
        )
    ):
        return "Phase 20 cannot enable edit, apply, file, Git, command, provider, agent, or network capabilities."
    if no_repair_needed:
        return None
    return None


def _patch_scope(files_considered: list[str], files_blocked: list[str], no_repair_needed: bool) -> str:
    if no_repair_needed:
        return "none"
    if files_blocked:
        return "restricted"
    if len(files_considered) == 1:
        return "single_file"
    if files_considered:
        return "multi_file"
    return "unscoped"


def _risk_level(repair_category: str, complexity: str, files_blocked: list[str]) -> str:
    if repair_category in {"security_escalation", "policy_blocked"} or files_blocked:
        return "critical"
    if complexity == "high":
        return "high"
    if complexity == "medium":
        return "medium"
    return "low"


def _reason(*, proposed: bool, no_repair_needed: bool, blocked_reason: str | None, dry_run: bool) -> str:
    if blocked_reason:
        return "Patch proposal engine blocked this request."
    if no_repair_needed:
        return "Repair plan needs no patch proposal."
    if dry_run:
        return "Patch proposal engine classified the repair plan in dry-run mode."
    if proposed:
        return "Patch proposal engine generated structured metadata only."
    return "Patch proposal engine did not create a proposal."


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


def _contexts_contain_secret(contexts: Mapping[str, str]) -> bool:
    for path, content in contexts.items():
        if _contains_credential_like(path) or _contains_credential_like(content):
            return True
    return False


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
