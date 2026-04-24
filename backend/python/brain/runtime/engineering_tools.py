from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from brain.runtime.patch_generator import apply_patch, build_patch, review_patch_risk
from brain.runtime.patch_set_manager import apply_patch_set, build_patch_set, review_patch_set
from brain.runtime.workspace_manager import WorkspaceManager


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
    workspace_root = Path(arguments.get("workspace_root") or project_root).resolve()

    if tool in {"filesystem_read", "read_file"}:
        target = (workspace_root / str(arguments.get("path", ""))).resolve()
        content = target.read_text(encoding="utf-8")
        limit = int(arguments.get("limit", 4000) or 4000)
        return _ok(tool, {"file": {"filePath": str(target), "content": content[:limit]}})

    if tool in {"filesystem_write", "write_file"}:
        patch = build_patch(
            workspace_root=workspace_root,
            file_path=str(arguments.get("path", "")),
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
        patch_set = build_patch_set(
            workspace_root=workspace_root,
            file_updates=list(arguments.get("file_updates", []) or []),
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
            depth = len(file_path.relative_to(workspace_root).parts)
            if depth > max_depth:
                continue
            lines.append(str(file_path.relative_to(workspace_root)).replace("\\", "/"))
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
            if not file_path.is_file():
                continue
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in file_path.parts):
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                if pattern in line:
                    matches.append(
                        {
                            "path": str(file_path.relative_to(workspace_root)).replace("\\", "/"),
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
        pattern = str(arguments.get("pattern", "")).strip()
        if not pattern:
            return _error(tool, "missing_pattern", "glob_search requires a pattern")
        search_root = workspace_root / str(arguments.get("path", ".") or ".")
        search_root = search_root.resolve()
        if not search_root.exists():
            return _error(tool, "missing_search_root", f"glob_search path does not exist: {search_root}")
        matches: list[str] = []
        for file_path in search_root.rglob(pattern):
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in file_path.parts):
                continue
            matches.append(str(file_path.relative_to(workspace_root)).replace("\\", "/"))
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
        path = workspace_root / candidate
        if path.exists():
            files.append(candidate)
    package_json = workspace_root / "package.json"
    dependencies: dict[str, Any] = {}
    if package_json.exists():
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
        return ["cmd", "/c", "npm", "test"] if os.name == "nt" else ["npm", "test"]
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
        return _error(tool, "timeout", f"{tool} timed out after {timeout_seconds} seconds")
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


def _ok(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "selected_tool": tool,
        "result_payload": payload,
    }


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
