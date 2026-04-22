from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_json, write_jsonl  # noqa: E402
from runtime_harvesting import build_runtime_harvest_examples  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest runtime examples into a training-ready JSONL queue.")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data" / "harvested" / "runtime_harvest.jsonl"))
    parser.add_argument("--report", default=str(Path(__file__).resolve().parents[1] / "reports" / "runtime_harvest_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_root = Path(__file__).resolve().parents[1]
    project_root = training_root.parents[0]
    records = build_runtime_harvest_examples(project_root, limit=max(1, int(args.limit)))
    output_path = resolve_training_path(args.output)
    report_path = resolve_training_path(args.report)
    write_jsonl(output_path, records)
    report = {
        "record_count": len(records),
        "output_path": str(output_path),
        "fallback_examples": sum(1 for item in records if bool(item.get("fallback_occurred", False))),
        "ambiguous_examples": sum(1 for item in records if bool((item.get("metadata") or {}).get("ambiguity_detected", False))),
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
