from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PolicyHint:
    recommended_provider: str | None
    recommended_strategy: str | None
    recommended_tool_profile: str | None
    confidence: float
    policy_reason_codes: list[str]
    baseline_provider: str | None
    shadow_only: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "recommended_provider": self.recommended_provider,
            "recommended_strategy": self.recommended_strategy,
            "recommended_tool_profile": self.recommended_tool_profile,
            "confidence": self.confidence,
            "policy_reason_codes": list(self.policy_reason_codes),
            "baseline_provider": self.baseline_provider,
            "shadow_only": self.shadow_only,
        }
