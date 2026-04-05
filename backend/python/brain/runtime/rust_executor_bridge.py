from __future__ import annotations

import json
import os
import subprocess
import tempfile
import ctypes
from pathlib import Path
from typing import Any


def _cargo_target_dir(project_root: Path) -> Path:
    temp_root = tempfile.gettempdir()
    if temp_root:
        base = Path(temp_root) / "omini-runtime" / "cargo-target"
    else:
        base = project_root / ".logs" / "fusion-runtime" / "cargo-target"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _compiled_bridge_path(project_root: Path) -> Path:
    candidates = [
        project_root / "backend" / "rust" / "target" / "x86_64-pc-windows-gnullvm" / "debug" / "executor_bridge.exe",
        project_root / "backend" / "rust" / "target" / "debug" / "executor_bridge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path()


def _windows_safe_path(raw_path: str) -> str:
    if os.name != "nt":
        return raw_path

    try:
        buffer = ctypes.create_unicode_buffer(32768)
        result = ctypes.windll.kernel32.GetShortPathNameW(str(raw_path), buffer, len(buffer))
        if result:
            return buffer.value
    except Exception:
        pass
    return raw_path


def execute_action(project_root: Path, action: dict[str, Any], timeout_seconds: int = 30) -> dict[str, Any]:
    rust_root = project_root / "backend" / "rust"
    safe_rust_root = _windows_safe_path(str(rust_root))
    safe_project_root = _windows_safe_path(str(project_root))
    bridge_bin = _compiled_bridge_path(project_root)
    action = dict(action)
    execution_context = dict(action.get("execution_context", {}) or {})
    if isinstance(execution_context.get("project_root"), str):
        execution_context["project_root"] = _windows_safe_path(execution_context["project_root"])
    action["execution_context"] = execution_context
    tool_arguments = dict(action.get("tool_arguments", {}) or {})
    if isinstance(tool_arguments.get("path"), str):
        raw_tool_path = Path(tool_arguments["path"])
        tool_arguments["path"] = str(raw_tool_path)
    action["tool_arguments"] = tool_arguments
    requested_mode = str(execution_context.get("runtime_mode", os.getenv("OMINI_EXECUTION_MODE", "auto"))).strip()

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        tmp.write(json.dumps(action, ensure_ascii=False))
        payload_path = Path(tmp.name)

    try:
        commands: list[tuple[str, list[str], str]] = []
        if bridge_bin and requested_mode != "python-rust-cargo":
            commands.append(
                (
                    "python-rust-packaged",
                    [_windows_safe_path(str(bridge_bin)), _windows_safe_path(str(payload_path))],
                    safe_project_root,
                )
            )

        last_error: dict[str, Any] | None = None
        cargo_target_dir = _cargo_target_dir(project_root)
        enable_cargo_fallback = True
        if enable_cargo_fallback:
            commands.append(
                (
                    "python-rust-cargo",
                    ["cargo", "run", "--quiet", "--bin", "executor_bridge", "--", _windows_safe_path(str(payload_path))],
                    safe_rust_root,
                )
            )

        for runtime_mode, command, command_cwd in commands:
            try:
                command_env = os.environ.copy()
                if runtime_mode == "python-rust-cargo":
                    command_env["CARGO_TARGET_DIR"] = _windows_safe_path(str(cargo_target_dir))
                    command_env["CARGO_INCREMENTAL"] = "0"
                completed = subprocess.run(
                    command,
                    cwd=command_cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=max(timeout_seconds, 120) if runtime_mode == "python-rust-cargo" else timeout_seconds,
                    check=False,
                    env=command_env,
                )
            except subprocess.TimeoutExpired:
                last_error = {
                    "ok": False,
                    "error_payload": {
                        "kind": "rust_bridge_timeout",
                        "message": f"Rust bridge timed out after {timeout_seconds} seconds",
                        "runtime_mode": runtime_mode,
                    },
                }
                continue

            stdout_text = (completed.stdout or "").strip()
            stderr_text = (completed.stderr or "").strip()

            if completed.returncode != 0:
                last_error = {
                    "ok": False,
                    "error_payload": {
                        "kind": "rust_bridge_failure",
                        "message": stderr_text or stdout_text or "Rust bridge failed",
                        "code": completed.returncode,
                        "runtime_mode": runtime_mode,
                    },
                }
                continue

            try:
                parsed = json.loads(stdout_text or "{}")
                parsed["runtime_mode"] = runtime_mode
                parsed["runtime_mode_requested"] = requested_mode or "auto"
                return parsed
            except json.JSONDecodeError as error:
                last_error = {
                    "ok": False,
                    "error_payload": {
                        "kind": "rust_bridge_parse_error",
                        "message": str(error),
                        "raw": completed.stdout or "",
                        "runtime_mode": runtime_mode,
                    },
                }

        return last_error or {
            "ok": False,
            "error_payload": {
                "kind": "rust_bridge_failure",
                "message": "Rust bridge failed before execution",
            },
        }
    finally:
        try:
            payload_path.unlink(missing_ok=True)
        except Exception:
            pass


def summarize_action_result(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        error_payload = result.get("error_payload", {}) or {}
        return f"Não consegui concluir a execução porque {error_payload.get('message', 'ocorreu uma falha na ferramenta')}."

    payload = result.get("result_payload", {}) or {}
    if isinstance(payload.get("file"), dict):
        return str(payload["file"].get("content", "")).strip()

    filenames = payload.get("filenames")
    if isinstance(filenames, list):
        return "\n".join(str(item) for item in filenames[:20]).strip()

    content = payload.get("content")
    if isinstance(content, str):
        return content.strip()

    return json.dumps(payload, ensure_ascii=False)
