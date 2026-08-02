from __future__ import annotations

import hashlib
import os
import secrets
import stat
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


REQUIRED_MARKERS = (
    "package.json",
    "backend/python",
    "backend/rust",
    "js-runner/queryEngineRunner.js",
    "contract/runner-schema.v1.json",
)

SECURITY_FILE_ALLOWLIST = (
    "js-runner/queryEngineRunner.js",
    "js-runner/pathPolicy.js",
    "contract/runner-schema.v1.json",
    "src/queryEngineRunnerAdapter.js",
    "src/queryEngineRunnerAdapter.mjs",
    "core/brain/fusionBrain.js",
    "js-runner/runtimeHealthcheck.js",
    "dist/QueryEngine.js",
    "build/QueryEngine.js",
    "src/QueryEngine.js",
    "runtime/node/QueryEngine.js",
    "src/QueryEngine.ts",
    "runtime/node/QueryEngine.ts",
)

REQUIRED_SECURITY_FILES = (
    "js-runner/queryEngineRunner.js",
    "js-runner/pathPolicy.js",
    "contract/runner-schema.v1.json",
    "src/queryEngineRunnerAdapter.js",
    "core/brain/fusionBrain.js",
    "js-runner/runtimeHealthcheck.js",
)

ENGINE_FILE_ALLOWLIST = (
    "dist/QueryEngine.js",
    "build/QueryEngine.js",
    "src/QueryEngine.js",
    "runtime/node/QueryEngine.js",
    "src/QueryEngine.ts",
    "runtime/node/QueryEngine.ts",
)

RESERVED_NODE_ENV_KEYS = frozenset(
    {
        "BASE_DIR",
        "OMNI_BASE_DIR",
        "NODE_RUNNER_BASE_DIR",
        "NODE_BIN",
        "OMNI_NODE_BIN",
        "OMNI_JS_RUNTIME",
        "OMNI_JS_RUNTIME_BIN",
        "OMNI_JS_RUNTIME_SOURCE",
        "OMNI_JS_RUNTIME_SELECTED",
        "RUNNER_SCHEMA_PATH",
        "RUNNER_ADAPTER_PATH",
        "NODE_OPTIONS",
        "NODE_PATH",
        "BUN_BIN",
    }
)

PROVIDER_OVERLAY_KEYS = frozenset(
    {
        "GROQ_API_KEY", "GROQ_MODEL",
        "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
        "OPENAI_API_KEY", "OPENAI_MODEL",
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
        "GEMINI_API_KEY", "GEMINI_MODEL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL",
        "OLLAMA_URL", "OLLAMA_MODEL", "OLLAMA_API_KEY",
        "LMSTUDIO_URL", "LMSTUDIO_MODEL", "LMSTUDIO_API_KEY",
    }
)

_PLAN_KEY = secrets.token_bytes(32)
_WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class NodePathPolicyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = int(getattr(info, "st_file_attributes", 0) or 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & _WINDOWS_REPARSE_ATTRIBUTE)


def _assert_no_link_components(path: Path, *, include_leaf: bool = True) -> None:
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    if not parts:
        raise NodePathPolicyError("node_path_policy_violation")
    current = Path(parts[0])
    end = len(parts) if include_leaf else max(1, len(parts) - 1)
    for part in parts[1:end]:
        current /= part
        if _is_reparse_or_symlink(current):
            raise NodePathPolicyError("node_path_policy_violation")
    if include_leaf and _is_reparse_or_symlink(absolute):
        raise NodePathPolicyError("node_path_policy_violation")


def _canonical_existing_directory(path: Path, code: str) -> Path:
    try:
        raw = Path(os.path.abspath(path))
        _assert_no_link_components(raw)
        resolved = raw.resolve(strict=True)
    except (OSError, RuntimeError, ValueError, NodePathPolicyError) as error:
        raise NodePathPolicyError(code) from error
    if not resolved.is_dir():
        raise NodePathPolicyError(code)
    return resolved


