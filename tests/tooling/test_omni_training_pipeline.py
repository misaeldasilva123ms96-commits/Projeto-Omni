from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = PROJECT_ROOT / "omni-training" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dataset_pipeline import (  # noqa: E402
    build_prompt_text,
    filter_raw_records,
    load_normalization_rules,
    normalize_records,
    read_records,
    save_report,
    write_records,
)
from oil_adapter import convert_text_to_oil  # noqa: E402
from sft_builder import build_sft_record_from_curated, build_sft_record_from_public  # noqa: E402


class OmniTrainingPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_normalization_rules(PROJECT_ROOT / "omni-training" / "configs" / "normalization_rules.json")

    def test_filter_raw_records_discards_empty_examples(self) -> None:
        records = [
            {"instruction": "Explique OIL", "output": "OIL estrutura a intenção."},
            {"instruction": "", "output": "vazio"},
            {"instruction": "Planeje", "output": ""},
        ]
        filtered, stats = filter_raw_records(records, self.rules)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(stats["total_discarded"], 2)

    def test_normalize_records_produces_canonical_schema(self) -> None:
        raw = [{"instruction": "Explique o manifest", "input": "Use markdown", "output": "Resumo operacional."}]
        normalized, stats = normalize_records(raw, source="unit-test", rules=self.rules)
        self.assertEqual(stats["total_normalized"], 1)
        record = normalized[0]
        self.assertEqual(record["source"], "unit-test")
        self.assertEqual(record["instruction"], "Explique o manifest")
        self.assertEqual(record["task_family"], "runtime")
        self.assertIn("metadata", record)

    def test_convert_text_to_oil_returns_operational_shape(self) -> None:
        oil_payload = convert_text_to_oil("Crie um plano para melhorar o orchestrator")
        self.assertIn("user_intent", oil_payload)
        self.assertIn("desired_output", oil_payload)
        self.assertIn("execution_bias", oil_payload)

    def test_sft_builders_generate_prompt_text(self) -> None:
        public_record = {
            "id": "pub-1",
            "source": "public",
            "language": "pt",
            "task_family": "runtime",
            "instruction": "Explique OIL",
            "input": "Use exemplos curtos",
            "output": "OIL resume intenção e restrições.",
            "oil": convert_text_to_oil("Explique OIL com exemplos curtos"),
            "metadata": {},
        }
        public_sft = build_sft_record_from_public(public_record)
        self.assertIn("<|system|>", public_sft["text"])
        self.assertIn("OIL:", public_sft["text"])
        curated_record = {
            "id": "cur-1",
            "source": "internal_curated",
            "language": "pt-BR",
            "task_family": "planning",
            "user_input": "Planeje uma evolução segura",
            "context": "Use pequenos incrementos",
            "oil": convert_text_to_oil("Planeje uma evolução segura"),
            "runtime_hints": {"strategy": "MULTI_STEP_REASONING", "requires_tools": False, "requires_node_runtime": False, "fallback_allowed": True},
            "assistant_output": "Comece por contratos explícitos.",
            "quality_score": 0.9,
            "review_status": "approved",
        }
        curated_sft = build_sft_record_from_curated(curated_record)
        self.assertIn("Planeje uma evolução segura", curated_sft["prompt_text"])
        self.assertEqual(curated_sft["assistant_text"], "Comece por contratos explícitos.")

    def test_jsonl_round_trip_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            records = [{"id": "one", "value": 1}]
            jsonl_path = tmp_path / "records.jsonl"
            write_records(jsonl_path, records)
            loaded = read_records(jsonl_path)
            self.assertEqual(loaded, records)
            report_path = tmp_path / "reports" / "run.json"
            save_report(report_path, step="unit", source="test", stats={"count": 1})
            self.assertTrue(report_path.exists())

    def test_build_prompt_text_is_stable(self) -> None:
        prompt = build_prompt_text(
            instruction="Explique capability routing",
            input_text="Contexto Omni",
            oil_payload={"user_intent": "explain"},
        )
        self.assertIn("INPUT: Explique capability routing", prompt)
        self.assertIn("CONTEXT: Contexto Omni", prompt)


if __name__ == "__main__":
    unittest.main()
