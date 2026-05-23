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
    CONTROLLED_SELF_EVOLUTION_PHASE,
    CONTROLLED_SELF_EVOLUTION_PROGRAM,
    EvolutionService,
    empty_governed_evolution_summary,
    validate_governed_evolution_summary_shape,
)
from brain.runtime.observability.run_reader import read_evolution_summary  # noqa: E402


class EvolutionProgramClosureTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-evolution-program-closure"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"evolution-closure-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _create_approved_proposal(self, root: Path):
        service = EvolutionService(root)
        proposal = service.create_proposal(
            title="Closure coherence proposal",
            summary="Ensure lifecycle coherence across proposal/validation/application/rollback.",
            target_area="runtime.evolution.closure",
            proposal_type="validation_insertion",
            rationale="Control plane closure needs deterministic and auditable integrated behavior.",
            requested_change="Write bounded content in sandbox for controlled apply checks.",
            expected_benefit="Operationally coherent closure state.",
            risk_level="low",
            extensions={
                "patch_payload": {
                    "mode": "text_replace",
                    "target_path": ".logs/fusion-runtime/evolution/sandbox/closure.txt",
                    "replace_with": "closure-data",
                    "postcheck_contains": "closure-data",
                }
            },
        )
        service.validate_proposal(proposal_id=proposal.proposal_id)
        service.review_proposal(proposal_id=proposal.proposal_id, approved=True, decision_source="operator_cli")
        return service, proposal.proposal_id

    def test_empty_state_shape_is_stable_and_readable(self) -> None:
        with self.temp_workspace() as root:
            summary = read_evolution_summary(root)
            validate_governed_evolution_summary_shape(summary)
            self.assertEqual(summary["program"], CONTROLLED_SELF_EVOLUTION_PROGRAM)
            self.assertEqual(summary["program_phase"], CONTROLLED_SELF_EVOLUTION_PHASE)
            self.assertEqual(summary["total_proposals"], 0)
            self.assertEqual(summary["status_counts"], summary["proposal_counts"])

    def test_approved_proposal_does_not_imply_applied(self) -> None:
        with self.temp_workspace() as root:
            service, proposal_id = self._create_approved_proposal(root)
            proposal = service.get_proposal(proposal_id)
            self.assertIsNotNone(proposal)
            self.assertEqual(proposal.status, "approved")
            self.assertEqual(proposal.application_history, [])
            summary = service.summary()
            self.assertEqual(summary["application_counts"]["applied"], 0)

    def test_latest_shortcuts_align_with_histories(self) -> None:
        with self.temp_workspace() as root:
            service, proposal_id = self._create_approved_proposal(root)
            service.validate_proposal(proposal_id=proposal_id)
            applied = service.apply_proposal_patch(proposal_id=proposal_id)
            proposal = service.get_proposal(proposal_id)
            self.assertIsNotNone(proposal)
            self.assertEqual(
                (proposal.latest_validation or {}).get("validation_id"),
                proposal.validation_history[-1]["validation_id"],
            )
            self.assertEqual(
                (proposal.latest_application or {}).get("application_id"),
                proposal.application_history[-1]["application_id"],
            )
            self.assertEqual(applied["application_id"], proposal.latest_application["application_id"])

    def test_rollback_visibility_is_coherent(self) -> None:
        with self.temp_workspace() as root:
            service, proposal_id = self._create_approved_proposal(root)
            proposal = service.get_proposal(proposal_id)
            proposal.extensions["patch_payload"]["postcheck_contains"] = "missing-token"
            service.registry.register(proposal)
            service.apply_proposal_patch(proposal_id=proposal_id)
            summary = read_evolution_summary(root)
            self.assertGreaterEqual(summary["rollback_counts"]["executed"], 1)
            latest = summary["latest_application_by_proposal"][proposal_id]
            self.assertEqual(latest["status"], "rolled_back")

    def test_no_autonomous_path_is_exposed(self) -> None:
        service = EvolutionService(PROJECT_ROOT)
        self.assertFalse(hasattr(service, "run_autonomous_cycle"))
        self.assertFalse(service.summary()["lifecycle"]["auto_apply_enabled"])

    def test_closure_helper_empty_shape_contract(self) -> None:
        payload = empty_governed_evolution_summary()
        validate_governed_evolution_summary_shape(payload)
        self.assertEqual(payload["program"], CONTROLLED_SELF_EVOLUTION_PROGRAM)
        self.assertEqual(payload["program_phase"], CONTROLLED_SELF_EVOLUTION_PHASE)


if __name__ == "__main__":
    unittest.main()