def _relative(candidate: Path, root: Path, code: str) -> Path:
    try:
        return candidate.relative_to(root)
    except ValueError as error:
        raise NodePathPolicyError(code) from error


@dataclass(frozen=True, slots=True)
class NodePathPolicy:
    project_root: Path
    python_root: Path
    runner_path: Path
    schema_path: Path
    adapter_paths: tuple[Path, ...]
    engine_paths: tuple[Path, ...]

    @classmethod
    def from_runtime(
        cls,
        *,
        project_root: Path,
        python_root: Path,
        runner_path: Path,
        active_python_entrypoint: Path | None = None,
    ) -> "NodePathPolicy":
        root = _canonical_existing_directory(project_root, "node_project_root_invalid")
        python = _canonical_existing_directory(python_root, "node_project_root_invalid")
        active = Path(active_python_entrypoint or __file__)
        try:
            active = active.resolve(strict=True)
            active.relative_to(root / "backend" / "python")
            python.relative_to(root / "backend" / "python")
        except (OSError, RuntimeError, ValueError) as error:
            raise NodePathPolicyError("node_project_root_invalid") from error

        policy = cls(
            project_root=root,
            python_root=python,
            runner_path=root / "js-runner" / "queryEngineRunner.js",
            schema_path=root / "contract" / "runner-schema.v1.json",
            adapter_paths=(
                root / "src" / "queryEngineRunnerAdapter.js",
                root / "src" / "queryEngineRunnerAdapter.mjs",
            ),
            engine_paths=tuple(root / relative for relative in ENGINE_FILE_ALLOWLIST),
        )
        for marker in REQUIRED_MARKERS:
            marker_path = root / marker
            expected = "directory" if marker in {"backend/python", "backend/rust"} else "file"
            policy._validate_expected(marker_path, expected, required=True, code="node_project_root_invalid")
        supplied_runner = Path(os.path.abspath(runner_path))
        if supplied_runner != policy.runner_path:
            raise NodePathPolicyError("node_runner_outside_root")
        for relative in REQUIRED_SECURITY_FILES:
            policy.validate_file(root / relative, _label_for(relative), required=True)
        for relative in SECURITY_FILE_ALLOWLIST:
            if relative not in REQUIRED_SECURITY_FILES:
                policy.validate_file(root / relative, _label_for(relative), required=False)
        return policy

    def _validate_expected(
        self,
        candidate: Path,
        expected: str,
        *,
        required: bool,
        code: str,
    ) -> Path | None:
        raw = Path(os.path.abspath(candidate))
        _relative(raw, self.project_root, code)
        try:
            _assert_no_link_components(raw, include_leaf=False)
        except NodePathPolicyError as error:
            raise NodePathPolicyError(code) from error
        exists = os.path.lexists(raw)
        if not exists:
            if required:
                raise NodePathPolicyError(code)
            return None
        try:
            _assert_no_link_components(raw)
            resolved = raw.resolve(strict=True)
            _relative(resolved, self.project_root, code)
            info = raw.stat()
        except (OSError, RuntimeError, ValueError, NodePathPolicyError) as error:
            raise NodePathPolicyError(code) from error
        valid_type = stat.S_ISREG(info.st_mode) if expected == "file" else stat.S_ISDIR(info.st_mode)
        if not valid_type:
            raise NodePathPolicyError(code)
        return resolved

    def validate_file(self, candidate: Path, label: str, *, required: bool = True) -> Path | None:
        raw = Path(os.path.abspath(candidate))
        relative = _relative(raw, self.project_root, f"node_{label}_outside_root")
        normalized = relative.as_posix()
        if normalized not in SECURITY_FILE_ALLOWLIST:
            raise NodePathPolicyError(f"node_{label}_outside_root")
        return self._validate_expected(
            raw,
            "file",
            required=required,
            code=(f"node_{label}_unsafe" if label == "engine_candidate" else f"node_{label}_symlink_rejected"),
        )

    def revalidate_runner(self) -> Path:
        return self.validate_file(self.runner_path, "runner", required=True)  # type: ignore[return-value]


