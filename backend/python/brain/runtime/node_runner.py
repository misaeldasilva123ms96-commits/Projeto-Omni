from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from brain.env import read_env
from brain.runtime.learning.redaction import redact_sensitive_payload, redact_sensitive_text
from brain.runtime.node_path_policy import (
    RESERVED_NODE_ENV_KEYS,
    NodePathPolicy,
    NodePathPolicyError,
    ValidatedNodeExecutionPlan,
    validate_provider_overlay,
    validate_runtime_executable,
)
from config.provider_registry import PROVIDERS


def resolve_node_bin(js_runtime_adapter: Any) -> str | None:
    selection = js_runtime_adapter.select_runtime()
    if selection.runtime_name == "node" and selection.node_available:
        return selection.executable
    configured = read_env("OMNI_NODE_BIN")
    if configured:
        return configured
    return shutil.which("node")


def build_node_subprocess_env(
    js_runtime_adapter: Any,
    *,
    session_byok_active: bool = False,
    session_provider_preference: str = "",
    session_provider_env_overlay: dict[str, str] | None = None,
    pending_policy_hint_json: str | None = None,
) -> dict[str, str]:
    env, selection = js_runtime_adapter.build_env()
    trusted_root = getattr(js_runtime_adapter, "root", None) or env.get("OMNI_BASE_DIR") or env.get("BASE_DIR")
    for key in RESERVED_NODE_ENV_KEYS:
        env.pop(key, None)
    env.update(validate_provider_overlay(session_provider_env_overlay))
    if session_byok_active and session_provider_preference:
        if str(session_provider_preference).strip().lower() not in PROVIDERS:
            raise NodePathPolicyError("node_reserved_env_override")
        env["OMNI_BYOK_SESSION_MODE"] = "true"
        env["OMNI_BYOK_PROVIDER"] = str(session_provider_preference).strip().lower()
        env["OMNI_BYOK_FAIL_CLOSED"] = "true"
    root = str(Path(trusted_root).resolve()) if trusted_root else ""
    executable = str(getattr(selection, "executable", "") or resolve_node_bin(js_runtime_adapter) or "node")
    env["BASE_DIR"] = root
    env["OMNI_BASE_DIR"] = root
    env["NODE_RUNNER_BASE_DIR"] = root
    env["NODE_BIN"] = executable
    env["OMNI_JS_RUNTIME"] = selection.runtime_name
    env["OMNI_JS_RUNTIME_BIN"] = executable
    env["OMNI_JS_RUNTIME_SOURCE"] = str(getattr(selection, "source", "controlled"))
    env["OMNI_JS_RUNTIME_SELECTED"] = selection.runtime_name
    if session_byok_active and session_provider_preference:
        env["OMNI_POLICY_HINT_JSON"] = json.dumps(
            {"recommended_provider": session_provider_preference, "shadow_only": False},
            ensure_ascii=False,
        )
    elif isinstance(pending_policy_hint_json, str) and pending_policy_hint_json.strip():
        env["OMNI_POLICY_HINT_JSON"] = pending_policy_hint_json.strip()
    elif session_provider_preference:
        env["OMNI_POLICY_HINT_JSON"] = json.dumps(
            {"recommended_provider": session_provider_preference, "shadow_only": False},
            ensure_ascii=False,
        )
    return env


def resolve_node_command_context(
    paths: Any,
    js_runtime_adapter: Any,
    payload: str,
    *,
    session_byok_active: bool = False,
    session_provider_preference: str = "",
    session_provider_env_overlay: dict[str, str] | None = None,
    pending_policy_hint_json: str | None = None,
) -> ValidatedNodeExecutionPlan:
    policy = NodePathPolicy.from_runtime(
        project_root=paths.root,
        python_root=paths.python_root,
        runner_path=paths.js_runner,
    )
    env = build_node_subprocess_env(
        js_runtime_adapter,
        session_byok_active=session_byok_active,
        session_provider_preference=session_provider_preference,
        session_provider_env_overlay=session_provider_env_overlay,
        pending_policy_hint_json=pending_policy_hint_json,
    )
    selected = js_runtime_adapter.select_runtime()
    executable, runtime_name = validate_runtime_executable(
        str(selected.executable),
        controlled_path=env.get("PATH"),
    )
    if runtime_name != str(selected.runtime_name):
        raise NodePathPolicyError("node_runtime_invalid")
    env["NODE_BIN"] = str(executable)
    env["OMNI_JS_RUNTIME"] = runtime_name
    env["OMNI_JS_RUNTIME_BIN"] = str(executable)
    env["OMNI_JS_RUNTIME_SOURCE"] = str(selected.source)
    return ValidatedNodeExecutionPlan.create(
        policy=policy,
        executable=executable,
        runtime_name=runtime_name,
        environment=env,
    )


