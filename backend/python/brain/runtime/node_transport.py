from __future__ import annotations

import json
import subprocess
from typing import Any

NODE_BRIDGE_EMPTY_STDOUT = "NODE_BRIDGE_EMPTY_STDOUT"
NODE_BRIDGE_INVALID_JSON = "NODE_BRIDGE_INVALID_JSON"
NODE_BRIDGE_NONZERO_EXIT = "NODE_BRIDGE_NONZERO_EXIT"
NODE_BRIDGE_TIMEOUT = "NODE_BRIDGE_TIMEOUT"
NODE_EMPTY_RESPONSE = "NODE_EMPTY_RESPONSE"


def truncate_node_text(value: str, limit: int = 1200) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit]


def classify_node_subprocess_failure(
    *,
    diagnostics: dict[str, Any],
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    exception: Exception | None = None,
    timed_out: bool = False,
) -> tuple[str, dict[str, Any]]:
    details = {
        "runner_path": diagnostics["runner_path"],
        "adapter_path": diagnostics["adapter_path"],
        "fusion_brain_path": diagnostics["fusion_brain_path"],
        "cwd": diagnostics["cwd"],
        "command_preview": diagnostics["command_preview"],
        "node_bin": diagnostics["node_bin"],
        "node_resolved": diagnostics["node_resolved"],
        "returncode": returncode,
        "stdout": truncate_node_text(stdout),
        "stderr": truncate_node_text(stderr),
        "timed_out": timed_out,
        "exception": repr(exception) if exception else "",
        "typescript_direct_execution_detected": diagnostics["typescript_direct_execution_detected"],
        "typescript_candidates_exist": diagnostics["typescript_candidates_exist"],
        "compiled_runner_artifact_exists": diagnostics["compiled_runner_artifact_exists"],
        "missing_paths": diagnostics["missing_paths"],
        "env_preview": diagnostics["env_preview"],
    }
    combined = f"{stdout}\n{stderr}".lower()

    if not diagnostics["node_resolved"]:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if not diagnostics["runner_exists"]:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if not diagnostics["cwd_exists"]:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if diagnostics["missing_paths"]:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if timed_out:
        return NODE_BRIDGE_TIMEOUT, details
    if exception is not None:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if not stdout.strip() and not stderr.strip() and returncode == 0:
        return NODE_BRIDGE_EMPTY_STDOUT, details
    if "err_module_not_found" in combined or "cannot find module" in combined or "module not found" in combined:
        return NODE_BRIDGE_NONZERO_EXIT, details
    if "unknown file extension \".ts\"" in combined or "cannot use import statement outside a module" in combined:
        details["typescript_direct_execution_detected"] = True
        return NODE_BRIDGE_NONZERO_EXIT, details
    if returncode not in (None, 0):
        return NODE_BRIDGE_NONZERO_EXIT, details
    return NODE_BRIDGE_INVALID_JSON, details


def run_node_subprocess(
    *,
    diagnostics: dict[str, Any],
    payload: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            diagnostics["command"],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            cwd=diagnostics["cwd"],
            env=diagnostics["subprocess_env"],
        )
    except subprocess.TimeoutExpired as error:
        reason_code, details = classify_node_subprocess_failure(
            diagnostics=diagnostics,
            stdout=error.stdout or "",
            stderr=error.stderr or "",
            exception=error,
            timed_out=True,
        )
        return {
            "ok": False,
            "stage": "timeout",
            "reason_code": reason_code,
            "details": details,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "returncode": None,
            "parsed": None,
        }
    except Exception as error:
        reason_code, details = classify_node_subprocess_failure(
            diagnostics=diagnostics,
            exception=error,
        )
        return {
            "ok": False,
            "stage": "exception",
            "reason_code": reason_code,
            "details": details,
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "parsed": None,
        }

    stdout = (completed.stdout or "").strip()
    stderr = completed.stderr or ""
    if completed.returncode != 0 or not stdout:
        reason_code, details = classify_node_subprocess_failure(
            diagnostics=diagnostics,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=stderr,
        )
        return {
            "ok": False,
            "stage": "completed",
            "reason_code": reason_code,
            "details": details,
            "stdout": completed.stdout or "",
            "stderr": stderr,
            "returncode": completed.returncode,
            "parsed": None,
        }

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as error:
        reason_code, details = classify_node_subprocess_failure(
            diagnostics=diagnostics,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=stderr,
        )
        return {
            "ok": False,
            "stage": "completed",
            "reason_code": reason_code,
            "details": details,
            "stdout": completed.stdout or "",
            "stderr": stderr,
            "returncode": completed.returncode,
            "parsed": None,
        }

    return {
        "ok": True,
        "stage": "completed",
        "reason_code": "success",
        "details": {
            "returncode": completed.returncode,
            "stdout": truncate_node_text(completed.stdout or ""),
            "stderr": truncate_node_text(stderr),
            "command_preview": diagnostics["command_preview"],
            "cwd": diagnostics["cwd"],
            "node_bin": diagnostics["node_bin"],
            "node_resolved": diagnostics["node_resolved"],
            "env_preview": diagnostics["env_preview"],
        },
        "stdout": completed.stdout or "",
        "stderr": stderr,
        "returncode": completed.returncode,
        "parsed": parsed,
    }
