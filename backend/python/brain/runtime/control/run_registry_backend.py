"""Persistence backend contract for :class:`RunRegistry` (Phase 30.16).

The registry keeps governance semantics; backends only move the canonical JSON
document between memory and storage. Default storage remains
``<root>/.logs/fusion-runtime/control/run_registry.json`` with atomic replace writes.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RunRegistryBackendMetadata:
    """Lightweight, non-JSON-contract metadata for diagnostics and tests."""

    backend_id: str
    """Stable identifier, e.g. ``filesystem`` or ``memory``."""

    storage_path: str | None
    """Primary storage location when applicable (e.g. absolute JSON path)."""


@runtime_checkable
class RunRegistryBackend(Protocol):
    """Load/save contract for the run registry root document ``{"runs": {...}}``."""

    def exists(self) -> bool:
        """Return whether persisted state should be loaded on registry open/reload."""

    def load(self) -> dict[str, Any]:
        """
        Return the parsed root object. Must be a ``dict`` with a ``runs`` mapping
        after validation by :class:`RunRegistry` (same rules as today).

        Implementations should raise :exc:`FileNotFoundError` when there is no
        readable snapshot so callers can wrap errors consistently.
        """

    def save(self, payload: dict[str, Any]) -> None:
        """Persist ``payload`` (already the full registry document)."""

    def metadata(self) -> RunRegistryBackendMetadata:
        """Describe this backend for logging or tests."""


class FileSystemRunRegistryBackend:
    """Filesystem-backed registry document (historical default)."""

    __slots__ = ("_control_dir", "_path")

    def __init__(self, root: Path) -> None:
        self._control_dir = root / ".logs" / "fusion-runtime" / "control"
        self._control_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._control_dir / "run_registry.json"

    @property
    def control_dir(self) -> Path:
        return self._control_dir

    @property
    def registry_path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> dict[str, Any]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as error:
            raise ValueError(f"Invalid run registry data: {error}") from error

    def save(self, payload: dict[str, Any]) -> None:
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self._path)

    def metadata(self) -> RunRegistryBackendMetadata:
        return RunRegistryBackendMetadata(
            backend_id="filesystem",
            storage_path=str(self._path.resolve()),
        )


class InMemoryRunRegistryBackend:
    """In-memory backend for tests (no I/O)."""

    __slots__ = ("_payload", "_written")

    def __init__(self) -> None:
        self._payload: dict[str, Any] = {"runs": {}}
        self._written = False

    def exists(self) -> bool:
        return self._written

    def load(self) -> dict[str, Any]:
        if not self._written:
            raise FileNotFoundError("in-memory run registry has not been persisted yet")
        return copy.deepcopy(self._payload)

    def save(self, payload: dict[str, Any]) -> None:
        self._payload = copy.deepcopy(payload)
        self._written = True

    def metadata(self) -> RunRegistryBackendMetadata:
        return RunRegistryBackendMetadata(backend_id="memory", storage_path=None)
