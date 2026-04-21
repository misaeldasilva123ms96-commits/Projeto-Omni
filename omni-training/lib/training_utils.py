from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_sft_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


def format_training_examples(records: list[dict[str, Any]], *, max_samples: int | None = None) -> list[dict[str, str]]:
    limited = records[:max_samples] if isinstance(max_samples, int) and max_samples > 0 else records
    return [{"text": str(record.get("text", "")).strip()} for record in limited if str(record.get("text", "")).strip()]


def validate_training_config(training_config: dict[str, Any], lora_config: dict[str, Any]) -> None:
    required_training = ("base_model", "dataset_path", "output_dir", "num_train_epochs", "learning_rate")
    required_lora = ("r", "lora_alpha", "lora_dropout", "task_type")
    missing_training = [key for key in required_training if key not in training_config]
    missing_lora = [key for key in required_lora if key not in lora_config]
    if missing_training:
        raise ValueError(f"missing training config keys: {missing_training}")
    if missing_lora:
        raise ValueError(f"missing LoRA config keys: {missing_lora}")
