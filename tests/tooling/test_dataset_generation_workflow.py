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

from auto_review import classify_examples, summarize_review  # noqa: E402
from common import write_jsonl  # noqa: E402
from dataset_growth_report import main as dataset_growth_report_main  # noqa: E402
from evaluate_model_quality import main as evaluate_model_quality_main  # noqa: E402
from training_readiness import main as training_readiness_main  # noqa: E402


class DatasetGenerationWorkflowTest(unittest.TestCase):
    def test_auto_review_marks_duplicates_for_review(self) -> None:
        classified = classify_examples(
            [
                {
                    "id": "a",
                    "instruction": "Explique o fallback",
                    "output": "Use fallback seguro e registre observabilidade do runtime.",
                    "oil": {
                        "user_intent": "explain",
                        "desired_output": "analysis",
                        "urgency": "medium",
                        "execution_bias": "balanced",
                        "memory_relevance": "high",
                    },
                    "runtime_hints": {"strategy": "SAFE_FALLBACK", "requires_tools": False, "requires_node_runtime": False, "fallback_allowed": True},
                },
                {
                    "id": "b",
                    "instruction": "Explique o fallback",
                    "output": "Use fallback seguro e registre observabilidade do runtime.",
                    "oil": {
                        "user_intent": "explain",
                        "desired_output": "analysis",
                        "urgency": "medium",
                        "execution_bias": "balanced",
                        "memory_relevance": "high",
                    },
                    "runtime_hints": {"strategy": "SAFE_FALLBACK", "requires_tools": False, "requires_node_runtime": False, "fallback_allowed": True},
                },
            ]
        )
        self.assertEqual(len(classified), 2)
        self.assertTrue(any("duplicate_approx" in item["quality_flags"] for item in classified))
        report = summarize_review(classified)
        self.assertEqual(report["total_records"], 2)

    def test_training_readiness_can_reach_medium_lora(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "mixed_sft.jsonl"
            output_path = Path(tmp) / "training_readiness.json"
            records = []
            for index in range(220):
                records.append(
                    {
                        "source": "runtime_harvest" if index < 90 else "internal_curated",
                        "task_family": "runtime" if index < 120 else "coding",
                        "language": "pt-BR",
                        "quality_score": 0.86,
                        "review_status": "approved" if index < 120 else "reviewed",
                    }
                )
            records.extend(
                {
                    "source": "default_small_instruction",
                    "task_family": "instruction",
                    "language": "pt-BR",
                    "quality_score": 0.75,
                    "review_status": "reviewed",
                }
                for _ in range(100)
            )
            write_jsonl(input_path, records)
            with patch.object(sys, "argv", ["training_readiness.py", "--input", str(input_path), "--output", str(output_path)]):
                result = training_readiness_main()
            self.assertEqual(result, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["readiness"], "READY_FOR_MEDIUM_LORA")

    def test_evaluate_model_quality_writes_before_after_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "eval_cases.jsonl"
            output_path = Path(tmp) / "before_after_summary.json"
            write_jsonl(
                input_path,
                [
                    {
                        "assistant_output": "Use fallback seguro, preserve o runtime e mantenha observabilidade auditável.",
                        "selected_strategy": "SAFE_FALLBACK",
                    }
                ],
            )
            with patch.object(sys, "argv", ["evaluate_model_quality.py", "--input", str(input_path), "--output", str(output_path)]):
                result = evaluate_model_quality_main()
            self.assertEqual(result, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("baseline", payload)

    def test_dataset_growth_report_counts_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "mixed_sft.jsonl"
            output_path = Path(tmp) / "growth.json"
            records = [
                {"source": "runtime_harvest", "task_family": "runtime", "language": "pt-BR"}
                for _ in range(120)
            ] + [
                {"source": "synthetic_controlled", "task_family": "governance", "language": "pt-BR"}
                for _ in range(30)
            ]
            write_jsonl(input_path, records)
            with patch.object(sys, "argv", ["dataset_growth_report.py", "--input", str(input_path), "--output", str(output_path)]):
                result = dataset_growth_report_main()
            self.assertEqual(result, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["progress_targets"]["100"])
            self.assertFalse(payload["progress_targets"]["300"])


if __name__ == "__main__":
    unittest.main()