def _label_for(relative: str) -> str:
    if relative == "js-runner/pathPolicy.js":
        return "path_policy"
    if relative.startswith("js-runner/queryEngineRunner"):
        return "runner"
    if relative.startswith("contract/"):
        return "schema"
    if "Adapter" in relative:
        return "adapter"
    if relative.endswith("fusionBrain.js"):
        return "adapter"
    if relative.endswith("runtimeHealthcheck.js"):
        return "runner"
    return "engine_candidate"


def validate_runtime_executable(candidate: str, *, controlled_path: str | None = None) -> tuple[Path, str]:
    import shutil

    value = str(candidate or "").strip()
    if not value or "\x00" in value:
        raise NodePathPolicyError("node_runtime_invalid")
    path_value = Path(value)
    if path_value.is_absolute():
        selected = path_value
    else:
        if "/" in value or "\\" in value or value in {".", ".."} or any(ch.isspace() for ch in value):
            raise NodePathPolicyError("node_runtime_invalid")
        if value.lower() not in {"node", "node.exe", "bun", "bun.exe"}:
            raise NodePathPolicyError("node_runtime_invalid")
        found = shutil.which(value, path=controlled_path)
        if not found:
            raise NodePathPolicyError("node_runtime_invalid")
        selected = Path(found)
    try:
        resolved = selected.resolve(strict=True)
        info = resolved.stat()
    except (OSError, RuntimeError, ValueError) as error:
        raise NodePathPolicyError("node_runtime_invalid") from error
    if not stat.S_ISREG(info.st_mode):
        raise NodePathPolicyError("node_runtime_invalid")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise NodePathPolicyError("node_runtime_invalid")
    identity = resolved.name.lower()
    if identity not in {"node", "node.exe", "bun", "bun.exe"}:
        raise NodePathPolicyError("node_runtime_invalid")
    return resolved, "bun" if identity.startswith("bun") else "node"


def validate_provider_overlay(overlay: Mapping[str, str] | None) -> dict[str, str]:
    accepted: dict[str, str] = {}
    for raw_key, raw_value in (overlay or {}).items():
        key = str(raw_key).strip().upper()
        if key in RESERVED_NODE_ENV_KEYS or key not in PROVIDER_OVERLAY_KEYS:
            raise NodePathPolicyError("node_reserved_env_override")
        value = str(raw_value)
        if value:
            accepted[key] = value
    return accepted


