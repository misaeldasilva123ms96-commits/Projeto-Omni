from __future__ import annotations

from pathlib import Path
from typing import Any

from common import read_jsonl, write_jsonl
from dataset_weighting import derive_weight_fields


def build_ambiguity_examples_from_runtime_logs(project_root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    log_path = project_root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
    records = read_jsonl(log_path)
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(reversed(records), start=1):
        event_type = str(record.get("event_type", "") or "")
        payload = dict(record.get("payload") or {})
        if event_type not in {"runtime.decision.ranking.applied", "runtime.decision_ranking.fallback"}:
            continue
        candidate_strategies = [str(item) for item in payload.get("candidate_strategies", []) if str(item).strip()]
        if len(candidate_strategies) < 2:
            continue
        example = {
            "id": f"ambiguity-example-{index:04d}",
            "source": "runtime_ambiguity",
            "language": "pt-BR",
            "task_family": "runtime",
            "user_input": str(payload.get("message_preview", "Analise um caso ambíguo do runtime.")).strip(),
            "oil": dict(payload.get("oil_summary") or {}),
            "candidate_strategies": candidate_strategies,
            "selected_strategy": str(payload.get("selected_strategy", "") or payload.get("deterministic_strategy", "")).strip(),
            "decision_source": str(payload.get("decision_source", "rule") or "rule").strip(),
            "assistant_output": str(payload.get("selected_strategy", "") or "").strip() or "Escolha a estratégia mais segura e auditável.",
            "review_status": "draft",
            "metadata": {
                "session_id": str(record.get("session_id", "") or ""),
                "event_type": event_type,
                "ambiguity_score": float(payload.get("ambiguity_score", 0.0) or 0.0),
            },
        }
        example.update(derive_weight_fields(example))
        examples.append(example)
        if len(examples) >= limit:
            break
    return list(reversed(examples))


def export_ambiguity_examples(path: Path, examples: list[dict[str, Any]]) -> int:
    return write_jsonl(path, examples)

