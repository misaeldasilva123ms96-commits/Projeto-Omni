from __future__ import annotations

import os

from .models import EvolutionPolicy


class DeterministicGovernancePolicy:
    @staticmethod
    def from_env() -> EvolutionPolicy:
        return EvolutionPolicy(
            enabled=str(os.getenv("OMINI_EVOLUTION_ENABLED", "false")).lower() == "true",
            allow_validation=str(os.getenv("OMINI_EVOLUTION_ALLOW_VALIDATION", "true")).lower() != "false",
            allow_promotion=str(os.getenv("OMINI_EVOLUTION_ALLOW_PROMOTION", "false")).lower() == "true",
            max_active_proposals=max(1, int(os.getenv("OMINI_EVOLUTION_MAX_ACTIVE_PROPOSALS", "5") or "5")),
            require_governance_for_medium_and_above=str(os.getenv("OMINI_EVOLUTION_REQUIRE_GOVERNANCE_FOR_MEDIUM_AND_ABOVE", "true")).lower() != "false",
            block_critical=str(os.getenv("OMINI_EVOLUTION_BLOCK_CRITICAL", "true")).lower() != "false",
        )
