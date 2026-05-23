from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.evolution import (  # noqa: E402
    EvolutionProposalStatus,
    EvolutionService,
    EvolutionValidationOutcome,
)
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.observability.run_reader import read_evolution_summary  # noqa: E402


class EvolutionValidationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-evolution-validation"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"evolution-validation-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _create_proposal(self, service: EvolutionService, **overrides: str):
        payload = {
            "title": "Bounded governance diagnostics refinement",
            "summary": "Improve deterministic diagnostics in governed evolution validation.",
            "target_area": "runtime.evolution.validation",
            "proposal_type": "validation_insertion",
            "rationale": "Operators require deterministic and auditable proposal checks.",
            "requested_change": "Add deterministic validation checks and append-only result history.",
            "expected_benefit": "Safer evolution decisions with explicit structured outcomes.",
            "risk_level": "medium",
        }
        payload.update(overrides)
        return service.create_proposal(**payload)

    def test_validation_result_creation_valid(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(service)
            result = service.validate_proposal(proposal_id=proposal.proposal_id)
            self.assertEqual(result["proposal_id"], proposal.proposal_id)
            self.assertIn(result["outcome"], {outcome.value for outcome in EvolutionValidationOutcome})
            self.assertIn("validation_id", result)
            self.assertIn("governance", result)
            self.assertEqual(result["governance"]["source"], "system_validation")

    def test_validation_logic_invalid_case(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(service, proposal_type="unknown_type")
            result = service.validate_proposal(proposal_id=proposal.proposal_id)
            self.assertEqual(result["outcome"], EvolutionValidationOutcome.INVALID.value)
            self.assertIn("unsupported_proposal_type", result["issues"])

    def test_validation_logic_risky_case(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(
                service,
                proposal_type="template_adjustment",
                requested_change="Global full rewrite across all runtime modules",
                risk_level="high",
            )
            result = service.validate_proposal(proposal_id=proposal.proposal_id)
            self.assertEqual(result["outcome"], EvolutionValidationOutcome.RISKY.value)
            self.assertIn("overly_broad_requested_change", result["issues"])

    def test_validation_history_is_append_only(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(service)
            first = service.validate_proposal(proposal_id=proposal.proposal_id)
            second = service.validate_proposal(proposal_id=proposal.proposal_id)
            history = service.get_validation_history(proposal_id=proposal.proposal_id)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["validation_id"], first["validation_id"])
            self.assertEqual(history[1]["validation_id"], second["validation_id"])

    def test_validate_proposal_does_not_mutate_status_implicitly(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(service)
            self.assertEqual(proposal.status, EvolutionProposalStatus.PROPOSED.value)
            service.validate_proposal(proposal_id=proposal.proposal_id)
            stored = service.get_proposal(proposal.proposal_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.status, EvolutionProposalStatus.PROPOSED.value)

    def test_explicit_promotion_to_status_mapping(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            valid_proposal = self._create_proposal(service)
            service.validate_proposal(proposal_id=valid_proposal.proposal_id)
            updated = service.promote_validation_result_to_status(
                proposal_id=valid_proposal.proposal_id,
                decision_source="operator_cli",
            )
            self.assertEqual(updated.status, EvolutionProposalStatus.UNDER_REVIEW.value)

            invalid_proposal = self._create_proposal(service, proposal_type="invalid_type")
            service.validate_proposal(proposal_id=invalid_proposal.proposal_id)
            rejected = service.promote_validation_result_to_status(
                proposal_id=invalid_proposal.proposal_id,
                decision_source="operator_cli",
            )
            self.assertEqual(rejected.status, EvolutionProposalStatus.REJECTED.value)

    def test_observability_summary_contains_validation_data(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = self._create_proposal(service)
            service.validate_proposal(proposal_id=proposal.proposal_id)
            summary = read_evolution_summary(root, recent_limit=10)
            self.assertIn("validation_counts", summary)
            self.assertIn("proposals_with_recent_validation", summary)
            self.assertIn("latest_validation_by_proposal", summary)
            self.assertGreaterEqual(summary["validation_counts"]["valid"], 1)
            snap = ObservabilityReader(root).snapshot().as_dict()
            self.assertIn("governed_evolution", snap)
            self.assertIn("validation_counts", snap["governed_evolution"])

    def test_no_application_side_effects_exposed(self) -> None:
        service = EvolutionService(PROJECT_ROOT)
        self.assertFalse(hasattr(service, "apply_patch"))
        self.assertFalse(hasattr(service, "execute_proposal"))


if __name__ == "__main__":
    unittest.main()
