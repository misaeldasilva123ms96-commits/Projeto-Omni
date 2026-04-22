from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRAINING_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TRAINING_ROOT.parents[0]


def load_json_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_training_path(path_value: str | Path) -> Path:
    raw = Path(path_value)
    if raw.is_absolute():
        return raw
    candidates = (
        (PROJECT_ROOT / raw).resolve(),
        (TRAINING_ROOT / raw).resolve(),
        raw.resolve(),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_sft_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    resolved_path = resolve_training_path(path)
    for line in resolved_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


def format_training_examples(records: list[dict[str, Any]], *, max_samples: int | None = None) -> list[dict[str, Any]]:
    limited = records[:max_samples] if isinstance(max_samples, int) and max_samples > 0 else records
    formatted: list[dict[str, Any]] = []
    for record in limited:
        text = str(record.get("text", "")).strip()
        if not text:
            continue
        formatted.append(
            {
                "text": text,
                "weight": float(record.get("sample_weight", 1.0) or 1.0),
                "quality_score": float(record.get("quality_score", 0.0) or 0.0),
                "selected_strategy": str(record.get("selected_strategy", "") or ""),
                "executor_used": str(record.get("executor_used", "") or ""),
                "execution_status": str(record.get("execution_status", "") or ""),
            }
        )
    return formatted


def validate_training_config(training_config: dict[str, Any], lora_config: dict[str, Any]) -> None:
    required_training = ("base_model", "dataset_path", "output_dir", "num_train_epochs", "learning_rate")
    required_lora = ("r", "lora_alpha", "lora_dropout", "task_type")
    missing_training = [key for key in required_training if key not in training_config]
    missing_lora = [key for key in required_lora if key not in lora_config]
    if missing_training:
        raise ValueError(f"missing training config keys: {missing_training}")
    if missing_lora:
        raise ValueError(f"missing LoRA config keys: {missing_lora}")
