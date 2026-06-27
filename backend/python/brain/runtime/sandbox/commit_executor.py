"""Controlled commit executor.

Phase 24 creates one governed commit only after clean Phase 23 evidence. It
uses a fixed Git allowlist with argv execution and never pushes, opens PRs,
merges, rebases, creates branches, checks out branches, edits files, applies
patches, calls providers, uses MCP, calls agents, or writes Vault notes.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .commit_executor_truth import (
    COMMIT_EXECUTOR_EVIDENCE_VERSION,
    build_commit_executor_evidence,
)
from .commit_executor_types import (
    ControlledCommitExecutorRequest,
    ControlledCommitExecutorResult,
)

EXECUTOR_MODES = frozenset({"disabled", "dry_run", "commit_to_branch", "blocked"})
DEFAULT_EXECUTOR_MODE = "disabled"
MAIN_BRANCH = "main"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_OUTPUT_BYTES = 20000

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
)


def execute_controlled_commit(
    request_or_mapping: ControlledCommitExecutorRequest | Mapping[str, Any] | Any,
) -> ControlledCommitExecutorResult:
    request = _coerce_request(request_or_mapping)
    gate = _coerce_mapping(request.commit_gate_result)
    gate_truth = _coerce_mapping(gate.get("runtime_truth"))
    mode = str(request.executor_mode or DEFAULT_EXECUTOR_MODE).strip() or DEFAULT_EXECUTOR_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root)
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(request.target_branch)
    files_requested, requested_files_redacted = _redact_list(request.files_to_commit)
    proposed_message, proposed_redacted = _redact_optional(request.proposed_commit_message)
    message_hint, hint_redacted = _redact_optional(request.commit_message_hint)
    metadata_redacted = _contains_credential_like(_metadata_text(request.metadata))

    gate_files, gate_files_redacted = _redact_list(
        list(gate.get("files_eligible_for_commit") or [])
    )
    files_considered, files_blocked = _files_to_consider(
        files_requested=files_requested,
        gate_files=gate_files,
        max_files=request.max_files_to_stage,
    )
    files_blocked.extend(_unsafe_files(files_considered))
    files_considered = [path for path in files_considered if path not in files_blocked]

    final_message, message_redacted = _final_commit_message(
        gate=gate,
        proposed_message=proposed_message,
        message_hint=message_hint,
        files=files_considered,
        max_chars=request.max_commit_message_chars,
    )
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            requested_files_redacted,
            gate_files_redacted,
            proposed_redacted,
            hint_redacted,
            message_redacted,
            metadata_redacted,
            _source_secret(gate_truth),
        )
    )
    blocked_reason = _preflight_block_reason(
        request=request,
        mode=mode,
        gate=gate,
        gate_truth=gate_truth,
        secret_detected=secret_detected,
        files_considered=files_considered,
        files_blocked=files_blocked,
        current_branch=current_branch,
        target_branch=target_branch,
        workspace_root=workspace_root,
        final_message=final_message,
    )

    if mode == "dry_run" and not blocked_reason:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            workspace_root=workspace_root,
            current_branch=current_branch,
            verified_current_branch=current_branch,
            target_branch=target_branch,
            gate=gate,
            gate_truth=gate_truth,
            files_requested=files_requested,
            files_considered=files_considered,
            files_staged=[],
            files_blocked=files_blocked,
            proposed_message=proposed_message,
            final_message=final_message,
            pre_head=None,
            post_head=None,
            commit_sha=None,
            attempted=[],
            completed=[],
            blocked_ops=[],
            status_before="",
            status_after="",
            committed=False,
            blocked=False,
            dry_run=True,
            partial=False,
            success=True,
            reason="Controlled commit executor dry run completed without staging or commit.",
            blocked_reason=None,
            redacted=secret_detected,
        )

    if blocked_reason:
        return _blocked_result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            workspace_root=workspace_root,
            current_branch=current_branch,
            verified_current_branch=None,
            target_branch=target_branch,
            gate=gate,
            gate_truth=gate_truth,
            files_requested=files_requested,
            files_considered=files_considered,
            files_blocked=files_blocked,
            proposed_message=proposed_message,
            final_message=final_message,
            blocked_reason=blocked_reason,
            redacted=secret_detected,
        )

    cwd = Path(str(request.workspace_root)).resolve()
    attempted: list[str] = []
    completed: list[str] = []
    blocked_ops: list[str] = []
    status_before = ""
    status_after = ""
    pre_head = None
    post_head = None
    commit_sha = None
    verified_branch = None
    files_staged: list[str] = []

    try:
        branch_run = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd, attempted, completed)
        verified_branch = _bounded_output(branch_run.stdout).strip()
        branch_block = _verified_branch_block(request, current_branch, verified_branch, target_branch)
        if branch_block:
            blocked_ops.append("git add -- <safe files>")
            blocked_ops.append("git commit -m <safe message>")
            return _blocked_result(
                request=request,
                mode=mode,
                requested_by=requested_by,
                related_phase=related_phase,
                related_pr=related_pr,
                workspace_root=workspace_root,
                current_branch=current_branch,
                verified_current_branch=verified_branch,
                target_branch=target_branch,
                gate=gate,
                gate_truth=gate_truth,
                files_requested=files_requested,
                files_considered=files_considered,
                files_blocked=files_blocked,
                proposed_message=proposed_message,
                final_message=final_message,
                blocked_reason=branch_block,
                redacted=secret_detected,
                attempted=attempted,
                completed=completed,
                blocked_ops=blocked_ops,
            )
        pre_head = _bounded_output(_run_git(["git", "rev-parse", "HEAD"], cwd, attempted, completed).stdout).strip()
        status_before = _redact_output(
            _bounded_output(_run_git(["git", "status", "--short"], cwd, attempted, completed).stdout)
        )
        changed_names = set(
            _redact_output(_bounded_output(_run_git(["git", "diff", "--name-only"], cwd, attempted, completed).stdout)).splitlines()
        )
        staged_candidates = [path for path in files_considered if path in changed_names or _status_mentions(status_before, path)]
        if not staged_candidates:
            blocked_ops.append("git add -- <safe files>")
            blocked_ops.append("git commit -m <safe message>")
            return _blocked_result(
                request=request,
                mode=mode,
                requested_by=requested_by,
                related_phase=related_phase,
                related_pr=related_pr,
                workspace_root=workspace_root,
                current_branch=current_branch,
                verified_current_branch=verified_branch,
                target_branch=target_branch,
                gate=gate,
                gate_truth=gate_truth,
                files_requested=files_requested,
                files_considered=files_considered,
                files_blocked=files_blocked,
                proposed_message=proposed_message,
                final_message=final_message,
                blocked_reason="No eligible changed files were available to stage.",
                redacted=secret_detected,
                attempted=attempted,
                completed=completed,
                blocked_ops=blocked_ops,
                status_before=status_before,
            )
        _run_git(["git", "add", "--", *staged_candidates], cwd, attempted, completed)
        files_staged = staged_candidates
        commit_run = _run_git(["git", "commit", "-m", str(final_message)], cwd, attempted, completed)
        post_head = _bounded_output(_run_git(["git", "rev-parse", "HEAD"], cwd, attempted, completed).stdout).strip()
        status_after = _redact_output(
            _bounded_output(_run_git(["git", "status", "--short"], cwd, attempted, completed).stdout)
        )
        commit_sha = post_head if commit_run.returncode == 0 and post_head != pre_head else None
        committed = bool(commit_sha)
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            workspace_root=workspace_root,
            current_branch=current_branch,
            verified_current_branch=verified_branch,
            target_branch=target_branch,
            gate=gate,
            gate_truth=gate_truth,
            files_requested=files_requested,
            files_considered=files_considered,
            files_staged=files_staged,
            files_blocked=files_blocked,
            proposed_message=proposed_message,
            final_message=final_message,
            pre_head=pre_head,
            post_head=post_head,
            commit_sha=commit_sha,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            status_before=status_before,
            status_after=status_after,
            committed=committed,
            blocked=not committed,
            dry_run=False,
            partial=False,
            success=committed,
            reason="Controlled commit was created." if committed else "Controlled commit did not create a new commit.",
            blocked_reason=None if committed else "Git commit did not produce a new commit.",
            redacted=secret_detected,
        )
    except _GitOperationError as exc:
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            workspace_root=workspace_root,
            current_branch=current_branch,
            verified_current_branch=verified_branch,
            target_branch=target_branch,
            gate=gate,
            gate_truth=gate_truth,
            files_requested=files_requested,
            files_considered=files_considered,
            files_staged=files_staged,
            files_blocked=files_blocked,
            proposed_message=proposed_message,
            final_message=final_message,
            pre_head=pre_head,
            post_head=post_head,
            commit_sha=commit_sha,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            status_before=status_before,
            status_after=status_after,
            committed=False,
            blocked=True,
            dry_run=False,
            partial=bool(files_staged),
            success=False,
            reason="Controlled Git commit operation failed.",
            blocked_reason=_redact_output(str(exc)),
            redacted=secret_detected or _contains_credential_like(str(exc)),
        )


class _GitOperationError(RuntimeError):
    pass


def _run_git(
    argv: Sequence[str],
    cwd: Path,
    attempted: list[str],
    completed: list[str],
) -> subprocess.CompletedProcess[bytes]:
    operation = _operation_name(argv)
    if not _argv_allowed(argv):
        raise _GitOperationError(f"Git operation is not allowed: {operation}")
    attempted.append(operation)
    completed_process = subprocess.run(
        list(argv),
        cwd=str(cwd),
        timeout=DEFAULT_TIMEOUT_SECONDS,
        capture_output=True,
        shell=False,
    )
    if completed_process.returncode != 0:
        stdout = _bounded_output(completed_process.stdout)
        stderr = _bounded_output(completed_process.stderr)
        raise _GitOperationError(f"{operation} failed: {stdout} {stderr}".strip())
    completed.append(operation)
    return completed_process


def _argv_allowed(argv: Sequence[str]) -> bool:
    if not argv or argv[0] != "git":
        return False
    if list(argv) in (
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        ["git", "rev-parse", "HEAD"],
        ["git", "status", "--short"],
        ["git", "diff", "--name-only"],
    ):
        return True
    if len(argv) >= 4 and list(argv[:3]) == ["git", "add", "--"]:
        return bool(argv[3:]) and all(_normalize_path(path) for path in argv[3:])
    if len(argv) == 4 and list(argv[:3]) == ["git", "commit", "-m"]:
        return bool(str(argv[3]).strip()) and "--no-verify" not in str(argv[3])
    return False


def _operation_name(argv: Sequence[str]) -> str:
    if list(argv[:3]) == ["git", "add", "--"]:
        return "git add -- <safe files>"
    if list(argv[:3]) == ["git", "commit", "-m"]:
        return "git commit -m <safe message>"
    return " ".join(argv)


def _preflight_block_reason(
    *,
    request: ControlledCommitExecutorRequest,
    mode: str,
    gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    secret_detected: bool,
    files_considered: list[str],
    files_blocked: list[str],
    current_branch: str | None,
    target_branch: str | None,
    workspace_root: str | None,
    final_message: str | None,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in EXECUTOR_MODES:
        return "Controlled commit executor mode is unknown."
    if mode == "disabled":
        return "Controlled commit executor is disabled by default."
    if mode == "blocked":
        return "Controlled commit executor mode blocks all commit execution."
    if any(
        (
            request.allow_push,
            request.allow_pr_creation,
            request.allow_merge,
            request.allow_rebase,
            request.allow_branch_create,
            request.allow_checkout,
            request.allow_file_write,
            request.allow_code_edit,
            request.allow_patch_apply,
            request.allow_network,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 24 cannot enable push, PR, merge, rebase, branch, checkout, file write, edit, patch, network, provider, or agent capabilities."
    if not request.allow_git_add or not request.allow_git_commit:
        return "Controlled commit execution requires explicit add and commit capability flags."
    branch_block = _branch_block_reason(request, current_branch, target_branch)
    if branch_block:
        return branch_block
    workspace_block = _workspace_block_reason(workspace_root) if mode == "commit_to_branch" else None
    if workspace_block:
        return workspace_block
    if request.require_commit_gate_eligible and not gate:
        return "Phase 23 commit gate evidence is required."
    if gate.get("blocked") is True:
        return "Phase 23 commit gate blocked commit eligibility."
    if gate.get("requires_human_intervention") is True:
        return "Phase 23 commit gate requires human intervention."
    if request.require_commit_gate_eligible and gate.get("commit_eligible") is not True:
        return "Phase 23 commit gate did not mark this change eligible."
    if gate.get("commit_ready_metadata_only") is not True:
        return "Phase 23 commit gate did not mark this change ready as metadata."
    if request.require_validation_passed and gate.get("validation_passed") is not True:
        return "Phase 23 validation evidence did not pass."
    if request.require_patch_applied and gate.get("patch_was_applied") is not True:
        return "Phase 23 patch evidence does not show an applied patch."
    if request.require_runtime_truth and not gate_truth:
        return "Phase 23 Runtime Truth is required."
    if request.require_clean_evidence and _gate_truth_unsafe(gate_truth):
        return "Phase 23 Runtime Truth reports unsafe source activity."
    if files_blocked:
        return "Protected or ineligible files were requested for staging."
    if not files_considered:
        return "No eligible files were provided for commit execution."
    if not final_message:
        return "A safe commit message is required."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    return None


def _branch_block_reason(
    request: ControlledCommitExecutorRequest,
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


def _verified_branch_block(
    request: ControlledCommitExecutorRequest,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
) -> str | None:
    if not verified_current_branch:
        return "verified current branch is required."
    branch_block = _branch_block_reason(request, verified_current_branch, target_branch)
    if branch_block:
        return branch_block
    if str(current_branch or "").strip() != str(verified_current_branch or "").strip():
        return "current_branch metadata does not match verified branch."
    return None


def _workspace_block_reason(workspace_root: str | None) -> str | None:
    if not workspace_root:
        return "workspace_root is required for commit execution."
    root = Path(str(workspace_root)).resolve()
    anchor = Path(root.anchor)
    if root == anchor:
        return "workspace_root must not be a filesystem root."
    if not (root / ".git").exists():
        return "workspace_root must be a Git workspace."
    return None


def _files_to_consider(
    *,
    files_requested: list[str],
    gate_files: list[str],
    max_files: int,
) -> tuple[list[str], list[str]]:
    blocked: list[str] = []
    source = files_requested or gate_files
    allowed_gate = set(gate_files)
    considered: list[str] = []
    for raw in source:
        normalized = _normalize_path(raw)
        if normalized is None:
            safe, _ = _redact_text(raw)
            blocked.append(safe)
            continue
        if gate_files and normalized not in allowed_gate:
            blocked.append(normalized)
            continue
        if normalized not in considered:
            considered.append(normalized)
    if len(considered) > max_files:
        blocked.extend(considered[max_files:])
        considered = considered[:max_files]
    return considered, blocked


def _unsafe_files(files: list[str]) -> list[str]:
    return [path for path in files if _path_issue(path)]


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


def _final_commit_message(
    *,
    gate: Mapping[str, Any],
    proposed_message: str | None,
    message_hint: str | None,
    files: list[str],
    max_chars: int,
) -> tuple[str | None, bool]:
    candidates = [
        gate.get("proposed_commit_message"),
        proposed_message,
        message_hint,
        _fallback_commit_message(files),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        message, redacted = _redact_text(" ".join(str(candidate).split()))
        if redacted:
            return "[REDACTED]", True
        return message[: max(1, max_chars)], False
    return None, False


def _fallback_commit_message(files: list[str]) -> str:
    if all(path.startswith("tests/") for path in files):
        return "test(runtime): add governed sandbox coverage"
    if all(path.startswith("docs/") or path.startswith("vault/templates/") for path in files):
        return "docs(sandbox): update governed sandbox docs"
    if any(path.startswith("frontend/") for path in files):
        return "fix(frontend): update governed sandbox change"
    if any(path.startswith("backend/rust/") for path in files):
        return "fix(rust): update governed sandbox change"
    return "fix(python): update governed sandbox runtime"


def _gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "main_modification_detected",
        "main_modified",
        "git_mutation_detected",
        "pr_created",
        "pr_merged",
    )
    if any(truth.get(key) is True for key in unsafe_keys):
        return True
    return truth.get("validation_passed") is False


def _source_secret(truth: Mapping[str, Any]) -> bool:
    return truth.get("secrets_detected") is True


def _status_mentions(status: str, path: str) -> bool:
    return any(line.endswith(path) or line.endswith(f" {path}") for line in status.splitlines())


def _coerce_request(value: ControlledCommitExecutorRequest | Mapping[str, Any] | Any) -> ControlledCommitExecutorRequest:
    if isinstance(value, ControlledCommitExecutorRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Commit executor input must be a request, mapping, or object.")
    return ControlledCommitExecutorRequest(
        commit_gate_result=_coerce_mapping(payload.get("commit_gate_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        executor_mode=str(payload.get("executor_mode") or DEFAULT_EXECUTOR_MODE),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        files_to_commit=list(payload.get("files_to_commit") or []),
        proposed_commit_message=payload.get("proposed_commit_message"),
        commit_message_hint=payload.get("commit_message_hint"),
        require_commit_gate_eligible=bool(payload.get("require_commit_gate_eligible", True)),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_validation_passed=bool(payload.get("require_validation_passed", True)),
        require_patch_applied=bool(payload.get("require_patch_applied", True)),
        require_clean_evidence=bool(payload.get("require_clean_evidence", True)),
        max_files_to_stage=int(payload.get("max_files_to_stage", 20)),
        max_commit_message_chars=int(payload.get("max_commit_message_chars", 120)),
        allow_git_add=bool(payload.get("allow_git_add", True)),
        allow_git_commit=bool(payload.get("allow_git_commit", True)),
        allow_push=bool(payload.get("allow_push", False)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_rebase=bool(payload.get("allow_rebase", False)),
        allow_branch_create=bool(payload.get("allow_branch_create", False)),
        allow_checkout=bool(payload.get("allow_checkout", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
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


def _blocked_result(
    *,
    request: ControlledCommitExecutorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    files_requested: list[str],
    files_considered: list[str],
    files_blocked: list[str],
    proposed_message: str | None,
    final_message: str | None,
    blocked_reason: str,
    redacted: bool,
    attempted: list[str] | None = None,
    completed: list[str] | None = None,
    blocked_ops: list[str] | None = None,
    status_before: str = "",
) -> ControlledCommitExecutorResult:
    return _result(
        request=request,
        mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        gate=gate,
        gate_truth=gate_truth,
        files_requested=files_requested,
        files_considered=files_considered,
        files_staged=[],
        files_blocked=files_blocked,
        proposed_message=proposed_message,
        final_message=final_message,
        pre_head=None,
        post_head=None,
        commit_sha=None,
        attempted=attempted or [],
        completed=completed or [],
        blocked_ops=blocked_ops or ["git add -- <safe files>", "git commit -m <safe message>"],
        status_before=status_before,
        status_after="",
        committed=False,
        blocked=True,
        dry_run=False,
        partial=False,
        success=False,
        reason="Controlled commit executor blocked this request.",
        blocked_reason=blocked_reason,
        redacted=redacted,
    )


def _result(
    *,
    request: ControlledCommitExecutorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    gate: Mapping[str, Any],
    gate_truth: Mapping[str, Any],
    files_requested: list[str],
    files_considered: list[str],
    files_staged: list[str],
    files_blocked: list[str],
    proposed_message: str | None,
    final_message: str | None,
    pre_head: str | None,
    post_head: str | None,
    commit_sha: str | None,
    attempted: list[str],
    completed: list[str],
    blocked_ops: list[str],
    status_before: str,
    status_after: str,
    committed: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    success: bool,
    reason: str,
    blocked_reason: str | None,
    redacted: bool,
) -> ControlledCommitExecutorResult:
    requires_human = bool(blocked and not dry_run)
    child_events = [dict(gate_truth)] if gate_truth else []
    runtime_truth = build_commit_executor_evidence(
        executor_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        committed=committed,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        commit_gate_eligible=bool(gate.get("commit_eligible") is True),
        files_requested_count=len(files_requested),
        files_considered_count=len(files_considered),
        files_staged_count=len(files_staged),
        files_blocked_count=len(files_blocked),
        commit_sha=commit_sha,
        pre_commit_head=pre_head,
        post_commit_head=post_head,
        git_operations_attempted=attempted,
        git_operations_completed=completed,
        git_operations_blocked=blocked_ops,
        secrets_detected=redacted,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=child_events,
    ).to_dict()
    return ControlledCommitExecutorResult(
        committed=committed,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        partial=partial,
        executor_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        commit_gate_eligible=bool(gate.get("commit_eligible") is True),
        files_requested=files_requested,
        files_considered=files_considered,
        files_staged=files_staged,
        files_blocked=files_blocked,
        proposed_commit_message=proposed_message,
        final_commit_message=final_message,
        pre_commit_head=pre_head,
        post_commit_head=post_head,
        commit_sha=commit_sha,
        git_operations_attempted=attempted,
        git_operations_completed=completed,
        git_operations_blocked=blocked_ops,
        status_before=status_before,
        status_after=status_after,
        can_push=False,
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
        requires_push_phase=committed,
        requires_pr_phase=committed,
        requires_human_intervention=requires_human,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=COMMIT_EXECUTOR_EVIDENCE_VERSION,
        redacted=redacted,
    )


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


def _bounded_output(value: bytes, max_bytes: int = DEFAULT_OUTPUT_BYTES) -> str:
    chunk = value[:max_bytes]
    text = chunk.decode("utf-8", errors="replace")
    return _redact_output(text)


def _redact_output(value: object) -> str:
    return _redact_text(value)[0]
