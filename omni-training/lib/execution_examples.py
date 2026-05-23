from __future__ import annotations

from pathlib import Path
from typing import Any

from common import read_jsonl, write_jsonl
from dataset_weighting import derive_weight_fields


def build_execution_examples_from_runtime_logs(project_root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    log_path = project_root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
    records = read_jsonl(log_path)
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(reversed(records), start=1):
        event_type = str(record.get("event_type", "") or "")
        if event_type != "runtime.strategy.execution.result":
            continue
        payload = dict(record.get("payload") or {})
        selected_strategy = str(payload.get("selected_strategy", "") or "").strip()
        executor_used = str(payload.get("executor_used", "") or "").strip()
        if not selected_strategy:
            continue
        example = {
            "id": f"execution-example-{index:04d}",
            "source": "runtime_execution",
            "language": "pt-BR",
            "task_family": "runtime",
            "user_input": str(payload.get("message_preview", "Analise uma execução do runtime Omni.")).strip(),
            "context": str(payload.get("execution_trace_summary", "") or "").strip(),
            "assistant_output": str(payload.get("selected_strategy", "") or "").strip(),
            "selected_strategy": selected_strategy,
            "executor_used": executor_used,
            "execution_status": str(payload.get("strategy_execution_status", "") or "").strip() or "unknown",
            "strategy_trace_summary": str(payload.get("execution_trace_summary", "") or "").strip(),
            "candidate_strategies": list(payload.get("candidate_strategies", []) or []),
            "runtime_hints": {
                "strategy": selected_strategy,
                "requires_tools": selected_strategy in {"TOOL_ASSISTED", "NODE_RUNTIME_DELEGATION"},
                "requires_node_runtime": selected_strategy == "NODE_RUNTIME_DELEGATION",
                "fallback_allowed": True,
            },
            "metadata": {
                "event_type": event_type,
                "session_id": str(record.get("session_id", "") or ""),
                "ranking_source": str(payload.get("ranking_source", "") or ""),
                "manifest_driven_execution": bool(payload.get("manifest_driven_execution", False)),
                "strategy_execution_fallback": bool(payload.get("strategy_execution_fallback", False)),
            },
            "review_status": "draft",
        }
        example.update(derive_weight_fields(example))
        examples.append(example)
        if len(examples) >= limit:
            break
    return list(reversed(examples))


def export_execution_examples(path: Path, examples: list[dict[str, Any]]) -> int:
    return write_jsonl(path, examples)

