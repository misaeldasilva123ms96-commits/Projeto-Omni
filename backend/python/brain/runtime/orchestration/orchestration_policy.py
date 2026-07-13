from __future__ import annotations

from brain.env import read_env
from .models import OrchestrationPolicy


class DeterministicOrchestrationPolicy:
    @staticmethod
    def from_env() -> OrchestrationPolicy:
        return OrchestrationPolicy(
            allow_tool_delegation=read_env("OMNI_ORCHESTRATION_ALLOW_TOOL_DELEGATION", "true").lower() != "false",
            allow_analysis_routing=read_env("OMNI_ORCHESTRATION_ALLOW_ANALYSIS_ROUTING", "true").lower() != "false",
            allow_learning_hints=read_env("OMNI_ORCHESTRATION_ALLOW_LEARNING_HINTS", "true").lower() != "false",
            max_learning_weight=max(0.0, min(0.5, float(read_env("OMNI_ORCHESTRATION_MAX_LEARNING_WEIGHT", "0.25") or "0.25"))),
        )
