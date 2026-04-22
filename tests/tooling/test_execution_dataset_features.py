from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = PROJECT_ROOT / "omni-training" / "lib"
SCRIPTS_DIR = PROJECT_ROOT / "omni-training" / "scripts"
for candidate in (LIB_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from common import write_jsonl  # noqa: E402
from execution_examples import build_execution_examples_from_runtime_logs  # noqa: E402
from evaluate_execution import main as evaluate_execution_main  # noqa: E402


class ExecutionDatasetFeaturesTest(unittest.TestCase):
    def test_build_execution_examples_from_runtime_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
            write_jsonl(
                log_path,
                [
                    {
                        "event_type": "runtime.strategy.execution.result",
                        "session_id": "sess-1",
                        "payload": {
                            "selected_strategy": "TOOL_ASSISTED",
                            "executor_used": "tool_assisted_executor",
                            "strategy_execution_status": "success",
                            "execution_trace_summary": "Tool executor completed safely.",
                            "manifest_driven_execution": True,
                        },
                    }
                ],
            )
            examples = build_execution_examples_from_runtime_logs(root, limit=5)
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["selected_strategy"], "TOOL_ASSISTED")
            self.assertEqual(examples[0]["executor_used"], "tool_assisted_executor")
            self.assertIn("sample_weight", examples[0])

    def test_evaluate_execution_script_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "execution-audit.jsonl"
            output_path = root / "execution-report.json"
            write_jsonl(
                input_path,
                [
                    {
                        "event_type": "runtime.strategy.execution.result",
                        "payload": {
                            "selected_strategy": "MULTI_STEP_REASONING",
                            "executor_used": "multi_step_reasoning_executor",
                            "strategy_execution_status": "success",
                            "strategy_execution_fallback": False,
                            "governance_blocked": False,
                            "governance_downgrade_applied": False,
                            "manifest_driven_execution": True,
                            "ranked_confidence": 0.82,
                        },
                    }
                ],
            )
            with patch.object(sys, "argv", ["evaluate_execution.py", "--input", str(input_path), "--output", str(output_path)]):
                result = evaluate_execution_main()
            self.assertEqual(result, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["strategy_execution_count"], 1)
            self.assertEqual(report["unsafe_execution_count"], 0)


if __name__ == "__main__":
    unittest.main()

