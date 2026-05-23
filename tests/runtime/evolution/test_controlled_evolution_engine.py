from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.evolution.controlled_apply import Phase39TuningStore  # noqa: E402
from brain.runtime.evolution.controlled_evolution_engine import ControlledEvolutionEngine  # noqa: E402
from brain.runtime.evolution.controlled_evolution_models import ImprovementOpportunity  # noqa: E402
from brain.runtime.evolution.controlled_proposal_builder import ControlledProposalBuilder  # noqa: E402
from brain.runtime.evolution.controlled_validation import validate_governed_proposal  # noqa: E402


class ControlledEvolutionEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_apply = os.environ.pop("OMINI_PHASE39_APPLY", None)
        self._prev_disable = os.environ.pop("OMINI_PHASE39_DISABLE", None)

    def tearDown(self) -> None:
        if self._prev_apply is not None:
            os.environ["OMINI_PHASE39_APPLY"] = self._prev_apply
        if self._prev_disable is not None:
            os.environ["OMINI_PHASE39_DISABLE"] = self._prev_disable

    def test_disabled_env(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-controlled-evo"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            os.environ["OMINI_PHASE39_DISABLE"] = "true"
            eng = ControlledEvolutionEngine(root)
            tr = eng.evaluate_turn(session_id="s1", evidence={})
            self.assertTrue(tr.get("disabled"))
        finally:
            shutil.rmtree(root, ignore_errors=True)
            os.environ.pop("OMINI_PHASE39_DISABLE", None)

    def test_detect_validate_apply_rollback(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-controlled-evo"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            os.environ["OMINI_PHASE39_APPLY"] = "true"
            store = Phase39TuningStore(root)
            eng = ControlledEvolutionEngine(root)
            evidence = {
                "performance": {"trace": {"trace_id": "p1", "degraded": True}},
                "task_decomposition": {},
                "coordination": {"trace": {"issues_aggregate": []}},
                "learning_trace": {"outcome_class": "success", "execution_degraded": False},
                "last_runtime_reason": "",
            }
            tr1 = eng.evaluate_turn(session_id="s1", evidence=evidence)
            self.assertGreaterEqual(tr1.get("opportunity_count", 0), 1)
            self.assertEqual(tr1.get("apply_status"), "applied")
            data = store.read()
            self.assertIsInstance(data.get("pending_monitor"), dict)

            opp = ImprovementOpportunity(
                opportunity_id="x",
                session_id="s1",
                source_type="performance",
                category="repeated_degraded_fallback",
                summary="again",
                confidence=0.8,
                evidence_refs=["e"],
                recommended_proposal_type="performance_cache_tune",
                governance_relevant=True,
            )
            tr2 = eng.evaluate_turn(
                session_id="s1",
                evidence={
                    **evidence,
                    "performance": {"trace": {"trace_id": "p2", "degraded": True}},
                },
            )
            self.assertTrue(tr2.get("rollback_applied"))
            self.assertEqual(tr2.get("apply_status"), "rollback")

            b = ControlledProposalBuilder()
            prop = b.build(
                opportunity=opp,
                current_tuning=store.read(),
            )
            assert prop is not None
            vr = validate_governed_proposal(prop)
            self.assertTrue(vr.accepted)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            os.environ.pop("OMINI_PHASE39_APPLY", None)

    def test_reject_invalid_bounds(self) -> None:
        b = ControlledProposalBuilder()
        opp = ImprovementOpportunity(
            opportunity_id="o1",
            session_id="s",
            source_type="decomposition",
            category="repeated_truncation_signal",
            summary="t",
            confidence=0.5,
            evidence_refs=[],
            recommended_proposal_type="decomposition_limit_tune",
            governance_relevant=True,
        )
        prop = b.build(opportunity=opp, current_tuning={"decomposition_max_subtasks": 8})
        assert prop is not None
        prop.payload["new_value"] = 99
        vr = validate_governed_proposal(prop)
        self.assertFalse(vr.accepted)


if __name__ == "__main__":
    unittest.main()
