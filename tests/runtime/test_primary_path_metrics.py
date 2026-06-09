from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

import pytest

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths


@pytest.fixture
def orchestrator() -> BrainOrchestrator:
    paths = BrainPaths.from_entrypoint(Path(__file__))
    orch = BrainOrchestrator(paths)
    return orch


class TestGetPrimaryPathSuccessRate:
    def test_returns_zero_when_no_attempts(self, orchestrator: BrainOrchestrator) -> None:
        metrics = orchestrator.get_primary_path_success_rate()
        assert metrics["attempts"] == 0
        assert metrics["successes"] == 0
        assert metrics["fallbacks"] == 0
        assert metrics["fallback_rate_pct"] == 0.0
        assert metrics["success_rate_pct"] == 0.0

    def test_computes_correct_rate_all_success(self, orchestrator: BrainOrchestrator) -> None:
        orchestrator._primary_path_metrics["attempts"] = 10
        orchestrator._primary_path_metrics["successes"] = 10
        orchestrator._primary_path_metrics["fallbacks"] = 0
        orchestrator._primary_path_metrics["exit_D_direct_success"] = 5
        orchestrator._primary_path_metrics["exit_D_action_success"] = 5

        metrics = orchestrator.get_primary_path_success_rate()
        assert metrics["success_rate_pct"] == 100.0
        assert metrics["fallback_rate_pct"] == 0.0

    def test_computes_correct_rate_all_fallback(self, orchestrator: BrainOrchestrator) -> None:
        orchestrator._primary_path_metrics["attempts"] = 10
        orchestrator._primary_path_metrics["successes"] = 0
        orchestrator._primary_path_metrics["fallbacks"] = 10
        orchestrator._primary_path_metrics["exit_C_semantic_fallback"] = 7
        orchestrator._primary_path_metrics["exit_B_transport_failure"] = 3

        metrics = orchestrator.get_primary_path_success_rate()
        assert metrics["success_rate_pct"] == 0.0
        assert metrics["fallback_rate_pct"] == 100.0

    def test_computes_mixed_rate(self, orchestrator: BrainOrchestrator) -> None:
        orchestrator._primary_path_metrics["attempts"] = 20
        orchestrator._primary_path_metrics["successes"] = 15
        orchestrator._primary_path_metrics["fallbacks"] = 5
        orchestrator._primary_path_metrics["exit_D_direct_success"] = 10
        orchestrator._primary_path_metrics["exit_D_bridge_success"] = 3
        orchestrator._primary_path_metrics["exit_D_action_success"] = 2
        orchestrator._primary_path_metrics["exit_A_configured_fallback"] = 1
        orchestrator._primary_path_metrics["exit_C_semantic_fallback"] = 4

        metrics = orchestrator.get_primary_path_success_rate()
        assert metrics["success_rate_pct"] == 75.0
        assert metrics["fallback_rate_pct"] == 25.0

    def test_avoids_division_by_zero(self, orchestrator: BrainOrchestrator) -> None:
        orchestrator._primary_path_metrics["attempts"] = 0
        metrics = orchestrator.get_primary_path_success_rate()
        assert metrics["success_rate_pct"] == 0.0
        assert metrics["fallback_rate_pct"] == 0.0

    def test_returns_all_counter_keys(self, orchestrator: BrainOrchestrator) -> None:
        metrics = orchestrator.get_primary_path_success_rate()
        expected_keys = {
            "attempts", "successes", "fallbacks",
            "exit_A_configured_fallback", "exit_B_transport_failure",
            "exit_C_semantic_fallback", "exit_D_direct_success",
            "exit_D_bridge_success", "exit_D_action_success",
            "fallback_rate_pct", "success_rate_pct", "total_attempts",
        }
        assert set(metrics.keys()) == expected_keys
