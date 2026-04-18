from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.coordination.agent_coordinator import AgentCoordinator  # noqa: E402
from brain.runtime.coordination.agent_roles import ROLE_ORDER  # noqa: E402


class AgentCoordinatorTest(unittest.TestCase):
    def _minimal_planning(self) -> dict:
        return {
            "execution_plan": {
                "plan_id": "plan-test-1",
                "execution_ready": True,
                "planning_summary": "Do the thing",
                "steps": [
                    {"step_id": "s1", "summary": "A", "requires_validation": False},
                    {"step_id": "s2", "summary": "B", "requires_validation": True},
                ],
            },
            "planning_trace": {
                "trace_id": "pt-1",
                "plan_id": "plan-test-1",
                "step_count": 2,
                "execution_ready": True,
                "degraded": False,
                "error": "",
            },
        }

    def test_full_coordination_role_order_and_trace(self) -> None:
        c = AgentCoordinator()
        r = c.coordinate(
            session_id="s1",
            run_id="",
            planning_payload=self._minimal_planning(),
            reasoning_handoff={
                "proceed": True,
                "intent": "analyze",
                "task_type": "repository",
                "suggested_capabilities": ["read_file"],
            },
            reasoning_payload={"trace": {"trace_id": "rt-1"}},
            memory_context_payload={"context_id": "mem-1"},
            strategy_payload={"strategy_trace": {"trace_id": "st-1"}},
            control_execution_summary={
                "allowed": True,
                "reason_code": "execution_allowed",
                "task_type": "repository",
                "risk_level": "medium",
                "execution_strategy": "swarm",
                "verification_intensity": "normal",
            },
            coordination_mode="full",
        )
        tr = r.trace
        self.assertTrue(tr.coordination_id.startswith("mac37-"))
        self.assertEqual(len(tr.participations), len(ROLE_ORDER))
        self.assertListEqual([p.role for p in tr.participations], [role.value for role in ROLE_ORDER])
        self.assertTrue(tr.governance_authority_preserved)
        self.assertTrue(tr.control_execution_allowed)
        self.assertFalse(tr.degraded)
        self.assertIn("handoff_bundle", r.as_dict())
        self.assertEqual(r.handoff_bundle.get("phase"), "37")
        self.assertIn("specialist_digest", r.handoff_bundle)

    def test_skipped_direct_memory_mode(self) -> None:
        c = AgentCoordinator()
        r = c.coordinate(
            session_id="s1",
            run_id="",
            planning_payload=self._minimal_planning(),
            reasoning_handoff={"proceed": True, "intent": "x", "task_type": "repository"},
            reasoning_payload={"trace": {}},
            memory_context_payload={},
            strategy_payload={},
            control_execution_summary={"allowed": True, "reason_code": "execution_allowed", "task_type": "repository"},
            coordination_mode="skipped_direct_memory",
        )
        self.assertEqual(r.trace.execution_readiness, "not_applicable")
        for p in r.trace.participations:
            self.assertEqual(p.status, "skipped")

    def test_control_blocked_branch_is_governance_safe(self) -> None:
        c = AgentCoordinator()
        r = c.coordinate(
            session_id="s1",
            run_id="",
            planning_payload=self._minimal_planning(),
            reasoning_handoff={"proceed": True, "intent": "x", "task_type": "repository"},
            reasoning_payload={"trace": {}},
            memory_context_payload={},
            strategy_payload={},
            control_execution_summary={"allowed": False, "reason_code": "policy_block"},
            coordination_mode="full",
        )
        self.assertFalse(r.trace.control_execution_allowed)
        self.assertEqual(r.trace.execution_readiness, "blocked_by_control")
        self.assertNotIn("execution_override", str(r.handoff_bundle))

    def test_validator_issues_propagate_to_readiness(self) -> None:
        c = AgentCoordinator()
        bad_plan = {
            "execution_plan": {"plan_id": "", "steps": [], "execution_ready": False},
            "planning_trace": {"step_count": 0},
        }
        r = c.coordinate(
            session_id="s1",
            run_id="",
            planning_payload=bad_plan,
            reasoning_handoff={
                "proceed": True,
                "intent": "a",
                "task_type": "repository",
            },
            reasoning_payload={"trace": {}},
            memory_context_payload={},
            strategy_payload={},
            control_execution_summary={
                "allowed": True,
                "task_type": "other",
                "risk_level": "high",
                "execution_strategy": "swarm",
                "verification_intensity": "strict",
            },
            coordination_mode="full",
        )
        self.assertNotEqual(r.trace.execution_readiness, "ready")
        self.assertTrue(r.trace.issues_aggregate)

    def test_degraded_on_internal_error(self) -> None:
        c = AgentCoordinator()
        with patch.object(c, "_run_planner", side_effect=RuntimeError("boom")):
            r = c.coordinate(
                session_id="s1",
                run_id="",
                planning_payload=self._minimal_planning(),
                reasoning_handoff={"proceed": True, "intent": "x", "task_type": "repository"},
                reasoning_payload={"trace": {}},
                memory_context_payload={},
                strategy_payload={},
                control_execution_summary={"allowed": True, "task_type": "repository"},
                coordination_mode="full",
            )
        self.assertTrue(r.trace.degraded)
        self.assertTrue(r.handoff_bundle.get("fallback"))


if __name__ == "__main__":
    unittest.main()
