from __future__ import annotations

import json
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class NodeTransportResult:
    ok: bool
    stage: str
    reason_code: str
    details: dict[str, Any]
    stdout: str
    stderr: str
    returncode: int | None
    parsed: dict[str, Any] | None

NODE_BRIDGE_EMPTY_STDOUT = "NODE_BRIDGE_EMPTY_STDOUT"
NODE_BRIDGE_INVALID_JSON = "NODE_BRIDGE_INVALID_JSON"
NODE_BRIDGE_NONZERO_EXIT = "NODE_BRIDGE_NONZERO_EXIT"
NODE_BRIDGE_TIMEOUT = "NODE_BRIDGE_TIMEOUT"
NODE_EMPTY_RESPONSE = "NODE_EMPTY_RESPONSE"
NODE_CIRCUIT_OPEN = "NODE_CIRCUIT_OPEN"


@dataclass(frozen=True)
class NodeCircuitDecision:
    allowed: bool
    state: str
    failure_count: int
    retry_after_seconds: float


class NodeCircuitBreaker:
    """Process-local failure guard for the Python -> Node transport boundary."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = "CLOSED"
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_probe_active = False

    def before_call(
        self,
        *,
        enabled: bool,
        reset_seconds: int,
        now: float | None = None,
    ) -> NodeCircuitDecision:
        current = time.monotonic() if now is None else float(now)
        reset = max(1, int(reset_seconds))
        with self._lock:
            if not enabled:
                return NodeCircuitDecision(True, "DISABLED", self._failure_count, 0.0)
            if self._state == "OPEN":
                elapsed = max(0.0, current - (self._opened_at or current))
                if elapsed < reset:
                    return NodeCircuitDecision(
                        False,
                        "OPEN",
                        self._failure_count,
                        max(0.0, reset - elapsed),
                    )
                self._state = "HALF_OPEN"
                self._half_open_probe_active = True
                return NodeCircuitDecision(True, "HALF_OPEN", self._failure_count, 0.0)
            if self._state == "HALF_OPEN":
                return NodeCircuitDecision(
                    not self._half_open_probe_active,
                    "HALF_OPEN",
                    self._failure_count,
                    float(reset),
                )
            return NodeCircuitDecision(True, "CLOSED", self._failure_count, 0.0)

    def record_success(self, *, enabled: bool) -> None:
        if not enabled:
            return
        with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
            self._opened_at = None
            self._half_open_probe_active = False

    def record_failure(
        self,
        *,
        enabled: bool,
        failure_threshold: int,
        now: float | None = None,
    ) -> None:
        if not enabled:
            return
        current = time.monotonic() if now is None else float(now)
        threshold = max(1, int(failure_threshold))
        with self._lock:
            self._failure_count += 1
            if self._state == "HALF_OPEN" or self._failure_count >= threshold:
                self._state = "OPEN"
                self._opened_at = current
            self._half_open_probe_active = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "half_open_probe_active": self._half_open_probe_active,
            }


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


def call_node_with_preflight(
    *,
    diagnostics: dict[str, Any],
    payload: str,
    timeout_seconds: int,
) -> NodeTransportResult:
    if not diagnostics.get("node_resolved") or not diagnostics.get("runner_exists") or not diagnostics.get("cwd_exists"):
        reason_code, details = classify_node_subprocess_failure(diagnostics=diagnostics)
        return NodeTransportResult(
            ok=False, stage="preflight", reason_code=reason_code, details=details,
            stdout="", stderr="", returncode=None, parsed=None,
        )
    if diagnostics.get("missing_paths"):
        reason_code, details = classify_node_subprocess_failure(diagnostics=diagnostics)
        return NodeTransportResult(
            ok=False, stage="preflight", reason_code=reason_code, details=details,
            stdout="", stderr="", returncode=None, parsed=None,
        )
    raw = run_node_subprocess(diagnostics=diagnostics, payload=payload, timeout_seconds=timeout_seconds)
    return NodeTransportResult(
        ok=raw["ok"], stage=raw["stage"], reason_code=raw["reason_code"],
        details=raw["details"], stdout=raw["stdout"], stderr=raw["stderr"],
        returncode=raw["returncode"], parsed=raw["parsed"],
    )
