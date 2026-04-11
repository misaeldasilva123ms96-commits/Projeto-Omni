from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class JSRuntimeSelection:
    runtime_name: str
    executable: str
    source: str
    bun_available: bool
    node_available: bool
    preferred: bool
    fallback_used: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class JSRuntimeAdapter:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def select_runtime(self) -> JSRuntimeSelection:
        explicit_runtime = str(os.getenv("OMINI_JS_RUNTIME_BIN", "")).strip()
        if explicit_runtime:
            resolved = self._resolve_explicit_runtime(explicit_runtime)
            runtime_name = self._runtime_name_from_executable(explicit_runtime)
            return JSRuntimeSelection(
                runtime_name=runtime_name,
                executable=resolved or explicit_runtime,
                source="explicit_env",
                bun_available=bool(self._resolve_candidate(os.getenv("BUN_BIN", "").strip() or "bun")),
                node_available=bool(self._resolve_candidate(os.getenv("NODE_BIN", "").strip() or "node")),
                preferred=runtime_name == "bun",
                fallback_used=runtime_name != "bun",
            )

        bun_candidate = os.getenv("BUN_BIN", "").strip() or "bun"
        bun_resolved = self._resolve_candidate(bun_candidate)
        if bun_resolved:
            return JSRuntimeSelection(
                runtime_name="bun",
                executable=bun_resolved,
                source="bun_detected",
                bun_available=True,
                node_available=bool(self._resolve_candidate(os.getenv("NODE_BIN", "").strip() or "node")),
                preferred=True,
                fallback_used=False,
            )

        node_candidate = os.getenv("NODE_BIN", "").strip() or "node"
        node_resolved = self._resolve_candidate(node_candidate)
        if node_resolved:
            return JSRuntimeSelection(
                runtime_name="node",
                executable=node_resolved,
                source="node_fallback",
                bun_available=False,
                node_available=True,
                preferred=False,
                fallback_used=True,
            )

        configured_node = os.getenv("NODE_BIN", "").strip()
        return JSRuntimeSelection(
            runtime_name="node",
            executable=configured_node or "node",
            source="node_missing",
            bun_available=False,
            node_available=False,
            preferred=False,
            fallback_used=True,
        )

    def build_env(self) -> tuple[dict[str, str], JSRuntimeSelection]:
        env = os.environ.copy()
        selection = self.select_runtime()
        root = str(self.root)
        env["BASE_DIR"] = root
        env["NODE_RUNNER_BASE_DIR"] = root
        env["OMINI_JS_RUNTIME"] = selection.runtime_name
        env["OMINI_JS_RUNTIME_BIN"] = selection.executable
        env["OMINI_JS_RUNTIME_SOURCE"] = selection.source
        env.setdefault("NODE_BIN", self._resolve_candidate(os.getenv("NODE_BIN", "").strip() or "node") or "node")
        return env, selection

    def build_command(self, *, script_path: Path, payload: str | None = None) -> tuple[list[str], JSRuntimeSelection]:
        selection = self.select_runtime()
        command = [selection.executable, str(script_path.resolve())]
        if payload is not None:
            command.append(payload)
        return command, selection

    @staticmethod
    def _resolve_candidate(candidate: str) -> str | None:
        if not candidate:
            return None
        if os.path.isabs(candidate):
            return candidate if Path(candidate).exists() else None
        return shutil.which(candidate)

    def _resolve_explicit_runtime(self, candidate: str) -> str | None:
        resolved = self._resolve_candidate(candidate)
        if resolved:
            return resolved
        if Path(candidate).exists():
            return str(Path(candidate))
        return None

    @staticmethod
    def _runtime_name_from_executable(executable: str) -> str:
        lowered = Path(executable).name.lower()
        if "bun" in lowered:
            return "bun"
        return "node"