def runner_smoke_cwd_label(cwd: str) -> str:
    try:
        name = Path(cwd).name.strip().lower()
    except Exception:
        return "unknown"
    if name == "app":
        return "app"
    if name in {"project", "repo"}:
        return "repo"
    return "unknown"


def runner_smoke_scrub_provider_env(env: dict[str, str]) -> dict[str, str]:
    scrubbed = dict(env)
    for key in (
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "DEEPSEEK_API_KEY",
        "OLLAMA_API_KEY",
        "LMSTUDIO_API_KEY",
        "OLLAMA_URL",
        "LMSTUDIO_URL",
        "OMNI_BYOK_SESSION_MODE",
        "OMNI_BYOK_PROVIDER",
        "OMNI_BYOK_FAIL_CLOSED",
        "OMNI_POLICY_HINT_JSON",
    ):
        scrubbed.pop(key, None)
    return scrubbed


def runner_smoke_failure_class(transport: dict[str, Any], parsed: Any) -> str | None:
    reason = str(transport.get("reason_code", "") or "").strip()
    if reason and reason != "success":
        return reason
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            failure_class = str(error.get("failure_class", "") or "").strip()
            if failure_class:
                return failure_class
        response = str(parsed.get("response", "") or "")
        if response.startswith("[degraded:node_runner]"):
            return "node_runner_degraded"
    return None


def runner_smoke_summary(status: str, failure_class: str | None) -> str | None:
    if status == "ok":
        return "runner_smoke_ok"
    if failure_class:
        return f"runner_smoke_{failure_class}"
    return "runner_smoke_failed"


def truncate_text(value: str, limit: int = 1200) -> str:
    normalized = redact_sensitive_text(value).strip()
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
        "stdout": truncate_text(stdout),
        "stderr": truncate_text(stderr),
        "timed_out": timed_out,
        "exception": redact_sensitive_text(repr(exception)) if exception else "",
        "typescript_direct_execution_detected": diagnostics["typescript_direct_execution_detected"],
        "typescript_candidates_exist": diagnostics["typescript_candidates_exist"],
        "compiled_runner_artifact_exists": diagnostics["compiled_runner_artifact_exists"],
        "missing_paths": diagnostics["missing_paths"],
        "env_preview": diagnostics["env_preview"],
    }
    combined = f"{stdout}\n{stderr}".lower()
    details = redact_sensitive_payload(details)

    if not diagnostics["node_resolved"]:
        return "node_not_found", details
    if not diagnostics["runner_exists"]:
        return "runner_not_found", details
    if not diagnostics["cwd_exists"]:
        return "cwd_not_found", details
    if diagnostics["missing_paths"]:
        return "module_resolution_error", details
    if timed_out:
        return "timeout", details
    if exception is not None:
        return "subprocess_exception", details
    if not stdout.strip() and not stderr.strip() and returncode == 0:
        return "empty_stdout", details
    if "err_module_not_found" in combined or "cannot find module" in combined or "module not found" in combined:
        return "module_resolution_error", details
    if "unknown file extension \".ts\"" in combined or "cannot use import statement outside a module" in combined:
        details["typescript_direct_execution_detected"] = True
        return "module_resolution_error", details
    if returncode not in (None, 0):
        return "node_subprocess_failed", details
    return "invalid_json", details


def compact_history_for_node(history: object, limit: int = 6) -> list[dict[str, Any]]:
    if not isinstance(history, list):
        return []
    compacted: list[dict[str, Any]] = []
    for item in history[-limit:]:
        if not isinstance(item, dict):
            continue
        compacted.append(
            {
                "role": str(item.get("role", "")),
                "content": str(item.get("content", ""))[:600],
            }
        )
    return compacted


def compact_session_payload_for_node(
    session_payload: dict[str, Any],
    *,
    history_limit: int = 4,
    summary_limit: int = 1200,
) -> dict[str, Any]:
    compact = dict(session_payload)
    compact["history"] = compact_history_for_node(compact.get("history", []), limit=history_limit)
    if isinstance(compact.get("summary"), str):
        compact["summary"] = compact["summary"][:summary_limit]
    if isinstance(compact.get("agent_registry"), list):
        compact["agent_registry"] = compact["agent_registry"][:8]
    if isinstance(compact.get("agent_trace"), list):
        compact["agent_trace"] = compact["agent_trace"][-8:]
    return compact
