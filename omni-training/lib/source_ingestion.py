from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import read_json, read_jsonl
from feedback_loop import build_feedback_examples_from_runtime_logs


@dataclass(slots=True)
class DatasetSource:
    source_name: str
    source_type: str
    enabled: bool
    license_hint: str = ""
    language_hint: str = "unknown"
    max_samples: int = 0
    task_family_hint: str = "general"
    dataset_name: str = ""
    dataset_config: str = ""
    split: str = ""
    revision: str = ""
    path: str = ""
    notes: str = ""
    metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_dataset_sources(path: Path) -> list[DatasetSource]:
    payload = read_json(path)
    if isinstance(payload, dict) and "sources" in payload:
        items = list(payload.get("sources", []) or [])
    elif isinstance(payload, dict):
        items = []
        for key, value in payload.items():
            if isinstance(value, dict):
                items.append({"source_name": key, **value})
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    sources: list[DatasetSource] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sources.append(
            DatasetSource(
                source_name=str(item.get("source_name", "") or "").strip(),
                source_type=str(item.get("source_type", "") or "").strip(),
                enabled=bool(item.get("enabled", True)),
                license_hint=str(item.get("license_hint", "") or "").strip(),
                language_hint=str(item.get("language_hint", "unknown") or "unknown").strip(),
                max_samples=int(item.get("max_samples", 0) or 0),
                task_family_hint=str(item.get("task_family_hint", "general") or "general").strip(),
                dataset_name=str(item.get("dataset_name", "") or "").strip(),
                dataset_config=str(item.get("dataset_config", "") or "").strip(),
                split=str(item.get("split", "") or "").strip(),
                revision=str(item.get("revision", "") or "").strip(),
                path=str(item.get("path", "") or "").strip(),
                notes=str(item.get("notes", "") or "").strip(),
                metadata=dict(item.get("metadata") or {}),
            )
        )
    return sources


def _apply_source_metadata(records: list[dict[str, Any]], source: DatasetSource) -> list[dict[str, Any]]:
    limited = records[: source.max_samples] if source.max_samples > 0 else records
    output: list[dict[str, Any]] = []
    for index, record in enumerate(limited, start=1):
        enriched = dict(record)
        metadata = dict(enriched.get("metadata") or {})
        metadata.setdefault("source_name", source.source_name)
        metadata.setdefault("license_hint", source.license_hint)
        metadata.setdefault("source_type", source.source_type)
        enriched["metadata"] = metadata
        enriched.setdefault("source", source.source_name)
        enriched.setdefault("language", source.language_hint)
        enriched.setdefault("task_family", source.task_family_hint)
        enriched.setdefault("id", f"{source.source_name}-{index:06d}")
        output.append(enriched)
    return output


def ingest_source(source: DatasetSource, *, project_root: Path) -> list[dict[str, Any]]:
    if not source.enabled:
        return []
    if source.source_type == "local_jsonl":
        path = Path(source.path)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        return _apply_source_metadata(read_jsonl(path), source)
    if source.source_type == "curated":
        path = Path(source.path)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        return _apply_source_metadata(read_jsonl(path), source)
    if source.source_type == "runtime_logs":
        return _apply_source_metadata(
            build_feedback_examples_from_runtime_logs(project_root, limit=source.max_samples or 25),
            source,
        )
    if source.source_type == "hf":
        try:
            from datasets import load_dataset
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"datasets library is required for HF ingestion: {exc}") from exc
        dataset = load_dataset(
            source.dataset_name,
            name=source.dataset_config or None,
            split=source.split or "train[:64]",
            revision=source.revision or None,
            streaming=False,
        )
        return _apply_source_metadata([dict(row) for row in dataset], source)
    return []


def group_sources_by_type(sources: list[DatasetSource]) -> dict[str, list[DatasetSource]]:
    grouped: dict[str, list[DatasetSource]] = {}
    for source in sources:
        grouped.setdefault(source.source_type, []).append(source)
    return grouped
