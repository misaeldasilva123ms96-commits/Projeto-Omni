from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ToolMetadata:
    name: str
    category: str
    description: str
    input_schema_hint: str
    risk_level: str
    estimated_cost: str
    latency_class: str
    deterministic: bool
    requires_network: bool
    requires_auth: bool
    safe_fallback_available: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def conservative_tool_metadata(name: str, *, category: str = "general", description: str = "") -> ToolMetadata:
    return ToolMetadata(
        name=name,
        category=category,
        description=description or f"metadata not explicitly registered for {name}",
        input_schema_hint="opaque_dict",
        risk_level="medium",
        estimated_cost="medium",
        latency_class="variable",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    )
