from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from brain.env import read_env
from brain.runtime.patch_generator import apply_patch, build_patch, review_patch_risk
from brain.runtime.patch_set_manager import apply_patch_set, build_patch_set, review_patch_set
from brain.runtime.error_taxonomy import OmniErrorCode, build_public_error
from brain.runtime.shell_policy import build_shell_blocked_result, validate_shell_command
from brain.runtime.tool_governance_policy import build_governance_blocked_result, evaluate_tool_governance
from brain.runtime.workspace_manager import WorkspaceManager
from brain.runtime.workspace_paths import (
    WorkspacePathError,
    resolve_workspace_entry,
    resolve_workspace_path,
    validate_workspace_glob_pattern,
)


ENGINEERING_TOOLS = {
    "filesystem_read",
    "read_file",
    "filesystem_write",
    "write_file",
    "directory_tree",
    "git_status",
    "git_diff",
    "git_commit",
    "test_runner",
    "package_manager",
    "dependency_inspection",
    "code_search",
    "glob_search",
    "autonomous_debug_loop",
    "verification_runner",
    "filesystem_patch_set",
}


def supports_engineering_tool(tool_name: str) -> bool:
    return str(tool_name or "") in ENGINEERING_TOOLS


def execute_engineering_action(
    *,
    project_root: Path,
    action: dict[str, Any],
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    tool = str(action.get("selected_tool", ""))
    arguments = dict(action.get("tool_arguments", {}) or {})
    project_root = Path(project_root).resolve()
    workspace_root = Path(arguments.get("workspace_root") or project_root).resolve()
    if not _is_allowed_workspace_root(project_root, workspace_root):
        return _error(tool, "workspace_outside_allowed_roots", "Requested workspace is outside the allowed project roots.")
    governance_decision = evaluate_tool_governance(action)
    if not governance_decision.get("allowed"):
        return build_governance_blocked_result(tool, governance_decision)

    if tool in {"filesystem_read", "read_file"}:
        try:
            target = resolve_workspace_path(workspace_root, str(arguments.get("path", "")))
        except WorkspacePathError as error:
            return _error(tool, error.code, "Requested file is outside the allowed workspace.")
        if _public_demo_mode() and _is_sensitive_public_demo_file(workspace_root, target):
            return _error(tool, "public_demo_sensitive_read_blocked", "Requested file is not readable in public demo mode.")
        content = target.read_text(encoding="utf-8")
        limit = int(arguments.get("limit", 4000) or 4000)
        return _ok(tool, {"file": {"filePath": str(target), "content": content[:limit]}})

    if tool in {"filesystem_write", "write_file"}:
        file_path = str(arguments.get("path", ""))
        try:
            resolve_workspace_path(workspace_root, file_path)
        except WorkspacePathError as error:
            return _error(tool, error.code, "Requested file is outside the allowed workspace.")
        patch = build_patch(
            workspace_root=workspace_root,
            file_path=file_path,
            new_content=str(arguments.get("content", "")),
            confidence_score=float(arguments.get("confidence_score", 0.6) or 0.6),
        )
        review = review_patch_risk(patch=patch)
        if not review["accepted"]:
            return _error(tool, "patch_review_blocked", f"Patch review blocked write: {', '.join(review['warnings'])}", review=review, patch=patch)
        applied = apply_patch(workspace_root=workspace_root, patch=patch)
        if not applied.get("ok"):
            return _error(tool, "patch_apply_failed", "Unable to apply patch safely.", patch=patch, apply_result=applied)
        return _ok(tool, {"patch": patch, "review": review, "workspace_root": str(workspace_root)})

    if tool == "filesystem_patch_set":
        file_updates = list(arguments.get("file_updates", []) or [])
        for update in file_updates:
            if not isinstance(update, dict):
                return _error(tool, "invalid_patch_set", "Patch set entries must be objects.")
            try:
                resolve_workspace_path(workspace_root, str(update.get("file_path", "")))
            except WorkspacePathError as error:
                return _error(tool, error.code, "Requested file is outside the allowed workspace.")
        patch_set = build_patch_set(
            workspace_root=workspace_root,
            file_updates=file_updates,
            dependency_notes=list(arguments.get("dependency_notes", []) or []),
            verification_plan=dict(arguments.get("verification_plan", {}) or {}),
        )
        review = review_patch_set(patch_set=patch_set)
        if not review["accepted"]:
            return _error(tool, "patch_set_review_blocked", f"Patch set review blocked write: {', '.join(review['warnings'])}", review=review, patch_set=patch_set)
        applied = apply_patch_set(workspace_root=workspace_root, patch_set=patch_set)
        if not applied.get("ok"):
            return _error(tool, "patch_set_apply_failed", "Unable to apply patch set safely.", patch_set=patch_set, apply_result=applied)
        return _ok(tool, {"patch_set": patch_set, "review": review, "workspace_root": str(workspace_root)})

    if tool == "directory_tree":
        max_depth = int(arguments.get("max_depth", 2) or 2)
        lines: list[str] = []
        for file_path in sorted(workspace_root.rglob("*")):
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in file_path.parts):
                continue
            try:
                _, relative_path = resolve_workspace_entry(workspace_root, file_path)
            except WorkspacePathError:
                continue
            depth = len(relative_path.parts)
            if depth > max_depth:
                continue
            lines.append(str(relative_path).replace("\\", "/"))
        return _ok(tool, {"tree": lines[:500]})

    if tool == "dependency_inspection":
        result = _dependency_inspection(workspace_root)
        return _ok(tool, result)

    if tool == "git_status":
        return _run_command(tool, ["git", "status", "--short"], cwd=workspace_root, timeout_seconds=timeout_seconds)

    if tool == "git_diff":
        return _run_command(tool, ["git", "diff", "--", str(arguments.get("path", "."))], cwd=workspace_root, timeout_seconds=timeout_seconds)

    if tool == "git_commit":
        if str(action.get("approval_state", "")) != "approved":
            return _error(tool, "permission_denied", "git_commit requires explicit approval.")
        message = str(arguments.get("message", "Automated commit")).strip()
        return _run_command(tool, ["git", "commit", "-m", message], cwd=workspace_root, timeout_seconds=timeout_seconds)

    if tool == "shell_command":
        command = _normalize_shell_command(arguments.get("command"))
        return _run_command(tool, command, cwd=workspace_root, timeout_seconds=timeout_seconds)

    if tool == "test_runner":
        command = arguments.get("command")
        test_env = _build_test_env(workspace_root)
        if isinstance(command, list) and command:
            return _run_command(tool, [str(part) for part in command], cwd=workspace_root, timeout_seconds=timeout_seconds, env=test_env)
        return _run_command(tool, _default_test_command(workspace_root), cwd=workspace_root, timeout_seconds=timeout_seconds, env=test_env)

    if tool == "package_manager":
        subcommand = str(arguments.get("subcommand", "inspect"))
        if subcommand == "inspect":
            return _ok(tool, _dependency_inspection(workspace_root))
        if subcommand in {"install", "update"}:
            return _error(tool, "missing_approval", "Package mutation commands require explicit operator approval.")
        return _error(tool, "unsupported_package_manager_subcommand", f"Unsupported package manager subcommand: {subcommand}")

    if tool == "code_search":
        pattern = str(arguments.get("pattern", "")).strip()
        if not pattern:
            return _error(tool, "missing_pattern", "code_search requires a pattern")
        matches: list[dict[str, Any]] = []
        for file_path in workspace_root.rglob("*"):
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in file_path.parts):
                continue
            try:
                safe_path, relative_path = resolve_workspace_entry(workspace_root, file_path)
                if not safe_path.is_file():
                    continue
                content = safe_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError, WorkspacePathError):
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                if pattern in line:
                    matches.append(
                        {
                            "path": str(relative_path).replace("\\", "/"),
                            "line_number": line_number,
                            "line": line.strip(),
                        }
                    )
                    if len(matches) >= 200:
                        break
            if len(matches) >= 200:
                    break
        return _ok(tool, {"matches": matches})

    if tool == "glob_search":
        raw_pattern = str(arguments.get("pattern", "")).strip()
        if not raw_pattern:
            return _error(tool, "missing_pattern", "glob_search requires a pattern")
        try:
            pattern = validate_workspace_glob_pattern(raw_pattern)
            search_root = resolve_workspace_path(
                workspace_root,
                str(arguments.get("path", ".") or "."),
                allow_workspace_root=True,
            )
        except WorkspacePathError as error:
            message = (
                "glob_search pattern is invalid"
                if error.code == "invalid_glob_pattern"
                else "Requested search path is outside the allowed workspace."
            )
            return _error(tool, error.code, message)
        if not search_root.exists():
            return _error(tool, "missing_search_root", "glob_search path does not exist")
        matches: list[str] = []
        for file_path in search_root.rglob(pattern):
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in file_path.parts):
                continue
            try:
                _, relative_path = resolve_workspace_entry(workspace_root, file_path)
            except WorkspacePathError:
                continue
            matches.append(str(relative_path).replace("\\", "/"))
            if len(matches) >= 200:
                break
        return _ok(tool, {"filenames": matches})

    if tool == "autonomous_debug_loop":
        from brain.runtime.debug_loop_controller import DebugLoopController

        controller = DebugLoopController(workspace_root)
        result = controller.run(
            task_message=str(arguments.get("task_message", "")),
            test_command=arguments.get("test_command"),
            max_iterations=int(arguments.get("max_iterations", 2) or 2),
            repository_analysis=arguments.get("repository_analysis"),
        )
        return _ok(tool, result)

    if tool == "verification_runner":
        plan = dict(arguments.get("plan", {}) or {})
        summary = _run_verification_plan(
            workspace_root=workspace_root,
            plan=plan,
            timeout_seconds=timeout_seconds,
        )
        return _ok(tool, summary) if summary.get("ok") else {
            "ok": False,
            "selected_tool": tool,
            "result_payload": summary,
            "error_payload": {
                "kind": "verification_failed",
                "message": "Verification plan reported failures.",
            },
        }

    return _error(tool, "unsupported_engineering_tool", f"Unsupported engineering tool: {tool}")


