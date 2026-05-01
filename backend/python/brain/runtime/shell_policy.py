from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}
ALLOWLISTED_NPM_RUN_SCRIPTS = {
    "build",
    "test",
    "test:js-runtime",
    "test:python:pytest",
    "typecheck",
}
DANGEROUS_TOKEN_PATTERNS = {
    "rm",
    "/bin/rm",
    "del",
    "format",
    "mkfs",
    "shutdown",
    "reboot",
    "sudo",
    "su",
    "chown",
    "powershell",
    "cmd.exe",
}


def _truthy_env(*names: str) -> bool:
    for name in names:
        value = str(os.getenv(name, "") or "").strip().lower()
        if value in TRUE_VALUES:
            return True
    return False


def is_public_demo_mode() -> bool:
    return _truthy_env("OMNI_PUBLIC_DEMO_MODE", "OMINI_PUBLIC_DEMO_MODE")


def is_shell_allowed() -> bool:
    if is_public_demo_mode():
        return False
    return _truthy_env("OMNI_ALLOW_SHELL_TOOLS", "OMINI_ALLOW_SHELL_TOOLS", "ALLOW_SHELL")


def is_shell_allowlist_mode() -> bool:
    return _truthy_env("OMNI_SHELL_ALLOWLIST_MODE", "OMINI_SHELL_ALLOWLIST_MODE") or True


def build_shell_blocked_result(reason: str) -> dict[str, Any]:
    public_demo = reason == "public_demo_mode"
    return {
        "ok": False,
        "tool_status": "blocked",
        "error_public_code": "TOOL_BLOCKED_PUBLIC_DEMO" if public_demo else "SHELL_TOOL_BLOCKED",
        "error_public_message": "Shell execution is disabled by policy.",
        "internal_error_redacted": True,
        "error_payload": {
            "kind": "shell_policy_blocked",
            "message": "Shell execution is disabled by policy.",
            "public_code": "TOOL_BLOCKED_PUBLIC_DEMO" if public_demo else "SHELL_TOOL_BLOCKED",
        },
    }


def validate_shell_command(command: list[str], args: list[str] | None = None, repo_root: Path | None = None) -> tuple[bool, str]:
    parts = [str(part) for part in (command or [])]
    if args:
        parts.extend(str(part) for part in args)
    if not parts:
        return False, "empty_command"
    if is_public_demo_mode():
        return False, "public_demo_mode"
    if not is_shell_allowed():
        return False, "shell_disabled"
    if _has_dangerous_pattern(parts):
        return False, "dangerous_pattern"
    if is_shell_allowlist_mode():
        return _validate_allowlisted_command(parts, repo_root or Path.cwd())
    return True, "allowed"


def _has_dangerous_pattern(parts: list[str]) -> bool:
    lowered = [part.strip().lower() for part in parts if str(part).strip()]
    joined = " ".join(lowered)
    if any(token in DANGEROUS_TOKEN_PATTERNS for token in lowered):
        return True
    if "chmod 777" in joined or "find -delete" in joined:
        return True
    if "curl" in lowered and "|" in joined:
        return True
    if "wget" in lowered and "|" in joined:
        return True
    if len(lowered) >= 2 and lowered[0] in {"bash", "sh"} and lowered[1] == "-c":
        return True
    if len(lowered) >= 2 and lowered[0] in {"python", "python3", "node"} and lowered[1] in {"-c", "-e"}:
        return True
    if re.search(r"(^|[\\/])rm$", lowered[0]):
        return True
    return False


def _validate_allowlisted_command(parts: list[str], repo_root: Path) -> tuple[bool, str]:
    executable = Path(parts[0]).name.lower()
    if executable in {"git", "git.exe"}:
        return _allow_git(parts)
    if executable in {"npm", "npm.cmd", "npm.exe"}:
        return _allow_npm(parts, repo_root)
    if executable in {"python", "python.exe", "python3", "python3.exe"}:
        return _allow_python(parts)
    if executable in {"pytest", "pytest.exe"}:
        return _allow_pytest(parts)
    return False, "not_allowlisted"


def _allow_git(parts: list[str]) -> tuple[bool, str]:
    if len(parts) < 2:
        return False, "missing_git_subcommand"
    return (True, "allowed") if parts[1] in {"status", "log", "diff", "show", "branch"} else (False, "git_subcommand_not_allowlisted")


def _allow_npm(parts: list[str], repo_root: Path) -> tuple[bool, str]:
    if len(parts) < 2:
        return False, "missing_npm_subcommand"
    subcommand = parts[1]
    if subcommand in {"test", "ci"}:
        return True, "allowed"
    if subcommand != "run":
        return False, "npm_subcommand_not_allowlisted"
    if len(parts) < 3:
        return False, "missing_npm_script"
    script_name = parts[2]
    if script_name not in ALLOWLISTED_NPM_RUN_SCRIPTS:
        return False, "npm_script_not_allowlisted"
    package_json = repo_root / "package.json"
    if not package_json.is_file():
        return False, "missing_package_json"
    try:
        scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
    except Exception:
        return False, "invalid_package_json"
    if script_name not in scripts:
        return False, "missing_npm_script"
    return True, "allowed"


def _allow_python(parts: list[str]) -> tuple[bool, str]:
    if len(parts) < 2:
        return False, "missing_python_arg"
    return (True, "allowed") if parts[1] in {"-m", "--version"} else (False, "python_arg_not_allowlisted")


def _allow_pytest(parts: list[str]) -> tuple[bool, str]:
    allowed = {"-x", "-v", "--tb=short"}
    return (True, "allowed") if all(part in allowed for part in parts[1:]) else (False, "pytest_arg_not_allowlisted")
