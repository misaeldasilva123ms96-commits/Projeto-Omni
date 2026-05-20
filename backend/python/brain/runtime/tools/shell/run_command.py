"""
Shell tool — deny-by-default hardening (Phase 1A — Roadmap Oficial v2.1).

Policy:
  - Shell is BLOCKED by default.
  - Shell is ALWAYS blocked in public-demo mode, regardless of other flags.
  - Explicit allow requires OMNI_ALLOW_SHELL_TOOLS=true AND NOT public-demo.
  - Allowlist of safe commands + safe arguments only.
  - Dangerous patterns are rejected at parse time.
  - npm run validates against package.json scripts.
  - Legacy env vars (OMINI_*, ALLOW_SHELL) are supported as aliases.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Env var names (canonical + legacy aliases)
# ---------------------------------------------------------------------------

_ENV_ALLOW_SHELL = "OMNI_ALLOW_SHELL_TOOLS"
_ENV_ALLOW_SHELL_LEGACY = "OMINI_ALLOW_SHELL_TOOLS"
_ENV_ALLOW_SHELL_BARE = "ALLOW_SHELL"

_ENV_PUBLIC_DEMO = "OMNI_PUBLIC_DEMO_MODE"
_ENV_PUBLIC_DEMO_LEGACY = "OMINI_PUBLIC_DEMO_MODE"

_ENV_ALLOWLIST_MODE = "OMNI_SHELL_ALLOWLIST_MODE"
_ENV_ALLOWLIST_MODE_LEGACY = "OMINI_SHELL_ALLOWLIST_MODE"

# ---------------------------------------------------------------------------
# Public error codes
# ---------------------------------------------------------------------------

SHELL_TOOL_BLOCKED = "SHELL_TOOL_BLOCKED"
SHELL_TOOL_DANGEROUS_COMMAND = "SHELL_TOOL_DANGEROUS_COMMAND"
SHELL_TOOL_COMMAND_NOT_ALLOWED = "SHELL_TOOL_COMMAND_NOT_ALLOWED"
SHELL_TOOL_ARG_NOT_ALLOWED = "SHELL_TOOL_ARG_NOT_ALLOWED"
SHELL_TOOL_NPM_SCRIPT_NOT_ALLOWED = "SHELL_TOOL_NPM_SCRIPT_NOT_ALLOWED"
SHELL_TOOL_EXECUTION_ERROR = "SHELL_TOOL_EXECUTION_ERROR"

# ---------------------------------------------------------------------------
# Command allowlist
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS: dict[str, list[str]] = {
    "git": ["status", "log", "diff", "show", "branch", "--no-pager"],
    "npm": ["test", "run", "ci"],
    "python": ["-m", "--version"],
    "python3": ["-m", "--version"],
    "pytest": ["-x", "-v", "--tb=short"],
}

ALLOWED_NPM_SCRIPTS: frozenset[str] = frozenset({
    "test",
    "test:python:pytest",
    "test:js-runtime",
    "typecheck",
    "build",
})

# ---------------------------------------------------------------------------
# Dangerous patterns — always rejected, even when shell is enabled
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:^|\s|;|&&|\|\|)rm(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)del(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)format(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)mkfs(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)shutdown(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)reboot(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)sudo(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)su(?:\s|$|;|&&|\|\|)"),
    re.compile(r"\bchmod\s+777\b"),
    re.compile(r"(?:^|\s|;|&&|\|\|)chown(?:\s|$|;|&&|\|\|)"),
    re.compile(r"(?:^|\s|;|&&|\|\|)dd(?:\s|$|;|&&|\|\|)"),
    re.compile(r"\bcurl\b.*\|"),
    re.compile(r"\bwget\b.*\|"),
    re.compile(r"(?:^|\s|;|&&|\|\|)powershell(?:\s|$|;|&&|\|\|)"),
    re.compile(r"\bcmd\.exe\b"),
    re.compile(r"\bbash\s+-c\b"),
    re.compile(r"\bsh\s+-c\b"),
    re.compile(r"\bpython\s+-c\b"),
    re.compile(r"\bnode\s+-e\b"),
    re.compile(r"\bfind\b.*-delete"),
    re.compile(r"/bin/rm\b"),
    re.compile(r"/bin/bash\b"),
    re.compile(r"/bin/sh\b"),
]


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _is_truthy(name: str, *aliases: str) -> bool:
    for n in (name, *aliases):
        val = str(os.getenv(n, "")).strip().lower()
        if val in {"1", "true", "yes", "on"}:
            return True
    return False


def is_public_demo_mode() -> bool:
    return _is_truthy(_ENV_PUBLIC_DEMO, _ENV_PUBLIC_DEMO_LEGACY)


def is_shell_allowed() -> bool:
    if is_public_demo_mode():
        return False
    return _is_truthy(_ENV_ALLOW_SHELL, _ENV_ALLOW_SHELL_LEGACY, _ENV_ALLOW_SHELL_BARE)


def is_allowlist_mode() -> bool:
    return _is_truthy(_ENV_ALLOWLIST_MODE, _ENV_ALLOWLIST_MODE_LEGACY)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _blocked_response(error_public_code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "tool_status": "blocked",
        "error_public_code": error_public_code,
        "error_public_message": message,
        "internal_error_redacted": True,
    }


def _contains_dangerous_pattern(command_str: str) -> bool:
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(command_str):
            return True
    return False


def _validate_npm_run(args: list[str], repo_root: str) -> bool:
    """Return True only if `npm run <script>` targets an allowed script in package.json."""
    if len(args) < 2 or args[0] != "run":
        return False
    script = args[1]
    if script not in ALLOWED_NPM_SCRIPTS:
        return False
    pkg_path = Path(repo_root) / "package.json"
    try:
        with open(pkg_path, encoding="utf-8") as f:
            scripts = json.load(f).get("scripts", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    return script in scripts


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_command(
    command: str | list[str],
    *,
    repo_root: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """
    Execute a shell command with strict safety policy.

    Returns a structured result dict. Never raises — errors are captured
    and returned as controlled error payloads.
    """
    # Public demo always blocks — this check MUST come first
    if is_public_demo_mode():
        return _blocked_response(
            SHELL_TOOL_BLOCKED,
            "Shell execution is disabled by policy.",
        )

    # Blocked by default unless explicitly allowed
    if not is_shell_allowed():
        return _blocked_response(
            SHELL_TOOL_BLOCKED,
            "Shell execution is disabled by policy.",
        )

    # Normalize command to list
    if isinstance(command, str):
        parts = command.strip().split()
    else:
        parts = [str(p) for p in command]

    if not parts:
        return _blocked_response(SHELL_TOOL_BLOCKED, "Shell execution is disabled by policy.")

    command_str = " ".join(parts)
    cmd_name = parts[0]
    cmd_args = parts[1:]

    # Reject dangerous patterns first
    if _contains_dangerous_pattern(command_str):
        return _blocked_response(
            SHELL_TOOL_DANGEROUS_COMMAND,
            "Shell execution is disabled by policy.",
        )

    # Allowlist check
    if cmd_name not in ALLOWED_COMMANDS:
        return _blocked_response(
            SHELL_TOOL_COMMAND_NOT_ALLOWED,
            "Shell execution is disabled by policy.",
        )

    allowed_args = ALLOWED_COMMANDS[cmd_name]

    # npm run requires extra validation
    if cmd_name == "npm":
        if not _validate_npm_run(cmd_args, repo_root or os.getcwd()):
            return _blocked_response(
                SHELL_TOOL_NPM_SCRIPT_NOT_ALLOWED,
                "Shell execution is disabled by policy.",
            )
    else:
        # Validate first argument is in allowlist
        if cmd_args and cmd_args[0] not in allowed_args:
            return _blocked_response(
                SHELL_TOOL_ARG_NOT_ALLOWED,
                "Shell execution is disabled by policy.",
            )

    # Execute
    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=repo_root or os.getcwd(),
        )
        return {
            "ok": result.returncode == 0,
            "tool_status": "succeeded" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[:8000],
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "tool_status": "failed",
            "error_public_code": SHELL_TOOL_EXECUTION_ERROR,
            "error_public_message": "Command timed out.",
            "internal_error_redacted": True,
        }
    except Exception:
        return {
            "ok": False,
            "tool_status": "failed",
            "error_public_code": SHELL_TOOL_EXECUTION_ERROR,
            "error_public_message": "Shell execution failed.",
            "internal_error_redacted": True,
        }


__all__ = [
    "run_command",
    "is_public_demo_mode",
    "is_shell_allowed",
    "ALLOWED_COMMANDS",
    "ALLOWED_NPM_SCRIPTS",
    "SHELL_TOOL_BLOCKED",
]
