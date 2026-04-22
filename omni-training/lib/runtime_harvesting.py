from __future__ import annotations

from pathlib import Path
from typing import Any

from common import read_jsonl, write_jsonl
from dataset_enrichment import enrich_curated_example


HARVEST_EVENT_TYPES = {
    "runtime.decision.ranking.applied",
    "runtime.strategy.execution.result",
    "runtime.strategy.execution.fallback",
    "runtime.learning_integration.fallback",
    "runtime.manifest.summary",
}


def build_runtime_harvest_examples(project_root: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    log_path = project_root / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
    records = read_jsonl(log_path)
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(reversed(records), start=1):
        event_type = str(record.get("event_type", "") or "")
        if event_type not in HARVEST_EVENT_TYPES:
            continue
        payload = dict(record.get("payload") or {})
        fallback_occurred = bool(
            payload.get("fallback_triggered", False)
            or payload.get("strategy_execution_fallback", False)
            or payload.get("fallback_applied", False)
        )
        ambiguity_detected = bool(payload.get("ambiguity_detected", False))
        selected_strategy = str(payload.get("selected_strategy", "") or payload.get("deterministic_strategy", "")).strip()
        executor_used = str(payload.get("executor_used", "") or "").strip()
        user_input = str(payload.get("message_preview", "") or f"Analise o evento {event_type} do runtime Omni.").strip()
        context = str(payload.get("execution_trace_summary", "") or str(payload)[:1800]).strip()
        assistant_output = (
            "Explique a decisão operacional, preserve o fallback seguro quando necessário e proponha apenas ajustes auditáveis."
        )
        example = {
            "id": f"runtime-harvest-{index:05d}",
            "source": "runtime_harvest",
            "language": "pt-BR",
            "task_family": "runtime",
            "user_input": user_input,
            "context": context,
            "assistant_output": assistant_output,
            "selected_strategy": selected_strategy,
            "executor_used": executor_used,
            "execution_status": str(payload.get("strategy_execution_status", "") or payload.get("status", "")).strip(),
            "candidate_strategies": list(payload.get("candidate_strategies", []) or []),
            "review_status": "draft",
            "metadata": {
                "event_type": event_type,
                "session_id": str(record.get("session_id", "") or ""),
                "selected_strategy": selected_strategy,
                "executor_used": executor_used,
                "ambiguity_detected": ambiguity_detected,
                "fallback_occurred": fallback_occurred,
                "quality_candidate_flags": [
                    "runtime_signal",
                    "ambiguity_case" if ambiguity_detected else "non_ambiguous_case",
                    "fallback_case" if fallback_occurred else "stable_case",
                ],
            },
        }
        examples.append(enrich_curated_example(example))
        if len(examples) >= limit:
            break
    return list(reversed(examples))


def export_runtime_harvest(path: Path, examples: list[dict[str, Any]]) -> int:
    return write_jsonl(path, examples)
