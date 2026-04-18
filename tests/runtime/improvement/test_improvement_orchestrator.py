from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.evolution.controlled_apply import Phase39TuningStore  # noqa: E402
from brain.runtime.improvement.improvement_orchestrator import ImprovementOrchestrator  # noqa: E402


def _proposal_dict(*, opp_id: str, new_value: int = 8) -> dict:
    return {
        "proposal_id": f"prop39-test-{uuid4().hex[:8]}",
        "opportunity_id": opp_id,
        "proposal_type": "decomposition_limit_tune",
        "scope": "runtime_tuning_file",
        "target_layer": "decomposition",
        "change_summary": "Raise cap",
        "risk_class": "low",
        "validation_requirements": ["shape_ok", "bounds_ok", "governance_safe"],
        "approval_state": "auto_validated_low_risk",
        "apply_status": "pending",
        "monitor_status": "pending",
        "rollback_status": "rollback_ready",
        "payload": {
            "key": "decomposition_max_subtasks",
            "new_value": new_value,
            "previous_value": 6,
            "opportunity_category": "repeated_truncation_signal",
        },
    }


class ImprovementOrchestratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env: dict[str, str | None] = {
            "OMINI_PHASE40_ENABLE": os.environ.get("OMINI_PHASE40_ENABLE"),
            "OMINI_PHASE40_APPLY": os.environ.get("OMINI_PHASE40_APPLY"),
            "OMINI_PHASE40_AUTO_APPROVE": os.environ.get("OMINI_PHASE40_AUTO_APPROVE"),
            "OMINI_PHASE40_DISABLE": os.environ.get("OMINI_PHASE40_DISABLE"),
            "OMINI_PHASE40_APPROVE": os.environ.get("OMINI_PHASE40_APPROVE"),
        }

    def tearDown(self) -> None:
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_disabled(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-improvement"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            with patch.dict(os.environ, {"OMINI_PHASE40_DISABLE": "true", "OMINI_PHASE40_ENABLE": "true"}):
                orch = ImprovementOrchestrator(root)
                tr = orch.run_cycle(
                    session_id="s",
                    ce_trace={"proposals": [_proposal_dict(opp_id="o1")]},
                    evidence={"duration_ms": 10.0},
                )
            self.assertTrue(tr.get("disabled"))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_idle_when_phase40_off(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-improvement"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            os.environ.pop("OMINI_PHASE40_ENABLE", None)
            orch = ImprovementOrchestrator(root)
            tr = orch.run_cycle(
                session_id="s",
                ce_trace={"proposals": [_proposal_dict(opp_id="o1")]},
                evidence={},
            )
            self.assertTrue(tr.get("idle"))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_pending_without_auto_approve(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-improvement"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            with patch.dict(
                os.environ,
                {
                    "OMINI_PHASE40_ENABLE": "true",
                    "OMINI_PHASE40_APPLY": "true",
                },
                clear=False,
            ):
                os.environ.pop("OMINI_PHASE40_AUTO_APPROVE", None)
                os.environ.pop("OMINI_PHASE40_APPROVE", None)
                orch = ImprovementOrchestrator(root)
                tr = orch.run_cycle(
                    session_id="s",
                    ce_trace={"proposals": [_proposal_dict(opp_id="o2")]},
                    evidence={"duration_ms": 100.0},
                )
            self.assertEqual(tr.get("approval_decision"), "pending")
            self.assertEqual(tr.get("rollout_stage"), "idle")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_gradual_rollout_three_stages(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-improvement"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            opp = "o-rollout-1"
            with patch.dict(
                os.environ,
                {
                    "OMINI_PHASE40_ENABLE": "true",
                    "OMINI_PHASE40_APPLY": "true",
                    "OMINI_PHASE40_AUTO_APPROVE": "true",
                },
                clear=False,
            ):
                orch = ImprovementOrchestrator(root)
                ce = {"proposals": [_proposal_dict(opp_id=opp, new_value=8)]}
                ev = {"duration_ms": 50.0, "learning_trace": {"outcome_class": "success", "execution_degraded": False}}
                t1 = orch.run_cycle(session_id="s", ce_trace=ce, evidence=ev)
                self.assertEqual(t1.get("approval_decision"), "approved_auto")
                self.assertEqual(t1["cycle"]["monitoring_state"].get("apply_status"), "applied")
                store = Phase39TuningStore(root)
                v1 = int(store.read().get("decomposition_max_subtasks") or 0)

                t2 = orch.run_cycle(session_id="s", ce_trace=ce, evidence=ev)
                self.assertEqual(t2.get("approval_decision"), "approved_auto")
                v2 = int(store.read().get("decomposition_max_subtasks") or 0)

                t3 = orch.run_cycle(session_id="s", ce_trace=ce, evidence=ev)
                v3 = int(store.read().get("decomposition_max_subtasks") or 0)

                self.assertLessEqual(v1, v2)
                self.assertLessEqual(v2, v3)
                self.assertEqual(v3, 8)
                self.assertEqual(t3.get("rollout_stage"), "complete")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_regression_triggers_rollback(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-improvement"
        base.mkdir(parents=True, exist_ok=True)
        root = base / uuid4().hex[:10]
        root.mkdir(parents=True, exist_ok=True)
        try:
            opp = "o-reg-1"
            with patch.dict(
                os.environ,
                {
                    "OMINI_PHASE40_ENABLE": "true",
                    "OMINI_PHASE40_APPLY": "true",
                    "OMINI_PHASE40_AUTO_APPROVE": "true",
                },
                clear=False,
            ):
                orch = ImprovementOrchestrator(root)
                ce = {"proposals": [_proposal_dict(opp_id=opp, new_value=8)]}
                orch.run_cycle(
                    session_id="s",
                    ce_trace=ce,
                    evidence={"duration_ms": 100.0, "learning_trace": {}},
                )
                t2 = orch.run_cycle(
                    session_id="s",
                    ce_trace=ce,
                    evidence={
                        "duration_ms": 5000.0,
                        "learning_trace": {"outcome_class": "success", "execution_degraded": False},
                    },
                )
            self.assertEqual(t2.get("rollout_stage"), "rolled_back")
            self.assertEqual(t2.get("rollback_status"), "applied_chain")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