def _dependency_inspection(workspace_root: Path) -> dict[str, Any]:
    files = []
    for candidate in ["package.json", "requirements.txt", "pyproject.toml", "backend/rust/Cargo.toml", "Cargo.toml"]:
        try:
            path = resolve_workspace_path(workspace_root, candidate)
        except WorkspacePathError:
            continue
        if path.exists():
            files.append(candidate)
    try:
        package_json = resolve_workspace_path(workspace_root, "package.json")
    except WorkspacePathError:
        package_json = None
    dependencies: dict[str, Any] = {}
    if package_json is not None and package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            dependencies = {
                "dependencies": payload.get("dependencies", {}),
                "devDependencies": payload.get("devDependencies", {}),
                "scripts": payload.get("scripts", {}),
            }
        except Exception:
            dependencies = {}
    return {
        "dependency_files": files,
        "package_json": dependencies,
    }


def _default_test_command(workspace_root: Path) -> list[str]:
    if (workspace_root / "package.json").exists():
        return ["npm", "test"]
    return ["python", "-m", "pytest", "-q"]


def _run_verification_plan(*, workspace_root: Path, plan: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    modes = list(plan.get("verification_modes", []) or [])
    runs: list[dict[str, Any]] = []
    if "targeted-tests" in modes:
        targeted_tests = list(plan.get("targeted_tests", []) or [])
        if targeted_tests:
            runs.append({
                "mode": "targeted-tests",
                "targeted_tests": targeted_tests,
                "status": "planned",
            })
        else:
            runs.append({
                "mode": "targeted-tests",
                "targeted_tests": [],
                "status": "skipped",
            })
    if "full-tests" in modes:
        result = _run_command("verification_runner", _default_test_command(workspace_root), cwd=workspace_root, timeout_seconds=timeout_seconds, env=_build_test_env(workspace_root))
        runs.append({
            "mode": "full-tests",
            "result": result.get("result_payload", {}),
            "status": "passed" if result.get("ok") else "failed",
        })
    if "dependency-health" in modes:
        inspection = _dependency_inspection(workspace_root)
        runs.append({
            "mode": "dependency-health",
            "result": inspection,
            "status": "passed",
        })
    overall_ok = all(item.get("status") in {"passed", "planned", "skipped"} for item in runs)
    return {
        "ok": overall_ok,
        "verification_modes": modes,
        "runs": runs,
        "merge_readiness": "ready" if overall_ok else "needs-review",
    }


def _run_command(tool: str, command: list[str], *, cwd: Path, timeout_seconds: int, env: dict[str, str] | None = None) -> dict[str, Any]:
    allowed, reason = validate_shell_command(command, repo_root=cwd)
    if not allowed:
        blocked = build_shell_blocked_result(reason)
        blocked["selected_tool"] = tool
        return blocked
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "selected_tool": tool,
            **build_public_error(OmniErrorCode.TIMEOUT),
            "error_payload": {
                "kind": "timeout",
                "message": "The operation timed out.",
                "public_code": "TIMEOUT",
            },
        }
    return {
        "ok": completed.returncode == 0,
        "selected_tool": tool,
        "result_payload": {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        "error_payload": None if completed.returncode == 0 else {
            "kind": "command_failed",
            "message": completed.stderr or completed.stdout or f"{tool} failed",
        },
    }


def _normalize_shell_command(command: Any) -> list[str]:
    if isinstance(command, list):
        return [str(part) for part in command]
    if isinstance(command, str):
        try:
            return shlex.split(command, posix=os.name != "nt")
        except ValueError:
            return []
    return []


def _ok(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "selected_tool": tool,
        "result_payload": payload,
    }


def _is_allowed_workspace_root(project_root: Path, workspace_root: Path) -> bool:
    allowed = [project_root.resolve()]
    configured = str(os.getenv("OMNI_ENGINEERING_ALLOWED_ROOTS", "") or "").strip()
    for raw_root in configured.split(os.pathsep):
        if raw_root.strip():
            allowed.append(Path(raw_root).expanduser().resolve())
    resolved = workspace_root.resolve()
    return any(resolved == root or root in resolved.parents for root in allowed)


def _public_demo_mode() -> bool:
    return read_env("OMNI_PUBLIC_DEMO_MODE").strip().lower() in {"1", "true", "yes", "on"}


def _is_sensitive_public_demo_file(workspace_root: Path, target: Path) -> bool:
    try:
        rel = target.resolve().relative_to(workspace_root.resolve())
    except (OSError, ValueError):
        return True
    parts = [part.lower() for part in rel.parts]
    basename = parts[-1] if parts else ""
    if basename == ".env" or basename.startswith(".env."):
        return True
    if any(part in {".logs", "logs", "runtime_logs", "learning_logs", ".cache", "cache"} for part in parts):
        return True
    if any(token in basename for token in ("key", "token", "secret", "credential")):
        return True
    if "memory" in parts and any(part in {"private", "local", "storage"} for part in parts):
        return True
    return False


def _error(tool: str, kind: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "selected_tool": tool,
        "error_payload": {
            "kind": kind,
            "message": message,
            **extra,
        },
    }


def _build_test_env(workspace_root: Path) -> dict[str, str]:
    allowed_keys = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "PROGRAMDATA",
        "OS",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed_keys}
    env["PYTHONPATH"] = str(workspace_root)
    env["PYTHONNOUSERSITE"] = "1"
    return env