def _plan_digest(executable: Path, runner: Path, cwd: Path, env: tuple[tuple[str, str], ...]) -> str:
    material = "\0".join((str(executable), str(runner), str(cwd), *(f"{k}={v}" for k, v in env)))
    return hashlib.blake2b(material.encode("utf-8"), key=_PLAN_KEY, digest_size=32).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidatedNodeExecutionPlan(Mapping[str, Any]):
    policy: NodePathPolicy
    executable: Path
    runtime_name: str
    runner_path: Path
    cwd: Path
    environment: tuple[tuple[str, str], ...]
    token: str

    @classmethod
    def create(
        cls,
        *,
        policy: NodePathPolicy,
        executable: Path,
        runtime_name: str,
        environment: Mapping[str, str],
    ) -> "ValidatedNodeExecutionPlan":
        runner = policy.revalidate_runner()
        env = tuple(sorted((str(key), str(value)) for key, value in environment.items()))
        token = _plan_digest(executable, runner, policy.project_root, env)
        return cls(policy, executable, runtime_name, runner, policy.project_root, env, token)

    @property
    def command(self) -> tuple[str, str]:
        return (str(self.executable), str(self.runner_path))

    @property
    def env(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.environment))

    def verify(self) -> None:
        if self.token != _plan_digest(self.executable, self.runner_path, self.cwd, self.environment):
            raise NodePathPolicyError("node_execution_plan_invalid")
        if self.cwd != self.policy.project_root or self.runner_path != self.policy.runner_path:
            raise NodePathPolicyError("node_execution_plan_invalid")
        fresh_policy = NodePathPolicy.from_runtime(
            project_root=self.cwd,
            python_root=self.policy.python_root,
            runner_path=self.runner_path,
        )
        if fresh_policy.project_root != self.policy.project_root:
            raise NodePathPolicyError("node_cwd_invalid")
        executable, runtime = validate_runtime_executable(str(self.executable))
        if executable != self.executable or runtime != self.runtime_name:
            raise NodePathPolicyError("node_execution_plan_invalid")
        if fresh_policy.revalidate_runner() != self.runner_path:
            raise NodePathPolicyError("node_execution_plan_invalid")
        env = dict(self.environment)
        expected_root = str(self.policy.project_root)
        for key in ("BASE_DIR", "OMNI_BASE_DIR", "NODE_RUNNER_BASE_DIR"):
            if env.get(key) != expected_root:
                raise NodePathPolicyError("node_execution_plan_invalid")
        if "NODE_OPTIONS" in env or "NODE_PATH" in env:
            raise NodePathPolicyError("node_startup_options_rejected")
        for key in ("RUNNER_SCHEMA_PATH", "RUNNER_ADAPTER_PATH", "OMNI_NODE_BIN", "BUN_BIN"):
            if key in env:
                raise NodePathPolicyError("node_execution_plan_invalid")
        if env.get("NODE_BIN") != str(self.executable) or env.get("OMNI_JS_RUNTIME_BIN") != str(self.executable):
            raise NodePathPolicyError("node_execution_plan_invalid")
        if env.get("OMNI_JS_RUNTIME") != self.runtime_name or env.get("OMNI_JS_RUNTIME_SELECTED") != self.runtime_name:
            raise NodePathPolicyError("node_execution_plan_invalid")

    def _diagnostics(self) -> dict[str, Any]:
        existing_engines = [path.name for path in self.policy.engine_paths if path.exists()]
        return {
            "node_bin": self.runtime_name,
            "node_resolved": self.runtime_name,
            "js_runtime": {"runtime_name": self.runtime_name},
            "cwd": "repo",
            "cwd_exists": self.cwd.is_dir(),
            "runner_path": "js-runner/queryEngineRunner.js",
            "runner_exists": self.runner_path.is_file(),
            "adapter_path": "src/queryEngineRunnerAdapter.js",
            "adapter_exists": True,
            "esm_adapter_path": "src/queryEngineRunnerAdapter.mjs",
            "esm_adapter_exists": self.policy.adapter_paths[1].is_file(),
            "fusion_brain_path": "core/brain/fusionBrain.js",
            "fusion_brain_exists": True,
            "healthcheck_path": "js-runner/runtimeHealthcheck.js",
            "healthcheck_exists": True,
            "command": [self.runtime_name, "js-runner/queryEngineRunner.js"],
            "command_preview": [self.runtime_name, "js-runner/queryEngineRunner.js"],
            "typescript_direct_execution_detected": False,
            "typescript_candidates_exist": [name for name in existing_engines if name.endswith(".ts")],
            "compiled_runner_artifact_exists": any(not name.endswith(".ts") for name in existing_engines) or bool(self.policy.adapter_paths),
            "missing_paths": [],
            "env_preview": {
                "BASE_DIR": "repo",
                "NODE_RUNNER_BASE_DIR": "repo",
                "NODE_BIN": self.runtime_name,
                "OMNI_JS_RUNTIME": self.runtime_name,
            },
            "subprocess_env": self.env,
        }

    def __getitem__(self, key: str) -> Any:
        return self._diagnostics()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._diagnostics())

    def __len__(self) -> int:
        return len(self._diagnostics())


def safe_policy_failure(code: str) -> dict[str, Any]:
    return {
        "ok": False,
        "stage": "preflight",
        "reason_code": "NODE_BRIDGE_NONZERO_EXIT",
        "details": {"failure_class": str(code or "node_path_policy_violation")[:96]},
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "parsed": None,
    }
