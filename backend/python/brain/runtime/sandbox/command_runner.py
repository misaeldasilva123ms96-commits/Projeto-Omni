"""Governed sandbox command runner.

Phase 17 is the first controlled execution layer. It executes only read-safe
commands approved by the Safe Command Execution Gate, uses argv execution with
shell disabled, captures bounded output, and returns Runtime Truth evidence.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .command_runner_truth import (
    COMMAND_RUNNER_EVIDENCE_VERSION,
    build_command_runner_evidence,
)
from .command_runner_types import (
    SandboxCommandRunnerRequest,
    SandboxCommandRunnerResult,
)
from .command_types import CommandGateRequest
from .command_gate import evaluate_command_gate

RUNNER_MODES = frozenset({"disabled", "dry_run", "sandbox_readonly", "blocked"})
DEFAULT_RUNNER_MODE = "disabled"
MAX_TIMEOUT_SECONDS = 300
MIN_TIMEOUT_SECONDS = 1
DEFAULT_OUTPUT_BYTES = 20000

_WORKSPACE_MARKERS = (".git", "package.json", "backend/python")
_SHELL_OPERATOR_PATTERNS = (
    re.compile(r";"),
    re.compile(r"&&"),
    re.compile(r"\|\|"),
    re.compile(r"(?<!-)\|(?!-)"),
    re.compile(r">"),
    re.compile(r"<"),
    re.compile(r"`[^`]*`"),
    re.compile(r"\$\("),
    re.compile(r"\$\{"),
)
_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]+[_-])?TO" r"KEN(?:[_-][A-Za-z0-9]+)?\s*(?:=|:)\s*\S+",
        re.IGNORECASE,
    ),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile("AUTH" + r"ORIZATION", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)
_SECRET_PATH_PARTS = frozenset(
    {
        ".env",
        ".ssh",
        ".aws",
        ".azure",
        ".gcloud",
        ".npmrc",
        ".pypirc",
        "id_rsa",
        "id_ed25519",
    }
)
_ALLOWED_ENV_KEYS = frozenset(
    {
        "PATH",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "PYTHONPATH",
    }
)


def run_sandbox_command(
    request_or_mapping: SandboxCommandRunnerRequest | Mapping[str, Any] | Any,
) -> SandboxCommandRunnerResult:
    request = _coerce_request(request_or_mapping)
    started = time.monotonic()
    started_at = _utc_now()
    timeout_seconds = _normalize_timeout(request.timeout_seconds)
    runner_mode = str(request.runner_mode or DEFAULT_RUNNER_MODE).strip() or DEFAULT_RUNNER_MODE
    command, command_redacted = _redact_text(request.command)
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    working_directory, working_directory_redacted = _redact_optional(request.working_directory)
    purpose, purpose_redacted = _redact_optional(request.purpose)
    metadata_redacted = _contains_credential_like(_metadata_text(request.metadata))

    gate = evaluate_command_gate(
        CommandGateRequest(
            command=request.command,
            requested_by=request.requested_by,
            command_mode=request.command_mode,
            target_branch=request.target_branch,
            base_branch=request.base_branch,
            working_directory=request.working_directory,
            related_phase=request.related_phase,
            related_pr=request.related_pr,
            purpose=request.purpose,
            timeout_seconds=timeout_seconds,
            metadata=request.metadata,
        )
    )
    argv, parse_error = _parse_argv(gate.normalized_command)
    workspace_root, workspace_root_error = _resolve_workspace_root(request.workspace_root)
    cwd, cwd_error = _resolve_working_directory(request.working_directory, workspace_root)
    allowlist_error = _validate_executable_argv(argv, cwd, workspace_root)
    secret_detected = any(
        (
            command_redacted,
            requested_by_redacted,
            working_directory_redacted,
            purpose_redacted,
            metadata_redacted,
            gate.redacted,
        )
    )
    blocked_reason = _blocked_reason(
        runner_mode=runner_mode,
        request=request,
        gate=gate,
        parse_error=parse_error,
        workspace_root_error=workspace_root_error,
        cwd_error=cwd_error,
        allowlist_error=allowlist_error,
        secret_detected=secret_detected,
    )

    if runner_mode == "dry_run" and not blocked_reason:
        return _result(
            request=request,
            gate=gate,
            argv=argv,
            runner_mode=runner_mode,
            command=command,
            requested_by=requested_by,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            started_at=started_at,
            started=started,
            executed=False,
            blocked=False,
            dry_run=True,
            timed_out=False,
            exit_code=None,
            reason="Command classified for dry run; no process was executed.",
            blocked_reason=None,
            stdout="",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            stdout_bytes=0,
            stderr_bytes=0,
            redacted=secret_detected,
            secrets_detected=secret_detected,
        )

    if blocked_reason:
        return _result(
            request=request,
            gate=gate,
            argv=argv,
            runner_mode=runner_mode,
            command=command,
            requested_by=requested_by,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            started_at=started_at,
            started=started,
            executed=False,
            blocked=True,
            dry_run=False,
            timed_out=False,
            exit_code=None,
            reason="Sandbox command runner blocked this request.",
            blocked_reason=blocked_reason,
            stdout="",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            stdout_bytes=0,
            stderr_bytes=0,
            redacted=secret_detected,
            secrets_detected=secret_detected,
        )

    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=_sanitized_environment(cwd, workspace_root),
            timeout=timeout_seconds,
            capture_output=True,
            shell=False,
        )
        stdout, stdout_bytes, stdout_truncated, stdout_redacted = _bounded_output(
            completed.stdout,
            request.max_stdout_bytes,
        )
        stderr, stderr_bytes, stderr_truncated, stderr_redacted = _bounded_output(
            completed.stderr,
            request.max_stderr_bytes,
        )
        output_secret_detected = stdout_redacted or stderr_redacted
        return _result(
            request=request,
            gate=gate,
            argv=argv,
            runner_mode=runner_mode,
            command=command,
            requested_by=requested_by,
            working_directory=str(cwd),
            timeout_seconds=timeout_seconds,
            started_at=started_at,
            started=started,
            executed=True,
            blocked=False,
            dry_run=False,
            timed_out=False,
            exit_code=completed.returncode,
            reason="Command executed in sandbox_readonly mode.",
            blocked_reason=None,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            redacted=secret_detected or output_secret_detected,
            secrets_detected=secret_detected or output_secret_detected,
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_bytes, stdout_truncated, stdout_redacted = _bounded_output(
            exc.stdout,
            request.max_stdout_bytes,
        )
        stderr, stderr_bytes, stderr_truncated, stderr_redacted = _bounded_output(
            exc.stderr,
            request.max_stderr_bytes,
        )
        return _result(
            request=request,
            gate=gate,
            argv=argv,
            runner_mode=runner_mode,
            command=command,
            requested_by=requested_by,
            working_directory=str(cwd),
            timeout_seconds=timeout_seconds,
            started_at=started_at,
            started=started,
            executed=True,
            blocked=False,
            dry_run=False,
            timed_out=True,
            exit_code=None,
            reason="Command timed out in sandbox_readonly mode.",
            blocked_reason=None,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            redacted=secret_detected or stdout_redacted or stderr_redacted,
            secrets_detected=secret_detected or stdout_redacted or stderr_redacted,
        )


def _coerce_request(
    value: SandboxCommandRunnerRequest | Mapping[str, Any] | Any,
) -> SandboxCommandRunnerRequest:
    if isinstance(value, SandboxCommandRunnerRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError(
            "Sandbox command runner input must be a request, mapping, or object with to_dict()."
        )

    return SandboxCommandRunnerRequest(
        command=str(payload.get("command") or ""),
        requested_by=str(payload.get("requested_by") or "unknown"),
        runner_mode=str(payload.get("runner_mode") or DEFAULT_RUNNER_MODE),
        command_mode=str(payload.get("command_mode") or "sandbox_allowed"),
        workspace_root=payload.get("workspace_root"),
        working_directory=payload.get("working_directory"),
        timeout_seconds=int(
            payload["timeout_seconds"] if payload.get("timeout_seconds") is not None else 60
        ),
        max_stdout_bytes=int(payload.get("max_stdout_bytes") or DEFAULT_OUTPUT_BYTES),
        max_stderr_bytes=int(payload.get("max_stderr_bytes") or DEFAULT_OUTPUT_BYTES),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or "main"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        purpose=payload.get("purpose"),
        metadata=dict(payload.get("metadata") or {}),
    )


def _blocked_reason(
    *,
    runner_mode: str,
    request: SandboxCommandRunnerRequest,
    gate: Any,
    parse_error: str | None,
    workspace_root_error: str | None,
    cwd_error: str | None,
    allowlist_error: str | None,
    secret_detected: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if runner_mode not in RUNNER_MODES:
        return "Sandbox command runner mode is unknown."
    if runner_mode == "disabled":
        return "Sandbox command runner is disabled by default."
    if runner_mode == "blocked":
        return "Sandbox command runner mode blocks all commands."
    if request.command_mode != "sandbox_allowed":
        return "Command mode must be sandbox_allowed for execution."
    if gate.blocked or not gate.allowed:
        return gate.escalation_reason or gate.reason
    if not gate.safe_for_future_execution:
        return "Command is not safe for future sandbox execution."
    if not gate.requires_runtime_truth:
        return "Runtime Truth is required for sandbox execution."
    if not gate.requires_sandbox:
        return "Sandbox isolation is required for command execution."
    if gate.category != "read_safe":
        return "Phase 17 executes only read-safe commands."
    if parse_error:
        return parse_error
    if workspace_root_error:
        return workspace_root_error
    if cwd_error:
        return cwd_error
    if allowlist_error:
        return allowlist_error
    if _is_git_write_command(gate.normalized_command):
        return "Git write commands are blocked in Phase 17."
    return None


def _parse_argv(command: str) -> tuple[list[str], str | None]:
    if not command:
        return [], "Command is empty."
    for pattern in _SHELL_OPERATOR_PATTERNS:
        if pattern.search(command):
            return [], "Shell operators and command chaining are blocked."
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return [], "Command could not be parsed safely."
    if not argv:
        return [], "Command is empty."
    if any(_contains_credential_like(arg) for arg in argv):
        return [], "Secret-like command argument was detected."
    return argv, None


def _validate_executable_argv(
    argv: list[str],
    cwd: Path | None,
    workspace_root: Path | None,
) -> str | None:
    if not argv:
        return "Command is empty."
    command = argv[0].lower()
    joined = " ".join(argv).lower()
    if _is_git_write_command(joined):
        return "Git write commands are blocked in Phase 17."
    if command == "gh":
        return "GitHub CLI commands are blocked in Phase 17."
    if command in {"curl", "wget", "ssh", "scp", "ftp", "nc", "netcat"}:
        return "Network commands are blocked in Phase 17."
    if command in {"sudo", "su", "chmod", "chown", "rm", "del", "rmdir"}:
        return "Privileged or destructive commands are blocked in Phase 17."

    validators = (
        _is_allowed_git(argv),
        _is_allowed_python(argv, cwd, workspace_root),
        _is_allowed_pytest(argv, cwd, workspace_root),
        _is_allowed_npm(argv),
        _is_allowed_node(argv),
        _is_allowed_cargo(argv, cwd, workspace_root),
        _is_allowed_rustc(argv),
    )
    if any(validators):
        return None
    return "Command is not in the Phase 17 executable allowlist."


def _is_allowed_git(argv: list[str]) -> bool:
    return argv in (
        ["git", "status"],
        ["git", "diff"],
        ["git", "diff", "--check"],
        ["git", "log"],
        ["git", "branch", "--show-current"],
    )


def _is_allowed_python(
    argv: list[str],
    cwd: Path | None,
    workspace_root: Path | None,
) -> bool:
    if argv == ["python", "--version"]:
        return True
    if len(argv) >= 4 and argv[:3] == ["python", "-m", "pytest"]:
        return _safe_path_args(
            argv[3:],
            cwd,
            workspace_root,
            path_flags={"--basetemp", "--rootdir", "--config-file", "-c"},
        )
    if len(argv) >= 4 and argv[:3] == ["python", "-m", "json.tool"]:
        return _safe_path_args(argv[3:], cwd, workspace_root)
    if len(argv) >= 4 and argv[:3] == ["python", "-m", "compileall"]:
        return _safe_path_args(argv[3:], cwd, workspace_root)
    return False


def _is_allowed_pytest(
    argv: list[str],
    cwd: Path | None,
    workspace_root: Path | None,
) -> bool:
    return (
        len(argv) >= 2
        and argv[0] == "pytest"
        and _safe_path_args(
            argv[1:],
            cwd,
            workspace_root,
            path_flags={"--basetemp", "--rootdir", "--config-file", "-c"},
        )
    )


def _is_allowed_npm(argv: list[str]) -> bool:
    return argv in (
        ["npm", "--version"],
        ["npm", "test"],
        ["npm", "run", "test"],
        ["npm", "run", "build"],
        ["npm", "run", "lint"],
        ["npm", "run", "typecheck"],
    )


def _is_allowed_node(argv: list[str]) -> bool:
    return argv == ["node", "--version"]


def _is_allowed_cargo(
    argv: list[str],
    cwd: Path | None = None,
    workspace_root: Path | None = None,
) -> bool:
    if argv in (["cargo", "--version"], ["cargo", "fmt", "--check"]):
        return True
    if len(argv) < 2 or argv[1] not in {"check", "test", "clippy"}:
        return False
    if len(argv) == 2:
        return True
    return _safe_path_args(
        argv[2:],
        cwd,
        workspace_root,
        path_flags={"--manifest-path"},
        require_path=False,
        allowed_bare_flags={"--locked", "--all", "--all-targets", "--all-features"},
    )


def _is_allowed_rustc(argv: list[str]) -> bool:
    return argv == ["rustc", "--version"]


def _safe_path_args(
    args: list[str],
    cwd: Path | None,
    workspace_root: Path | None,
    *,
    path_flags: set[str] | None = None,
    require_path: bool = True,
    allowed_bare_flags: set[str] | None = None,
) -> bool:
    if not args:
        return not require_path
    supported_path_flags = path_flags or set()
    supported_bare_flags = allowed_bare_flags
    path_args: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if not arg.startswith("-"):
            path_args.append(arg)
            index += 1
            continue

        flag, separator, inline_value = arg.partition("=")
        if flag in supported_path_flags:
            if separator:
                value = inline_value
            else:
                index += 1
                if index >= len(args):
                    return False
                value = args[index]
            if not value or value.startswith("-"):
                return False
            path_args.append(value)
            index += 1
            continue

        if _looks_like_security_sensitive_path_flag(flag):
            return False
        if supported_bare_flags is not None and arg not in supported_bare_flags:
            return False
        if separator and _looks_like_path_value(inline_value):
            return False
        index += 1

    if require_path and not path_args:
        return False
    return all(_is_safe_argument_path(arg, cwd, workspace_root) for arg in path_args)


def _looks_like_security_sensitive_path_flag(flag: str) -> bool:
    normalized = flag.lstrip("-").lower().replace("_", "-")
    components = {part for part in normalized.split("-") if part}
    return bool(
        components
        & {
            "config",
            "cwd",
            "dir",
            "file",
            "manifest",
            "output",
            "path",
            "root",
            "temp",
            "workspace",
        }
    ) or normalized in {"cov", "junitxml", "rootdir", "basetemp"}


def _looks_like_path_value(value: str) -> bool:
    if not value:
        return False
    path = Path(value)
    return path.is_absolute() or value.startswith((".", "~")) or "/" in value or "\\" in value


def _is_safe_argument_path(
    value: str,
    cwd: Path | None,
    workspace_root: Path | None,
) -> bool:
    if not value or _contains_credential_like(value):
        return False
    path = Path(value)
    if ".." in path.parts:
        return False
    if any(part.lower() in _SECRET_PATH_PARTS for part in path.parts):
        return False
    if workspace_root is None:
        return False
    base = cwd or workspace_root
    candidate = path if path.is_absolute() else base / path
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        return False
    return _is_inside(resolved, workspace_root)


def _resolve_workspace_root(explicit_root: str | None) -> tuple[Path | None, str | None]:
    if explicit_root is not None:
        return _validate_workspace_root(explicit_root, require_markers=False)

    configured_root = os.environ.get("OMNI_WORKSPACE_ROOT")
    if configured_root is not None:
        return _validate_workspace_root(configured_root, require_markers=True)

    discovered = _discover_repository_root(Path(__file__).resolve().parent)
    if discovered is None:
        return None, "Sandbox workspace root could not be established safely."
    return discovered, None


def _validate_workspace_root(
    value: str,
    *,
    require_markers: bool,
) -> tuple[Path | None, str | None]:
    if not value or _contains_credential_like(value):
        return None, "Sandbox workspace root is missing or contains secret-like content."
    path = Path(value)
    if not path.is_absolute():
        return None, "Sandbox workspace root must be absolute."
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None, "Sandbox workspace root must already exist."
    if not resolved.is_dir():
        return None, "Sandbox workspace root must be a directory."
    if _is_filesystem_root(resolved):
        return None, "Filesystem root cannot be a sandbox workspace root."
    try:
        user_home = Path.home().resolve(strict=True)
    except OSError:
        user_home = None
    if user_home is not None and resolved == user_home:
        return None, "User home cannot be a sandbox workspace root."
    if require_markers and not _has_workspace_markers(resolved):
        return None, "Configured sandbox workspace root does not match a repository checkout."
    return resolved, None


def _discover_repository_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if _is_filesystem_root(candidate):
            break
        if _has_workspace_markers(candidate):
            resolved, error = _validate_workspace_root(
                str(candidate),
                require_markers=True,
            )
            return None if error else resolved
    return None


def _has_workspace_markers(path: Path) -> bool:
    return all((path / marker).exists() for marker in _WORKSPACE_MARKERS)


def _resolve_working_directory(
    value: str | None,
    workspace_root: Path | None,
) -> tuple[Path | None, str | None]:
    if workspace_root is None:
        return None, "Sandbox workspace root is unavailable."
    if not value:
        return workspace_root, None
    if _contains_credential_like(value):
        return None, "Working directory contains secret-like content."
    path = Path(value)
    if ".." in path.parts:
        return None, "Working directory path traversal is blocked."
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None, "Working directory must already exist."
    if not resolved.is_dir():
        return None, "Working directory must be a directory."
    lowered_parts = {part.lower() for part in resolved.parts}
    if ".git" in lowered_parts or any(part in _SECRET_PATH_PARTS for part in lowered_parts):
        return None, "Working directory cannot target repository internals or secrets."
    if _is_filesystem_root(resolved):
        return None, "Filesystem root is not an allowed working directory."
    if _is_inside(resolved, workspace_root):
        return resolved, None
    return None, "Working directory must stay inside the configured sandbox workspace."


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _is_filesystem_root(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    return str(resolved) == resolved.anchor or resolved.parent == resolved


def _sanitized_environment(
    cwd: Path | None,
    workspace_root: Path | None,
) -> dict[str, str]:
    safe_env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper_key = key.upper()
        if upper_key not in _ALLOWED_ENV_KEYS:
            continue
        if _contains_credential_like(key) or _contains_credential_like(value):
            continue
        if upper_key == "PYTHONPATH" and not _env_path_is_safe(
            value,
            cwd,
            workspace_root,
        ):
            continue
        safe_env[key] = value
    return safe_env


def _env_path_is_safe(
    value: str,
    cwd: Path | None,
    workspace_root: Path | None,
) -> bool:
    if workspace_root is None:
        return False
    separator = os.pathsep
    for part in value.split(separator):
        if not part:
            continue
        try:
            resolved = Path(part).resolve(strict=False)
        except OSError:
            return False
        if not _is_inside(resolved, workspace_root):
            return False
        if cwd and not (_is_inside(resolved, cwd) or _is_inside(cwd, resolved)):
            return False
    return True


def _bounded_output(value: bytes | str | None, limit: int) -> tuple[str, int, bool, bool]:
    raw = _to_bytes(value)
    safe_limit = max(0, int(limit or DEFAULT_OUTPUT_BYTES))
    truncated = len(raw) > safe_limit
    clipped = raw[:safe_limit]
    decoded = clipped.decode("utf-8", errors="replace")
    redacted, was_redacted = _redact_text(decoded)
    return redacted, len(raw), truncated, was_redacted


def _to_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8", errors="replace")


def _result(
    *,
    request: SandboxCommandRunnerRequest,
    gate: Any,
    argv: list[str],
    runner_mode: str,
    command: str,
    requested_by: str,
    working_directory: str | None,
    timeout_seconds: int,
    started_at: str,
    started: float,
    executed: bool,
    blocked: bool,
    dry_run: bool,
    timed_out: bool,
    exit_code: int | None,
    reason: str,
    blocked_reason: str | None,
    stdout: str,
    stderr: str,
    stdout_truncated: bool,
    stderr_truncated: bool,
    stdout_bytes: int,
    stderr_bytes: int,
    redacted: bool,
    secrets_detected: bool,
) -> SandboxCommandRunnerResult:
    finished_at = _utc_now()
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    evidence = build_command_runner_evidence(
        command=command,
        normalized_command=gate.normalized_command,
        category=gate.category,
        runner_mode=runner_mode,
        command_mode=request.command_mode,
        requested_by=requested_by,
        working_directory=working_directory,
        gate_allowed=gate.allowed,
        gate_blocked=gate.blocked,
        gate_reason=gate.reason,
        gate_risk_level=gate.risk_level,
        execution_attempted=executed,
        command_executed=executed,
        blocked=blocked or secrets_detected,
        dry_run=dry_run,
        timed_out=timed_out,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        secrets_detected=secrets_detected,
        human_intervention_required=blocked or secrets_detected,
        related_phase=request.related_phase,
        related_pr=request.related_pr,
    ).to_dict()
    return SandboxCommandRunnerResult(
        executed=executed,
        blocked=blocked,
        dry_run=dry_run,
        timed_out=timed_out,
        exit_code=exit_code,
        command=command,
        normalized_command=gate.normalized_command,
        argv=argv,
        runner_mode=runner_mode,
        command_mode=request.command_mode,
        category=gate.category,
        risk_level=gate.risk_level,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=gate.escalation_reason,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        requested_by=requested_by,
        related_phase=request.related_phase,
        related_pr=request.related_pr,
        gate_allowed=gate.allowed,
        gate_blocked=gate.blocked,
        gate_requires_runtime_truth=gate.requires_runtime_truth,
        gate_requires_sandbox=gate.requires_sandbox,
        runtime_truth=evidence,
        evidence_version=COMMAND_RUNNER_EVIDENCE_VERSION,
        redacted=redacted,
    )


def _normalize_timeout(value: int) -> int:
    return min(MAX_TIMEOUT_SECONDS, max(MIN_TIMEOUT_SECONDS, int(value)))


def _is_git_write_command(command: str) -> bool:
    lowered = command.lower()
    return lowered.startswith(
        (
            "git add",
            "git commit",
            "git push",
            "git checkout -b",
            "git switch -c",
            "git merge",
            "git rebase",
        )
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
