"""Controlled push executor.

Phase 26 performs a governed branch push only after clean Phase 25 evidence.
It uses a fixed Git allowlist with argv execution and never force pushes,
pushes main, opens PRs, merges, rebases, creates branches, checks out
branches, stages files, commits, edits files, applies patches, calls
providers, uses MCP, calls agents, or writes Vault notes.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .push_executor_truth import (
    PUSH_EXECUTOR_EVIDENCE_VERSION,
    build_push_executor_evidence,
)
from .push_executor_types import (
    ControlledPushExecutorRequest,
    ControlledPushExecutorResult,
)

EXECUTOR_MODES = frozenset({"disabled", "dry_run", "push_branch", "blocked"})
DEFAULT_EXECUTOR_MODE = "disabled"
MAIN_BRANCH = "main"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_OUTPUT_BYTES = 20000

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
_SAFE_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_PROTECTED_BRANCH_PREFIXES = ("release/", "prod/", "production/", "protected/")


def execute_controlled_push(
    request_or_mapping: ControlledPushExecutorRequest | Mapping[str, Any] | Any,
) -> ControlledPushExecutorResult:
    request = _coerce_request(request_or_mapping)
    push_gate = _coerce_mapping(request.push_gate_result)
    commit_executor = _coerce_mapping(request.commit_executor_result)
    push_gate_truth = _coerce_mapping(push_gate.get("runtime_truth"))
    commit_executor_truth = _coerce_mapping(commit_executor.get("runtime_truth"))
    mode = str(request.executor_mode or DEFAULT_EXECUTOR_MODE).strip() or DEFAULT_EXECUTOR_MODE

    requested_by, requested_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(
        request.workspace_root or push_gate.get("workspace_root") or commit_executor.get("workspace_root")
    )
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(
        request.target_branch or push_gate.get("target_branch") or commit_executor.get("target_branch")
    )
    verified_branch, verified_redacted = _redact_optional(request.verified_current_branch)
    remote_name, remote_name_redacted = _redact_text(request.remote_name or push_gate.get("remote_name") or "origin")
    remote_branch, remote_branch_redacted = _redact_optional(
        request.remote_branch or push_gate.get("remote_branch") or current_branch
    )
    proposed_push_ref, push_ref_redacted = _redact_optional(
        request.proposed_push_ref or push_gate.get("proposed_push_ref") or remote_branch
    )
    commit_sha, commit_sha_redacted = _redact_optional(
        request.commit_sha or commit_executor.get("commit_sha") or push_gate.get("commit_sha")
    )
    final_push_ref = _final_push_ref(current_branch, remote_branch)
    final_push_ref, final_ref_redacted = _redact_optional(final_push_ref)
    status_before = ""
    status_after = ""
    push_stdout = ""
    push_stderr = ""

    source_truths = [
        truth for truth in (push_gate_truth, commit_executor_truth) if truth
    ]
    secret_detected = any(
        (
            requested_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            verified_redacted,
            remote_name_redacted,
            remote_branch_redacted,
            push_ref_redacted,
            final_ref_redacted,
            commit_sha_redacted,
            _contains_credential_like(_metadata_text(request.metadata)),
            _source_secret(source_truths),
        )
    )
    blocked_reason = _preflight_block_reason(
        request=request,
        mode=mode,
        push_gate=push_gate,
        commit_executor=commit_executor,
        push_gate_truth=push_gate_truth,
        commit_executor_truth=commit_executor_truth,
        secret_detected=secret_detected,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_branch=verified_branch,
        target_branch=target_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
        commit_sha=commit_sha,
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
            verified_current_branch=verified_branch or current_branch,
            target_branch=target_branch,
            remote_name=remote_name,
            remote_branch=remote_branch,
            proposed_push_ref=proposed_push_ref,
            final_push_ref=final_push_ref,
            push_gate=push_gate,
            push_gate_truth=push_gate_truth,
            commit_executor=commit_executor,
            commit_executor_truth=commit_executor_truth,
            commit_sha=commit_sha,
            pre_head=None,
            post_head=None,
            attempted=[],
            completed=[],
            blocked_ops=[],
            status_before="",
            status_after="",
            push_stdout="",
            push_stderr="",
            pushed=False,
            blocked=False,
            dry_run=True,
            partial=False,
            success=True,
            reason="Controlled push executor dry run completed without remote mutation.",
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
            verified_current_branch=verified_branch,
            target_branch=target_branch,
            remote_name=remote_name,
            remote_branch=remote_branch,
            proposed_push_ref=proposed_push_ref,
            final_push_ref=final_push_ref,
            push_gate=push_gate,
            push_gate_truth=push_gate_truth,
            commit_executor=commit_executor,
            commit_executor_truth=commit_executor_truth,
            commit_sha=commit_sha,
            blocked_reason=blocked_reason,
            redacted=secret_detected,
        )

    cwd = Path(str(workspace_root)).resolve()
    attempted: list[str] = []
    completed: list[str] = []
    blocked_ops: list[str] = []
    pre_head = None
    post_head = None
    verified_runtime_branch = verified_branch

    try:
        branch_run = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd, attempted, completed)
        verified_runtime_branch = _bounded_output(branch_run.stdout).strip()
        branch_block = _verified_branch_block(
            request=request,
            current_branch=current_branch,
            verified_current_branch=verified_runtime_branch,
            target_branch=target_branch,
            remote_branch=remote_branch,
        )
        if branch_block:
            blocked_ops.append("git push origin <safe_branch>:refs/heads/<safe_remote_branch>")
            return _blocked_result(
                request=request,
                mode=mode,
                requested_by=requested_by,
                related_phase=related_phase,
                related_pr=related_pr,
                workspace_root=workspace_root,
                current_branch=current_branch,
                verified_current_branch=verified_runtime_branch,
                target_branch=target_branch,
                remote_name=remote_name,
                remote_branch=remote_branch,
                proposed_push_ref=proposed_push_ref,
                final_push_ref=final_push_ref,
                push_gate=push_gate,
                push_gate_truth=push_gate_truth,
                commit_executor=commit_executor,
                commit_executor_truth=commit_executor_truth,
                commit_sha=commit_sha,
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
        status_block = _status_block_reason(status_before)
        if status_block:
            blocked_ops.append("git push origin <safe_branch>:refs/heads/<safe_remote_branch>")
            return _blocked_result(
                request=request,
                mode=mode,
                requested_by=requested_by,
                related_phase=related_phase,
                related_pr=related_pr,
                workspace_root=workspace_root,
                current_branch=current_branch,
                verified_current_branch=verified_runtime_branch,
                target_branch=target_branch,
                remote_name=remote_name,
                remote_branch=remote_branch,
                proposed_push_ref=proposed_push_ref,
                final_push_ref=final_push_ref,
                push_gate=push_gate,
                push_gate_truth=push_gate_truth,
                commit_executor=commit_executor,
                commit_executor_truth=commit_executor_truth,
                commit_sha=commit_sha,
                blocked_reason=status_block,
                redacted=True,
                attempted=attempted,
                completed=completed,
                blocked_ops=blocked_ops,
                status_before=status_before,
            )
        push_run = _run_git(["git", "push", remote_name, str(final_push_ref)], cwd, attempted, completed)
        push_stdout = _bounded_output(push_run.stdout)
        push_stderr = _bounded_output(push_run.stderr)
        post_head = _bounded_output(_run_git(["git", "rev-parse", "HEAD"], cwd, attempted, completed).stdout).strip()
        status_after = _redact_output(
            _bounded_output(_run_git(["git", "status", "--short"], cwd, attempted, completed).stdout)
        )
        return _result(
            request=request,
            mode=mode,
            requested_by=requested_by,
            related_phase=related_phase,
            related_pr=related_pr,
            workspace_root=workspace_root,
            current_branch=current_branch,
            verified_current_branch=verified_runtime_branch,
            target_branch=target_branch,
            remote_name=remote_name,
            remote_branch=remote_branch,
            proposed_push_ref=proposed_push_ref,
            final_push_ref=final_push_ref,
            push_gate=push_gate,
            push_gate_truth=push_gate_truth,
            commit_executor=commit_executor,
            commit_executor_truth=commit_executor_truth,
            commit_sha=commit_sha,
            pre_head=pre_head,
            post_head=post_head,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            status_before=status_before,
            status_after=status_after,
            push_stdout=push_stdout,
            push_stderr=push_stderr,
            pushed=True,
            blocked=False,
            dry_run=False,
            partial=False,
            success=True,
            reason="Controlled branch push completed.",
            blocked_reason=None,
            redacted=secret_detected or _contains_credential_like(push_stdout) or _contains_credential_like(push_stderr),
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
            verified_current_branch=verified_runtime_branch,
            target_branch=target_branch,
            remote_name=remote_name,
            remote_branch=remote_branch,
            proposed_push_ref=proposed_push_ref,
            final_push_ref=final_push_ref,
            push_gate=push_gate,
            push_gate_truth=push_gate_truth,
            commit_executor=commit_executor,
            commit_executor_truth=commit_executor_truth,
            commit_sha=commit_sha,
            pre_head=pre_head,
            post_head=post_head,
            attempted=attempted,
            completed=completed,
            blocked_ops=blocked_ops,
            status_before=status_before,
            status_after=status_after,
            push_stdout=push_stdout,
            push_stderr=push_stderr,
            pushed=False,
            blocked=True,
            dry_run=False,
            partial=False,
            success=False,
            reason="Controlled Git push operation failed.",
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
    ):
        return True
    if len(argv) == 4 and list(argv[:3]) == ["git", "push", "origin"]:
        return _refspec_safe(str(argv[3]))
    return False


def _operation_name(argv: Sequence[str]) -> str:
    if list(argv[:3]) == ["git", "push", "origin"]:
        return "git push origin <safe_branch>:refs/heads/<safe_remote_branch>"
    return " ".join(argv)


def _preflight_block_reason(
    *,
    request: ControlledPushExecutorRequest,
    mode: str,
    push_gate: Mapping[str, Any],
    commit_executor: Mapping[str, Any],
    push_gate_truth: Mapping[str, Any],
    commit_executor_truth: Mapping[str, Any],
    secret_detected: bool,
    workspace_root: str | None,
    current_branch: str | None,
    verified_branch: str | None,
    target_branch: str | None,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    final_push_ref: str | None,
    commit_sha: str | None,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if mode not in EXECUTOR_MODES:
        return "Controlled push executor mode is unknown."
    if mode == "disabled":
        return "Controlled push executor is disabled by default."
    if mode == "blocked":
        return "Controlled push executor mode blocks all push execution."
    if not request.allow_push_execution and mode == "push_branch":
        return "Controlled push execution requires explicit push capability."
    if any(
        (
            request.allow_force_push,
            request.allow_main_push,
            request.allow_protected_branch_push,
            request.allow_pr_creation,
            request.allow_merge,
            request.allow_rebase,
            request.allow_branch_create,
            request.allow_checkout,
            request.allow_file_write,
            request.allow_code_edit,
            request.allow_patch_apply,
            request.allow_provider_call,
            request.allow_agent_call,
        )
    ):
        return "Phase 26 cannot enable force push, main push, protected branch push, PR, merge, rebase, branch, checkout, file write, edit, patch, provider, or agent capabilities."
    branch_block = _branch_block_reason(request, current_branch, target_branch, remote_branch)
    if branch_block:
        return branch_block
    if mode == "dry_run":
        verified_block = _verified_branch_block(
            request=request,
            current_branch=current_branch,
            verified_current_branch=verified_branch,
            target_branch=target_branch,
            remote_branch=remote_branch,
        )
        if verified_block:
            return verified_block
    workspace_block = _workspace_block_reason(workspace_root) if mode == "push_branch" else None
    if workspace_block:
        return workspace_block
    remote_block = _remote_block_reason(
        request=request,
        remote_name=remote_name,
        current_branch=current_branch,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
    )
    if remote_block:
        return remote_block
    if request.require_push_gate_eligible and not push_gate:
        return "Phase 25 push gate evidence is required."
    if push_gate.get("blocked") is True:
        return "Phase 25 push gate blocked push eligibility."
    if push_gate.get("requires_human_intervention") is True:
        return "Phase 25 push gate requires human intervention."
    if push_gate.get("success") is False:
        return "Phase 25 push gate was not successful."
    if request.require_push_gate_eligible and push_gate.get("push_eligible") is not True:
        return "Phase 25 push gate did not mark this branch eligible."
    if push_gate.get("push_ready_metadata_only") is not True:
        return "Phase 25 push gate did not mark this branch ready as metadata."
    if request.require_runtime_truth and not push_gate_truth:
        return "Phase 25 Runtime Truth is required."
    if request.require_clean_evidence and _push_gate_truth_unsafe(push_gate_truth):
        return "Phase 25 Runtime Truth reports unsafe push evidence."
    if request.require_commit_executed and not commit_executor:
        return "Phase 24 commit executor evidence is required."
    if commit_executor.get("blocked") is True:
        return "Phase 24 commit executor result is blocked."
    if commit_executor.get("requires_human_intervention") is True:
        return "Phase 24 commit executor requires human intervention."
    if request.require_commit_executed and commit_executor.get("committed") is not True:
        return "Phase 24 commit executor did not create a commit."
    if commit_executor.get("success") is False:
        return "Phase 24 commit executor was not successful."
    if request.require_commit_executed and not commit_executor.get("commit_sha"):
        return "Phase 24 commit executor did not provide a commit SHA."
    if request.require_commit_executed and not commit_sha:
        return "Commit SHA is required for push execution."
    if request.require_runtime_truth and not commit_executor_truth:
        return "Phase 24 Runtime Truth is required."
    if request.require_clean_evidence and _commit_executor_truth_unsafe(commit_executor_truth):
        return "Phase 24 Runtime Truth reports unsafe activity."
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked."
    if request.metadata.get("push_main") is True:
        return "push_main metadata is blocked."
    if request.metadata.get("force_push") is True:
        return "force_push metadata is blocked."
    return None


def _branch_block_reason(
    request: ControlledPushExecutorRequest,
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


def _verified_branch_block(
    *,
    request: ControlledPushExecutorRequest,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    remote_branch: str | None,
) -> str | None:
    if not verified_current_branch:
        return "verified current branch is required."
    branch_block = _branch_block_reason(request, verified_current_branch, target_branch, remote_branch)
    if branch_block:
        return branch_block
    if str(current_branch or "").strip() != str(verified_current_branch or "").strip():
        return "current_branch metadata does not match verified branch."
    return None


def _workspace_block_reason(workspace_root: str | None) -> str | None:
    if not workspace_root:
        return "workspace_root is required for push execution."
    root = Path(str(workspace_root)).resolve()
    anchor = Path(root.anchor)
    if root == anchor:
        return "workspace_root must not be a filesystem root."
    if not (root / ".git").exists():
        return "workspace_root must be a Git workspace."
    return None


def _remote_block_reason(
    *,
    request: ControlledPushExecutorRequest,
    remote_name: str,
    current_branch: str | None,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    final_push_ref: str | None,
) -> str | None:
    if not remote_name:
        return "remote_name is required."
    if request.require_remote_origin and remote_name != "origin":
        return "Only origin is allowed for controlled push execution."
    if _REMOTE_SHELL_CHARS.search(remote_name):
        return "remote_name contains unsafe characters."
    if _contains_credential_like(remote_name) or _contains_credential_like(remote_branch) or _contains_credential_like(proposed_push_ref):
        return "Remote metadata contains secret-like content."
    current = str(current_branch or "").strip()
    remote = str(remote_branch or "").strip()
    push_ref = str(proposed_push_ref or "").strip()
    if not _branch_name_safe(current):
        return "current_branch contains unsafe characters."
    if not _branch_name_safe(remote):
        return "remote_branch contains unsafe characters."
    if current != remote:
        return "remote_branch must match current_branch."
    if push_ref and push_ref not in {current, f"refs/heads/{current}", final_push_ref}:
        return "proposed_push_ref must match the current branch."
    if not _refspec_safe(final_push_ref):
        return "final push ref is not safe."
    return None


def _final_push_ref(current_branch: str | None, remote_branch: str | None) -> str | None:
    current = str(current_branch or "").strip()
    remote = str(remote_branch or "").strip()
    if not current or not remote:
        return None
    return f"{current}:refs/heads/{remote}"


def _refspec_safe(value: object) -> bool:
    text = str(value or "").strip()
    if not text or text.startswith("+") or "--force" in text or " -f" in text or text == "-f":
        return False
    if text.count(":") != 1:
        return False
    source, target = text.split(":", 1)
    if not target.startswith("refs/heads/"):
        return False
    return _branch_name_safe(source) and _branch_name_safe(target.removeprefix("refs/heads/"))


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
    return bool(_SAFE_BRANCH.fullmatch(text))


def _protected_branch(branch: object) -> bool:
    lowered = str(branch or "").strip().lower()
    return lowered.startswith(_PROTECTED_BRANCH_PREFIXES)


def _status_block_reason(status: str) -> str | None:
    if _contains_credential_like(status) or "[REDACTED]" in status:
        return "Git status output contains secret-like content."
    for line in status.splitlines():
        path = line[3:].strip() if len(line) > 3 else line.strip()
        normalized = path.replace("\\", "/").lower()
        if normalized in {".env"} or normalized.startswith((".env.", ".git/")):
            return "Git status reports protected or secret-like files."
    return None


def _push_gate_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "force_push_detected",
        "main_push_detected",
        "protected_branch_detected",
        "push_executed",
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


def _commit_executor_truth_unsafe(truth: Mapping[str, Any]) -> bool:
    unsafe_keys = (
        "secrets_detected",
        "pushed",
        "push_executed",
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


def _source_secret(truths: list[Mapping[str, Any]]) -> bool:
    return any(truth.get("secrets_detected") is True for truth in truths)


def _coerce_request(value: ControlledPushExecutorRequest | Mapping[str, Any] | Any) -> ControlledPushExecutorRequest:
    if isinstance(value, ControlledPushExecutorRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Push executor input must be a request, mapping, or object.")
    return ControlledPushExecutorRequest(
        push_gate_result=_coerce_mapping(payload.get("push_gate_result")),
        commit_executor_result=_coerce_mapping(payload.get("commit_executor_result")),
        requested_by=str(payload.get("requested_by") or "unknown"),
        executor_mode=str(payload.get("executor_mode") or DEFAULT_EXECUTOR_MODE),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        verified_current_branch=payload.get("verified_current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        remote_name=str(payload.get("remote_name") or "origin"),
        remote_branch=payload.get("remote_branch"),
        proposed_push_ref=payload.get("proposed_push_ref"),
        commit_sha=payload.get("commit_sha"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        require_push_gate_eligible=bool(payload.get("require_push_gate_eligible", True)),
        require_commit_executed=bool(payload.get("require_commit_executed", True)),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        require_clean_evidence=bool(payload.get("require_clean_evidence", True)),
        require_remote_origin=bool(payload.get("require_remote_origin", True)),
        allow_push_execution=bool(payload.get("allow_push_execution", True)),
        allow_force_push=bool(payload.get("allow_force_push", False)),
        allow_main_push=bool(payload.get("allow_main_push", False)),
        allow_protected_branch_push=bool(payload.get("allow_protected_branch_push", False)),
        allow_pr_creation=bool(payload.get("allow_pr_creation", False)),
        allow_merge=bool(payload.get("allow_merge", False)),
        allow_rebase=bool(payload.get("allow_rebase", False)),
        allow_branch_create=bool(payload.get("allow_branch_create", False)),
        allow_checkout=bool(payload.get("allow_checkout", False)),
        allow_file_write=bool(payload.get("allow_file_write", False)),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
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
    request: ControlledPushExecutorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    final_push_ref: str | None,
    push_gate: Mapping[str, Any],
    push_gate_truth: Mapping[str, Any],
    commit_executor: Mapping[str, Any],
    commit_executor_truth: Mapping[str, Any],
    commit_sha: str | None,
    blocked_reason: str,
    redacted: bool,
    attempted: list[str] | None = None,
    completed: list[str] | None = None,
    blocked_ops: list[str] | None = None,
    status_before: str = "",
) -> ControlledPushExecutorResult:
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
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
        push_gate=push_gate,
        push_gate_truth=push_gate_truth,
        commit_executor=commit_executor,
        commit_executor_truth=commit_executor_truth,
        commit_sha=commit_sha,
        pre_head=None,
        post_head=None,
        attempted=attempted or [],
        completed=completed or [],
        blocked_ops=blocked_ops or ["git push origin <safe_branch>:refs/heads/<safe_remote_branch>"],
        status_before=status_before,
        status_after="",
        push_stdout="",
        push_stderr="",
        pushed=False,
        blocked=True,
        dry_run=False,
        partial=False,
        success=False,
        reason="Controlled push executor blocked this request.",
        blocked_reason=blocked_reason,
        redacted=redacted,
    )


def _result(
    *,
    request: ControlledPushExecutorRequest,
    mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    final_push_ref: str | None,
    push_gate: Mapping[str, Any],
    push_gate_truth: Mapping[str, Any],
    commit_executor: Mapping[str, Any],
    commit_executor_truth: Mapping[str, Any],
    commit_sha: str | None,
    pre_head: str | None,
    post_head: str | None,
    attempted: list[str],
    completed: list[str],
    blocked_ops: list[str],
    status_before: str,
    status_after: str,
    push_stdout: str,
    push_stderr: str,
    pushed: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    success: bool,
    reason: str,
    blocked_reason: str | None,
    redacted: bool,
) -> ControlledPushExecutorResult:
    requires_human = bool(blocked and not dry_run)
    child_events = [dict(truth) for truth in (push_gate_truth, commit_executor_truth) if truth]
    runtime_truth = build_push_executor_evidence(
        executor_mode=mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
        pushed=pushed,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        push_gate_eligible=bool(push_gate.get("push_eligible") is True),
        commit_was_executed=bool(commit_executor.get("committed") is True),
        commit_sha=commit_sha,
        pre_push_head=pre_head,
        post_push_head=post_head,
        git_operations_attempted=attempted,
        git_operations_completed=completed,
        git_operations_blocked=blocked_ops,
        push_attempted=any(operation.startswith("git push") for operation in attempted),
        secrets_detected=redacted,
        human_intervention_required=requires_human,
        escalation_reason=blocked_reason if requires_human else None,
        child_runtime_truth_events=child_events,
    ).to_dict()
    return ControlledPushExecutorResult(
        pushed=pushed,
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
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
        push_gate_eligible=bool(push_gate.get("push_eligible") is True),
        commit_was_executed=bool(commit_executor.get("committed") is True),
        commit_sha=commit_sha,
        pre_push_head=pre_head,
        post_push_head=post_head,
        git_operations_attempted=attempted,
        git_operations_completed=completed,
        git_operations_blocked=blocked_ops,
        status_before=status_before,
        status_after=status_after,
        push_stdout_summary=_redact_output(push_stdout),
        push_stderr_summary=_redact_output(push_stderr),
        pushed_ref=final_push_ref if pushed else None,
        pushed_remote=remote_name if pushed else None,
        can_open_pr=False,
        can_merge=False,
        can_rebase=False,
        can_force_push=False,
        can_push_main=False,
        can_create_branch=False,
        can_checkout=False,
        can_edit_code=False,
        can_apply_patch=False,
        can_call_provider=False,
        can_call_agent=False,
        requires_pr_phase=pushed,
        requires_ci_monitor_phase=pushed,
        requires_human_intervention=requires_human,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason if requires_human else None,
        runtime_truth=runtime_truth,
        evidence_version=PUSH_EXECUTOR_EVIDENCE_VERSION,
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


def _bounded_output(value: bytes, max_bytes: int = DEFAULT_OUTPUT_BYTES) -> str:
    chunk = value[:max_bytes]
    text = chunk.decode("utf-8", errors="replace")
    return _redact_output(text)


def _redact_output(value: object) -> str:
    return _redact_text(value)[0]
