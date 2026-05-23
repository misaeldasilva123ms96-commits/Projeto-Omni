from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class CapabilityRoutingRecord:
    intent: str
    strategy: str
    confidence: float
    requires_tools: bool
    requires_node_runtime: bool
    fallback_allowed: bool
    internal_reasoning_hint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
