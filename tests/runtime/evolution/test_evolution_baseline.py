from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.evolution import (  # noqa: E402
    EvolutionProposalRecord,
    EvolutionProposalStatus,
    EvolutionRegistry,
    EvolutionService,
)
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.observability.run_reader import read_evolution_proposal, read_evolution_summary  # noqa: E402


class EvolutionBaselineTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-evolution-baseline"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"evolution-baseline-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _create_record(self) -> EvolutionProposalRecord:
        return EvolutionProposalRecord.build(
            title="Improve governance wait diagnostics",
            summary="Capture bounded diagnostics for governance waits without changing control semantics.",
            target_area="runtime.control.wait",
            proposal_type="bounded_runtime_refinement",
            rationale="Operator timeouts should be auditable and predictable.",
            requested_change="Add explicit attempt counters and expose summary reads.",
            expected_benefit="Improved auditability with no autonomous patch apply.",
            risk_level="medium",
        )

    def test_model_roundtrip_serialization(self) -> None:
        record = self._create_record()
        payload = record.as_dict()
        blob = json.dumps(payload, ensure_ascii=False)
        loaded = EvolutionProposalRecord.from_dict(json.loads(blob))
        self.assertEqual(loaded.proposal_id, record.proposal_id)
        self.assertEqual(loaded.status, EvolutionProposalStatus.PROPOSED.value)
        self.assertTrue(loaded.governance.get("governed"))

    def test_invalid_model_input_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EvolutionProposalRecord.build(
                title="",
                summary="x",
                target_area="runtime",
                proposal_type="bounded_runtime_refinement",
                rationale="x",
                requested_change="x",
                expected_benefit="x",
                risk_level="medium",
            )
        with self.assertRaises(ValueError):
            EvolutionProposalRecord.build(
                title="x",
                summary="x",
                target_area="runtime",
                proposal_type="bounded_runtime_refinement",
                rationale="x",
                requested_change="x",
                expected_benefit="x",
                risk_level="unknown-risk",
            )

    def test_registry_persistence_load_and_summary(self) -> None:
        with self.temp_workspace() as root:
            registry = EvolutionRegistry(root)
            created = registry.register(self._create_record())
            self.assertTrue(registry.path.exists())
            reg2 = EvolutionRegistry(root)
            loaded = reg2.get(created.proposal_id)
            self.assertIsNotNone(loaded)
            summary = reg2.get_summary()
            self.assertEqual(summary["total_proposals"], 1)
            self.assertEqual(summary["status_counts"]["proposed"], 1)
            self.assertEqual(summary["recent_proposals"][0]["proposal_id"], created.proposal_id)

    def test_service_create_and_controlled_transitions(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            created = service.create_proposal(
                title="Guard proposal schema",
                summary="Ensure proposal contract remains strict and auditable.",
                target_area="runtime.evolution.registry",
                proposal_type="policy_tuning",
                rationale="Baseline proposals must be governed before action.",
                requested_change="Enforce shape validation and status transition rules.",
                expected_benefit="Stable proposal lifecycle with explicit states.",
                risk_level="low",
            )
            self.assertEqual(created.status, EvolutionProposalStatus.PROPOSED.value)

            under_review = service.change_proposal_status(
                proposal_id=created.proposal_id,
                next_status=EvolutionProposalStatus.UNDER_REVIEW.value,
                decision_source="operator_cli",
            )
            self.assertEqual(under_review.status, EvolutionProposalStatus.UNDER_REVIEW.value)

            approved = service.review_proposal(
                proposal_id=created.proposal_id,
                approved=True,
                decision_source="operator_cli",
            )
            self.assertEqual(approved.status, EvolutionProposalStatus.APPROVED.value)

            with self.assertRaises(ValueError):
                service.change_proposal_status(
                    proposal_id=created.proposal_id,
                    next_status=EvolutionProposalStatus.UNDER_REVIEW.value,
                    decision_source="operator_cli",
                )

    def test_operational_read_surface_and_observability_include_governed_evolution(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            created = service.create_proposal(
                title="Bounded proposal summary visibility",
                summary="Expose proposal counts and recent governed proposal metadata.",
                target_area="runtime.observability",
                proposal_type="validation_insertion",
                rationale="Operators need quick visibility into governed evolution state.",
                requested_change="Add summary read helper and include in snapshot.",
                expected_benefit="Operational transparency without autonomous mutation.",
                risk_level="low",
            )
            service.change_proposal_status(
                proposal_id=created.proposal_id,
                next_status=EvolutionProposalStatus.UNDER_REVIEW.value,
                decision_source="operator_cli",
            )
            summary = read_evolution_summary(root, recent_limit=5)
            self.assertTrue(summary["governed"])
            self.assertEqual(summary["status_counts"]["under_review"], 1)
            self.assertFalse(summary["lifecycle"]["auto_apply_enabled"])

            proposal_payload = read_evolution_proposal(root, created.proposal_id)
            self.assertIsInstance(proposal_payload, dict)
            self.assertEqual(proposal_payload["proposal_id"], created.proposal_id)

            snapshot = ObservabilityReader(root).snapshot().as_dict()
            self.assertIn("governed_evolution", snapshot)
            self.assertEqual(snapshot["governed_evolution"]["total_proposals"], 1)

    def test_non_application_rule_no_auto_apply_method(self) -> None:
        service = EvolutionService(PROJECT_ROOT)
        self.assertFalse(hasattr(service, "apply_proposal"))


if __name__ == "__main__":
    unittest.main()
