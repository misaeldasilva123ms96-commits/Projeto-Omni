from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = PROJECT_ROOT / "omni-training" / "lib"
SCRIPTS_DIR = PROJECT_ROOT / "omni-training" / "scripts"
for candidate in (LIB_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from auto_curate import build_report, classify_prediction  # noqa: E402
from common import write_jsonl  # noqa: E402
from dataset_enrichment import enrich_curated_example, enrich_public_record  # noqa: E402
from dataset_quality import evaluate_dataset_records, find_duplicate_groups, quality_score  # noqa: E402
from feedback_loop import build_feedback_examples_from_runtime_logs, export_feedback_examples  # noqa: E402


class OmniTrainingDatasetEvolutionTest(unittest.TestCase):
    def test_quality_score_rewards_structured_examples(self) -> None:
        example = {
            "id": "cur-1",
            "task_family": "runtime",
            "user_input": "Explique como o fallback deve funcionar.",
            "assistant_output": "O fallback deve preservar o caminho determinístico, registrar observabilidade e manter compatibilidade.",
            "oil": {
                "user_intent": "explain",
                "entities": {},
                "constraints": {},
                "desired_output": "explanation",
                "urgency": "medium",
                "execution_bias": "balanced",
                "memory_relevance": "high",
            },
            "runtime_hints": {
                "strategy": "SAFE_FALLBACK",
                "requires_tools": False,
                "requires_node_runtime": False,
                "fallback_allowed": True,
            },
            "review_status": "approved",
        }
        self.assertGreaterEqual(quality_score(example), 0.8)

    def test_enrichment_adds_oil_and_runtime_hints(self) -> None:
        curated = enrich_curated_example(
            {
                "id": "seed-x",
                "source": "internal_curated",
                "language": "pt-BR",
                "task_family": "planning",
                "user_input": "Planeje a evolução do runtime.",
                "context": "Use etapas pequenas.",
                "assistant_output": "Comece pelo contrato e depois integre com fallback.",
            }
        )
        self.assertIn("oil", curated)
        self.assertIn("runtime_hints", curated)
        public = enrich_public_record(
            {
                "id": "pub-x",
                "source": "public",
                "language": "pt",
                "task_family": "analysis",
                "instruction": "Analise o registry",
                "input": "",
                "output": "O registry deve expor metadata adicional.",
            }
        )
        self.assertIn("quality_score", public)

    def test_duplicate_groups_detect_duplicates(self) -> None:
        records = [
            {"id": "a", "instruction": "Explique OIL", "output": "OIL estrutura intenção."},
            {"id": "b", "instruction": "Explique OIL", "output": "OIL estrutura intenção."},
            {"id": "c", "instruction": "Explique routing", "output": "Routing escolhe estratégia."},
        ]
        groups = find_duplicate_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(groups[0]), {"a", "b"})

    def test_feedback_loop_builds_examples_from_runtime_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
            write_jsonl(
                log_path,
                [
                    {
                        "event_type": "runtime.learning_integration.fallback",
                        "session_id": "s1",
                        "payload": {"reason": "adapter_missing"},
                    }
                ],
            )
            examples = build_feedback_examples_from_runtime_logs(root, limit=5)
            self.assertEqual(len(examples), 1)
            output_path = root / "feedback.jsonl"
            export_feedback_examples(output_path, examples)
            self.assertTrue(output_path.exists())

    def test_auto_curate_report_and_classification_work(self) -> None:
        records = [
            {
                "id": "seed-1",
                "source": "internal_curated",
                "language": "pt-BR",
                "task_family": "runtime",
                "user_input": "Explique o fallback do runtime.",
                "context": "Compatibilidade forte.",
                "assistant_output": "O fallback deve preservar o caminho determinístico e registrar observabilidade.",
                "oil": {
                    "user_intent": "explain",
                    "entities": {},
                    "constraints": {},
                    "desired_output": "explanation",
                    "urgency": "medium",
                    "execution_bias": "balanced",
                    "memory_relevance": "high",
                },
                "runtime_hints": {
                    "strategy": "SAFE_FALLBACK",
                    "requires_tools": False,
                    "requires_node_runtime": False,
                    "fallback_allowed": True,
                },
            }
        ]
        report = build_report(records, engine=None, max_samples=5)
        self.assertEqual(report["total_examples"], 1)
        self.assertIn(report["items"][0]["status"], {"good", "weak", "incorrect"})
        self.assertEqual(classify_prediction("resposta boa", "resposta boa"), "good")

    def test_evaluate_dataset_records_returns_metrics(self) -> None:
        metrics = evaluate_dataset_records(
            [
                {
                    "id": "x",
                    "user_input": "Explique observabilidade.",
                    "assistant_output": "A observabilidade registra sinais auditáveis e seguros para o runtime.",
                    "oil": {
                        "user_intent": "explain",
                        "entities": {},
                        "constraints": {},
                        "desired_output": "explanation",
                        "urgency": "medium",
                        "execution_bias": "balanced",
                        "memory_relevance": "high",
                    },
                    "runtime_hints": {
                        "strategy": "DIRECT_RESPONSE",
                        "requires_tools": False,
                        "requires_node_runtime": False,
                        "fallback_allowed": True,
                    },
                }
            ]
        )
        self.assertEqual(metrics["record_count"], 1)
        self.assertGreater(metrics["average_quality_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
