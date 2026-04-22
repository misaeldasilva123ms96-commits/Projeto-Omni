from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = PROJECT_ROOT / "omni-training" / "lib"
SCRIPTS_DIR = PROJECT_ROOT / "omni-training" / "scripts"
for candidate in (LIB_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from ambiguity_examples import build_ambiguity_examples_from_runtime_logs, export_ambiguity_examples  # noqa: E402
from common import read_json, write_jsonl  # noqa: E402
from dataset_weighting import apply_dataset_weights, derive_weight_fields  # noqa: E402
from evaluate_decisions import main as evaluate_decisions_main  # noqa: E402


class DecisionDatasetFeaturesTest(unittest.TestCase):
    def test_dataset_weighting_adds_expected_fields(self) -> None:
        example = {
            "id": "x",
            "task_family": "runtime",
            "quality_score": 0.91,
            "candidate_strategies": ["DIRECT_RESPONSE", "MULTI_STEP_REASONING"],
            "review_status": "approved",
        }
        weighted = derive_weight_fields(example)
        self.assertIn("sample_weight", weighted)
        self.assertEqual(weighted["ambiguity_label"], "high")
        self.assertEqual(weighted["runtime_value"], "high")

    def test_apply_dataset_weights_preserves_compatibility(self) -> None:
        records = [{"id": "a", "task_family": "analysis", "quality_score": 0.85}]
        weighted = apply_dataset_weights(records)
        self.assertEqual(len(weighted), 1)
        self.assertIn("sample_weight", weighted[0])

    def test_ambiguity_examples_are_generated_from_runtime_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
            write_jsonl(
                log_path,
                [
                    {
                        "event_type": "runtime.decision.ranking.applied",
                        "session_id": "s1",
                        "payload": {
                            "candidate_strategies": ["DIRECT_RESPONSE", "MULTI_STEP_REASONING"],
                            "selected_strategy": "MULTI_STEP_REASONING",
                            "decision_source": "hybrid_ranked",
                            "ambiguity_score": 0.72,
                            "message_preview": "Explique e planeje a resposta",
                            "oil_summary": {"user_intent": "plan"},
                        },
                    }
                ],
            )
            examples = build_ambiguity_examples_from_runtime_logs(root, limit=10)
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["selected_strategy"], "MULTI_STEP_REASONING")
            output_path = root / "ambiguity.jsonl"
            export_ambiguity_examples(output_path, examples)
            self.assertTrue(output_path.exists())

    def test_evaluate_decisions_reports_expected_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_path = tmp_root / "execution-audit.jsonl"
            output_path = tmp_root / "decision-report.json"
            write_jsonl(
                input_path,
                [
                    {"event_type": "runtime.decision.ambiguity", "payload": {}},
                    {
                        "event_type": "runtime.decision.ranking.applied",
                        "payload": {
                            "selected_strategy": "MULTI_STEP_REASONING",
                            "deterministic_strategy": "DIRECT_RESPONSE",
                            "decision_source": "hybrid_ranked",
                            "ranked_confidence": 0.83,
                            "review_required": True,
                            "unsafe_override": False,
                        },
                    },
                ],
            )
            stream = io.StringIO()
            with patch.object(
                sys,
                "argv",
                ["evaluate_decisions.py", "--input", str(input_path), "--output", str(output_path)],
            ):
                with redirect_stdout(stream):
                    result = evaluate_decisions_main()
            self.assertEqual(result, 0)
            report = read_json(output_path)
            self.assertEqual(report["ambiguous_case_count"], 1)
            self.assertEqual(report["ranking_applied_count"], 1)
            self.assertEqual(report["unsafe_override_count"], 0)


if __name__ == "__main__":
    unittest.main()

