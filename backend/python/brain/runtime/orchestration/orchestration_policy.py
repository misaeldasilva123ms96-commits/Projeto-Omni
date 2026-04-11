from __future__ import annotations

import os

from .models import OrchestrationPolicy


class DeterministicOrchestrationPolicy:
    @staticmethod
    def from_env() -> OrchestrationPolicy:
        return OrchestrationPolicy(
            allow_tool_delegation=str(os.getenv("OMINI_ORCHESTRATION_ALLOW_TOOL_DELEGATION", "true")).lower() != "false",
            allow_analysis_routing=str(os.getenv("OMINI_ORCHESTRATION_ALLOW_ANALYSIS_ROUTING", "true")).lower() != "false",
            allow_learning_hints=str(os.getenv("OMINI_ORCHESTRATION_ALLOW_LEARNING_HINTS", "true")).lower() != "false",
            max_learning_weight=max(0.0, min(0.5, float(os.getenv("OMINI_ORCHESTRATION_MAX_LEARNING_WEIGHT", "0.25") or "0.25"))),
        )
