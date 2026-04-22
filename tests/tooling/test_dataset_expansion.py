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

from common import write_json, write_jsonl  # noqa: E402
from curated_dataset_builder import build_curated_dataset  # noqa: E402
from dataset_mixer import build_mix_report, mix_dataset_records  # noqa: E402
from dataset_quality import quality_assessment  # noqa: E402
from source_ingestion import ingest_source, load_dataset_sources  # noqa: E402
from synthetic_examples import generate_synthetic_examples  # noqa: E402
from training_readiness import main as training_readiness_main  # noqa: E402
from evaluate_model_quality import main as evaluate_model_quality_main  # noqa: E402


class DatasetExpansionTest(unittest.TestCase):
    def test_load_dataset_sources_supports_sources_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "dataset_sources.json"
            write_json(
                config_path,
                {
                    "sources": [
                        {
                            "source_name": "local-demo",
                            "source_type": "local_jsonl",
                            "path": "demo.jsonl",
                            "enabled": True,
                        }
                    ]
                },
            )
            sources = load_dataset_sources(config_path)
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].source_name, "local-demo")

    def test_ingest_source_reads_local_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "demo.jsonl"
            write_jsonl(data_path, [{"id": "x", "instruction": "oi", "output": "ola"}])
            config_path = root / "dataset_sources.json"
            write_json(
                config_path,
                {"sources": [{"source_name": "local-demo", "source_type": "local_jsonl", "path": str(data_path), "enabled": True}]},
            )
            source = load_dataset_sources(config_path)[0]
            records = ingest_source(source, project_root=root)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["source"], "local-demo")

    def test_mix_dataset_records_respects_source_quota(self) -> None:
        records = [
            {"id": "a", "source": "synthetic_controlled", "language": "pt-BR", "task_family": "runtime", "quality_score": 0.9, "sample_weight": 1.5},
            {"id": "b", "source": "synthetic_controlled", "language": "pt-BR", "task_family": "runtime", "quality_score": 0.88, "sample_weight": 1.4},
            {"id": "c", "source": "internal_curated", "language": "pt-BR", "task_family": "coding", "quality_score": 0.95, "sample_weight": 1.8, "review_status": "approved"},
        ]
        mixed = mix_dataset_records(records, max_records=3, source_quota={"synthetic_controlled": 1})
        report = build_mix_report(mixed)
        self.assertEqual(report["by_source"]["synthetic_controlled"], 1)
        self.assertEqual(len(mixed), 2)

    def test_curated_dataset_builder_expands_seed(self) -> None:
        records = build_curated_dataset()
        self.assertGreaterEqual(len(records), 25)
        self.assertTrue(all(record["source"] == "internal_curated" for record in records))

    def test_quality_assessment_can_reject_generic_short_example(self) -> None:
        assessment = quality_assessment(
            {
                "instruction": "Explique isso",
                "output": "Depende do contexto.",
                "oil": {"user_intent": "explain"},
                "runtime_hints": {},
            }
        )
        self.assertIn(assessment["review_action"], {"review", "reject"})
        self.assertIn("generic_answer_risk", assessment["quality_flags"])

    def test_generate_synthetic_examples_marks_controlled_origin(self) -> None:
        records = generate_synthetic_examples(category="manifest_driven_cases", limit=4)
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["source"] == "synthetic_controlled" for record in records))

    def test_training_readiness_script_reports_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "mixed_sft.jsonl"
            output_path = Path(tmp) / "training_readiness.json"
            write_jsonl(
                input_path,
                [
                    {"source": "internal_curated", "task_family": "runtime", "language": "pt-BR", "quality_score": 0.9, "review_status": "approved"},
                    {"source": "runtime_harvest", "task_family": "coding", "language": "pt-BR", "quality_score": 0.8, "review_status": "reviewed"},
                ],
            )
            with patch.object(sys, "argv", ["training_readiness.py", "--input", str(input_path), "--output", str(output_path)]):
                result = training_readiness_main()
            self.assertEqual(result, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["record_count"], 2)

    def test_evaluate_model_quality_baseline_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "eval_cases.jsonl"
            output_path = Path(tmp) / "model_quality.json"
            write_jsonl(
                input_path,
                [
                    {
                        "assistant_output": "Use fallback seguro e mantenha observabilidade do runtime.",
                        "selected_strategy": "SAFE_FALLBACK",
                        "runtime_hints": {"strategy": "SAFE_FALLBACK"},
                    }
                ],
            )
            with patch.object(sys, "argv", ["evaluate_model_quality.py", "--input", str(input_path), "--output", str(output_path)]):
                result = evaluate_model_quality_main()
            self.assertEqual(result, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_count"], 1)
            self.assertFalse(payload["adapter_available"])


if __name__ == "__main__":
    unittest.main()
