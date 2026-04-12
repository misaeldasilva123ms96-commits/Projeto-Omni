from __future__ import annotations

from .base_specialist import BaseSpecialist
from .models import SpecialistDecision, SynthesisDecision


class SynthesisSpecialist(BaseSpecialist):
    def synthesize(
        self,
        *,
        goal_id: str | None,
        simulation_id: str | None,
        decisions: list[SpecialistDecision],
        final_outcome: str,
    ) -> SynthesisDecision:
        artifact_refs: list[str] = []
        learning_highlights: list[str] = []
        specialist_path = " -> ".join(decision.specialist_type.value for decision in decisions)
        for decision in decisions:
            artifact_refs.append(decision.decision_id)
            if decision.metadata.get("simulation_id"):
                learning_highlights.append(f"simulation:{decision.metadata['simulation_id']}")
        summary = f"Specialist flow {specialist_path or 'none'} ended with outcome '{final_outcome}'."
        return SynthesisDecision.build(
            goal_id=goal_id,
            simulation_id=simulation_id,
            reasoning="Synthesis specialist consolidated the bounded specialist path into a single auditable outcome.",
            confidence=0.86,
            summary=summary,
            artifact_refs=artifact_refs,
            learning_highlights=learning_highlights,
            metadata={"final_outcome": final_outcome},
        )
