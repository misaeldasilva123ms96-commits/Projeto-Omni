from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_jsonl, write_json  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Omni dataset growth across sources and milestones.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "sft" / "mixed_sft.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "dataset_growth_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = resolve_training_path(args.input)
    output_path = resolve_training_path(args.output)
    records = read_jsonl(input_path)
    total = len(records)
    by_source: dict[str, int] = {}
    by_task: dict[str, int] = {}
    pt_count = 0
    synthetic_count = 0
    runtime_count = 0
    for record in records:
        source = str(record.get("source", "") or "unknown")
        task = str(record.get("task_family", "") or "general")
        by_source[source] = by_source.get(source, 0) + 1
        by_task[task] = by_task.get(task, 0) + 1
        language = str(record.get("language", "") or "")
        if language.lower() in {"pt", "pt-br"}:
            pt_count += 1
        if source == "synthetic_controlled":
            synthetic_count += 1
        if source.startswith("runtime_") or source == "runtime_feedback":
            runtime_count += 1
    payload = {
        "total_examples": total,
        "examples_by_source": by_source,
        "examples_by_task": by_task,
        "pt_br_ratio": round(pt_count / max(1, total), 4),
        "synthetic_ratio": round(synthetic_count / max(1, total), 4),
        "runtime_ratio": round(runtime_count / max(1, total), 4),
        "progress_targets": {
            "100": total >= 100,
            "300": total >= 300,
            "500": total >= 500,
            "1000": total >= 1000,
        },
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
