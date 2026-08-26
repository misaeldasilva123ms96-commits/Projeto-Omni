"""Canonical Node subprocess failure classification shared by runner and transport.

The classification decision tree is identical for both call sites; only the
returned reason-code vocabulary and detail redaction differ. This module owns
the canonical taxonomy so the two vocabularies cannot drift apart.
"""
from __future__ import annotations

from typing import Any

NODE_FAILURE_NODE_NOT_FOUND = "node_not_found"
NODE_FAILURE_RUNNER_NOT_FOUND = "runner_not_found"
NODE_FAILURE_CWD_NOT_FOUND = "cwd_not_found"
NODE_FAILURE_MODULE_RESOLUTION_ERROR = "module_resolution_error"
NODE_FAILURE_TIMEOUT = "timeout"
NODE_FAILURE_SUBPROCESS_EXCEPTION = "subprocess_exception"
NODE_FAILURE_EMPTY_STDOUT = "empty_stdout"
NODE_FAILURE_NODE_SUBPROCESS_FAILED = "node_subprocess_failed"
NODE_FAILURE_INVALID_JSON = "invalid_json"

NODE_TRANSPORT_NONZERO_EXIT_CLASSES = frozenset(
    {
        NODE_FAILURE_NODE_NOT_FOUND,
        NODE_FAILURE_RUNNER_NOT_FOUND,
        NODE_FAILURE_CWD_NOT_FOUND,
        NODE_FAILURE_MODULE_RESOLUTION_ERROR,
        NODE_FAILURE_SUBPROCESS_EXCEPTION,
        NODE_FAILURE_NODE_SUBPROCESS_FAILED,
    }
)

TRANSPORT_REASON_BY_CLASSIFICATION: dict[str, str] = {
    NODE_FAILURE_TIMEOUT: "NODE_BRIDGE_TIMEOUT",
    NODE_FAILURE_EMPTY_STDOUT: "NODE_BRIDGE_EMPTY_STDOUT",
    NODE_FAILURE_INVALID_JSON: "NODE_BRIDGE_INVALID_JSON",
    **{classification: "NODE_BRIDGE_NONZERO_EXIT" for classification in sorted(NODE_TRANSPORT_NONZERO_EXIT_CLASSES)},
}


def classify_node_failure_outcome(
    *,
    diagnostics: dict[str, Any],
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    exception: Exception | None = None,
    timed_out: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Return the canonical failure classification with unredacted details.

    Callers own redaction policy. The returned details payload is truncated
    but intentionally not redacted; apply the caller-specific redaction pass
    before exposing details beyond the process boundary.
    """
    details = {
        "runner_path": diagnostics["runner_path"],
        "adapter_path": diagnostics["adapter_path"],
        "fusion_brain_path": diagnostics["fusion_brain_path"],
        "cwd": diagnostics["cwd"],
        "command_preview": diagnostics["command_preview"],
        "node_bin": diagnostics["node_bin"],
        "node_resolved": diagnostics["node_resolved"],
        "returncode": returncode,
        "stdout": _truncate(stdout),
        "stderr": _truncate(stderr),
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
        return NODE_FAILURE_NODE_NOT_FOUND, details
    if not diagnostics["runner_exists"]:
        return NODE_FAILURE_RUNNER_NOT_FOUND, details
    if not diagnostics["cwd_exists"]:
        return NODE_FAILURE_CWD_NOT_FOUND, details
    if diagnostics["missing_paths"]:
        return NODE_FAILURE_MODULE_RESOLUTION_ERROR, details
    if timed_out:
        return NODE_FAILURE_TIMEOUT, details
    if exception is not None:
        return NODE_FAILURE_SUBPROCESS_EXCEPTION, details
    if not stdout.strip() and not stderr.strip() and returncode == 0:
        return NODE_FAILURE_EMPTY_STDOUT, details
    if "err_module_not_found" in combined or "cannot find module" in combined or "module not found" in combined:
        return NODE_FAILURE_MODULE_RESOLUTION_ERROR, details
    if 'unknown file extension ".ts"' in combined or "cannot use import statement outside a module" in combined:
        details["typescript_direct_execution_detected"] = True
        return NODE_FAILURE_MODULE_RESOLUTION_ERROR, details
    if returncode not in (None, 0):
        return NODE_FAILURE_NODE_SUBPROCESS_FAILED, details
    return NODE_FAILURE_INVALID_JSON, details


def _truncate(value: str, limit: int = 1200) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit]
