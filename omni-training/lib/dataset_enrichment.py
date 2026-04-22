from __future__ import annotations

from typing import Any

from dataset_quality import quality_score
from oil_adapter import convert_text_to_oil
from sft_builder import runtime_hints_from_oil


def _combined_text(example: dict[str, Any]) -> str:
    return " ".join(
        part.strip()
        for part in (
            str(example.get("instruction", "")),
            str(example.get("input", "")),
            str(example.get("user_input", "")),
            str(example.get("context", "")),
        )
        if str(part).strip()
    ).strip()


def enrich_curated_example(example: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(example)
    text = _combined_text(enriched)
    oil_payload = dict(enriched.get("oil") or {})
    if not oil_payload or not str(oil_payload.get("user_intent", "")).strip():
        oil_payload = convert_text_to_oil(text, session_id="omni-curated")
    task_family = str(enriched.get("task_family", "analysis") or "analysis")
    runtime_hints = dict(enriched.get("runtime_hints") or {})
    if not runtime_hints:
        runtime_hints = runtime_hints_from_oil(oil_payload, task_family)
    metadata = dict(enriched.get("metadata") or {})
    metadata.setdefault("dataset_origin", "curated_internal")
    enriched["oil"] = oil_payload
    enriched["runtime_hints"] = runtime_hints
    enriched["metadata"] = metadata
    enriched["quality_score"] = max(float(enriched.get("quality_score", 0.0) or 0.0), quality_score(enriched))
    return enriched


def enrich_public_record(record: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(record)
    text = _combined_text(enriched)
    oil_payload = dict(enriched.get("oil") or {})
    if not oil_payload or not str(oil_payload.get("user_intent", "")).strip():
        oil_payload = convert_text_to_oil(text, session_id="omni-public")
    metadata = dict(enriched.get("metadata") or {})
    metadata.setdefault("dataset_origin", str(enriched.get("source", "external_dataset") or "external_dataset"))
    enriched["oil"] = oil_payload
    enriched["runtime_hints"] = runtime_hints_from_oil(oil_payload, str(enriched.get("task_family", "general") or "general"))
    enriched["metadata"] = metadata
    enriched["quality_score"] = quality_score(enriched)
    return enriched


def enrich_records(records: list[dict[str, Any]], *, curated: bool) -> list[dict[str, Any]]:
    if curated:
        return [enrich_curated_example(record) for record in records]
    return [enrich_public_record(record) for record in records]

