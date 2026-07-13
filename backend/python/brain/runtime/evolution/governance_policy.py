from __future__ import annotations

from brain.env import read_env
from .models import EvolutionPolicy


class DeterministicGovernancePolicy:
    @staticmethod
    def from_env() -> EvolutionPolicy:
        return EvolutionPolicy(
            enabled=read_env("OMNI_EVOLUTION_ENABLED", "false").lower() == "true",
            allow_validation=read_env("OMNI_EVOLUTION_ALLOW_VALIDATION", "true").lower() != "false",
            allow_promotion=read_env("OMNI_EVOLUTION_ALLOW_PROMOTION", "false").lower() == "true",
            max_active_proposals=max(1, int(read_env("OMNI_EVOLUTION_MAX_ACTIVE_PROPOSALS", "5") or "5")),
            require_governance_for_medium_and_above=read_env("OMNI_EVOLUTION_REQUIRE_GOVERNANCE_FOR_MEDIUM_AND_ABOVE", "true").lower() != "false",
            block_critical=read_env("OMNI_EVOLUTION_BLOCK_CRITICAL", "true").lower() != "false",
        )
