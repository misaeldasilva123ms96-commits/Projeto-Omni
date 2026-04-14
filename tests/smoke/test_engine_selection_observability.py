from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class EngineSelectionObservabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        self.orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        self.orchestrator.memory_facade.record_event = MagicMock()
        self.orchestrator.engine_adoption_store = MagicMock()

    def test_records_engine_selection_event_when_metadata_exists(self) -> None:
        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "packaged_upstream",
                    "engine_reason": "dist_candidate_selected",
                },
            }
        )

        self.orchestrator.memory_facade.record_event.assert_called_once_with(
            event_type="engine_selection",
            description="QueryEngine responded via packaged_upstream",
            metadata={
                "engine_mode": "packaged_upstream",
                "engine_reason": "dist_candidate_selected",
            },
        )
        self.orchestrator.engine_adoption_store.record_selection.assert_called_once_with(
            engine_mode="packaged_upstream",
            engine_reason="dist_candidate_selected",
            session_id="",
        )

    def test_engine_selection_updates_adoption_store_with_session_id(self) -> None:
        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "authority_fallback",
                    "engine_reason": "heavy_execution_request",
                },
            },
            session_id="sess-26",
        )

        self.orchestrator.engine_adoption_store.record_selection.assert_called_once_with(
            engine_mode="authority_fallback",
            engine_reason="heavy_execution_request",
            session_id="sess-26",
        )

    def test_promoted_engine_selection_records_engine_promotion_event(self) -> None:
        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "packaged_upstream",
                    "engine_reason": "dist_candidate_selected",
                    "promoted_scenario": "executor_bridge_light_request",
                    "promotion_phase": "27",
                },
            },
            session_id="sess-27",
        )

        self.assertEqual(self.orchestrator.memory_facade.record_event.call_count, 2)
        promotion_call = self.orchestrator.memory_facade.record_event.call_args_list[1]
        self.assertEqual(promotion_call.kwargs["event_type"], "engine_promotion")
        self.assertEqual(
            promotion_call.kwargs["metadata"],
            {
                "promoted_scenario": "executor_bridge_light_request",
                "previous_route": "authority_fallback",
                "new_route": "packaged_upstream",
                "phase": "27",
            },
        )

    def test_promotion_rollback_records_event(self) -> None:
        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "authority_fallback",
                    "engine_reason": "fallback_policy_triggered",
                    "promoted_scenario": "executor_bridge_light_request",
                    "promotion_phase": "27",
                    "promotion_rollback_reason": "packaged_import_failed_threshold_exceeded",
                },
            },
            session_id="sess-27",
        )

        self.assertEqual(self.orchestrator.memory_facade.record_event.call_count, 2)
        rollback_call = self.orchestrator.memory_facade.record_event.call_args_list[1]
        self.assertEqual(rollback_call.kwargs["event_type"], "engine_promotion_rollback")
        self.assertEqual(
            rollback_call.kwargs["metadata"],
            {
                "promoted_scenario": "executor_bridge_light_request",
                "reason": "packaged_import_failed_threshold_exceeded",
                "phase": "27",
            },
        )

    def test_missing_metadata_is_ignored_without_exception(self) -> None:
        self.orchestrator._record_engine_selection_event({"response": "ok"})
        self.orchestrator._record_engine_selection_event(None)

        self.orchestrator.memory_facade.record_event.assert_not_called()
        self.orchestrator.engine_adoption_store.record_selection.assert_not_called()

    def test_engine_selection_store_failure_does_not_block_memory_event(self) -> None:
        self.orchestrator.engine_adoption_store.record_selection.side_effect = RuntimeError("store down")

        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "packaged_upstream",
                    "engine_reason": "dist_candidate_selected",
                },
            },
            session_id="sess-26",
        )

        self.orchestrator.memory_facade.record_event.assert_called_once()

    def test_records_runtime_selection_event_when_metadata_exists(self) -> None:
        self.orchestrator._record_runtime_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "runtime_mode": "bun",
                    "runtime_reason": "bun_native",
                },
            },
            runner="queryEngineRunner.js",
        )

        self.orchestrator.memory_facade.record_event.assert_called_once_with(
            event_type="runtime_selection",
            description="JS runner responded via bun",
            metadata={
                "runtime_mode": "bun",
                "runtime_reason": "bun_native",
                "runner": "queryEngineRunner.js",
            },
        )

    def test_missing_runtime_metadata_is_ignored_without_exception(self) -> None:
        self.orchestrator._record_runtime_selection_event({"response": "ok"}, runner="queryEngineRunner.js")
        self.orchestrator._record_runtime_selection_event(None, runner="queryEngineRunner.js")

        self.orchestrator.memory_facade.record_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
