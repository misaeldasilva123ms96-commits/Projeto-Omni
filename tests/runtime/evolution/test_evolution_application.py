from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.evolution import EvolutionService  # noqa: E402
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.observability.run_reader import read_evolution_summary  # noqa: E402


class EvolutionApplicationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-evolution-application"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"evolution-application-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _create_approved_valid_proposal(self, root: Path, *, patch_payload: dict[str, object]):
        service = EvolutionService(root)
        proposal = service.create_proposal(
            title="Governed sandbox patch attempt",
            summary="Apply deterministic text replacement in evolution sandbox only.",
            target_area="runtime.evolution.application",
            proposal_type="validation_insertion",
            rationale="Need auditable and reversible baseline for governed patch execution.",
            requested_change="Apply bounded text replacement in sandbox file.",
            expected_benefit="Demonstrate safe apply path with rollback support.",
            risk_level="low",
            extensions={"patch_payload": patch_payload},
        )
        service.validate_proposal(proposal_id=proposal.proposal_id)
        service.review_proposal(proposal_id=proposal.proposal_id, approved=True, decision_source="operator_cli")
        return service, proposal.proposal_id

    def test_eligible_approved_valid_proposal_can_apply(self) -> None:
        with self.temp_workspace() as root:
            target_path = ".logs/fusion-runtime/evolution/sandbox/eligible.txt"
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": target_path,
                    "replace_with": "hello governed apply",
                    "postcheck_contains": "governed",
                },
            )
            attempt = service.apply_proposal_patch(proposal_id=proposal_id)
            self.assertEqual(attempt["status"], "applied")
            self.assertTrue(attempt["rollback_available"])
            content = (root / target_path).read_text(encoding="utf-8")
            self.assertIn("governed", content)

    def test_ineligible_proposal_is_blocked_cleanly(self) -> None:
        with self.temp_workspace() as root:
            service = EvolutionService(root)
            proposal = service.create_proposal(
                title="Not approved yet",
                summary="Should fail eligibility.",
                target_area="runtime.evolution.application",
                proposal_type="validation_insertion",
                rationale="Testing blocked path.",
                requested_change="Apply bounded patch.",
                expected_benefit="Ensure eligibility gate blocks non-approved proposals.",
                risk_level="low",
                extensions={
                    "patch_payload": {
                        "mode": "text_replace",
                        "target_path": ".logs/fusion-runtime/evolution/sandbox/blocked.txt",
                        "replace_with": "blocked",
                    }
                },
            )
            service.validate_proposal(proposal_id=proposal.proposal_id)
            with self.assertRaises(ValueError):
                service.apply_proposal_patch(proposal_id=proposal.proposal_id)
            history = service.get_application_history(proposal_id=proposal.proposal_id)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["status"], "failed")
            self.assertIn("application_blocked", history[0]["governance"]["reason"])

    def test_application_history_append_only_and_latest_application(self) -> None:
        with self.temp_workspace() as root:
            target_path = ".logs/fusion-runtime/evolution/sandbox/history.txt"
            (root / target_path).parent.mkdir(parents=True, exist_ok=True)
            (root / target_path).write_text("original", encoding="utf-8")
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": target_path,
                    "replace_with": "attempt one",
                    "postcheck_contains": "missing-token",
                },
            )
            first = service.apply_proposal_patch(proposal_id=proposal_id)
            self.assertEqual(first["status"], "rolled_back")
            proposal = service.get_proposal(proposal_id)
            self.assertIsNotNone(proposal)
            self.assertEqual((proposal.latest_application or {}).get("application_id"), first["application_id"])
            self.assertEqual(len(proposal.application_history), 1)

            # Update payload and apply again; history must append.
            proposal.extensions["patch_payload"] = {
                "mode": "text_replace",
                "target_path": target_path,
                "replace_with": "attempt two",
                "postcheck_contains": "attempt",
            }
            service.registry.register(proposal)
            second = service.apply_proposal_patch(proposal_id=proposal_id)
            proposal = service.get_proposal(proposal_id)
            self.assertEqual(second["status"], "applied")
            self.assertEqual(len(proposal.application_history), 2)
            self.assertEqual((proposal.latest_application or {}).get("application_id"), second["application_id"])

    def test_failed_postcheck_rolls_back(self) -> None:
        with self.temp_workspace() as root:
            target_path = ".logs/fusion-runtime/evolution/sandbox/postcheck.txt"
            target_file = root / target_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text("before", encoding="utf-8")
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": target_path,
                    "replace_with": "after",
                    "postcheck_contains": "not-present",
                },
            )
            attempt = service.apply_proposal_patch(proposal_id=proposal_id)
            self.assertEqual(attempt["status"], "rolled_back")
            self.assertTrue(attempt["rollback_executed"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), "before")

    def test_explicit_rollback_is_recorded(self) -> None:
        with self.temp_workspace() as root:
            target_path = ".logs/fusion-runtime/evolution/sandbox/rollback.txt"
            target_file = root / target_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text("before", encoding="utf-8")
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": target_path,
                    "replace_with": "after",
                    "postcheck_contains": "after",
                },
            )
            applied = service.apply_proposal_patch(proposal_id=proposal_id)
            self.assertEqual(applied["status"], "applied")
            rollback = service.rollback_application(
                proposal_id=proposal_id,
                application_id=applied["application_id"],
                rollback_reason="operator_requested_rollback",
                decision_source="operator_cli",
            )
            self.assertEqual(rollback["status"], "rolled_back")
            self.assertEqual(target_file.read_text(encoding="utf-8"), "before")
            history = service.get_application_history(proposal_id=proposal_id)
            self.assertEqual(len(history), 2)

    def test_observability_includes_application_aggregates(self) -> None:
        with self.temp_workspace() as root:
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": ".logs/fusion-runtime/evolution/sandbox/obs.txt",
                    "replace_with": "obs-data",
                },
            )
            service.apply_proposal_patch(proposal_id=proposal_id)
            summary = read_evolution_summary(root, recent_limit=10)
            self.assertIn("application_counts", summary)
            self.assertIn("latest_application_by_proposal", summary)
            self.assertIn("proposals_with_recent_application", summary)
            self.assertIn("rollback_counts", summary)
            snap = ObservabilityReader(root).snapshot().as_dict()
            self.assertIn("application_counts", snap["governed_evolution"])

    def test_safety_boundary_blocks_outside_sandbox_target(self) -> None:
        with self.temp_workspace() as root:
            service, proposal_id = self._create_approved_valid_proposal(
                root,
                patch_payload={
                    "mode": "text_replace",
                    "target_path": "backend/python/brain/runtime/orchestrator.py",
                    "replace_with": "unsafe",
                },
            )
            with self.assertRaises(ValueError):
                service.apply_proposal_patch(proposal_id=proposal_id)


if __name__ == "__main__":
    unittest.main()
