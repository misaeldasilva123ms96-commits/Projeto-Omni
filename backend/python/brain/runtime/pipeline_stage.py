from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PipelineStage(Protocol):
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ...


class PipelineResult:
    def __init__(self, success: bool, data: dict[str, Any] | None = None, error: str | None = None):
        self.success = success
        self.data = data or {}
        self.error = error

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }
