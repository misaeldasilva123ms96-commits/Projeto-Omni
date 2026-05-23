from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ManifestStep:
    step_id: str
    kind: str
    description: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionManifest:
    manifest_id: str
    intent: str
    chosen_strategy: str
    selected_tools: list[str]
    step_plan: list[ManifestStep]
    fallback_strategy: str
    observability_tags: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    output_mode: str = "direct"
    summary_rationale: str = ""
    provider_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["step_plan"] = [item.as_dict() for item in self.step_plan]
        return payload


@dataclass(slots=True)
class ManifestBuildResult:
    manifest: ExecutionManifest | None
    degraded: bool
    fallback_triggered: bool
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.as_dict() if self.manifest is not None else None,
            "degraded": self.degraded,
            "fallback_triggered": self.fallback_triggered,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
