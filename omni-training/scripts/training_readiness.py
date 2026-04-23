from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_jsonl, write_json  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess Omni dataset readiness for useful LoRA training.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "sft" / "mixed_sft.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "training_readiness.json"))
    parser.add_argument("--quality-threshold", type=float, default=0.7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_jsonl(Path(args.input))
    by_source: dict[str, int] = {}
    by_task_family: dict[str, int] = {}
    by_language: dict[str, int] = {}
    synthetic_count = 0
    runtime_count = 0
    approved_count = 0
    above_threshold = 0
    pt_br_count = 0
    for record in records:
        source = str(record.get("source", "") or "unknown")
        task_family = str(record.get("task_family", "") or "general")
        language = str(record.get("language", "") or "unknown")
        by_source[source] = int(by_source.get(source, 0)) + 1
        by_task_family[task_family] = int(by_task_family.get(task_family, 0)) + 1
        by_language[language] = int(by_language.get(language, 0)) + 1
        if language.lower() in {"pt", "pt-br"}:
            pt_br_count += 1
        if source == "synthetic_controlled":
            synthetic_count += 1
        if source in {"runtime_harvest", "runtime_feedback", "runtime_execution"} or source.startswith("runtime_"):
            runtime_count += 1
        if str(record.get("review_status", "") or "").strip().lower() in {"approved", "reviewed"}:
            approved_count += 1
        if float(record.get("quality_score", 0.0) or 0.0) >= args.quality_threshold:
            above_threshold += 1
    pt_br_ratio = round(pt_br_count / max(1, len(records)), 4)
    runtime_ratio = round(runtime_count / max(1, len(records)), 4)
    synthetic_ratio = round(synthetic_count / max(1, len(records)), 4)
    readiness = "NOT_READY"
    if len(records) >= 120 and above_threshold >= 80 and pt_br_ratio >= 0.55 and runtime_ratio >= 0.20:
        readiness = "READY_FOR_SMALL_LORA"
    if (
        len(records) >= 300
        and above_threshold >= 180
        and approved_count >= 80
        and pt_br_ratio >= 0.60
        and runtime_ratio >= 0.25
        and synthetic_ratio <= 0.20
    ):
        readiness = "READY_FOR_MEDIUM_LORA"
    payload = {
        "record_count": len(records),
        "by_source": by_source,
        "by_task_family": by_task_family,
        "by_language": by_language,
        "above_quality_threshold": above_threshold,
        "reviewed_or_approved": approved_count,
        "pt_br_ratio": pt_br_ratio,
        "runtime_ratio": runtime_ratio,
        "synthetic_ratio": synthetic_ratio,
        "synthetic_count": synthetic_count,
        "runtime_count": runtime_count,
        "readiness": readiness,
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
