from __future__ import annotations

from pathlib import Path
from typing import Any

from common import read_jsonl, write_jsonl
from dataset_enrichment import enrich_curated_example


def _runtime_log_path(project_root: Path) -> Path:
    return project_root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"


def build_feedback_examples_from_runtime_logs(project_root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    records = read_jsonl(_runtime_log_path(project_root))
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(reversed(records), start=1):
        event_type = str(record.get("event_type", "") or "")
        payload = dict(record.get("payload") or {})
        if event_type not in {
            "runtime.upgrade.fallback",
            "runtime.learning_integration.fallback",
            "runtime.manifest.summary",
        }:
            continue
        user_input = f"Analise o evento {event_type} e proponha um ajuste de runtime."
        context = str(payload)[:1800]
        assistant_output = (
            "Revise os sinais observados, preserve o caminho determinístico existente e "
            "adicione um fallback curto e auditável antes de ampliar o comportamento."
        )
        example = {
            "id": f"feedback-{index:04d}",
            "source": "runtime_feedback",
            "language": "pt-BR",
            "task_family": "runtime",
            "user_input": user_input,
            "context": context,
            "assistant_output": assistant_output,
            "review_status": "draft",
            "quality_score": 0.0,
            "metadata": {
                "event_type": event_type,
                "session_id": str(record.get("session_id", "") or ""),
            },
        }
        examples.append(enrich_curated_example(example))
        if len(examples) >= limit:
            break
    return list(reversed(examples))


def export_feedback_examples(path: Path, examples: list[dict[str, Any]]) -> int:
    return write_jsonl(path, examples)

