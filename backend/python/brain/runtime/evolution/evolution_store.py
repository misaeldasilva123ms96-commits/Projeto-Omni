from __future__ import annotations

import json
from pathlib import Path

from .models import EvolutionOpportunity, EvolutionProposal, GovernanceDecision, ValidationPlan


class EvolutionStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "evolution"
        self.opportunities_dir = self.base_dir / "opportunities"
        self.proposals_dir = self.base_dir / "proposals"
        self.validations_dir = self.base_dir / "validations"
        self.governance_dir = self.base_dir / "governance"
        self.promotions_dir = self.base_dir / "promotions"
        for directory in (
            self.opportunities_dir,
            self.proposals_dir,
            self.validations_dir,
            self.governance_dir,
            self.promotions_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def append_opportunity(self, opportunity: EvolutionOpportunity) -> None:
        self._append_jsonl(self.opportunities_dir / "opportunities.jsonl", opportunity.as_dict())

    def append_proposal(self, proposal: EvolutionProposal) -> None:
        self._append_jsonl(self.proposals_dir / "proposals.jsonl", proposal.as_dict())

    def append_validation(self, validation: ValidationPlan) -> None:
        self._append_jsonl(self.validations_dir / "validations.jsonl", validation.as_dict())

    def append_governance(self, decision: GovernanceDecision) -> None:
        self._append_jsonl(self.governance_dir / "governance.jsonl", decision.as_dict())

    def append_promotion(self, payload: dict[str, object]) -> None:
        self._append_jsonl(self.promotions_dir / "promotions.jsonl", payload)

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
